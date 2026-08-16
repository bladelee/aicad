"""FreeCADBackend — 主后端：FreeCAD BIM + Arch Space 房间识别。

实现 FloorplanBackend 接口。在容器内的 FreeCAD 进程里运行
（通过 freecad-ai 的 user_tools 机制加载）。

关键链路（Phase 0 要验证）：
    DWG →(ODA)→ DXF →(importDXF)→ 裸 LINE/LWPOLYLINE
        →(按墙图层关键词过滤)→ Draft.draftify 成墙
        →(Arch.makeSpace)→ 房间

⚠️ 修正 v2 §11.2 的天真错误：不能直接 makeSpace，
   必须先把 importDXF 进来的 LINE draftify 成墙。
"""

from __future__ import annotations
import os
import re
import shutil
import subprocess
import math
from typing import Any

from ._safety import make_backup, with_transaction


# ─── 关键词表（来源：v1 cad_tools/blocks.py，已 bake 进此处单一真源；v1 已归档 cad_tools.archived/）───
# 注：v1 的 cad_tools/ 已归档（cad_tools.archived/），本表是单一真源。
WALL_KEYWORDS = ("WALL", "墙", "WALLS", "W-WALL")
DOOR_KEYWORDS = ("DOOR", "门", "M_", "D_")
WINDOW_KEYWORDS = ("WINDOW", "窗", "W_", "WIN")
# 注意 v1 linter 风险：W_/D_ 短前缀可能误命中（BUILD_1800/W_POOL 等）—— Phase 1 加用户配置 + 三维特征缓解

FURNITURE_KEYWORDS = {
    "sofa": ("SOFA", "沙发", "COUCH", "SEATING"),
    "bed": ("BED", "床", "MATTRESS"),
    "table": ("TABLE", "桌", "DESK", "台"),
    "chair": ("CHAIR", "椅", "SEAT"),
    "tv": ("TV", "电视", "TELEVISION", "SCREEN"),
    "fridge": ("FRIDGE", "冰箱", "REFRIGERATOR"),
    "washer": ("WASH", "洗", "WASHER", "LAUNDRY"),
    "toilet": ("TOILET", "马桶", "WC"),  # 注：v1 含 CLOSET，但易与衣柜 CLOSET 撞，故不共用
    "bathtub": ("BATHTUB", "浴", "TUB", "BATH"),
    "sink": ("SINK", "盆", "BASIN", "LAVATORY"),
    "stove": ("STOVE", "灶", "COOKTOP", "RANGE"),
    "wardrobe": ("WARDROBE", "柜", "CABINET"),
    "kitchen": ("KITCHEN", "厨", "COUNTER"),
    "aircon": ("AC", "空调", "AIRCON", "AIR_CONDITIONER"),
}


def _classify(name: str) -> str:
    """块名 → 类型分类。

    顺序很重要：先匹配细粒度家具类型（具体），最后才兜底到门/窗（关键词含
    "D_"/"W_" 这种短前缀，会把 BED_1800 误判为门 —— 见 test_classify_block_name）。
    真实 Phase 1 解决方案：用块几何 + 名称 + 图层三维特征 + 用户配置映射表，
    不靠单关键词（见 方案-F2 §1.2 P2 风险）。
    """
    up = name.upper()
    # 先匹配具体家具（命中任一即返回，避免被门/窗短前缀抢走）
    for ftype, kws in FURNITURE_KEYWORDS.items():
        if any(k.upper() in up for k in kws):
            return ftype
    # 再判门/窗（仍会有 W_ 误命中 WORK 等，待 Phase 1 映射表缓解）
    if any(k in up for k in DOOR_KEYWORDS):
        return "door"
    if any(k in up for k in WINDOW_KEYWORDS):
        return "window"
    return "unknown"


