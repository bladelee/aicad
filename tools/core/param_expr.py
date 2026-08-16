"""Tools/core/param_expr.py — 重新暴露 A1 表达式求值。

底层 = tools/dxf_edit/param_expr.py（保留不动）
"""
from __future__ import annotations
from pathlib import Path
import sys

# 把老目录加 sys.path
_OLD = Path(__file__).resolve().parent.parent / "dxf_edit"
if str(_OLD) not in sys.path:
    sys.path.insert(0, str(_OLD))

from param_expr import eval_expr, get_num, params_for_eval  # type: ignore  # noqa: E402,F401

__all__ = ["eval_expr", "get_num", "params_for_eval"]
