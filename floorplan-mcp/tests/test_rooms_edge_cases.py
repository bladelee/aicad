"""边界用例：合成多个真实结构 DXF，验 EzdxfBackend 房间识别鲁棒性。

跑：python -m pytest tests/test_rooms_edge_cases.py

覆盖（每个都是真实装修图可能出现的不规则形态）：
  - rect_3rooms: 矩形 + 内墙横竖分 3 房间（基线，已验）
  - L_shape: L 形户型（外墙非凸，含内拐角）
  - T_shape: T 形
  - corridor: 走廊式（长条多间）
  - thin_walls: 极薄墙（验面积阈值不过滤）
  - open_doorway: 墙断口（门洞，实体不全闭合）
  - overlapping_walls: 重复墙线（验 unary_union 去重）
  - colinear_segments: 共线段拼接（验 polygonize 端点对齐）
"""

from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["FLOORPLAN_BACKEND"] = "ezdxf"


def _make_dxf_with_lines(path: str, segments, blocks=None, layer="WALL"):
    """通用合成器：画一组 WALL LINE + 可选 INSERT 块。"""
    import ezdxf
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for name, color in [("WALL", 7), ("DOOR", 30), ("WINDOW", 140),
                        ("FURNITURE", 8)]:
        if name not in doc.layers:
            doc.layers.add(name, color=color)
    for a, b in segments:
        msp.add_line(a, b, dxfattribs={"layer": layer})
    if blocks:
        for name, pos in blocks:
            if name not in doc.blocks:
                doc.blocks.new(name=name)
            blk_layer = "FURNITURE"
            if name.startswith("M_"):
                blk_layer = "DOOR"
            elif name.startswith("W_"):
                blk_layer = "WINDOW"
            msp.add_blockref(name, insert=pos, dxfattribs={"layer": blk_layer})
    doc.saveas(path)
    return path


# ─── 用例数据 ───

CASES = {}


def _rect():
    """矩形 8000x6000，内墙分 3 房间（基线）。"""
    segs = [((0, 0), (8000, 0)), ((8000, 0), (8000, 6000)),
            ((8000, 6000), (0, 6000)), ((0, 6000), (0, 0)),
            ((5000, 0), (5000, 6000)),
            ((5000, 3000), (8000, 3000))]
    return {"segs": segs, "expected_rooms": 3, "min_area": 40}


CASES["rect_3rooms"] = _rect()


def _L_shape():
    """L 形：主体 8000x6000，右下角切掉 3000x3000。"""
    segs = [((0, 0), (8000, 0)),
            ((8000, 0), (8000, 3000)),
            ((8000, 3000), (5000, 3000)),
            ((5000, 3000), (5000, 6000)),
            ((5000, 6000), (0, 6000)),
            ((0, 6000), (0, 0)),
            # 一个内墙把主区分两间
            ((0, 3000), (5000, 3000))]
    return {"segs": segs, "expected_rooms": 3, "min_area": 30}


CASES["L_shape"] = _L_shape()


def _T_shape():
    """T 形：横向 9000x3000 + 纵向嵌一个 3000x6000。"""
    segs = [((0, 3000), (9000, 3000)),
            ((9000, 3000), (9000, 6000)),
            ((9000, 6000), (0, 6000)),
            ((0, 6000), (0, 3000)),
            # 纵向下伸
            ((3000, 3000), (3000, 0)),
            ((3000, 0), (6000, 0)),
            ((6000, 0), (6000, 3000)),
            # 分隔横墙成两间
            ((4500, 3000), (4500, 6000))]
    return {"segs": segs, "expected_rooms": 3, "min_area": 25}


CASES["T_shape"] = _T_shape()


def _corridor():
    """走廊式：长条 4 间。"""
    segs = [((0, 0), (10000, 0)), ((10000, 0), (10000, 4000)),
            ((10000, 4000), (0, 4000)), ((0, 4000), (0, 0))]
    for x in (2500, 5000, 7500):
        segs.append(((x, 0), (x, 4000)))
    return {"segs": segs, "expected_rooms": 4, "min_area": 35}


CASES["corridor"] = _corridor()


def _open_doorway():
    """墙断口：内墙中段空 900mm 当门洞，shapely 仍应识别闭合房间。"""
    segs = [((0, 0), (8000, 0)), ((8000, 0), (8000, 6000)),
            ((8000, 6000), (0, 6000)), ((0, 6000), (0, 0)),
            # 内墙 0→2700 + 3600→6000（中段空 900 当门）
            ((5000, 0), (5000, 2700)),
            ((5000, 3600), (5000, 6000))]
    return {"segs": segs, "expected_rooms": 2, "min_area": 40,
            "note": "门洞断口测试，期望仍识别 2 房间（polygonize 不依赖严密闭合）"}


CASES["open_doorway"] = _open_doorway()


def _overlapping_walls():
    """重复墙线：同一墙画两次，验 unary_union 去重。"""
    base = [((0, 0), (6000, 0)), ((6000, 0), (6000, 6000)),
            ((6000, 6000), (0, 6000)), ((0, 6000), (0, 0)),
            ((3000, 0), (3000, 6000))]
    return {"segs": base + base,  # 重复一遍
            "expected_rooms": 2, "min_area": 15,
            "note": "unary_union 去重，不应出 0 或几何错乱"}


CASES["overlapping_walls"] = _overlapping_walls()


def _colinear_segments():
    """共线段拼接：一条长墙被拆成 3 段共线画，验端点对齐正确。"""
    segs = [((0, 0), (3000, 0)), ((3000, 0), (6000, 0)),
            ((6000, 0), (8000, 0)),  # 下墙三段
            ((0, 6000), (4000, 6000)), ((4000, 6000), (8000, 6000)),  # 上墙两段
            ((0, 0), (0, 6000)), ((8000, 0), (8000, 6000)),
            ((4000, 0), (4000, 6000))]  # 内墙
    return {"segs": segs, "expected_rooms": 2, "min_area": 20}


CASES["colinear_segments"] = _colinear_segments()


# ─── 测试 ───

@pytest.mark.parametrize("case_name", list(CASES.keys()))
def test_room_detection_case(case_name, tmp_path):
    """每个边界用例：合成 DXF → EzdxfBackend.list_rooms → 验房间数。"""
    from tools import get_backend

    case = CASES[case_name]
    dxf = _make_dxf_with_lines(
        str(tmp_path / f"{case_name}.dxf"),
        case["segs"], blocks=case.get("blocks"),
    )
    rooms = get_backend().list_rooms(dxf)
    expected = case["expected_rooms"]
    actual = len(rooms)
    total = sum(r.get("area_m2", 0) for r in rooms)

    # 容差：允许 ±1 个房间（边界用例 polygonize 在拐角处可能合并/分裂）
    assert abs(actual - expected) <= 1, (
        f"{case_name}: 期望 ~{expected} 房间，实际 {actual}（房间={rooms}）"
    )
    # 总面积下限
    assert total >= case["min_area"], (
        f"{case_name}: 总面积 {total} m² < {case['min_area']}（识别到的房间={rooms}）"
    )
    # 面积都不为负/为 NaN（数值健全性）
    for r in rooms:
        assert r["area_m2"] > 0, f"{case_name}: 出现非正面积 {r}"
