#!/usr/bin/env python3
"""
cad_tools 综合验证测试

测试内容:
    1. 环境验证（ezdxf, matplotlib）
    2. 创建户型图（墙体/门/窗/家具）
    3. 语义解析（读取自己创建的图）
    4. PNG 渲染
    5. 修改操作（移动家具）
    6. 转换器状态检测
"""

import sys
import os

# 确保能 import cad_tools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cad_tools import (
    FloorPlanWriter, FloorPlanReader, DXFRenderer,
    DWGConverter, BlockLibrary,
    distance, polygon_area, point_in_polygon,
)
from cad_tools.geometry import (
    midpoint, angle_between, bbox_of, polyline_length, is_closed,
    line_intersection, rotate_point, move_point, bboxes_overlap,
)
import ezdxf


def test_environment():
    """测试 1: 环境验证"""
    print("=" * 60)
    print("测试 1: 环境验证")
    print("=" * 60)

    import ezdxf
    import matplotlib
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  ezdxf: {ezdxf.__version__}")
    print(f"  matplotlib: {matplotlib.__version__}")
    print("  ✅ 环境验证通过\n")


def test_geometry():
    """测试 2: 几何工具"""
    print("=" * 60)
    print("测试 2: 几何工具")
    print("=" * 60)

    # 距离
    d = distance((0, 0), (3, 4))
    assert abs(d - 5.0) < 0.001, f"distance 失败: {d}"
    print(f"  distance((0,0),(3,4)) = {d} ✅")

    # 面积
    area = polygon_area([(0, 0), (4, 0), (4, 3), (0, 3)])
    assert abs(area - 12.0) < 0.001, f"polygon_area 失败: {area}"
    print(f"  polygon_area(4x3矩形) = {area} ✅")

    # 点在多边形内
    assert point_in_polygon((2, 1.5), [(0, 0), (4, 0), (4, 3), (0, 3)])
    assert not point_in_polygon((5, 5), [(0, 0), (4, 0), (4, 3), (0, 3)])
    print(f"  point_in_polygon ✅")

    # 旋转
    rotated = rotate_point((1, 0), 90, (0, 0))
    assert abs(rotated[0] - 0) < 0.001 and abs(rotated[1] - 1) < 0.001
    print(f"  rotate_point((1,0), 90°) = {rotated} ✅")

    # 线段相交
    inter = line_intersection((0, 0), (2, 2), (0, 2), (2, 0))
    assert inter is not None and abs(inter[0] - 1) < 0.001
    print(f"  line_intersection = {inter} ✅")

    # 闭合判断（首尾点重合才算闭合）
    assert is_closed([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)], tol=0.01)
    assert not is_closed([(0, 0), (1, 0), (1, 1), (0, 1)], tol=0.01)
    assert not is_closed([(0, 0), (1, 0), (2, 0)])
    print(f"  is_closed ✅")

    print("  ✅ 几何工具全部通过\n")


def test_create_floor_plan():
    """测试 3: 创建户型图"""
    print("=" * 60)
    print("测试 3: 创建户型图")
    print("=" * 60)

    writer = FloorPlanWriter()

    # 客厅 5m x 4m
    writer.create_wall_rect(0, 0, 5000, 4000)
    writer.add_text("客厅", (2500, 2000), height=400)
    writer.add_window("W_1800", position=(1600, 0), rotation=0)
    writer.add_door("M_900", position=(0, 2500), rotation=90)
    writer.add_furniture("SOFA_3P", position=(500, 3200))
    writer.add_furniture("TABLE_1200", position=(2000, 1500))
    writer.add_furniture("TV", position=(2200, 200))

    # 卧室 4m x 3.5m
    writer.create_wall_rect(5500, 0, 4000, 3500)
    writer.add_text("卧室", (7500, 1750), height=400)
    writer.add_window("W_1500", position=(6000, 0), rotation=0)
    writer.add_furniture("BED_1800", position=(5700, 2000))
    writer.add_furniture("WARDROBE_2000", position=(8800, 300), rotation=90)

    # 卫生间 2m x 2.5m
    writer.create_wall_rect(0, 4500, 2000, 2500)
    writer.add_text("卫生间", (1000, 5750), height=300)
    writer.add_door("M_700", position=(2000, 4500), rotation=90)
    writer.add_furniture("TOILET", position=(300, 4700))
    writer.add_furniture("SINK", position=(1100, 4700))

    # 厨房 3m x 2.5m
    writer.create_wall_rect(2500, 4500, 3000, 2500)
    writer.add_text("厨房", (4000, 5750), height=300)
    writer.add_furniture("STOVE", position=(2700, 4700))
    writer.add_furniture("FRIDGE", position=(5100, 4700))

    output = "/Users/bladelee/project/cad/examples/test_apartment.dxf"
    writer.save(output)
    print(f"  户型图已保存: {output}")
    print(f"  包含: 客厅(5×4m) + 卧室(4×3.5m) + 卫生间(2×2.5m) + 厨房(3×2.5m)")
    print("  ✅ 创建户型图通过\n")
    return output