class FreeCADBackend:
    """主后端。所有 FreeCAD import 都在方法内（无 FreeCAD 也能 import 此模块）。"""

    def __init__(self):
        self._doc_cache: dict[str, Any] = {}

    # ─── 公共接口 ───

    def read(self, path: str) -> dict:
        doc = self._open(path)
        walls = self._extract_walls(doc)
        doors, windows, furniture = self._extract_blocks(doc)
        rooms = self._detect_rooms(doc, walls, furniture)
        layers = self._layers(doc)
        return {
            "layers": layers,
            "walls": [w.to_summary() for w in walls],
            "doors": [d.to_summary() for d in doors],
            "windows": [w.to_summary() for w in windows],
            "furniture": [f.to_summary() for f in furniture],
            "rooms": rooms,
            "summary": {
                "wall_count": len(walls),
                "door_count": len(doors),
                "window_count": len(windows),
                "furniture_count": len(furniture),
                "room_count": len(rooms),
                "total_area_m2": round(sum(r["area_m2"] for r in rooms), 2),
            },
        }

    def list_rooms(self, path: str) -> list[dict]:
        return self.read(path)["rooms"]

    def move_entity(self, path, handle, dx_mm, dy_mm, auto_backup=True):
        doc = self._open(path)

        def do(d):
            obj = self._find_by_handle(d, handle)
            if obj is None:
                raise ValueError(f"实体 {handle} 未找到")
            import FreeCAD as App
            base = obj.Placement.Base
            obj.Placement.Base = App.Vector(base.x + dx_mm, base.y + dy_mm, base.z)
            return {"handle": handle, "new_position_xy": [base.x + dx_mm, base.y + dy_mm]}

        res = with_transaction(doc, f"Move {handle}", do,
                               save_path=path, auto_backup=auto_backup)
        if not res["ok"]:
            return {"ok": False, "error": res["error"]}
        return {
            "ok": True,
            "backup_path": res["backup_path"],
            "data": res["data"],
        }

    def render_preview(self, path, output_png, highlight_handles=None):
        # headless：用 QT_QPA_PLATFORM=offscreen（已在容器内 env 设好）
        # 渲染用抓取 model space 视图的方式，避免 v1 layer.off() 的破坏性副作用
        doc = self._open(path)
        import FreeCAD as App
        import FreeCADGui as Gui
        Gui.show(doc.Name)  # headless offscreen 下也能创建 view
        view = Gui.ActiveDocument.ActiveView
        if highlight_handles:
            Gui.Selection.clearSelection()
            for h in highlight_handles:
                obj = self._find_by_handle(doc, h)
                if obj:
                    Gui.Selection.addSelection(obj)
        view.viewAxonometric()
        view.fitAll()
        view.saveImage(output_png, 1600, 1200, "Current")
        return output_png

    def export(self, path, target_format, acad_version="ACAD2018"):
        target_format = target_format.lower()
        if target_format == "dxf":
            # FreeCAD 原生
            doc = self._open(path)
            out = path.rsplit(".", 1)[0] + ".export.dxf"
            import importDXF
            importDXF.export(doc.Objects, out)
            return out
        if target_format == "dwg":
            return _oda_convert(path, to_dxf=False, acad_version=acad_version)
        if target_format == "pdf":
            return _export_pdf(path)
        raise ValueError(f"不支持的格式: {target_format}")

    # ─── 内部 ───

    def _open(self, path: str):
        """打开或转换出 DXF，import 到 FreeCAD 文档。结果按 path 缓存。"""
        import FreeCAD as App
        if path in self._doc_cache:
            doc = self._doc_cache[path]
            return doc
        dxf = self._ensure_dxf(path)
        doc = App.open(dxf)
        doc.recompute()
        self._doc_cache[path] = doc
        return doc

    @staticmethod
    def _ensure_dxf(path: str) -> str:
        """DWG→DXF（如需要）；DXF 原样返回。"""
        if path.lower().endswith(".dxf"):
            return path
        return _oda_convert(path, to_dxf=True)

    @staticmethod
    def _layers(doc) -> list[dict]:
        out = []
        try:
            import FreeCAD as App
            for layer_name in doc.LayerListInstance.LayerNames if hasattr(doc, "LayerListInstance") else []:
                out.append({"name": layer_name})
        except Exception:
            pass
        return out

    @staticmethod
    def _extract_walls(doc):
        """按 WALL_KEYWORDS 抽墙（importDXF 后是 Draft 线/多段线）。"""
        import Draft
        walls = []
        for obj in doc.Objects:
            label = (getattr(obj, "Label", "") or obj.Name).upper()
            if not any(k in label for k in WALL_KEYWORDS):
                continue
            walls.append(_Wall.from_obj(obj))
        return walls

    @staticmethod
    def _extract_blocks(doc):
        """insert 块引用 → 门/窗/家具分类。"""
        import re
        doors, windows, furniture = [], [], []
        for obj in doc.Objects:
            if not hasattr(obj, "BlockName") and "block" not in (obj.Name or "").lower():
                continue
            name = getattr(obj, "BlockName", obj.Name or "")
            ftype = _classify(name)
            item = _Block.from_obj(obj, ftype)
            if ftype == "door":
                doors.append(item)
            elif ftype == "window":
                windows.append(item)
            elif ftype != "unknown":
                furniture.append(item)
        return doors, windows, furniture

    @staticmethod
    def _detect_rooms(doc, walls, furniture):
        """调共享 shapely 算法，与 EzdxfBackend 同源。

        ⚠️ 之前（v0 骨架）走 Arch.makeSpace 只产生 1 个总空间，无法分多房间。
        现统一交给 shapely polygonize（见 backends/rooms_detect.py），让
        主备 backend 房间数永远一致。已在 7 个边界用例上验证可靠。

        Arch Space 留作 Phase 3 3D 联动或疑难图的备选路径。
        """
        from .rooms_detect import detect_rooms
        # 把 _Wall 转成共享函数要的 ((x1,y1),(x2,y2)) 格式
        segs = []
        for w in walls:
            coords = w.coords_mm
            for i in range(len(coords) - 1):
                if len(coords[i]) >= 2 and len(coords[i + 1]) >= 2:
                    segs.append((coords[i], coords[i + 1]))
        # furniture 是 _Block 对象，转 dict
        fur_dicts = [{"block": f.summary["block"],
                       "position_xy": f.summary["position_xy"]}
                      for f in furniture]
        # close_openings_mm=1000: 真实装修图门洞/窗洞续断墙线，需补虚拟墙才能闭合
        return detect_rooms(segs, furniture=fur_dicts, close_openings_mm=1000.0)

    @staticmethod
    def _find_by_handle(doc, handle: str):
        """按 handle（如 "1A2F"）找对象，找不到回 None。

        FreeCAD 的 handle 通过 obj.LinkedObject 或 dxf attrs 拿，
        这里先做名字/handle 二选一的兜底。
        """
        # 方式 1: Name 直接匹配
        for obj in doc.Objects:
            if obj.Name == handle:
                return obj
        # 方式 2: block_name#idx 形式
        m = re.match(r"^(.+)#(\d+)$", handle)
        if m:
            block, idx = m.group(1), int(m.group(2))
            matches = [o for o in doc.Objects
                       if getattr(o, "BlockName", o.Name) == block]
            if 0 <= idx - 1 < len(matches):
                return matches[idx - 1]
        return None


