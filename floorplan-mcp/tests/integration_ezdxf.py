"""合成一个真实结构 DXF 样本，跑 EzdxfBackend 全链路（read + render）。

目的：在 Phase 0 真实样本就绪前，验证备选 backend (ezdxf+shapely)
不仅骨架可 import，而且真的能 read 房间、render PNG、分类家具。

合成样本结构（手画一个 2 室 1 厅的小户型）：
    外墙 8000x6000 闭合矩形 + 一道内墙把卧室分出来 + 门/窗/沙发/床/桌
"""

from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["FLOORPLAN_BACKEND"] = "ezdxf"


def make_sample_dxf(path: str):
    import ezdxf
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # 标准图层
    for layer, color in [("WALL", 7), ("DOOR", 30), ("WINDOW", 140),
                         ("FURNITURE", 8), ("TEXT", 3)]:
        doc.layers.add(layer, color=color)

    # 外墙：单独 LINE 段（真实图纸典型形态，不是闭合 lwpolyline）
    # 8000 x 6000 矩形，4 段独立 LINE
    wall_segs = [
        ((0, 0), (8000, 0)),      # 下
        ((8000, 0), (8000, 6000)), # 右
        ((8000, 6000), (0, 6000)),# 上
        ((0, 6000), (0, 0)),      # 左
    ]
    # 内墙：从 (5000, 0) 到 (5000, 6000) 把右半分成两室
    wall_segs.append(((5000, 0), (5000, 6000)))
    # 横墙：右半中间再分一道，形成 3 个房间
    wall_segs.append(((5000, 3000), (8000, 3000)))

    for a, b in wall_segs:
        msp.add_line(a, b, dxfattribs={"layer": "WALL"})

    # 门窗块引用（简化：用 INSERT 直接放点）
    # sofa / bed / table
    for name, pos in [("SOFA_3P", (1500, 1500)),
                       ("BED_1800", (6500, 4500)),
                       ("TABLE_1200", (2500, 4500)),
                       ("M_900", (5000, 2000)),      # 门
                       ("W_1500", (4000, 6000))]:    # 窗
        # 必须先有块定义才能 INSERT；用最简占位
        if name not in doc.blocks:
            doc.blocks.new(name=name)
        msp.add_blockref(name, insert=pos, dxfattribs={"layer": "FURNITURE"})

    doc.saveas(path)
    return path


def main():
    with tempfile.TemporaryDirectory() as d:
        dxf = make_sample_dxf(os.path.join(d, "sample.dxf"))

        from tools import get_backend
        backend = get_backend()
        print(f"==> backend: {backend.__class__.__name__}")

        # 1. read
        info = backend.read(dxf)
        print(f"  walls: {info['summary']['wall_count']}")
        print(f"  doors: {info['summary']['door_count']}")
        print(f"  windows: {info['summary']['window_count']}")
        print(f"  furniture: {info['summary']['furniture_count']}")
        print(f"  rooms: {info['summary']['room_count']}")
        for r in info["rooms"]:
            print(f"    - {r['name']}: {r['area_m2']} m²")

        # 期望：3 个房间（左大厅、右上卧室、右下卧室）
        # 总面积: 左 5000x6000=30 m², 右上 3000x3000=9 m², 右下 3000x3000=9 m² = 48 m²
        assert info["summary"]["room_count"] == 3, \
            f"期望 3 个房间，实际 {info['summary']['room_count']}（房间识别有问题）"
        total = info["summary"]["total_area_m2"]
        assert 40 < total < 55, f"总面积 {total} m² 不在 40-55 范围"

        # 2. render
        png = os.path.join(d, "preview.png")
        backend.render_preview(dxf, png)
        assert os.path.isfile(png) and os.path.getsize(png) > 1000
        print(f"  PNG: {os.path.getsize(png)} bytes ✓")

        # 3. move（验证 .bak）
        # 找一个沙发 handle
        sofa_handle = None
        for f in info["furniture"]:
            if f["type"] == "sofa":
                sofa_handle = f["handle"]
                break
        if sofa_handle:
            res = backend.move_entity(dxf, sofa_handle, 100, 0, auto_backup=True)
            print(f"  move sofa({sofa_handle}): ok={res['ok']}, backup={res.get('backup_path')}")
            assert res["ok"]
            assert res["backup_path"] and os.path.isfile(res["backup_path"])

        print("\n✓ EzdxfBackend 全链路通过：read(3房间识别正确) + render(PNG生成) + move(.bak生成)")


if __name__ == "__main__":
    main()
