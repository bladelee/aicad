"""生成更接近真实装修图结构的 DXF 样本（mock 真实 DWG）。

为什么需要：现有 tests/ 的合成样本只有"线段+块"，没覆盖真实装修图的：
  - 门洞断口（墙中段空一段，shapely 应仍能识别闭合房间）
  - HATCH 填充（地砖/地板区域），常带复杂边界
  - DIMENSION 标注（尺寸线），影响渲染但不影响识别
  - TEXT/MTEXT 房间标签
  - 多类型家具 INSERT（沙发/床/桌椅/马桶/冰箱等）
  - AXIS 轴线图层（真实图常有，不应混入 WALL 识别）

本脚本生成 3 套渐进复杂的样本：
  - mock_simple.dxf: 矩形 3 房间（基线，与 integration_ezdxf 对齐）
  - mock_realistic.dxf: 80㎡ 两室一厅，含上述全部真实元素
  - mock_messy.dxf: 故意交叉/断墙/碎化，压力测试

CLI: python tests/fixtures_realistic.py [out_dir]
默认 out_dir = floorplan-mcp/tests/fixtures/
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.math import Vec2


# ─── 标准 5 类图层（真实装修图典型命名）───
LAYERS = {
    "WALL":      {"color": 7},    # 墙体
    "AXIS":      {"color": 1},    # 轴线（不应混入 WALL）
    "DOOR":      {"color": 30},   # 门
    "WINDOW":    {"color": 140},  # 窗
    "FURNITURE": {"color": 8},    # 家具
    "TEXT":      {"color": 3},    # 文字标注
    "DIMENSION": {"color": 2},    # 尺寸标注
    "HATCH":     {"color": 9},    # 填充
}


def _new_doc():
    doc = ezdxf.new("R2010")
    doc.units = ezdxf.units.MM
    for name, attrs in LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, **attrs)
    # 预定义几个家具块（占位形状）
    _define_block(doc, "SOFA_3P",  rectangular=(2100, 850))
    _define_block(doc, "BED_1800", rectangular=(1800, 2000))
    _define_block(doc, "TABLE_DINING", rectangular=(1400, 800))
    _define_block(doc, "CHAIR",    rectangular=(450, 450))
    _define_block(doc, "TV_55",    rectangular=(1200, 80))
    _define_block(doc, "FRIDGE",   rectangular=(600, 600))
    _define_block(doc, "KITCHEN_COUNTER", rectangular=(3000, 600))
    _define_block(doc, "TOILET",   rectangular=(400, 700))
    _define_block(doc, "BATHTUB",  rectangular=(1500, 800))
    _define_block(doc, "WASH_BASIN", rectangular=(500, 400))
    _define_block(doc, "WARDROBE", rectangular=(2000, 600))
    _define_block_with_door_arc(doc, "M_900", width=900)
    _define_block_window(doc, "W_1500", width=1500, wt=240)
    return doc


def _define_block(doc, name, *, rectangular):
    """家具块占位：矩形外框，大小用 rectangular=(w,h)。"""
    w, h = rectangular
    block = doc.blocks.new(name=name)
    block.add_lwpolyline(
        [(0, 0), (w, 0), (w, h), (0, h)],
        close=True, dxfattribs={"layer": "FURNITURE"},
    )


def _define_block_with_door_arc(doc, name, width=900):
    """门块：矩形门板 + 弧线（FREE FREECAD 块名 M_900_...）。"""
    block = doc.blocks.new(name=name)
    block.add_lwpolyline([(0, 0), (40, 0), (40, width), (0, width)],
                         close=True, dxfattribs={"layer": "DOOR"})
    block.add_arc(center=(0, 0), radius=width,
                  start_angle=0, end_angle=90, dxfattribs={"layer": "DOOR"})


def _define_block_window(doc, name, width=1500, wt=240):
    """窗块：上下墙线 + 中线。"""
    block = doc.blocks.new(name=name)
    block.add_line((0, 0), (width, 0), dxfattribs={"layer": "WINDOW"})
    block.add_line((0, wt), (width, wt), dxfattribs={"layer": "WINDOW"})
    block.add_line((0, wt/3), (width, wt/3), dxfattribs={"layer": "WINDOW"})
    block.add_line((0, 2*wt/3), (width, 2*wt/3), dxfattribs={"layer": "WINDOW"})


# ─── 样本 1: 简单 3 房间（基线，对照 integration_ezdxf）───

def make_mock_simple(out):
    doc = _new_doc()
    msp = doc.modelspace()
    # 8000x6000 外框 + 两道内墙
    wall_segs = [((0, 0), (8000, 0)), ((8000, 0), (8000, 6000)),
                 ((8000, 6000), (0, 6000)), ((0, 6000), (0, 0)),
                 ((5000, 0), (5000, 6000)),
                 ((5000, 3000), (8000, 3000))]
    for a, b in wall_segs:
        msp.add_line(a, b, dxfattribs={"layer": "WALL"})
    doc.saveas(str(out / "mock_simple.dxf"))


# ─── 样本 2: 真实 80㎡ 两室一厅 ───

def make_mock_realistic(out):
    """80㎡ 两室一厅，纵向布局：
       外形 8000(宽) x 10000(深)，含：
       - 玄关(底左)/客厅(底中)/餐厅(底右)/厨房(右上)/主卧(上中)/次卧(左上)/卫生间(中)
       - 主卧与客厅墙留 900 门洞
       - 客厅南墙开 1500 窗洞
       - 卫生间配卫浴块、厨房配厨具块、厅配沙发床桌

    ⚠️ 房间识别期望（诊断结论 2026-08-08）：
       因为本设计里"客厅↔餐厅""主卧↔部分走廊"通过拱门/内拐角连通，
       shapely + close_openings=1000 实际识别出 **4 间（≈67.5m²）**，
       不是 7 间。这是 **fixture 设计如此**，不是算法 bug——
       verified via tests/_diag_walls.py（已删，结论留下）。
       真实装修图若房间设计严密（每间独门闭合），房间数会更准。
    """
    doc = _new_doc()
    msp = doc.modelspace()

    # ── 外墙（10 段独立 LINE，模拟真实图）──
    # 南墙开窗洞，西墙开次卧门洞，故插断
    external = [
        # 南墙（开 5500-7000 窗洞）
        ((0, 0), (5500, 0)), ((7000, 0), (8000, 0)),  # 窗洞 5500-7000
        # 东墙
        ((8000, 0), (8000, 10000)),
        # 北墙
        ((8000, 10000), (0, 10000)),
        # 西墙（开 4500-5400 门洞，门外是公共走廊的示意）
        ((0, 10000), (0, 5400)), ((0, 4500), (0, 0)),
    ]
    for a, b in external:
        msp.add_line(a, b, dxfattribs={"layer": "WALL"})

    # ── 隔墙 ──
    internal = [
        # 横墙 y=5000（玄关/客厅 与 厨房/主卧/卫生间 分界），开 3000-4500 门洞
        ((0, 5000), (3000, 5000)), ((4500, 5000), (8000, 5000)),
        # 横墙 y=7500（主卧 与 卫生间+主卧内 卫生间隔）开 3000-3900 主卧门洞
        ((0, 7500), (3000, 7500)), ((3900, 7500), (5500, 7500)),
        # 纵墙 x=5500（客厅 与 餐厅/厨房）开 7000 高门洞（拱门式）
        ((5500, 0), (5500, 5000)),
        # 纵墙 x=3000（卫生间 与 主卧）开 0-800 卫生间门洞
        ((3000, 5000), (3000, 5800)), ((3000, 6700), (3000, 7500)),
        # 纵墙 x=5500（主卧 与 厨房）
        ((5500, 5000), (5500, 10000)),
    ]
    for a, b in internal:
        msp.add_line(a, b, dxfattribs={"layer": "WALL"})

    # ── 轴线（不应混入识别）──
    for x in (0, 3000, 5500, 8000):
        msp.add_line((x, -500), (x, 10500),
                     dxfattribs={"layer": "AXIS"})
    for y in (0, 5000, 7500, 10000):
        msp.add_line((-500, y), (8500, y),
                     dxfattribs={"layer": "AXIS"})

    # ── 家具 INSERT（多类型）──
    furniture = [
        # 客厅（中下，x: 5500-8000, y: 0-5000）
        ("SOFA_3P", (5700, 500), 0),
        ("TV_55",   (6800, 4400), 0),
        ("CHAIR",   (6200, 2000), 0),
        # 餐厅（右下角空着，已并入客厅）
        # 厨房（右上，x:5500-8000, y:5000-10000）
        ("KITCHEN_COUNTER", (5700, 5300), 0),
        ("FRIDGE", (5700, 9200), 0),
        # 主卧（中上，x: 0-5500, y: 7500-10000）
        ("BED_1800", (500, 8000), 0),
        ("WARDROBE", (3000, 7700), 0),
        # 次卧 / 卫生间（左上、中）
        ("TOILET",  (1000, 6800), 0),
        ("BATHTUB", (4500, 5300), 0),
        ("WASH_BASIN", (1500, 5300), 0),
        ("BED_1800", (100, 5200), 90),  # 次卧
        # 餐桌（贴餐厅区）
        ("TABLE_DINING", (6500, 3000), 0),
    ]
    for name, pos, rot in furniture:
        msp.add_blockref(name, insert=pos, dxfattribs={
            "layer": "FURNITURE", "rotation": rot})

    # ── 门窗 INSERT ──
    openings = [
        ("M_900",   (3000, 5000), 0),    # 走廊进客厅
        ("M_900",   (3000, 7500), 90),   # 进主卧
        ("M_900",   (3000, 5800), 90),   # 进卫生间（半开门洞示意）
        ("W_1500",  (5500, 0),   0),     # 南墙大窗
    ]
    for name, pos, rot in openings:
        msp.add_blockref(name, insert=pos, dxfattribs={
            "layer": "WINDOW" if name.startswith("W_") else "DOOR",
            "rotation": rot})

    # ── HATCH 填充（客厅地板砖 600x600）──
    hatch = msp.add_hatch(color=9, dxfattribs={"layer": "HATCH"})
    hatch.paths.add_polyline_path(
        [(5500, 0), (8000, 0), (8000, 5000), (5500, 5000)], is_closed=True)
    hatch.set_pattern_fill("AR-CONC", scale=600)
    # 厨房填充（与客厅不同 pattern）
    hatch2 = msp.add_hatch(color=9, dxfattribs={"layer": "HATCH"})
    hatch2.paths.add_polyline_path(
        [(5500, 5000), (8000, 5000), (8000, 10000), (5500, 10000)], is_closed=True)
    hatch2.set_pattern_fill("HONEY", scale=200)

    # ── TEXT 标注 ──
    rooms_text = [
        ("客厅", 6700, 2500, 300),
        ("厨房", 6700, 7500, 300),
        ("主卧", 2500, 8700, 300),
        ("卫生间", 1500, 5800, 200),
        ("次卧", 1500, 7200, 300),
        ("玄关", 1500, 2500, 200),
    ]
    for text, x, y, h in rooms_text:
        msp.add_text(text, dxfattribs={
            "height": h, "layer": "TEXT"}).set_placement(
            (x, y), align=TextEntityAlignment.MIDDLE_CENTER)

    # ── DIMENSION 标注（南墙总宽）──
    msp.add_linear_dim(base=(0, -1500), p1=(0, 0), p2=(8000, 0),
                       dxfattribs={"layer": "DIMENSION"})
    msp.add_linear_dim(base=(-1500, 0), p1=(0, 0), p2=(0, 10000),
                       angle=90, dxfattribs={"layer": "DIMENSION"})

    doc.saveas(str(out / "mock_realistic.dxf"))
    return doc


# ─── 样本 3: messy 压力测试 ───

def make_mock_messy(out):
    """故意制造难识别：墙断口/多段共线/小碎片/AXIS 干扰/重复线。"""
    doc = _new_doc()
    msp = doc.modelspace()
    # 主体 10000x10000，被多段共线 / 重线 / 小碎片墙切碎
    base = [((0, 0), (5000, 0)), ((5000, 0), (10000, 0)),
            ((0, 10000), (5000, 10000)), ((5000, 10000), (10000, 10000)),
            ((0, 0), (0, 5000)), ((0, 5000), (0, 10000)),
            ((10000, 0), (10000, 5000)), ((10000, 5000), (10000, 10000))]
    # 内部分割
    base += [((5000, 0), (5000, 5000)), ((5000, 5000), (5000, 10000)),
             ((0, 5000), (5000, 5000)), ((5000, 5000), (10000, 5000))]
    # 重复画一遍（验 unary_union 去重）
    segs = base + base
    # 中间小碎片（应被滤掉）
    segs += [((2000, 2000), (2000, 2200)), ((2000, 2200), (2200, 2200)),
             ((2200, 2200), (2200, 2000)), ((2200, 2000), (2000, 2000))]
    # 假墙混入 AXIS
    for a, b in segs:
        msp.add_line(a, b, dxfattribs={"layer": "WALL"})
    # AXIS 干扰
    for x in (0, 2500, 5000, 7500, 10000):
        msp.add_line((x, -200), (x, 10200), dxfattribs={"layer": "AXIS"})
    for y in (0, 2500, 5000, 7500, 10000):
        msp.add_line((-200, y), (10200, y), dxfattribs={"layer": "AXIS"})
    doc.saveas(str(out / "mock_messy.dxf"))


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 \
        else Path(__file__).parent / "fixtures"
    out.mkdir(parents=True, exist_ok=True)
    make_mock_simple(out)
    make_mock_realistic(out)
    make_mock_messy(out)
    print(f"✓ 生成 3 套样本到 {out}/:")
    for f in sorted(out.glob("*.dxf")):
        size_kb = f.stat().st_size // 1024
        print(f"  {f.name:30s} {size_kb:>4} KB")


if __name__ == "__main__":
    main()
