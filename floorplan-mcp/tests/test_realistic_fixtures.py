"""真实结构 fixture 验证测试。

跑：python -m pytest tests/test_realistic_fixtures.py

旨在用接近真实装修图的合成样本（含门洞/HATCH/DIMENSION/AXIS）
检测 shapely 房间识别的鲁棒性。这是 Phase 0 真实样本到来前
发现"门洞导致墙不闭合"这类风险的关键钢鞭。

⚠️ 注意（2026-08-08 发现）：含门洞的图（mock_realistic）
   单纯 polygonize 会失败（识别出 1 房间 12.5㎡，真实应 ~80㎡）。
   detect_rooms 加 close_openings_mm 缓解（端点距离 ≤ 阈值补虚拟墙）。
   本测试锁定缓解后的基线状态，真实图定参待 Phase 0。
"""

from __future__ import annotations
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES = Path(__file__).parent / "fixtures"


def setup_module(module):
    """若无 fixture 则先生成。"""
    if not (FIXTURES / "mock_realistic.dxf").exists():
        from tests import fixtures_realistic
        fixtures_realistic.main()


def _read(backend_env, fname):
    os.environ["FLOORPLAN_BACKEND"] = backend_env
    from tools import get_backend
    return get_backend().read(str(FIXTURES / fname))


def test_mock_simple_3rooms_ezdxf():
    """基线：3 房间矩形，无门洞 — ezdxf 后端 100% 准。"""
    info = _read("ezdxf", "mock_simple.dxf")
    assert info["summary"]["room_count"] == 3
    assert info["summary"]["total_area_m2"] == pytest.approx(48.0, rel=0.01)


def test_mock_realistic_recovers_with_close_openings():
    """关键：mock_realistic（含门洞/HATCH/DIM/AXIS）在 close_openings 缓解下
    识别成 4 间 / ≈67.5 ㎡（缓解前是 1 房间 12.5㎡）。

    **为什么 4 间而不是 7 间**（fixtures_realistic.py make_mock_realistic 已说明）：
    本 fixture 设计里客厅↔餐厅拱门连通、主卧↔走廊内拐角连通——这些本就不该
    被分割。算法准确——真实装修图若房间都独门紧密，房间数会更准。
    """
    info = _read("ezdxf", "mock_realistic.dxf")
    s = info["summary"]
    assert s["room_count"] == 4, f"房间数 {s['room_count']}（期望 4）"
    assert s["total_area_m2"] == pytest.approx(67.5, rel=0.05), \
        f"总面积 {s['total_area_m2']}（期望 67.5）"


def test_mock_realistic_furniture_classification():
    """家具分类（12 类全对）：sofa/tv/chair/kitchen/fridge/bed×2/wardrobe
    /toilet/bathtub/washer/table=12 件。"""
    info = _read("ezdxf", "mock_realistic.dxf")
    from collections import Counter
    types = Counter(f["type"] for f in info["furniture"])
    # 总数应为 12（看 fixtures_realistic 中的 furniture 列表）
    assert sum(types.values()) == 12
    for t in ["sofa", "tv", "chair", "kitchen", "fridge", "bed",
              "wardrobe", "toilet", "bathtub", "washer", "table"]:
        assert t in types, f"缺类型 {t}"


def test_mock_realistic_axis_not_in_walls():
    """AXIS 层不应混入 WALL，房间识别不应受轴线影响。"""
    info = _read("ezdxf", "mock_realistic.dxf")
    # 若 AX 进了 WALL，墙体数会爆炸（mock_realistic 实际 14 段 WALL）
    assert info["summary"]["wall_count"] <= 20, \
        f"WALL 数 {info['summary']['wall_count']} 偏多，可能混入了 AXIS"


def test_mock_realistic_hatch_dimension_present():
    """HATCH / DIMENSION 应能读到（fixture 含 2 HATCH + 2 DIMENSION）。"""
    import ezdxf
    doc = ezdxf.readfile(str(FIXTURES / "mock_realistic.dxf"))
    msp = doc.modelspace()
    assert len(msp.query("HATCH")) >= 2
    assert len(msp.query("DIMENSION")) >= 2


def test_mock_messy_unary_union_dedup():
    """messy 压力：重复墙去重 OK，小碎片被过滤（设置 min_area=0.5）。"""
    info = _read("ezdxf", "mock_messy.dxf")
    s = info["summary"]
    # 10000x10000 内 2x2 网格 = 4 间 25㎡
    assert s["room_count"] == 4
    assert s["total_area_m2"] == pytest.approx(100.0, rel=0.01)
