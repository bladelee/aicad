"""任务 #10 调研：门的分布与结构。

回答 3 个问题：
1. 哪些图层/块代表门？（候选：图层含"门"、块名含 DOOR/M_/MC/MC_）
2. 门是 INSERT 块还是单独的 LINE/ARC？
3. 块定义里的几何怎么算"宽度"？是 x-scale 还是几何长度？

宿主机用：
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_scan/probe_doors.py"
"""
from __future__ import annotations
import re
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf

DXF_DIR = Path("/data/workdir/19-102/dxf")

# 候选判断
DOOR_LAYER_KEYS = ("门", "DOOR")
DOOR_BLOCK_KEYS = ("DOOR", "DOOR_", "M_", "MC_", "MEN", "YMKDOOR")


def is_door_layer(name: str) -> bool:
    n = (name or "").upper()
    return any(k in n for k in DOOR_LAYER_KEYS)


def is_door_block(name: str) -> bool:
    n = (name or "").upper()
    return any(k in n for k in DOOR_BLOCK_KEYS)


def main():
    print("=== #10 门分布调研（精简版，只扫 modelspace）===\n")

    for dxf in sorted(DXF_DIR.glob("*.dxf")):
        # 跳过非业务图
        if "XINLU" in dxf.stem or "1-19-102封面" in dxf.stem or "2-19-102材料表" in dxf.stem:
            continue
        doc = ezdxf.readfile(str(dxf))
        name = dxf.stem.split("-19-102")[-1] or dxf.stem
        print(f"--- {name} ---")

        # 只扫 modelspace（避免 layouts 遍历卡死）
        msp = doc.modelspace()
        layer_names = {l.dxf.name for l in doc.layers}
        shared_door_layer = "A原建筑外幕墙，门，窗"
        has_shared = shared_door_layer in layer_names
        local_door_layers = [n for n in layer_names if "门" in n or "DOOR" in n.upper()]
        print(f"  含'门'的图层: {local_door_layers}")
        print(f"  共享'门窗'图层 {'✓' if has_shared else '✗'}: {shared_door_layer!r}")

        # 统计门窗图层实体
        target = set(local_door_layers)
        if has_shared:
            target.add(shared_door_layer)
        if not target:
            print(f"  → 本图无门窗图层，跳过")
            print()
            continue

        types = Counter()
        blocks_on_layer = Counter()
        for ent in msp:
            if ent.dxf.layer not in target:
                continue
            types[ent.dxftype()] += 1
            if ent.dxftype() == "INSERT":
                blocks_on_layer[ent.dxf.name] += 1
        print(f"  门窗图层实体类型分布: {dict(types)}")
        if blocks_on_layer:
            print(f"  门窗图层用了哪些块 top 8:")
            for bn, n in blocks_on_layer.most_common(8):
                print(f"    {bn}: {n}")

        # 找 1 个样本 INSERT 看 scale（不读块定义几何，速度快）
        sample = None
        for ent in msp:
            if ent.dxftype() == "INSERT" and ent.dxf.layer in target:
                sample = ent
                break
        if sample:
            xs = sample.dxf.xscale if sample.dxf.hasattr("xscale") else 1.0
            ys = sample.dxf.yscale if sample.dxf.hasattr("yscale") else 1.0
            rot = sample.dxf.rotation if sample.dxf.hasattr("rotation") else 0
            print(f"  样本 INSERT: block={sample.dxf.name}, "
                  f"xscale={xs}, yscale={ys}, rot={rot}, "
                  f"layer={sample.dxf.layer}")
        print()


if __name__ == "__main__":
    main()
