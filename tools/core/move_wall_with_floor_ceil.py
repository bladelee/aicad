"""Tools/core/move_wall_with_floor_ceil.py — #2 改墙 + 地坪天花同步。

底层 = tools/dxf_edit/move_wall_with_floor_ceil.py 的最核心
shift_ent() + 中点判据逻辑（main() 是写死路径的，不能复用，这里重构成纯函数）。
"""
from __future__ import annotations
import math
import sys
from pathlib import Path
from typing import Optional

_OLD = Path(__file__).resolve().parent.parent / "dxf_edit"
if str(_OLD) not in sys.path:
    sys.path.insert(0, str(_OLD))

from .move_wall import safe_saveas  # type: ignore  # noqa: E402

# 联动层候选（来自 move_wall.py）
SYNC_LAYER_KEYWORDS = ("F地坪", "C天花", "L天灯", "J家具")


def _ent_center(ent, fallback) -> tuple[float, float]:
    """取实体几何中心用于近距判定。LINE 用中点，其它用 insert/center。"""
    try:
        if ent.dxftype() == "LINE":
            s, e = ent.dxf.start, ent.dxf.end
            return ((s[0] + e[0]) / 2, (s[1] + e[1]) / 2)
        elif ent.dxftype() in ("CIRCLE", "ARC"):
            c = ent.dxf.center
            return (c[0], c[1])
        else:  # INSERT / TEXT / MTEXT / LWPOLYLINE
            p = ent.dxf.insert
            return (p[0], p[1])
    except Exception:
        return fallback


def _shift_ent(ent, dx: float, dy: float):
    """平移实体几何（保持原行为）。"""
    etype = ent.dxftype()
    if etype == "LINE":
        s, e = ent.dxf.start, ent.dxf.end
        ent.dxf.start = (s[0] + dx, s[1] + dy, s[2])
        ent.dxf.end = (e[0] + dx, e[1] + dy, e[2])
    elif etype == "LWPOLYLINE":
        pts = [(p[0] + dx, p[1] + dy) + tuple(p[2:]) for p in ent.get_points()]
        ent.set_points(pts)
    elif etype in ("CIRCLE", "ARC"):
        c = ent.dxf.center
        ent.dxf.center = (c[0] + dx, c[1] + dy, c[2])
    elif etype == "INSERT":
        p = ent.dxf.insert
        ent.dxf.insert = (p[0] + dx, p[1] + dy, p[2])
    elif etype in ("TEXT", "MTEXT"):
        p = ent.dxf.insert
        ent.dxf.insert = (p[0] + dx, p[1] + dy, p[2])
    else:
        return False
    return True


def move_wall_with_floor_ceil(
    dxf_path: str | Path,
    handle: Optional[str] = None,
    wall_idx: Optional[int] = None,
    dx: float = 0.0,
    dy: float = 0.0,
    near: float = 2000.0,
    sync_layer_keywords: tuple[str, ...] = SYNC_LAYER_KEYWORDS,
    out_path: Optional[str | Path] = None,
    backup_dir: Optional[str | Path] = None,
) -> dict:
    """平移一堵墙 + 联动周边地坪/天花实体。

    Args:
        dxf_path: DXF 路径
        handle: 优先用 handle 选墙（hex 字符串）
        wall_idx: 没 handle 时用墙列表索引（来自 wall_layer 的第 N 条 LINE）
        dx, dy: 平移 mm
        near: 联动同步半径 mm（默认 2000）
        sync_layer_keywords: 联动层关键词（前缀匹配）
        out_path: 输出路径（None = 自动 <stem>_floor_ceil.dxf）
        backup_dir: 备份目录

    Returns:
        {"ok": True,
         "wall_handle": str, "mode": "translate",
         "shift": {"dx": .., "dy": .., "near": ..},
         "before": {"start": [x,y], "end": [x,y]},
         "after":  {"start": [x,y], "end": [x,y]},
         "synced_layers": {layer: n_entities},
         "output": str, "backup": str | None}
    """
    import ezdxf
    from .move_wall import backup_with_rotate, find_wall

    dxf_path = Path(dxf_path)
    out_path = Path(out_path) if out_path else dxf_path.with_name(
        f"{dxf_path.stem}_floor_ceil.dxf"
    )

    backup = None
    if backup_dir:
        backup = backup_with_rotate(dxf_path, Path(backup_dir))

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    # 1. 选墙（复用 move_wall.find_wall）
    wall, _all_walls = find_wall(msp, handle=handle, idx=wall_idx or 0)

    before = {
        "start": list(wall.dxf.start)[:2],
        "end": list(wall.dxf.end)[:2],
    }

    # 2. 墙中点（联动判据中心）
    s, e = wall.dxf.start, wall.dxf.end
    cx, cy = (s[0] + e[0]) / 2, (s[1] + e[1]) / 2

    # 3. 改墙
    wall.dxf.start = (s[0] + dx, s[1] + dy, s[2])
    wall.dxf.end = (e[0] + dx, e[1] + dy, e[2])

    after = {
        "start": list(wall.dxf.start)[:2],
        "end": list(wall.dxf.end)[:2],
    }

    # 4. 扫联动层内 near 半径内的实体，一并平移
    near_sq = near ** 2
    synced: dict[str, int] = {}
    for ent in msp:
        layer = ent.dxf.layer
        if not any(layer.startswith(k) for k in sync_layer_keywords):
            continue
        cx_e, cy_e = _ent_center(ent, fallback=(cx, cy))
        if (cx_e - cx) ** 2 + (cy_e - cy) ** 2 <= near_sq:
            if _shift_ent(ent, dx, dy):
                synced[layer] = synced.get(layer, 0) + 1

    # 5. 保存
    safe_saveas(doc, str(out_path))

    return {
        "ok": True,
        "wall_handle": wall.dxf.handle,
        "shift": {"dx": dx, "dy": dy, "near": near},
        "before": before,
        "after": after,
        "synced_layers": synced,
        "output": str(out_path),
        "backup": str(backup) if backup else None,
    }


__all__ = ["move_wall_with_floor_ceil"]
