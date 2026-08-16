# -*- coding: utf-8 -*-
"""
DXF → 内部 shape 列表（"局部图形可重放包"）。

借鉴自 wheel-drawing-tools（Rosyal/wheel-drawing-tools）的 ``cad_dxf.py::_doc_to_shapes``，
见 docs/借鉴-wheel-drawing-tools-参数化模式.md §3.1。

为什么需要：
  - #1 改墙任务要把"被改过的那段墙 + 配套尺寸/填充"打包成可重放图形，
    之前是散落在 probe_layer_bbox.py 里手写 LINE/CIRCLE/ARC/LWPOLYLINE 的点提取代码；
  - wheel 项目已经把这件事封装好了，我们直接复用 + 扩展（按图层过滤 + 持久化 JSON）。

形状列表格式（与 param_expr.flatten_shapes / write_dxf 互通）::

    [
      {"type": "line", "x1": .., "y1": .., "x2": .., "y2": .., "layer": "..", "handle": ".."},
      {"type": "circle", "cx": .., "cy": .., "r": .., "layer": "..", "handle": ".."},
      {"type": "arc",    "cx": .., "cy": .., "r": .., "start_angle": .., "end_angle": ..},
      {"type": "polyline", "points": [[x,y], ...], "closed": bool},
    ]

注意：
  - wheel 原版只扫 modelspace、忽略图层信息。我们加了 ``layer`` / ``handle`` 字段，
    因为我们的业务（多图层 + 跨视图联动）必须保留"这条线来自哪个图层"。
  - LWPOLYLINE 在 wheel 原版会被拆成多条 line；我们也保留拆分版本（``line_break=True``），
    默认行为与 wheel 一致；但额外提供 ``line_break=False`` 保留成单条 polyline，
    更适合"整段多段线一次性搬运"场景。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

try:
    import ezdxf
except ImportError:  # pragma: no cover — 容器/宿主机都装了 ezdxf，这里只是防御
    ezdxf = None  # type: ignore

__all__ = [
    "get_xy",
    "doc_to_shapes",
    "dxf_to_shapes",
    "save_shapes_json",
    "filter_shapes_by_layer",
    "shapes_bbox",
]


def get_xy(e, key: str) -> tuple:
    """从 DXF 实体取 2D 点 (x, y)；缺失则返回 (0.0, 0.0)。

    ezdxf 1.4.4 行为：对当前实体类型不存在的属性调用 ``dxf.get(key)``
    会**直接抛 ``DXFAttributeError``**（不是返回 None），所以这里必须 try/except。
    比 wheel 原版（仅判 None）更稳健 —— 适配更新版 ezdxf。
    """
    try:
        p = e.dxf.get(key)
    except Exception:  # noqa: BLE001 — DXFAttributeError 等
        return (0.0, 0.0)
    if p is None:
        return (0.0, 0.0)
    return (float(p.x), float(p.y))


def _layer_of(e) -> str:
    try:
        return str(e.dxf.layer)
    except Exception:  # noqa: BLE001
        return ""


def _handle_of(e) -> str:
    try:
        return str(e.dxf.handle)
    except Exception:  # noqa: BLE001
        return ""


def doc_to_shapes(
    doc,
    layers: Optional[Sequence[str]] = None,
    include_handles: bool = True,
    line_break: bool = True,
) -> List[Dict[str, Any]]:
    """从 ezdxf 文档对象提取 shape 列表。

    只扫 modelspace（对齐 wheel 原版；扫 layouts 见 scan_dxf.py）。
    支持 LINE / CIRCLE / ARC / LWPOLYLINE / HATCH（wheel 原版不支持 HATCH，
    我们加了 —— 因为本项目 A原建筑墙体填充 就是 HATCH 图层）。

    Args:
        doc: ezdxf 文档对象（``ezdxf.readfile()`` 或 odafc.readfile() 的返回）
        layers: 只保留这些图层里的实体；None 表示全图层（对齐 wheel 原版行为）
        include_handles: 是否在每条 shape 里附加 ``layer`` / ``handle`` 字段
            （wheel 原版 false；我们场景默认 true，因为多图层/跨视图联动需要）
        line_break:
            True（默认，对齐 wheel 原版）：LWPOLYLINE 拆成多条 line
            False：保留成单条 polyline，便于整体搬运

    Returns:
        shape 列表，原样可序列化 JSON，也可反向喂给 ezdxf 重画。
    """
    msp = doc.modelspace()
    layer_set = set(layers) if layers is not None else None
    shapes: List[Dict[str, Any]] = []

    def _attach(out: Dict[str, Any], e) -> Dict[str, Any]:
        if include_handles:
            out["layer"] = _layer_of(e)
            out["handle"] = _handle_of(e)
        return out

    for e in msp:
        if layer_set is not None and _layer_of(e) not in layer_set:
            continue
        etype = e.dxftype()
        try:
            if etype == "LINE":
                start = get_xy(e, "start")
                end = get_xy(e, "end")
                shapes.append(_attach({
                    "type": "line",
                    "x1": start[0], "y1": start[1],
                    "x2": end[0], "y2": end[1],
                }, e))
            elif etype == "CIRCLE":
                center = get_xy(e, "center")
                r = float(e.dxf.radius)
                shapes.append(_attach({
                    "type": "circle",
                    "cx": center[0], "cy": center[1], "r": r,
                }, e))
            elif etype == "ARC":
                center = get_xy(e, "center")
                r = float(e.dxf.radius)
                start_angle = float(e.dxf.start_angle)
                end_angle = float(e.dxf.end_angle)
                shapes.append(_attach({
                    "type": "arc",
                    "cx": center[0], "cy": center[1], "r": r,
                    "start_angle": start_angle, "end_angle": end_angle,
                }, e))
            elif etype == "LWPOLYLINE":
                # ezdxf 1.4.4 返回 np.float64，转 float 避免后续 JSON 序列化踩坑
                points = [(float(p[0]), float(p[1])) for p in e.get_points("xy")]
                if line_break:
                    # wheel 原版行为：拆成多条相邻线段（含闭合段）
                    for i in range(len(points) - 1):
                        x1, y1 = points[i][0], points[i][1]
                        x2, y2 = points[i + 1][0], points[i + 1][1]
                        shapes.append(_attach({
                            "type": "line",
                            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        }, e))
                    if e.closed and len(points) >= 2:
                        x1, y1 = points[-1][0], points[-1][1]
                        x2, y2 = points[0][0], points[0][1]
                        shapes.append(_attach({
                            "type": "line",
                            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        }, e))
                else:
                    shapes.append(_attach({
                        "type": "polyline",
                        "points": [[p[0], p[1]] for p in points],
                        "closed": bool(e.closed),
                    }, e))
            elif etype == "HATCH":
                # wheel 原版不支持 HATCH；本项目场景必需（A原建筑墙体填充 是
                # HATCH 图层，跨视图联动改墙必须能扫出填充轮廓一起搬）
                for path in e.paths:
                    ptype = type(path).__name__
                    if ptype == "PolylinePath":
                        # vertices 是属性（list of (x, y)），is_closed 是 bool
                        verts = [(float(v[0]), float(v[1]))
                                 for v in path.vertices]
                        if not verts:
                            continue
                        if line_break and len(verts) >= 2:
                            for i in range(len(verts) - 1):
                                shapes.append(_attach({"type": "line",
                                    "x1": verts[i][0], "y1": verts[i][1],
                                    "x2": verts[i + 1][0], "y2": verts[i + 1][1]},
                                    e))
                            if getattr(path, "is_closed", False):
                                shapes.append(_attach({"type": "line",
                                    "x1": verts[-1][0], "y1": verts[-1][1],
                                    "x2": verts[0][0], "y2": verts[0][1]}, e))
                        elif not line_break:
                            shapes.append(_attach({"type": "polyline",
                                "points": [[v[0], v[1]] for v in verts],
                                "closed": bool(getattr(path, "is_closed", False))},
                                e))
                    elif ptype == "EdgePath":
                        # EdgePath 由 LineEdge/ArcEdge/SplineEdge/EllipseEdge 组成；
                        # 用 vertices() 在 ezdxf 1.4.4 已废弃（称号冲突），
                        # 先近似用每条 edge 的 start/end 端点连线
                        for edge in path.edges:
                            etype2 = type(edge).__name__
                            s = getattr(edge, "start", None)
                            en = getattr(edge, "end", None)
                            if s is None or en is None:
                                continue
                            shapes.append(_attach({"type": "line",
                                "x1": float(s[0]), "y1": float(s[1]),
                                "x2": float(en[0]), "y2": float(en[1])},
                                e))
        except Exception:
            # 跳过损坏/特殊实体，不让一处坏点中断扫描（对齐 wheel 行为）
            continue
    return shapes


def dxf_to_shapes(
    dxf_path: Union[str, Path],
    layers: Optional[Sequence[str]] = None,
    include_handles: bool = True,
    line_break: bool = True,
) -> List[Dict[str, Any]]:
    """一行 API：从 DXF 文件路径直接读到 shape 列表。

    仅供 DXF（DWG 需要走 odafc.readfile，业务上由 floorplan-mcp 容器内处理；
    这里不强制依赖 odafc，避免宿主机没装 ODA SDK 时模块无法加载）。
    """
    if ezdxf is None:
        raise RuntimeError("请先安装 ezdxf: pip install ezdxf")
    doc = ezdxf.readfile(str(dxf_path))
    return doc_to_shapes(doc, layers=layers,
                         include_handles=include_handles, line_break=line_break)


def save_shapes_json(
    shapes: List[Dict[str, Any]],
    out_path: Union[str, Path],
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """把 shape 列表写到 JSON。

    meta 写到顶层 ``meta`` 字段，记录 source_dxf/layers/time 等，
    方便下一站（floor plan MCP / LLM）识别这个"局部图形可重放包"是哪段墙、从哪来。
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": meta or {},
        "shape_count": len(shapes),
        "shapes": shapes,
    }
    with out.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    return str(out)


