"""
cad_tools — Chat → DWG/DXF 房屋装修图操作工具库

通过自然语言对话驱动，读取/修改/创建 DXF（及 DWG）格式的房屋装修图。

核心模块:
    converter  — DWG↔DXF 格式转换桥
    reader     — DXF 读取 & 建筑语义解析（墙体/门窗/家具/房间）
    writer     — DXF 创建 & 修改
    renderer   — PNG 预览渲染
    geometry   — 几何工具（距离/面积/碰撞检测）
    blocks     — 装修图常用块库（门/窗/家具）
"""

from .reader import FloorPlanReader
from .writer import FloorPlanWriter
from .renderer import DXFRenderer
from .converter import DWGConverter
from .geometry import (
    distance, polygon_area, point_in_polygon,
    line_intersection, move_point, rotate_point,
)
from .blocks import BlockLibrary

__version__ = "0.1.0"
__all__ = [
    "FloorPlanReader",
    "FloorPlanWriter",
    "DXFRenderer",
    "DWGConverter",
    "BlockLibrary",
    "distance",
    "polygon_area",
    "point_in_polygon",
    "line_intersection",
    "move_point",
    "rotate_point",
]
