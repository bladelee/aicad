"""快速诊断各任务的真实数据可行性。

回答 3 个问题：
1. #6 ST-01→ST-A: 哪些图/哪些实体带 ST 标签？跨图分布是不是真正联动？
2. #1 改墙后联动哪些图？墙线在不同图里空间坐标是否对得上？
3. #10 门宽变更: 门在哪里？是 INSERT 还是单独实体？

宿主机用：
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_scan/probe_tasks.py"
"""
from __future__ import annotations
import re
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf

ST_RE = re.compile(r"ST[-_/]?[A-Z0-9]+", re.IGNORECASE)
DXF_DIR = Path("/data/workdir/19-102/dxf")


def st_distribution():
    """任务 #6 调研：ST 标签在哪里？"""
    print("=" * 60)
    print(" #6 调研：ST 编号分布")
    print("=" * 60)
    result = defaultdict(list)
    for dxf in sorted(DXF_DIR.glob("*.dxf")):
        doc = ezdxf.readfile(str(dxf))
        name = dxf.stem
        # 扫所有 layouts
        for layout in doc.layouts:
            for ent in layout:
                # 1. 块属性里的 ST
                if ent.dxftype() == "INSERT":
                    try:
                        for a in ent.attribs:
                            tag = getattr(a.dxf, "tag", "") or ""
                            val = getattr(a.dxf, "text", "") or ""
                            for src, label in [(tag, "tag"), (val, "val")]:
                                for m in ST_RE.findall(src):
                                    result[m.upper()].append({
                                        "file": name.split("-19-102")[-1] or name,
                                        "block": ent.dxf.name,
                                        "layout": layout.name,
                                        "type": "INSERT/" + label,
                                        "raw": src[:30],
                                    })
                    except Exception:
                        pass
                # 2. 文本里的 ST
                if ent.dxftype() in ("TEXT", "MTEXT"):
                    txt = ""
                    if ent.dxftype() == "TEXT":
                        txt = getattr(ent.dxf, "text", "") or ""
                    else:
                        try:
                            txt = ent.text or ""
                        except Exception:
                            txt = ""
                    if not txt:
                        continue
                    for m in ST_RE.findall(txt):
                        result[m.upper()].append({
                            "file": name.split("-19-102")[-1] or name,
                            "block": "(text)",
                            "layout": layout.name,
                            "type": "TEXT",
                            "raw": txt[:30],
                        })

    print(f"\n共发现 {len(result)} 个唯一 ST 编号：")
    for code in sorted(result.keys()):
        items = result[code]
        files = sorted({i["file"] for i in items})
        print(f"  {code}: {len(items)} 处, 跨 {len(files)} 张图: {files}")
        # 前 3 个示例
        for it in items[:3]:
            print(f"      - {it['file']} {it['layout']} {it['type']} "
                  f"{it['block']} raw={it['raw']!r}")
    return result


def door_distribution():
    """任务 #10 调研：门在哪里？是 INSERT 还是 LINE？"""
    print()
    print("=" * 60)
    print(" #10 调研：门的分布")
    print("=" * 60)
    DOOR_LAYER_KEYS = ("门", "DOOR")
    DOOR_BLOCK_KEYS = ("DOOR", "门", "M_", "MC")

    for dxf in sorted(DXF_DIR.glob("*.dxf")):
        if "XINLU" in dxf.stem or "1-19-102封面" in dxf.stem:
            continue
        doc = ezdxf.readfile(str(dxf))
        name = dxf.stem.split("-19-102")[-1] or dxf.stem
        door_layers = Counter()
        door_blocks = Counter()
        door_lines = Counter()
        msp = doc.modelspace()
        for ent in msp:
            layer = (ent.dxf.layer or "").upper() if ent.dxf.hasattr("layer") else ""
            if any(k in layer for k in DOOR_LAYER_KEYS):
                door_layers[ent.dxf.layer] += 1
                if ent.dxftype() == "INSERT":
                    door_blocks[ent.dxf.name] += 1
                elif ent.dxftype() in ("LINE", "LWPOLYLINE", "ARC"):
                    door_lines[ent.dxftype()] += 1
            # 块名带 DOOR
            elif ent.dxftype() == "INSERT":
                bname = (ent.dxf.name or "").upper()
                if any(k in bname for k in DOOR_BLOCK_KEYS):
                    door_blocks[ent.dxf.name] += 1
        print(f"\n  {name}:")
        print(f"    门图层: {dict(door_layers) or '(无)'}")
        print(f"    门块:   {dict(door_blocks) or '(无)'}")
        print(f"    门几何实体（在门图层）: {dict(door_lines) or '(无)'}")


def wall_spatial_match():
    """任务 #2/#4/#5 调研：墙在不同图里的空间坐标是否对得上？"""
    print()
    print("=" * 60)
    print(" #1/#2/#4/#5 调研：墙图层在多图的坐标范围")
    print("=" * 60)
    WALL_LAYER = "A原建筑墙体"

    for dxf in sorted(DXF_DIR.glob("*.dxf")):
        doc = ezdxf.readfile(str(dxf))
        name = dxf.stem.split("-19-102")[-1] or dxf.stem
        xs, ys = [], []
        n_lines = 0
        msp = doc.modelspace()
        for ent in msp:
            if ent.dxf.layer != WALL_LAYER or ent.dxftype() != "LINE":
                continue
            n_lines += 1
            xs.extend([ent.dxf.start[0], ent.dxf.end[0]])
            ys.extend([ent.dxf.start[1], ent.dxf.end[1]])
        if n_lines:
            print(f"  {name}: {n_lines} 条墙线")
            print(f"    X 范围: [{min(xs):.0f}, {max(xs):.0f}]  跨度={max(xs)-min(xs):.0f}")
            print(f"    Y 范围: [{min(ys):.0f}, {max(ys):.0f}]  跨度={max(ys)-min(ys):.0f}")


if __name__ == "__main__":
    st_result = st_distribution()
    door_distribution()
    wall_spatial_match()

    # 4. 总结
    print()
    print("=" * 60)
    print(" 综合判断（自动化可行性）")
    print("=" * 60)
    # 跨图 ≥ 2 的 ST 编号 = 真正的联动改造对象
    cross_st = {c: v for c, v in st_result.items()
                if len({i["file"] for i in v}) >= 2}
    print(f"\n  #6 ST 联动真候选（跨图 ≥ 2）: {sorted(cross_st.keys())}")
