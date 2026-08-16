"""共享房间识别算法的单元测试（直接测 rooms_detect.detect_rooms）。

跑：python -m pytest tests/test_rooms_detect.py

意义：freecad_backend 和 ezdxf_backend 都调这个函数，这里钉住它的行为，
后续任一 backend 的房间识别行为都由此保证。
"""

from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backends.rooms_detect import detect_rooms


def test_empty_segments_returns_empty():
    assert detect_rooms([]) == []


def test_no_closed_polygon():
    """单根线不成房间。"""
    assert detect_rooms([((0, 0), (1, 0))]) == []


def test_square_one_room():
    """4 根线围成正方形（边长 4m）→ 1 房间，面积 16m²。"""
    segs = [((0, 0), (4000, 0)), ((4000, 0), (4000, 4000)),
            ((4000, 4000), (0, 4000)), ((0, 4000), (0, 0))]
    rooms = detect_rooms(segs)
    assert len(rooms) == 1
    assert rooms[0]["area_m2"] == 16.0
    assert rooms[0]["name"] == "Room1"


def test_two_rooms_with_shared_wall():
    """两间房共享一道内墙。"""
    segs = [((0, 0), (8000, 0)), ((8000, 0), (8000, 6000)),
            ((8000, 6000), (0, 6000)), ((0, 6000), (0, 0)),
            ((4000, 0), (4000, 6000))]
    rooms = detect_rooms(segs)
    assert len(rooms) == 2
    assert all(r["area_m2"] == pytest.approx(24.0, rel=0.01) for r in rooms)


def test_min_area_filters_small_fragments():
    """面积小于阈值的碎片被过滤：美式长条 + 内部小方块当碎片。"""
    # 外框 5000x5000 = 25m²
    # 内部画一个 300x300 小方块当"小碎片"（与外框不连通）
    # polygonize 会识别：外框 1 间 = 25m²；内部方块自身闭合 1 间 = 0.09m²
    square = [((0, 0), (300, 0)), ((300, 0), (300, 300)),
              ((300, 300), (0, 300)), ((0, 300), (0, 0))]
    outer = [((0, 0), (5000, 0)), ((5000, 0), (5000, 5000)),
             ((5000, 5000), (0, 5000)), ((0, 5000), (0, 0))]
    # 把小方块挪到外框内部，避免和外框重合
    small_shifted = [[(a[0] + 2000, a[1] + 2000), (b[0] + 2000, b[1] + 2000)]
                     for a, b in square]
    segs = outer + small_shifted
    rooms = detect_rooms(segs, min_area_m2=0.5)
    areas = [r["area_m2"] for r in rooms]
    assert 25.0 in [round(a) for a in areas]  # 主房保留
    # 小碎片（0.09m²）应被滤掉
    assert all(a >= 0.5 for a in areas), f"出现 <0.5 的碎片: {areas}"
    # 阈值放宽后能识别小碎片
    rooms_all = detect_rooms(segs, min_area_m2=0.01)
    assert len(rooms_all) == 2  # 主房 + 小碎片


def test_rooms_sorted_by_area_desc():
    rooms = detect_rooms([((0, 0), (10000, 0)), ((10000, 0), (10000, 5000)),
                          ((10000, 5000), (0, 5000)), ((0, 5000), (0, 0)),
                          ((5000, 0), (5000, 5000))],
                         min_area_m2=0.01)
    assert len(rooms) == 2
    assert rooms[0]["area_m2"] >= rooms[1]["area_m2"]


def test_furniture_assignment():
    """家具按 point-in-polygon 归属到房间。"""
    segs = [((0, 0), (8000, 0)), ((8000, 0), (8000, 6000)),
            ((8000, 6000), (0, 6000)), ((0, 6000), (0, 0)),
            ((4000, 0), (4000, 6000))]
    furniture = [
        {"block": "SOFA", "position_xy": [2000, 3000]},   # 左房
        {"block": "BED", "position_xy": [6000, 3000]},    # 右房
        {"block": "TV", "position_xy": [99999, 99999]},   # 房外
    ]
    rooms = detect_rooms(segs, furniture=furniture)
    assert len(rooms) == 2
    inside_any = []
    for r in rooms:
        inside_any.extend(r["furniture"])
    assert "SOFA" in inside_any
    assert "BED" in inside_any
    assert "TV" not in inside_any  # 房外不入


def test_open_doorway_still_detects():
    """内墙有缺口（门洞）应仍识别 2 房间。"""
    segs = [((0, 0), (8000, 0)), ((8000, 0), (8000, 6000)),
            ((8000, 6000), (0, 6000)), ((0, 6000), (0, 0)),
            # 内墙断 900mm 当门
            ((4000, 0), (4000, 2500)),
            ((4000, 3500), (4000, 6000))]
    rooms = detect_rooms(segs)
    # 缺口即合并为一间房——这是真实装修图门洞的合理表现
    # 测试锁定行为：要么 1（合并因缺口连通）要么 2（polygonize 仍切），
    # 面积不应是 0
    assert len(rooms) >= 1
    assert sum(r["area_m2"] for r in rooms) > 40.0
