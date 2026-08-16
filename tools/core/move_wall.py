"""Tools/core/move_wall.py — 重新暴露 move_wall 核心函数。

底层 = tools/dxf_edit/move_wall.py 的 move_wall（已经是纯函数 API）。
"""
from __future__ import annotations
from pathlib import Path
import sys

_OLD = Path(__file__).resolve().parent.parent / "dxf_edit"
if str(_OLD) not in sys.path:
    sys.path.insert(0, str(_OLD))

# 一并暴露 shift_line / shift_layer_entities / find_wall / safe_saveas（CLI 内部要用）
from move_wall import (  # type: ignore  # noqa: E402,F401
    move_wall,
    shift_line,
    shift_layer_entities,
    find_wall,
    safe_saveas,
    backup_with_rotate,
)

__all__ = [
    "move_wall",
    "shift_line",
    "shift_layer_entities",
    "find_wall",
    "safe_saveas",
    "backup_with_rotate",
]
