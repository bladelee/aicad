"""深度探查5-节点的 Z节点索引 / 3-平面的 Z立面索引 / Z节点索引 这些 INSERT 块。

假设：这些 INSERT 的 insert 点 / 属性 编码了"指向哪个立面/节点"的映射。

跑法：
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_scan/probe_index_blocks.py"
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path

import ezdxf

DXF_DIR = Path("/data/workdir/19-102/dxf")


def dump_block_attribs(doc, msp, layer_filter: str, max_samples: int = 10):
    """dump 给定图层下 INSERT 块的所有属性"""
    print(f"\n  [{layer_filter}] 图层下的 INSERT 块属性：")
    samples = 0
    block_count = Counter()
    for ent in msp:
        if ent.dxftype() != "INSERT":
            continue
        if ent.dxf.layer != layer_filter:
            continue
        block_count[ent.dxf.name] += 1
        if samples >= max_samples:
            continue
        samples += 1
        print(f"\n    #{samples} 块名={ent.dxf.name!r}, "
              f"insert=({ent.dxf.insert[0]:.0f},{ent.dxf.insert[1]:.0f})")
        try:
            attribs = list(ent.attribs)
            if not attribs:
                print(f"      (无属性)")
            for a in attribs:
                tag = a.dxf.tag if a.dxf.hasattr("tag") else "?"
                val = a.dxf.text if a.dxf.hasattr("text") else ""
                print(f"      attrib {tag!r:20} = {val!r}")
        except Exception as e:
            print(f"      attribs 读取失败: {e}")
    print(f"\n    总计 INSERT 块统计: {dict(block_count)}")


def main():
    print("=== 探查'Z立面索引 / Z节点索引' 等指针块 ===")

    # 1. 3-平面的 Z 立面索引 / Z节点索引
    print("\n" + "=" * 70)
    print(" 1) 3-19-102平面系统图.dxf")
    print("=" * 70)
    p = DXF_DIR / "3-19-102平面系统图.dxf"
    doc = ezdxf.readfile(str(p))
    msp = doc.modelspace()

    for layer in ["Z立面索引", "Z节点索引", "Z材质标注及文字说明"]:
        # 先看本图层是否真的存在
        if layer not in [l.dxf.name for l in doc.layers]:
            print(f"\n  ⚠️ 图层 {layer!r} 不存在")
            continue
        dump_block_attribs(doc, msp, layer, max_samples=8)

    # 2. 4-立面的 Z节点索引
    print("\n" + "=" * 70)
    print(" 2) 4-19-102立面图.dxf")
    print("=" * 70)
    p = DXF_DIR / "4-19-102立面图.dxf"
    doc = ezdxf.readfile(str(p))
    msp = doc.modelspace()
    for layer in ["Z节点索引", "Z立面索引"]:
        if layer not in [l.dxf.name for l in doc.layers]:
            print(f"\n  ⚠️ 图层 {layer!r} 不存在")
            continue
        dump_block_attribs(doc, msp, layer, max_samples=8)

    # 3. 5-节点的 Z节点索引
    print("\n" + "=" * 70)
    print(" 3) 5-19-102节点.dxf")
    print("=" * 70)
    p = DXF_DIR / "5-19-102节点.dxf"
    doc = ezdxf.readfile(str(p))
    msp = doc.modelspace()
    for layer in ["Z节点索引", "Z立面索引"]:
        if layer not in [l.dxf.name for l in doc.layers]:
            print(f"\n  ⚠️ 图层 {layer!r} 不存在")
            continue
        dump_block_attribs(doc, msp, layer, max_samples=8)


if __name__ == "__main__":
    main()
