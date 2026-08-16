"""Tools/core/shapes.py — 重新暴露 A2 doc_to_shapes / 几何工具。"""
from __future__ import annotations
from pathlib import Path
import sys

_OLD = Path(__file__).resolve().parent.parent / "dxf_scan"
if str(_OLD) not in sys.path:
    sys.path.insert(0, str(_OLD))

from doc_to_shapes import (  # type: ignore  # noqa: E402
    doc_to_shapes,
    filter_shapes_by_layer,
    shapes_bbox,
    save_shapes_json,
)

__all__ = ["doc_to_shapes", "filter_shapes_by_layer", "shapes_bbox", "save_shapes_json"]
