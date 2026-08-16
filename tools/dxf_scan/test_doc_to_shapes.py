# -*- coding: utf-8 -*-
"""tools/dxf_scan/doc_to_shapes.py 的单元测试。

跑法（宿主机 miniconda 已装 ezdxf 1.4.4，无需 docker）：
    cd /Users/bladelee/project/cad
    /Users/bladelee/miniconda3/bin/python tools/dxf_scan/test_doc_to_shapes.py

知识点参考 docs/借鉴-wheel-drawing-tools-参数化模式.md §3.1 / §五 A2。
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ezdxf  # noqa: E402

from doc_to_shapes import (  # noqa: E402
    doc_to_shapes,
    dxf_to_shapes,
    filter_shapes_by_layer,
    get_xy,
    save_shapes_json,
    shapes_bbox,
)


# ---------- 测试 fixtures ----------

def _build_doc():
    """合成一个最小 DXF：2 条线（不同图层）+ 1 圆 + 1 弧 + 1 闭合多段线 + 1 HATCH。

    覆盖 wheel 原版支持的全部四种几何类型 + 本项目新增的 HATCH。
    """
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    # 用 wall 真实图层名，确保 case 跟生产场景一致
    msp.add_line((0, 0), (100, 0), dxfattribs={"layer": "A原建筑墙体"})
    msp.add_line((100, 0), (100, 50), dxfattribs={"layer": "A原建筑尺寸"})
    msp.add_circle((200, 200), radius=10, dxfattribs={"layer": "TEST_CIRCLE"})
    msp.add_arc((50, 50), radius=20, start_angle=0, end_angle=90,
                dxfattribs={"layer": "TEST_ARC"})
    pl = msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)],
                            dxfattribs={"layer": "TEST_POLY", "closed": True})
    # HATCH：A原建筑墙体填充 图层（生产里就是这种）
    hatch = msp.add_hatch(color=7, dxfattribs={"layer": "A原建筑墙体填充"})
    hatch.paths.add_polyline_path(
        [(1000, 1000), (1100, 1000), (1100, 1100), (1000, 1100)],
        is_closed=True,
    )
    return doc


# ---------- get_xy ----------

def test_get_xy_extracts_2d_point():
    doc = _build_doc()
    line = doc.modelspace().query("LINE")[0]
    sx, sy = get_xy(line, "start")
    assert (sx, sy) == (0.0, 0.0)
    ex, ey = get_xy(line, "end")
    assert (ex, ey) == (100.0, 0.0)


def test_get_xy_missing_returns_zero():
    doc = _build_doc()
    line = doc.modelspace().query("LINE")[0]
    # LINE 实体没有 center 字段
    cx, cy = get_xy(line, "center")
    assert (cx, cy) == (0.0, 0.0)


# ---------- doc_to_shapes：类型覆盖 ----------

def test_doc_to_shapes_extracts_all_types():
    doc = _build_doc()
    shapes = doc_to_shapes(doc)
    types = [s["type"] for s in shapes]
    # LINE: 2 + LWPOLYLINE 闭合拆 4 段 + HATCH(矩形) 闭合拆 4 段 = 10 个 line；circle 1；arc 1
    assert types.count("line") == 10
    assert types.count("circle") == 1
    assert types.count("arc") == 1


def test_doc_to_shapes_line_values():
    doc = _build_doc()
    shapes = doc_to_shapes(doc)
    lines = [s for s in shapes if s["type"] == "line"]
    # 找到那条从 (0,0) -> (100,0) 的墙线
    wall = next(s for s in lines if s["x1"] == 0.0 and s["y1"] == 0.0
                and s["x2"] == 100.0 and s["y2"] == 0.0)
    assert wall["layer"] == "A原建筑墙体"
    assert "handle" in wall and wall["handle"]


def test_doc_to_shapes_circle_values():
    doc = _build_doc()
    shapes = doc_to_shapes(doc)
    c = next(s for s in shapes if s["type"] == "circle")
    assert c["cx"] == 200.0 and c["cy"] == 200.0
    assert c["r"] == 10.0
    assert c["layer"] == "TEST_CIRCLE"


def test_doc_to_shapes_arc_values():
    doc = _build_doc()
    shapes = doc_to_shapes(doc)
    a = next(s for s in shapes if s["type"] == "arc")
    assert a["cx"] == 50.0 and a["cy"] == 50.0
    assert a["r"] == 20.0
    assert a["start_angle"] == 0.0
    assert a["end_angle"] == 90.0
    assert a["layer"] == "TEST_ARC"


def test_doc_to_shapes_polyline_closed_breaks_to_4_lines():
    """LWPOLYLINE(4 点 + 闭合) 应该拆成 4 段 line（默认行为，对齐 wheel）"""
    doc = _build_doc()
    shapes = doc_to_shapes(doc)
    poly_lines = [s for s in shapes if s["type"] == "line" and s["layer"] == "TEST_POLY"]
    assert len(poly_lines) == 4  # 4 段闭合线


def test_doc_to_shapes_polyline_kept_as_polyline_when_no_break():
    doc = _build_doc()
    shapes = doc_to_shapes(doc, line_break=False)
    polys = [s for s in shapes if s["type"] == "polyline"]
    # 两条：LWPOLYLINE(4 点) + HATCH PolylinePath(4 点)
    assert len(polys) == 2
    for p in polys:
        assert p["closed"] is True
        assert len(p["points"]) == 4
    # 区分一下：TEST_POLY 是 LWPOLYLINE，A原建筑墙体填充 是 HATCH
    layers = {p["layer"] for p in polys}
    assert "TEST_POLY" in layers
    assert "A原建筑墙体填充" in layers


# ---------- HATCH 支持（本项目新增，wheel 原版无） ----------

def test_doc_to_shapes_hatch_polyline_path_breaked():
    """闭合矩形 HATCH 应拆成 4 段 line，layer=HATCH 所在图层"""
    doc = _build_doc()
    shapes = doc_to_shapes(doc, layers=["A原建筑墙体填充"])
    lines = [s for s in shapes if s["type"] == "line"]
    assert len(lines) == 4  # 矩形 4 条边
    assert all(s["layer"] == "A原建筑墙体填充" for s in lines)
    # 矩形顶点都应该 ≥ 1000（fixture 里加在 (1000,1000) 区域）
    xs = [s["x1"] for s in lines] + [s["x2"] for s in lines]
    assert min(xs) >= 1000


def test_doc_to_shapes_hatch_kept_as_polyline_when_no_break():
    doc = _build_doc()
    shapes = doc_to_shapes(doc, layers=["A原建筑墙体填充"], line_break=False)
    polys = [s for s in shapes if s["type"] == "polyline"]
    assert len(polys) == 1
    assert polys[0]["closed"] is True
    assert len(polys[0]["points"]) == 4


# ---------- 过滤 ----------

def test_doc_to_shapes_filter_by_layer():
    doc = _build_doc()
    shapes = doc_to_shapes(doc, layers=["A原建筑墙体"])
    assert all(s["layer"] == "A原建筑墙体" for s in shapes)
    # 只剩那条墙线（其他都被过滤）
    assert len([s for s in shapes if s["type"] == "line"]) == 1


def test_doc_to_shapes_filter_by_multiple_layers():
    doc = _build_doc()
    shapes = doc_to_shapes(doc, layers=["A原建筑墙体", "A原建筑尺寸"])
    layers_seen = set(s["layer"] for s in shapes)
    assert layers_seen == {"A原建筑墙体", "A原建筑尺寸"}


def test_filter_shapes_by_layer_postfilter():
    doc = _build_doc()
    all_shapes = doc_to_shapes(doc)
    only_wall = filter_shapes_by_layer(all_shapes, ["A原建筑墙体"])
    assert len(only_wall) == 1
    assert only_wall[0]["layer"] == "A原建筑墙体"


# ---------- handle 控制 ----------

def test_doc_to_shapes_without_handles():
    doc = _build_doc()
    shapes = doc_to_shapes(doc, include_handles=False)
    # 对齐 wheel 原版行为：不带 layer / handle
    s0 = shapes[0]
    assert "layer" not in s0
    assert "handle" not in s0


# ---------- bbox ----------

def test_shapes_bbox_lines():
    doc = _build_doc()
    shapes = doc_to_shapes(doc, layers=["A原建筑墙体"])
    bbox = shapes_bbox(shapes)
    # 单条 (0,0)->(100,0) 线
    assert bbox == (0.0, 100.0, 0.0, 0.0)


def test_shapes_bbox_circle_includes_radius():
    shapes = [{"type": "circle", "cx": 100, "cy": 100, "r": 50}]
    bbox = shapes_bbox(shapes)
    assert bbox == (50.0, 150.0, 50.0, 150.0)


def test_shapes_bbox_empty_returns_none():
    assert shapes_bbox([]) is None


# ---------- JSON 持久化 ----------

def test_save_shapes_json_roundtrip():
    import json
    doc = _build_doc()
    shapes = doc_to_shapes(doc, layers=["A原建筑墙体"])
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "test.json")
        ret = save_shapes_json(shapes, out, meta={"source_dxf": "fake.dxf"})
        assert ret == out
        with open(out, encoding="utf-8") as fp:
            payload = json.load(fp)
        assert payload["shape_count"] == 1
        assert payload["meta"]["source_dxf"] == "fake.dxf"
        assert payload["shapes"][0]["layer"] == "A原建筑墙体"


def test_dxf_to_shapes_file_roundtrip():
    """完整跑一遍：new doc → saveas DXF → dxf_to_shapes →"""
    doc = _build_doc()
    with tempfile.TemporaryDirectory() as d:
        dxf_path = os.path.join(d, "synthetic.dxf")
        doc.saveas(dxf_path)
        shapes = dxf_to_shapes(dxf_path, layers=["A原建筑墙体"])
        assert len(shapes) == 1
        assert shapes[0]["x1"] == 0.0
        assert shapes[0]["x2"] == 100.0


# ---------- CLI 直跑兼容 ----------

def _run_all():
    mod = sys.modules[__name__]
    tests = sorted(
        name for name in dir(mod)
        if name.startswith("test_") and callable(getattr(mod, name))
    )
    passed, failed = 0, 0
    for name in tests:
        try:
            getattr(mod, name)()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed (of {len(tests)})")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
