"""EzdxfBackend — 备选：纯 ezdxf + shapely polygonize 房间识别。

触发条件（Phase 0）：FreeCADBackend 的 Arch Space 在真实图上
房间识别准确率 < 70% → 切此 backend（容器/客户端网络零修改，只换 env）。

与 FreeCADBackend 同接口（FloorplanBackend），差异在：
  - 房间识别用 shapely polygonize（planar-graph face detection，与 Arch Space 同源）
  - 修改用 ezdxf 直接改 DXF
  - 渲染用 ezdxf + matplotlib（修 v1 renderer 破图层 bug）
  - DWG↔DXF 仍走 ODA
"""

from __future__ import annotations
import os
import shutil
import subprocess
from typing import Any

from ._safety import make_backup


class EzdxfBackend:
    """备选后端骨架。Phase 0 触发时真正实现，现仅占位跑通链路。"""

    def __init__(self):
        self._doc_cache: dict[str, Any] = {}

    def read(self, path: str) -> dict:
        import ezdxf
        dxf = self._ensure_dxf(path)
        doc = ezdxf.readfile(dxf)
        msp = doc.modelspace()
        walls = self._extract_walls(msp)
        doors, windows, furniture = self._extract_blocks(msp)
        rooms = self._detect_rooms(walls, furniture)
        return {
            "layers": [{"name": l.dxf.name} for l in doc.layers],
            "walls": walls,
            "doors": doors,
            "windows": windows,
            "furniture": furniture,
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
        import ezdxf
        dxf = self._ensure_dxf(path)
        backup = make_backup(dxf, max_keep=10) if auto_backup else None
        doc = ezdxf.readfile(dxf)
        msp = doc.modelspace()
        # ezdxf 的实体的 dxf.handle 直接是 handle 属性
        from ezdxf.math import Vec3
        moved = False
        for ent in msp.query("INSERT"):
            if ent.dxf.handle == handle or ent.dxf.name == handle:
                ent.dxf.insert = Vec3(ent.dxf.insert.x + dx_mm,
                                      ent.dxf.insert.y + dy_mm, 0)
                moved = True
                break
        if not moved:
            return {"ok": False, "error": f"实体 {handle} 未找到"}
        doc.saveas(dxf)
        return {"ok": True, "backup_path": backup,
                "data": {"handle": handle, "delta_xy_mm": [dx_mm, dy_mm]}}

    def render_preview(self, path, output_png, highlight_handles=None):
        # 修复 v1 renderer 破图层 bug：用 RenderContext 副本，不动原图层
        import ezdxf
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        dxf = self._ensure_dxf(path)
        doc = ezdxf.readfile(dxf)
        fig = plt.figure(figsize=(20, 15))
        ax = fig.add_subplot(111)
        ctx = RenderContext(doc)  # 不论怎么用都不污染 doc
        backend = MatplotlibBackend(ax)
        Frontend(ctx, backend).draw_layout(doc.modelspace())
        if highlight_handles:
            for h in highlight_handles:
                for ent in doc.modelspace():
                    if ent.dxf.handle == h:
                        self._highlight(ax, ent)
                        break
        ax.set_aspect("equal")
        ax.autoscale()
        ax.axis("off")
        fig.savefig(output_png, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return output_png

    @staticmethod
    def _highlight(ax, ent):
        import ezdxf.enums
        if ent.dxftype() == "INSERT":
            return  # 简化：高亮实体类型支持可后扩
        try:
            for gp in ent.get_graphical_path():
                xs = [p[0] for p in gp]
                ys = [p[1] for p in gp]
                ax.plot(xs, ys, color="red", linewidth=3, alpha=0.6)
        except Exception:
            pass

    def export(self, path, target_format, acad_version="ACAD2018"):
        target_format = target_format.lower()
        if target_format == "dxf":
            return self._ensure_dxf(path)
        if target_format == "dwg":
            return _oda_convert(path, to_dxf=False, acad_version=acad_version)
        if target_format == "pdf":
            out = self._ensure_dxf(path).rsplit(".", 1)[0] + ".pdf"
            self.render_preview(path, out + ".tmp.png")
            # PNG→PDF 占位（Phase 1 用 matplotlib PDF 后端直出）
            return out
        raise ValueError(f"不支持的格式: {target_format}")

    # ─── 内部 ───

    def _ensure_dxf(self, path: str) -> str:
        if path.lower().endswith(".dxf"):
            return path
        return _oda_convert(path, to_dxf=True)

    @staticmethod
    def _extract_walls(msp) -> list[dict]:
        from .freecad_backend import WALL_KEYWORDS
        walls = []
        for ent in msp.query("LWPOLYLINE LINE"):
            layer = ent.dxf.layer.upper()
            if any(k in layer for k in WALL_KEYWORDS):
                pts = [(p[0], p[1]) for p in ent.get_points()] \
                    if ent.dxftype() == "LWPOLYLINE" \
                    else [(ent.dxf.start.x, ent.dxf.start.y),
                          (ent.dxf.end.x, ent.dxf.end.y)]
                length = sum(((pts[i+1][0]-pts[i][0])**2 + (pts[i+1][1]-pts[i][1])**2) ** 0.5
                             for i in range(len(pts)-1))
                walls.append({
                    "layer": ent.dxf.layer,
                    "coords_mm": [list(p) for p in pts],
                    "length_mm": round(length, 1),
                    "closed": ent.closed if ent.dxftype() == "LWPOLYLINE" else False,
                    "_segs": [pts[i:i+2] for i in range(len(pts)-1)],
                })
        return walls

    @staticmethod
    def _extract_blocks(msp) -> tuple[list, list, list]:
        from .freecad_backend import _classify
        doors, windows, furniture = [], [], []
        for ent in msp.query("INSERT"):
            ftype = _classify(ent.dxf.name)
            item = {
                "block": ent.dxf.name,
                "type": ftype,
                "position_xy": [ent.dxf.insert.x, ent.dxf.insert.y],
                "rotation_deg": ent.dxf.rotation,
                "layer": ent.dxf.layer,
                "handle": ent.dxf.handle,
            }
            if ftype == "door":
                doors.append(item)
            elif ftype == "window":
                windows.append(item)
            elif ftype != "unknown":
                furniture.append(item)
        return doors, windows, furniture

    @staticmethod
    def _detect_rooms(walls: list[dict], furniture: list[dict]) -> list[dict]:
        """调共享 shapely 算法，与 FreeCAD backend 同源。

        私有 _segs 字段是墙的线段（仅 EzdxfBackend 内部数据），
        共享函数接受标准 ((x1,y1),(x2,y2)) 格式。
        """
        from .rooms_detect import detect_rooms
        segs = []
        for w in walls:
            for s in w.get("_segs", []):
                if len(s) == 2 and len(s[0]) >= 2 and len(s[1]) >= 2:
                    segs.append((s[0], s[1]))
        # close_openings_mm=1000: 真实装修图门洞/窗洞续断墙线，需补虚拟墙才能闭合
        # 真实 Phase 0 样本到来时确认阈值
        return detect_rooms(segs, furniture=furniture, close_openings_mm=1000.0)


def _oda_convert(path: str, to_dxf: bool, acad_version: str = "ACAD2018") -> str:
    from .freecad_backend import _oda_convert as _oda
    return _oda(path, to_dxf=to_dxf, acad_version=acad_version)