class _Wall:
    def __init__(self, obj, coords_mm, length_mm, closed):
        self.obj = obj
        self.coords_mm = coords_mm
        self.length_mm = length_mm
        self.closed = closed

    @classmethod
    def from_obj(cls, obj):
        # importDXF 后通常是 Draft Line / DWire
        pts = []
        try:
            import Draft
            geo = obj.Shape
            for v in geo.Vertexes:
                pts.append([v.X, v.Y])
        except Exception:
            pass
        length = 0.0
        for i in range(len(pts) - 1):
            length += math.hypot(pts[i + 1][0] - pts[i][0],
                                 pts[i + 1][1] - pts[i][1])
        return cls(obj, pts, length, len(pts) > 2 and pts[0] == pts[-1])

    @property
    def summary(self):
        return {
            "layer": getattr(self.obj, "Label", self.obj.Name),
            "coords_mm": self.coords_mm,
            "length_mm": round(self.length_mm, 1),
            "closed": self.closed,
        }

    def to_summary(self):
        return self.summary


class _Block:
    def __init__(self, obj, ftype):
        self.obj = obj
        self.summary = {
            "block": getattr(obj, "BlockName", obj.Name),
            "type": ftype,
            "position_xy": [obj.Placement.Base.x, obj.Placement.Base.y],
            "rotation_deg": obj.Placement.Rotation.Angle * 180 / 3.14159265,
            "layer": getattr(obj, "Label", obj.Name),
        }

    @classmethod
    def from_obj(cls, obj, ftype):
        return cls(obj, ftype)

    def to_summary(self):
        return self.summary


# ─── ODA File Converter 封装（合规：不打包进镜像，运行时调宿主/容器装的）───

def _oda_convert(path: str, to_dxf: bool, acad_version: str = "ACAD2018") -> str:
    """调 ODA File Converter 转换 DWG↔DXF。"""
    oda = os.environ.get("ODA_FILE_CONVERTER", "ODAFileConverter")
    in_dir = os.path.dirname(os.path.abspath(path))
    out_dir = in_dir
    ext = "DXF" if to_dxf else "DWG"
    cmd = [oda, in_dir, out_dir, acad_version, "0", "1", ext]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"ODA 转换失败: {r.stderr}")
    out = os.path.splitext(path)[0] + ("." + ext.lower())
    return out


def _export_pdf(path: str) -> str:
    """占位：用 FreeCAD 的 TechDraw 导 PDF（Phase 1 实现）。"""
    raise NotImplementedError("PDF export 在 Phase 1 实现")