def filter_shapes_by_layer(
    shapes: Iterable[Dict[str, Any]],
    layers: Sequence[str],
) -> List[Dict[str, Any]]:
    """从 shape 列表里再切一层（已经 include_handles=True 的列表才带 layer 字段）。

    用于扫描整张图、再按需选图层，避免重复 readfile。
    """
    layer_set = set(layers)
    return [s for s in shapes
            if s.get("layer") in layer_set]


def shapes_bbox(shapes: Iterable[Dict[str, Any]]) -> Optional[tuple]:
    """快速求 shape 列表的 2D bbox（min_x, max_x, min_y, max_y）。

    平替 probe_layer_bbox 里散写的 bbox 计算，统一坐标探测入口。
    空列表返回 None。
    """
    xs: List[float] = []
    ys: List[float] = []
    for s in shapes:
        t = s.get("type")
        if t == "line":
            xs.extend([s.get("x1", 0.0), s.get("x2", 0.0)])
            ys.extend([s.get("y1", 0.0), s.get("y2", 0.0)])
        elif t in ("circle", "arc"):
            cx = s.get("cx", 0.0)
            cy = s.get("cy", 0.0)
            r = s.get("r", 0.0)
            xs.extend([cx - r, cx + r])
            ys.extend([cy - r, cy + r])
        elif t == "polyline":
            for px, py in s.get("points", []):
                xs.append(px); ys.append(py)
    if not xs:
        return None
    return (min(xs), max(xs), min(ys), max(ys))


