"""扫描 DXF 文件结构，建立跨图纸的"实关联图谱"。

输入：/data/workdir/19-102/dxf/*.dxf
输出：/data/workdir/19-102/scan_report.json + 控制台摘要，含：
  - 每张图：图层列表、块定义列表、各层实体数、属性（属性文本）、文字（TEXT/MTEXT）
  - 跨图关联：同名图层、同名块、同 ID 属性的项  - 同时扫描 modelspace + 所有 paper space layouts（解决"0 实体"问题）
跑法（在 floorplan-mcp 容器内）：
    docker run --rm \
        -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_scan/scan_dxf.py"
"""
from __future__ import annotations
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import ezdxf
except ImportError:
    print("✗ 需要 ezdxf：本脚本应在 floorplan-mcp 容器内跑", file=sys.stderr)
    sys.exit(1)


def scan_one(dxf_path: Path) -> dict:
    """扫描单个 DXF，返回结构 dict（扫所有 layouts，包括 paper space）"""
    name = dxf_path.stem
    try:
        doc = ezdxf.readfile(str(dxf_path))
    except Exception as e:
        return {"name": name, "error": f"{type(e).__name__}: {e}"}

    report = {
        "name": name,
        "dxfversion": doc.dxfversion,
        "encoding": doc.encoding,
        "entity_count_total": 0,             # 跨所有 layouts
        "entity_by_type": Counter(),
        "entity_by_layer": Counter(),
        "entity_by_layout": Counter(),       # 跨 layout 分布
        "layers": [],
        "blocks_defined": [],
        "blocks_used": Counter(),
        "text_strings": [],  # TEXT/MTEXT 文本（截断到 80 字符）
        "attribs": [],       # 块属性（block name + tag + value）
        "layouts": [],
        "tables": [],        # TABLE 实体（材料表可能用 TABLE）
    }

    # 图层
    report["layers"] = sorted([l.dxf.name for l in doc.layers])

    # 布局（layout）列表 + 每个 layout 的实体分布
    try:
        report["layouts"] = [lo.name for lo in doc.layouts]
    except Exception:
        pass

    # 块定义（只看非匿名）
    report["blocks_defined"] = sorted(
        [b.name for b in doc.blocks if not b.name.startswith("*")]
    )

    # 实体扫描：遍历所有 layouts（含 Model + Layout1/布局1/布局2）
    # 关键修复：之前只扫 doc.modelspace()，导致 paper space 里的封面/材料表全漏掉
    for layout in doc.layouts:
        layout_name = layout.name
        for ent in layout:
            try:
                etype = ent.dxftype()
                layer = ent.dxf.layer if ent.dxf.hasattr("layer") else "0"
                report["entity_count_total"] += 1
                report["entity_by_type"][etype] += 1
                report["entity_by_layer"][layer] += 1
                report["entity_by_layout"][layout_name] += 1

                # 文本类
                if etype in ("TEXT", "MTEXT"):
                    txt = ""
                    if etype == "TEXT":
                        txt = getattr(ent.dxf, "text", "")
                    else:
                        try:
                            txt = ent.text
                        except Exception:
                            txt = ent.plain_text() if hasattr(ent, "plain_text") else "?"
                    # 提高上限到 1000 一行，因为封面/材料表内容很多
                    if txt and len(report["text_strings"]) < 1000:
                        report["text_strings"].append({
                            "layer": layer, "layout": layout_name, "text": txt[:80],
                        })

                # 块引用：记录块名 + 属性
                elif etype == "INSERT":
                    bname = ent.dxf.name if ent.dxf.hasattr("name") else "?"
                    report["blocks_used"][bname] += 1
                    try:
                        for attrib in ent.attribs:
                            tag = attrib.dxf.tag if attrib.dxf.hasattr("tag") else "?"
                            val = attrib.dxf.text if attrib.dxf.hasattr("text") else ""
                            if len(report["attribs"]) < 500:
                                report["attribs"].append({
                                    "block": bname, "layer": layer,
                                    "layout": layout_name,
                                    "tag": tag, "value": val[:80],
                                })
                    except Exception:
                        pass

                # 表格实体
                elif etype == "TABLE":
                    report["tables"].append({"layer": layer, "layout": layout_name})
            except Exception:
                continue

    return report


