"""
geometry — 几何工具函数

提供距离计算、面积计算、点在多边形内判断、线段相交、
坐标变换等基础几何操作，供 reader/writer/blocks 模块调用。
"""

from __future__ import annotations
import math
from typing import Sequence, Tuple

Point = Tuple[float, float]


def distance(p1: Point, p2: Point) -> float:
    """计算两点之间的欧几里得距离"""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def polygon_area(coords: Sequence[Point]) -> float:
    """
    用鞋带公式计算多边形面积（逆时针为正，顺时针为负）。
    返回绝对值。
    """
    n = len(coords)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        j = (i + 1) % n
        s += coords[i][0] * coords[j][1]
        s -= coords[j][0] * coords[i][1]
    return abs(s) / 2.0


def point_in_polygon(pt: Point, polygon: Sequence[Point]) -> bool:
    """
    射线法判断点是否在多边形内部。
    """
    x, y = pt
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def line_intersection(
    p1: Point, p2: Point, p3: Point, p4: Point
) -> Point | None:
    """
    计算线段 p1p2 与线段 p3p4 的交点。
    若不相交（平行或交点不在线段上），返回 None。
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-12:
        return None  # 平行

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    if 0 <= t <= 1 and 0 <= u <= 1:
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)
        return (ix, iy)
    return None


def move_point(p: Point, dx: float, dy: float) -> Point:
    """平移点"""
    return (p[0] + dx, p[1] + dy)


def rotate_point(
    p: Point, angle_deg: float, center: Point = (0, 0)
) -> Point:
    """
    绕 center 旋转点，angle_deg 为角度（逆时针为正）。
    """
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    cx, cy = center
    x = p[0] - cx
    y = p[1] - cy
    rx = x * cos_a - y * sin_a + cx
    ry = x * sin_a + y * cos_a + cy
    return (rx, ry)


def midpoint(p1: Point, p2: Point) -> Point:
    """计算两点的中点"""
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)


def angle_between(p1: Point, p2: Point) -> float:
    """
    计算从 p1 到 p2 的角度（度），0° 为正东方向，逆时针。
    """
    return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))


def bbox_of(coords: Sequence[Point]) -> Tuple[Point, Point]:
    """
    计算点集的包围盒，返回 (min_corner, max_corner)。
    """
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return ((min(xs), min(ys)), (max(xs), max(ys)))


def bboxes_overlap(
    bb1: Tuple[Point, Point], bb2: Tuple[Point, Point]
) -> bool:
    """判断两个包围盒是否重叠"""
    return not (
        bb1[1][0] < bb2[0][0]
        or bb2[1][0] < bb1[0][0]
        or bb1[1][1] < bb2[0][1]
        or bb2[1][1] < bb1[0][1]
    )


def polyline_length(coords: Sequence[Point], closed: bool = False) -> float:
    """计算多段线总长度"""
    total = 0.0
    n = len(coords)
    for i in range(n - 1):
        total += distance(coords[i], coords[i + 1])
    if closed and n >= 3:
        total += distance(coords[-1], coords[0])
    return total


def is_closed(coords: Sequence[Point], tol: float = 1.0) -> bool:
    """判断多段线是否闭合（首尾点距离 < tol）"""
    if len(coords) < 3:
        return False
    return distance(coords[0], coords[-1]) < tol