# ---------- CLI：把任意 DXF 转成 shapes JSON ----------

def _main(argv: Optional[Sequence[str]] = None) -> int:
    ap_argv = list(sys.argv[1:] if argv is None else argv)
    if not ap_argv or ap_argv[0] in ("-h", "--help"):
        print(__doc__)
        print("\n用法:")
        print("  python doc_to_shapes.py <input.dxf> [output.json] [--layer NAME]...")
        print("  python doc_to_shapes.py <input.dxf> --summary")
        return 0
    dxf = ap_argv[0]
    rest = ap_argv[1:]
    layers: List[str] = []
    summary_only = False
    out: Optional[str] = None
    i = 0
    while i < len(rest):
        if rest[i] == "--layer" and i + 1 < len(rest):
            layers.append(rest[i + 1]); i += 2; continue
        if rest[i] == "--summary":
            summary_only = True; i += 1; continue
        if out is None:
            out = rest[i]; i += 1; continue
        i += 1

    shapes = dxf_to_shapes(dxf, layers=layers or None)
    print(f"扫描 {dxf}：", end=" ")
    if layers:
        print(f"仅图层 {layers}，共 {len(shapes)} 个 shape")
    else:
        print(f"全图层，共 {len(shapes)} 个 shape")

    # 类型分布
    by_type: Dict[str, int] = {}
    by_layer: Dict[str, int] = {}
    for s in shapes:
        by_type[s.get("type", "?")] = by_type.get(s.get("type", "?"), 0) + 1
        ly = s.get("layer", "")
        by_layer[ly] = by_layer.get(ly, 0) + 1
    print("  按类型:", by_type)
    print("  按图层 (top 10):")
    for ly, n in sorted(by_layer.items(), key=lambda kv: -kv[1])[:10]:
        print(f"    {n:>5}  {ly}")

    bbox = shapes_bbox(shapes)
    if bbox:
        print(f"  bbox: X[{bbox[0]:.1f}, {bbox[1]:.1f}]  Y[{bbox[2]:.1f}, {bbox[3]:.1f}]")

    if not summary_only:
        if out is None:
            from datetime import datetime
            stem = Path(dxf).stem
            out = f"{stem}_shapes.json"
            if layers:
                out = f"{stem}__{'-'.join(layers)}_shapes.json"
            out = f"shapes_{datetime.now():%Y%m%d_%H%M%S}_{Path(out).name}"
        meta = {
            "source_dxf": str(Path(dxf).resolve()),
            "layers": layers or None,
        }
        save_shapes_json(shapes, out, meta=meta)
        print(f"\n已写出: {out}")

    return 0


if __name__ == "__main__":
    sys.exit(_main())
