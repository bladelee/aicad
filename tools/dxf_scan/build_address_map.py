"""基于 Z 索引编号指针，建立 3-平面 ↔ 5-节点 的坐标映射。

算法：
1. 从 3-平面 Z节点索引 拿到 (insert_x, insert_y, code=DE-XX)
2. 在 5-节点 全 model + layout 搜 TEXT/MTEXT 的 text == code（或 contains code）
3. 拿到对应实体的 insert 点 (target_x, target_y)
4. 建立 mappings: [{code, plan_pos, node_pos, offset}]

宿主机:
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_scan/build_address_map.py"
"""
from __future__ import annotations
import re
from collections import defaultdict
from pathlib import Path

import ezdxf

DXF_DIR = Path("/data/workdir/19-102/dxf")
PLAN_DXF = DXF_DIR / "3-19-102平面系统图.dxf"
NODE_DXF = DXF_DIR / "5-19-102节点.dxf"
ELEV_DXF = DXF_DIR / "4-19-102立面图.dxf"


def extract_index_codes(doc, layer_name: str) -> list[dict]:
    """从 Z 节点/立面索引块提取 (code, insert_pos)"""
    results = []
    for layout in doc.layouts:
        for ent in layout:
            if ent.dxftype() != "INSERT":
                continue
            if ent.dxf.layer != layer_name:
                continue
            insert = tuple(round(c, 1) for c in ent.dxf.insert)
            codes = []
            try:
                for a in ent.attribs:
                    tag = a.dxf.tag if a.dxf.hasattr("tag") else ""
                    val = a.dxf.text if a.dxf.hasattr("text") else ""
                    # 把 tag 也作为候选 val 看（之前实测 tag 是 1EA-07/1EA-08）
                    # 真正的指针 value 在另一个 attrib 里
                    if re.match(r"(DE-\w+|FU-\w+|1EA-\w+|EA-\w+)", val):
                        codes.append(val)
            except Exception:
                pass
            for code in codes:
                results.append({"code": code, "src_pos": insert,
                                "src_block": ent.dxf.name, "src_layer": layer_name})
    return results


def find_code_in_text(doc, code: str) -> list[tuple]:
    """在 doc 全 layouts 找 TEXT/MTEXT 文本等于 code 的实体位置"""
    pos_list = []
    for layout in doc.layouts:
        for ent in layout:
            if ent.dxftype() == "TEXT":
                try:
                    if ent.dxf.text == code or ent.dxf.text.strip() == code:
                        pos_list.append(("TEXT", tuple(round(c, 1) for c in ent.dxf.insert),
                                        layout.name, ent.dxf.layer))
                except Exception:
                    pass
            elif ent.dxftype() == "MTEXT":
                try:
                    if code in ent.text:
                        pos_list.append(("MTEXT", tuple(round(c, 1) for c in ent.dxf.insert),
                                        layout.name, ent.dxf.layer))
                except Exception:
                    pass
    return pos_list


def main():
    print("=" * 70)
    print(" 跨图编号指针映射")
    print("=" * 70)

    # 1. 读 3-平面，提取所有 Z节点索引 编号
    print("\n[1] 3-平面 Z 节点/立面索引块 → 编号清单")
    plan = ezdxf.readfile(str(PLAN_DXF))
    plan_codes_node = extract_index_codes(plan, "Z节点索引")
    plan_codes_elev = extract_index_codes(plan, "Z立面索引")
    print(f"  Z节点索引: {len(plan_codes_node)} 个")
    for c in plan_codes_node[:5]:
        print(f"    - {c['code']} @ {c['src_pos']}")
    print(f"  Z立面索引: {len(plan_codes_elev)} 个")
    for c in plan_codes_elev[:3]:
        print(f"    - {c['code']} @ {c['src_pos']}")

    unique_codes = sorted({c["code"] for c in plan_codes_node + plan_codes_elev})
    print(f"\n  去重后唯一编号: {len(unique_codes)} 个 → {unique_codes}")

    # 2. 读 5-节点，找每个编号对应在 5-节点的位置
    print("\n[2] 在 5-节点 找含相同编号的 TEXT/MTEXT")
    node = ezdxf.readfile(str(NODE_DXF))

    matched = []
    unmatched = []
    for code in unique_codes:
        positions = find_code_in_text(node, code)
        if positions:
            matched.append({"code": code, "node_positions": positions})
        else:
            unmatched.append(code)

    print(f"  ✓ 找到位置: {len(matched)} / {len(unique_codes)}")
    for m in matched[:10]:
        n = len(m["node_positions"])
        p = m["node_positions"][0]
        print(f"    - {m['code']}: {n} 处, 首位置 {p[0]} @ ({p[1][0]:.0f},{p[1][1]:.0f}) "
              f"in {p[2]}/{p[3]}")
    if unmatched:
        print(f"  ✗ 未找到: {len(unmatched)} → {unmatched}")

    # 3. 读 4-立面 的反向指针（4 里的 Z节点索引 指向 5-节点 的 DE-WXX）
    print("\n[3] 4-立面 Z 节点索引 → 5-节点 反向指针")
    elev = ezdxf.readfile(str(ELEV_DXF))
    elev_codes = extract_index_codes(elev, "Z节点索引")
    unique_elev = sorted({c["code"] for c in elev_codes})
    print(f"  4-立面 Z节点索引: {len(elev_codes)} 个, 唯一编号 {len(unique_elev)} → {unique_elev[:10]}")

    matched_elev = []
    for code in unique_elev:
        positions = find_code_in_text(node, code)
        if positions:
            matched_elev.append({"code": code, "node_positions": positions})
    print(f"  ✓ 在 5-节点找到: {len(matched_elev)} / {len(unique_elev)}")
    for m in matched_elev[:5]:
        p = m["node_positions"][0]
        print(f"    - {m['code']}: @ ({p[1][0]:.0f},{p[1][1]:.0f}) in {p[2]}/{p[3]}")

    # 4. 输出映射 JSON
    import json
    out = {
        "plan_to_node": matched,
        "elev_to_node": matched_elev,
        "plan_unmatched": unmatched,
        "summary": {
            "plan_unique_codes": len(unique_codes),
            "plan_matched": len(matched),
            "elev_unique_codes": len(unique_elev),
            "elev_matched": len(matched_elev),
        },
    }
    out_path = DXF_DIR.parent / "address_map.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str),
                        encoding="utf-8")
    print(f"\n[4] 映射表写出: {out_path.name}")
    print(f"  统计: {out['summary']}")


if __name__ == "__main__":
    main()
