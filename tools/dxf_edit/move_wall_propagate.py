"""任务 #5 最小可工作 demo：改墙后通过 Z 节点索引指针联动 5-节点。

策略：
  1. 在 3-平面 改 wall_idx=6 的墙（dx=+500）
  2. 在改墙位置附近找 Z 节点索引 INSERT，按 attrib '1EA-07' 拿到目标节点编号（如 'DE-02'）
  3. 在 5-节点 搜索所有 TEXT/MTEXT 含 'DE-02' 的位置（这是该节点在节点图里被引用的地方）
  4. 在 5-节点 出一份"对应位置识别报告"，提示设计师此处需手工/自动调整

跑法:
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_edit/move_wall_propagate.py"
"""
from __future__ import annotations
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

import ezdxf

INPUT_3 = Path("/data/workdir/19-102/dxf/3-19-102平面系统图.dxf")
INPUT_5 = Path("/data/workdir/19-102/dxf/5-19-102节点.dxf")
DX = float(os.environ.get("DX", "500"))
WALL_IDX = int(os.environ.get("WALL_IDX", "6"))
NEAR_FOR_INDEX = float(os.environ.get("NEAR", "5000"))  # 改墙附近找索引块半径


def safe_saveas(doc, path: Path):
    original = type(doc)._update_header_vars
    def patched(self):
        try:
            original(self)
        except AttributeError as e:
            print(f"  [warn] 跳过 header materials: {e}")
    type(doc)._update_header_vars = patched
    try:
        doc.saveas(str(path))
    finally:
        type(doc)._update_header_vars = original


def main():
    print("=== #5 跨视图 demo: 改墙 3-平面 → 通过 Z 索引定位 5-节点 ===")
    print(f"  输入 3-平面: {INPUT_3.name}")
    print(f"  输入 5-节点: {INPUT_5.name}")
    print(f"  改墙 dx={DX}, wall_idx={WALL_IDX}")
    print()

    doc3 = ezdxf.readfile(str(INPUT_3))
    msp3 = doc3.modelspace()

    # 1. 选墙 + 改造
    walls = [e for e in msp3
             if e.dxftype() == "LINE" and e.dxf.layer == "A原建筑墙体"]
    wall = walls[WALL_IDX]
    s, e = tuple(wall.dxf.start), tuple(wall.dxf.end)
    wall.dxf.start = (s[0]+DX, s[1], s[2])
    wall.dxf.end = (e[0]+DX, e[1], e[2])
    cx, cy = (s[0]+e[0])/2, (s[1]+e[1])/2
    print(f"  改造墙: handle={wall.dxf.handle}, center=({cx:.0f}, {cy:.0f})")
    print(f"  原 end: ({e[0]:.0f}, {e[1]:.0f}) → 新 end: ({e[0]+DX:.0f}, {e[1]:.0f})")

    # 2. 找墙附近的 Z 节点索引 / Z 立面索引 块
    NEAR_SQ = NEAR_FOR_INDEX ** 2
    matched_codes = set()
    n_idx_total = 0
    for ent in msp3:
        if ent.dxf.layer not in ("Z节点索引", "Z立面索引"):
            continue
        n_idx_total += 1
        # 只 INSERT 才有 insert 点 + 有 attribs
        if ent.dxftype() != "INSERT":
            continue
        px, py = ent.dxf.insert[0], ent.dxf.insert[1]
        if (px - cx) ** 2 + (py - cy) ** 2 > NEAR_SQ:
            continue
        # 在范围内：读 attrib 拿目标编号
        try:
            for a in ent.attribs:
                tag = a.dxf.tag
                val = a.dxf.text
                if tag in ("1EA-07", "1EA-08") and val:
                    matched_codes.add(val)
        except Exception:
            pass

    print()
    print(f"  扫到 Z 索引块总数: {n_idx_total}")
    print(f"  范围内 ({NEAR_FOR_INDEX}mm) 命中的目标编号: {sorted(matched_codes)}")
    if not matched_codes:
        # 增大半径提示
        print(f"  ⚠️ 没命中，可调大 NEAR_FOR_INDEX 环境变量重跑")
        return

    # 3. 保存改过的 3-平面
    BACKUP_DIR = Path("/data/workdir/19-102/backups/cross_view")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    n = 1
    while (BACKUP_DIR / f"{INPUT_3.stem}.bak{n}.dxf").exists():
        n += 1
    bak3 = BACKUP_DIR / f"{INPUT_3.stem}.bak{n}.dxf"
    shutil.copy2(INPUT_3, bak3)
    out3 = INPUT_3.with_name(f"{INPUT_3.stem}_propagated.dxf")
    safe_saveas(doc3, out3)
    print()
    print(f"  3-平面 备份: {bak3.name}, 输出: {out3.name}")

    # 4. 在 5-节点 找含目标编号的 TEXT/MTEXT/INSERT 位置
    print()
    print(f"=== 5-节点内 '{', '.join(sorted(matched_codes))}' 的位置扫描 ===")
    doc5 = ezdxf.readfile(str(INPUT_5))
    hits = []  # (layout_name, layer, handle, entity_type, text)
    for layout in doc5.layouts:
        for ent in layout:
            etype = ent.dxftype()
            if etype == "TEXT":
                txt = ent.dxf.text or ""
                for code in matched_codes:
                    if code in txt:
                        hits.append((layout.name, ent.dxf.layer, ent.dxf.handle,
                                     "TEXT", txt))
                        break
            elif etype == "MTEXT":
                try:
                    txt = ent.text or ""
                except Exception:
                    txt = ""
                for code in matched_codes:
                    if code in txt:
                        hits.append((layout.name, ent.dxf.layer, ent.dxf.handle,
                                     "MTEXT", txt[:50]))
                        break
            elif etype == "INSERT":
                # INSERT 也可能含 attrib 带 code
                try:
                    for a in ent.attribs:
                        v = a.dxf.text or ""
                        for code in matched_codes:
                            if code in v:
                                hits.append((layout.name, ent.dxf.layer, ent.dxf.handle,
                                             f"INSERT[{ent.dxf.name}]", v[:30]))
                                break
                except Exception:
                    pass
    print(f"  5-节点命中数: {len(hits)}")
    for h_layout, h_layer, h_handle, h_type, h_text in hits[:20]:
        print(f"    layout={h_layout!r:8} layer={h_layer!r:30} "
              f"handle={h_handle} type={h_type} text={h_text!r}")

    if not hits:
        print(f"  ⚠️ 5-节点 未找到上述编号。可能节点编号在标题栏或别处。")
        return

    # 5. 输出"对应位置报告"（仅报告，不改 5-节点）
    print()
    print("=== 5-节点对应位置识别报告（建议设计师在以上位置手工调整）===")
    for h_layout, h_layer, h_handle, h_type, h_text in hits[:20]:
        print(f"  • {h_layer[:30]} ({h_type} {h_handle}): {h_text[:60]}")

    print()
    print("  说明：自动改 5-节点需要对节点图几何做变换（本期 MVP 不做）")
    print("        本 demo 价值在于：**证明了从改墙位置 → Z 索引编号 → 跨图定位** 的链路通")
    print("        后续可在此基础上加'对应位置几何变换'实现 #5 真 auto-propagate")


if __name__ == "__main__":
    main()
