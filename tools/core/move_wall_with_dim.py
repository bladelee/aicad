"""Tools/core/move_wall_with_dim.py — D1 路径 C: 改墙 + 同步 DIMENSION defpoint。

把原 tools/dxf_edit/move_wall_with_dim.py 的 main() 里的硬编码拆出来，
包成纯函数 API：move_wall_with_dim(dxf, handle, dx, dy, near, out) → dict
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import importlib.util
import sys

_OLD = Path(__file__).resolve().parent.parent / "dxf_edit"
if str(_OLD) not in sys.path:
    sys.path.insert(0, str(_OLD))

# 动态加载老 main() 文件，提取其中的纯逻辑 update_dimensions_near_wall
# 不能用普通 import，因为老文件名带下划线开头易和本模块重名冲突
_spec = importlib.util.spec_from_file_location(
    "_legacy_move_wall_with_dim", _OLD / "move_wall_with_dim.py"
)
_legacy = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_legacy)  # type: ignore[union-attr]
update_dimensions_near_wall = _legacy.update_dimensions_near_wall

# safe_saveas 在 tools/core/move_wall.py（re-export 自老 move_wall.py）
from .move_wall import safe_saveas  # type: ignore  # noqa: E402


def move_wall_with_dim(
    dxf_path: str | Path,
    handle: str,
    dx: float = 0.0,
    dy: float = 0.0,
    near: float = 2000.0,
    out_path: Optional[str | Path] = None,
) -> dict:
    """平移一堵墙，并同步 DEFPOINT 落在墙端 ±near 范围内的 DIMENSION。

    Args:
        dxf_path: DXF 文件路径
        handle: 墙的 handle（16 进制字符串）
        dx: 横向位移 mm
        dy: 纵向位移 mm
        near: DIMENSION 同步半径 mm（默认 2000）
        out_path: 输出路径（None = 自动 <原名>_with_dim.dxf）

    Returns:
        {"ok": bool, "wall_handle": str,
         "shift": {"dx": .., "dy": .., "near": ..},
         "before": {"start": [x,y], "end": [x,y]},
         "after":  {"start": [x,y], "end": [x,y]},
         "synced_dims": [{"handle": str, "text": str, "old_defpoint": (x,y),
                          "moved_dp": bool, "moved_dp2": bool}, ...],
         "output": str,
         "warnings": [..]}
    """
    import ezdxf

    dxf_path = Path(dxf_path)
    out_path = Path(out_path) if out_path else dxf_path.with_name(
        f"{dxf_path.stem}_with_dim.dxf"
    )
    warnings: list[str] = []

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    # 1. 找墙
    wall = None
    for e in msp:
        if e.dxftype() == "LINE" and e.dxf.handle == handle:
            wall = e
            break
    if not wall:
        return {"ok": False, "error": f"wall {handle} not found"}

    before = {
        "start": list(wall.dxf.start)[:2],
        "end": list(wall.dxf.end)[:2],
    }

    # 2. 同步 DIMENSION（在改墙前，用原始墙端点判距）
    n_dims, dim_logs = update_dimensions_near_wall(msp, wall, dx, dy, near)

    # 3. 改墙本体
    s, e = wall.dxf.start, wall.dxf.end
    wall.dxf.start = (s[0] + dx, s[1] + dy, s[2])
    wall.dxf.end = (e[0] + dx, e[1] + dy, e[2])

    after = {
        "start": list(wall.dxf.start)[:2],
        "end": list(wall.dxf.end)[:2],
    }

    # 4. 保存
    safe_saveas(doc, str(out_path))

    return {
        "ok": True,
        "wall_handle": handle,
        "shift": {"dx": dx, "dy": dy, "near": near},
        "before": before,
        "after": after,
        "synced_dims": dim_logs,
        "synced_dim_count": n_dims,
        "output": str(out_path),
        "warnings": warnings,
    }


__all__ = ["move_wall_with_dim"]
