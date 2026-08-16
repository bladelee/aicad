"""Tools/core/probe_dimensions.py — 探查墙端附近的 DIMENSION（D1 用）。

底层 = tools/dxf_edit/probe_dimensions.py 是 print-only 脚本，
这里重构成纯函数 API，返回结构化 dict。
"""
from __future__ import annotations
import math
from pathlib import Path
from typing import Optional


def probe_dimensions_near_wall(
    dxf_path: str | Path,
    handle: Optional[str] = None,
    wall_idx: Optional[int] = None,
    near: float = 2000.0,
) -> dict:
    """探查指定墙的端点 ±near 范围内有多少 DIMENSION / 各自的字段分布。

    Args:
        dxf_path: DXF 路径
        handle: 墙 handle（与 wall_idx 二选一）
        wall_idx: 墙列表索引（来自 wall_layer 的第 N 条 LINE）
        near: 半径 mm

    Returns:
        {"ok": True,
         "wall_handle": str,
         "wall_endpoints": {"start": [x,y], "end": [x,y]},
         "near_mm": float,
         "dimensions": [
            {"handle": str, "text": str, "defpoint": [x,y],
             "defpoint2": [x,y] | None,
             "dist_to_end": float,
             "actual_length": float | None}, ...],
         "all_dim_count_in_doc": int,
         "dimtype_distribution": {f"dimtype={k}": v}}
    """
    import ezdxf
    from collections import Counter

    dxf_path = Path(dxf_path)
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    # 选墙
    wall = None
    if handle:
        for e in msp:
            if e.dxftype() == "LINE" and e.dxf.handle == handle:
                wall = e
                break
        if not wall:
            return {"ok": False, "error": f"wall {handle} not found"}
    else:
        from .move_wall import find_wall
        wall, _ = find_wall(msp, idx=wall_idx or 0)

    wall_start = tuple(wall.dxf.start)[:2]
    wall_end = tuple(wall.dxf.end)[:2]

    # 统计全部 DIMENSION 全局信息
    all_dims = [e for e in msp if e.dxftype().startswith("DIMENSION")]
    subtype_count = Counter()
    for d in all_dims:
        try:
            dt = d.dxf.dimtype
            subtype_count[f"dimtype={dt}"] += 1
        except Exception:
            subtype_count["no_dimtype"] += 1

    # 探查 near 范围内
    dims_in_range = []
    for d in all_dims:
        try:
            dp = tuple(d.dxf.defpoint)[:2]
        except Exception:
            continue
        dist_start = math.hypot(dp[0] - wall_start[0], dp[1] - wall_start[1])
        dist_end = math.hypot(dp[0] - wall_end[0], dp[1] - wall_end[1])
        dist = min(dist_start, dist_end)
        if dist > near:
            continue
        item: dict = {
            "handle": d.dxf.handle,
            "text": getattr(d.dxf, "text", "") or "",
            "defpoint": [round(c, 1) for c in dp],
            "dist_to_end": round(dist, 1),
            "actual_length": None,
        }
        try:
            dp2 = tuple(d.dxf.defpoint2)[:2]
            item["defpoint2"] = [round(c, 1) for c in dp2]
            item["actual_length"] = round(
                math.hypot(dp2[0] - dp[0], dp2[1] - dp[1]), 1
            )
        except Exception:
            pass
        dims_in_range.append(item)

    dims_in_range.sort(key=lambda x: x["dist_to_end"])

    return {
        "ok": True,
        "wall_handle": wall.dxf.handle,
        "wall_endpoints": {"start": list(wall_start), "end": list(wall_end)},
        "near_mm": near,
        "dimensions": dims_in_range,
        "dimension_count_in_range": len(dims_in_range),
        "all_dim_count_in_doc": len(all_dims),
        "dimtype_distribution": dict(subtype_count),
    }


__all__ = ["probe_dimensions_near_wall"]