def cross_doc_analysis(reports: list[dict]) -> dict:
    """跨图分析：找同名图层、同名块、ST-01 模式属性"""
    # 同名图层（每张图都有的）
    layer_occurrence = defaultdict(list)
    for r in reports:
        if "error" in r:
            continue
        for ln in r["layers"]:
            layer_occurrence[ln].append(r["name"])

    common_layers = {
        ln: files for ln, files in layer_occurrence.items() if len(files) >= 2
    }

    # 同名块
    block_occurrence = defaultdict(list)
    for r in reports:
        if "error" in r:
            continue
        for bn in r["blocks_defined"]:
            block_occurrence[bn].append(r["name"])
    common_blocks = {
        bn: files for bn, files in block_occurrence.items() if len(files) >= 2
    }

    # ST-XX 模式（材料编号）—— 扩展到同时匹配 tag 和 value
    st_pattern = defaultdict(list)
    import re
    st_re = re.compile(r"ST[-_/]?[A-Z0-9]+", re.IGNORECASE)
    for r in reports:
        if "error" in r:
            continue
        for t in r["text_strings"]:
            for m in st_re.findall(t["text"]):
                st_pattern[m.upper()].append(f'{r["name"]}:{t["text"][:30]}')
        for a in r["attribs"]:
            # tag 和 value 都搜（材料表常见 tag=ST-01，value=材料描述）
            for src in (a.get("tag", ""), a.get("value", "")):
                for m in st_re.findall(src or ""):
                    st_pattern[m.upper()].append(
                        f'{r["name"]}:{a["block"]}.{a["tag"]}={a["value"][:30]}'
                    )

    return {
        "common_layers": dict(sorted(common_layers.items())),
        "common_blocks_across_docs": dict(sorted(common_blocks.items())),
        "material_codes_ST_XX": dict(sorted(st_pattern.items())),
    }


def main():
    in_dir = Path("/data/workdir/19-102/dxf")
    if not in_dir.is_dir():
        print(f"✗ 目录不存在: {in_dir}", file=sys.stderr)
        print("  请先跑 tools/dwg_to_dxf/convert_dwg.sh 转换 DWG 到 DXF", file=sys.stderr)
        sys.exit(1)

    dxfs = sorted(in_dir.glob("*.dxf"))
    if not dxfs:
        print(f"✗ {in_dir} 下无 .dxf 文件", file=sys.stderr)
        sys.exit(1)

    print(f"=== 扫描 {len(dxfs)} 张 DXF ===\n")
    reports = []
    for d in dxfs:
        print(f"--- {d.name} ---")
        r = scan_one(d)
        if "error" in r:
            print(f"  ✗ {r['error']}")
        else:
            print(f"  entities: {r['entity_count_total']}, "
                  f"layers: {len(r['layers'])}, "
                  f"blocks: {len(r['blocks_defined'])}, "
                  f"texts: {len(r['text_strings'])}, "
                  f"attribs: {len(r['attribs'])}")
            print(f"  layouts 分布: {dict(r['entity_by_layout'])}")
        reports.append(r)

    print(f"\n=== 跨图分析 ===")
    cross = cross_doc_analysis(reports)
    print(f"公共图层（≥2 张共享）: {len(cross['common_layers'])}")
    for ln, files in list(cross["common_layers"].items())[:15]:
        print(f"  - {ln}: {files}")
    print(f"\n公共块定义（≥2 张共享）: {len(cross['common_blocks_across_docs'])}")
    for bn, files in list(cross["common_blocks_across_docs"].items())[:10]:
        print(f"  - {bn}: {files}")
    print(f"\n材料编号 ST-XX 命中: {len(cross['material_codes_ST_XX'])}")
    for code, occurs in list(cross["material_codes_ST_XX"].items())[:15]:
        print(f"  - {code}: {occurs[:3]}{'...' if len(occurs) > 3 else ''}")

    # 输出 JSON 报告
    out = in_dir.parent / "scan_report.json"
    full_report = {"files": reports, "cross_analysis": cross}
    out.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ 详细 JSON 报告: {out}")


if __name__ == "__main__":
    main()