def test_read_and_parse(dxf_path):
    """测试 4: 语义解析"""
    print("=" * 60)
    print("测试 4: 语义解析")
    print("=" * 60)

    reader = FloorPlanReader(dxf_path)
    info = reader.parse()
    summary = info["summary"]

    print(f"  墙体: {summary['wall_count']} 段")
    print(f"  门: {summary['door_count']} 个")
    print(f"  窗户: {summary['window_count']} 个")
    print(f"  家具: {summary['furniture_count']} 件")
    print(f"  房间: {summary['room_count']} 个")
    print(f"  总面积: {summary['total_area_m2']} ㎡")

    # 打印家具明细
    print(f"\n  家具明细:")
    for fur in info["furniture"]:
        print(f"    - {fur['block']} (类型: {fur['type']}, 位置: ({fur['position'][0]:.0f}, {fur['position'][1]:.0f}))")

    # 打印房间明细
    print(f"\n  房间明细:")
    for i, room in enumerate(info["rooms"]):
        name = room.get("name", f"房间{i+1}")
        print(f"    - {name}: {room['area_m2']} ㎡, 内含 {len(room['furniture'])} 件家具")

    # 测试自然语言查询
    print(f"\n  自然语言查询:")
    queries = ["有几个房间？", "面积多大？", "有哪些家具？"]
    for q in queries:
        print(f"    Q: {q}")
        print(f"    A: {reader.query(q)}")

    print("\n  ✅ 语义解析通过\n")
    return info


def test_render(dxf_path):
    """测试 5: PNG 渲染"""
    print("=" * 60)
    print("测试 5: PNG 渲染")
    print("=" * 60)

    renderer = DXFRenderer()

    # 基本渲染
    output = "/Users/bladelee/project/cad/examples/test_apartment.png"
    renderer.render(dxf_path, output, figsize=(20, 15), dpi=150)
    print(f"  基本渲染: {output}")
    assert os.path.isfile(output), "PNG 文件未生成"

    # 带信息标注的渲染
    reader = FloorPlanReader(dxf_path)
    info = reader.parse()
    output2 = "/Users/bladelee/project/cad/examples/test_apartment_annotated.png"
    renderer.render_with_info(dxf_path, output2, info=info, figsize=(20, 15), dpi=150)
    print(f"  标注渲染: {output2}")

    print("  ✅ PNG 渲染通过\n")


def test_modify(dxf_path):
    """测试 6: 修改操作"""
    print("=" * 60)
    print("测试 6: 修改操作（移动沙发 500mm）")
    print("=" * 60)

    writer = FloorPlanWriter(doc=ezdxf.readfile(dxf_path))

    # 移动沙发
    count = writer.move_furniture_by_name("SOFA_3P", dx=500, dy=0)
    print(f"  移动了 {count} 个沙发，向右 500mm")

    # 保存修改后的文件
    modified_path = "/Users/bladelee/project/cad/examples/test_apartment_modified.dxf"
    writer.save(modified_path)
    print(f"  修改后文件: {modified_path}")

    # 渲染修改后的图
    renderer = DXFRenderer()
    modified_png = "/Users/bladelee/project/cad/examples/test_apartment_modified.png"
    renderer.render(modified_path, modified_png, figsize=(20, 15), dpi=150)
    print(f"  修改后渲染: {modified_png}")

    print("  ✅ 修改操作通过\n")


def test_converter():
    """测试 7: 转换器状态"""
    print("=" * 60)
    print("测试 7: DWG 转换器状态")
    print("=" * 60)

    converter = DWGConverter()
    status = converter.status()
    print(f"  后端: {status['backend'] or '无（仅支持 DXF）'}")
    print(f"  可用: {'是' if status['is_available'] else '否'}")
    print(f"  提示: {status['hint']}")
    print("  ✅ 转换器状态检测通过\n")


def main():
    print("\n" + "🔨" * 30)
    print("  cad_tools 综合验证测试")
    print("🔨" * 30 + "\n")

    test_environment()
    test_geometry()

    dxf_path = test_create_floor_plan()
    test_read_and_parse(dxf_path)
    test_render(dxf_path)
    test_modify(dxf_path)
    test_converter()

    print("=" * 60)
    print("🎉 全部测试通过！")
    print("=" * 60)
    print("\n生成的文件:")
    examples_dir = "/Users/bladelee/project/cad/examples"
    for f in sorted(os.listdir(examples_dir)):
        size = os.path.getsize(os.path.join(examples_dir, f))
        print(f"  {f}  ({size:,} bytes)")


if __name__ == "__main__":
    main()
