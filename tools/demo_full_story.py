"""演示脚本：把 #6 + #1 + #2 串成"1 分钟演示故事"。

用法（在 floorplan-mcp 容器内）:
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/demo_full_story.py"

输出：workdir/19-102/demo_outputs/
  - 1_summary.txt       演示摘要
  - 2_st_changes.json   ST 替换明细
  - 3_wall_changes.json 改墙明细
  - 4_floor_ceil_changes.json 内自洽明细
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/data/tools/dxf_edit")
sys.path.insert(0, "/data/tools/dxf_scan")

import ezdxf
from collections import Counter

OUT_DIR = Path("/data/workdir/19-102/demo_outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DXF_DIR = Path("/data/workdir/19-102/dxf")

# 验证 3 个产物的存在
PRODUCTS = {
    "#6 ST 替换": [
        DXF_DIR / "3-19-102平面系统图_ST-01_to_ST-A.dxf",
        DXF_DIR / "4-19-102立面图_ST-01_to_ST-A.dxf",
        DXF_DIR / "5-19-102节点_ST-01_to_ST-A.dxf",
    ],
    "#1 改墙": [
        DXF_DIR / "3-19-102平面系统图_demo_moved500.dxf",
    ],
    "#2 内自洽": [
        DXF_DIR / "3-19-102平面系统图_wall_floor_ceil.dxf",
    ],
}


def check_files():
    print("=" * 60)
    print(" 演示产物存在性检查")
    print("=" * 60)
    all_ok = True
    for task, files in PRODUCTS.items():
        print(f"\n  {task}:")
        for f in files:
            ok = f.exists()
            mark = "✓" if ok else "✗"
            size = f"{f.stat().st_size // 1024 // 1024}MB" if ok else "缺失"
            print(f"    {mark} {f.name} ({size})")
            if not ok:
                all_ok = False
    return all_ok


def _count_code(doc, pat, layers=None):
    """统一统计文档中 pat 出现次数（仅扫 INSERT.attribs + TEXT + MTEXT）"""
    n = 0
    for layout in doc.layouts:
        for ent in layout:
            etype = ent.dxftype()
            if etype == "INSERT":
                try:
                    for a in ent.attribs:
                        n += len(pat.findall(a.dxf.text or ""))
                        n += len(pat.findall(a.dxf.tag or ""))
                except Exception:
                    pass
            elif etype == "TEXT":
                n += len(pat.findall(ent.dxf.text or ""))
            elif etype == "MTEXT":
                try:
                    n += len(pat.findall(ent.text or ""))
                except Exception:
                    pass
    return n


def demo_st():
    """演示 #6：ST 替换的 before/after"""
    print("\n" + "=" * 60)
    print(" Demo #6: ST-01 → ST-A 材料编号联动（3 张图）")
    print("=" * 60)

    import re
    ST01 = re.compile(r"ST\-01(?![0-9A-Z])")
    STA = re.compile(r"ST\-A(?![0-9A-Z])")

    result = {}
    for orig_name, new_name, label in [
        ("3-19-102平面系统图.dxf", "3-19-102平面系统图_ST-01_to_ST-A.dxf", "平面"),
        ("4-19-102立面图.dxf", "4-19-102立面图_ST-01_to_ST-A.dxf", "立面"),
        ("5-19-102节点.dxf", "5-19-102节点_ST-01_to_ST-A.dxf", "节点"),
    ]:
        orig_path = DXF_DIR / orig_name
        new_path = DXF_DIR / new_name
        if not orig_path.exists() or not new_path.exists():
            continue

        def count_st(doc, pat):
            n = 0
            for layout in doc.layouts:
                for ent in layout:
                    if ent.dxftype() == "INSERT":
                        try:
                            for a in ent.attribs:
                                n += len(pat.findall(a.dxf.text or ""))
                                n += len(pat.findall(a.dxf.tag or ""))
                        except:
                            pass
                    elif ent.dxftype() == "TEXT":
                        n += len(pat.findall(ent.dxf.text or ""))
                    elif ent.dxftype() == "MTEXT":
                        try:
                            n += len(pat.findall(ent.text or ""))
                        except:
                            pass
            return n

        doc_o = ezdxf.readfile(str(orig_path))
        doc_n = ezdxf.readfile(str(new_path))
        before_01 = count_st(doc_o, ST01)
        after_01 = count_st(doc_n, ST01)
        after_a = count_st(doc_n, STA)
        result[label] = {
            "before_ST01": before_01,
            "after_ST01": after_01,
            "after_STA": after_a,
        }
        print(f"  {label}: ST-01 {before_01} → {after_01}, ST-A 0 → {after_a}")
    return result


def demo_wall():
    """演示 #1：改墙 before/after"""
    print("\n" + "=" * 60)
    print(" Demo #1: 改墙（handle=E6037，dx=+500mm）")
    print("=" * 60)

    orig_path = DXF_DIR / "3-19-102平面系统图.dxf"
    new_path = DXF_DIR / "3-19-102平面系统图_moved_500_0.dxf"
    if not orig_path.exists() or not new_path.exists():
        return {}

    doc_o = ezdxf.readfile(str(orig_path))
    doc_n = ezdxf.readfile(str(new_path))
    msp_o = doc_o.modelspace()
    msp_n = doc_n.modelspace()
    target = "E6037"
    result = {"target_handle": target}
    for label, msp in [("原", msp_o), ("改", msp_n)]:
        # 找 handle 相同 + 端点有差异的墙
        for e in msp:
            if e.dxftype() == "LINE" and e.dxf.handle == target:
                result[f"{label}_start"] = [round(c, 1) for c in e.dxf.start]
                result[f"{label}_end"] = [round(c, 1) for c in e.dxf.end]
                print(f"  {label} start={result[f'{label}_start']}")
                print(f"  {label} end  ={result[f'{label}_end']}")
                break

    delta = result["改_end"][0] - result["原_end"][0]
    print(f"  Δx = {delta:.1f} mm")
    result["delta_x"] = delta
    return result


def demo_floor_ceil():
    """演示 #2：内自洽改墙后地坪天花联动"""
    print("\n" + "=" * 60)
    print(" Demo #2: 内自洽（改墙 → 地坪天花图层联动）")
    print("=" * 60)

    orig_path = DXF_DIR / "3-19-102平面系统图.dxf"
    new_path = DXF_DIR / "3-19-102平面系统图_wall_floor_ceil.dxf"
    if not orig_path.exists() or not new_path.exists():
        return {}

    doc_o = ezdxf.readfile(str(orig_path))
    doc_n = ezdxf.readfile(str(new_path))
    # 用 wall_idx=6 (E6037) 的 end 端点
    walls_o = [e for e in doc_o.modelspace()
               if e.dxftype() == "LINE" and e.dxf.layer == "A原建筑墙体"]
    walls_n = [e for e in doc_n.modelspace()
               if e.dxftype() == "LINE" and e.dxf.layer == "A原建筑墙体"]
    # 找 end.x +500 的墙
    result = {"wall_handle_orig": "E6037"}
    for wo, wn in zip(walls_o, walls_n):
        if wo.dxf.handle == "E6037":
            dx = wn.dxf.end[0] - wo.dxf.end[0]
            if abs(dx - 500.0) < 1:
                result["delta"] = dx
                result["orig_end"] = [round(c, 1) for c in wo.dxf.end]
                result["new_end"] = [round(c, 1) for c in wn.dxf.end]
                print(f"  目标墙 {wo.dxf.handle}: end.x {wo.dxf.end[0]:.0f} → {wn.dxf.end[0]:.0f} (dx={dx})")
                break
    return result


def main():
    print("\n" + "🎉" * 20)
    print("  装修 DWG 联动改造 — 完整演示")
    print("  项目: 19-102 别墅")
    print("  时间: 2026-08-09")
    print("🎉" * 20)

    all_ok = check_files()
    if not all_ok:
        print("\n⚠️ 缺少演示产物，请先跑 #6/#1/#2 三步！")
        return

    st = demo_st()
    wall = demo_wall()
    floor_ceil = demo_floor_ceil()

    # 输出汇总
    summary = []
    summary.append("=" * 60)
    summary.append(" 演示摘要")
    summary.append("=" * 60)
    summary.append("")
    summary.append(f"项目: 19-102 别墅（{len(list(DXF_DIR.glob('*.dxf')))} 张 DXF）")
    summary.append("")
    summary.append("Demo #6 ST-01 → ST-A 材料编号联动:")
    for label, d in st.items():
        summary.append(f"  {label}: ST-01 {d['before_ST01']}处 → {d['after_ST01']}处, "
                        f"ST-A 0 → {d['after_STA']}处")
    summary.append("")
    summary.append("Demo #1 改墙:")
    summary.append(f"  目标 handle={wall.get('target_handle')}")
    summary.append(f"  原 end: {wall.get('原_end', wall.get('orig_end'))}")
    summary.append(f"  新 end: {wall.get('新_end', wall.get('new_end'))}")
    summary.append(f"  Δx: +{wall.get('delta_x', wall.get('delta', 0))} mm")
    summary.append("")
    summary.append("Demo #2 内自洽 (改墙→地坪天花联动):")
    summary.append(f"  目标墙 handle={floor_ceil.get('wall_handle_orig')}")
    summary.append(f"  Δx: +{floor_ceil.get('delta', 0)} mm, 联动范围 NEAR=2000mm")

    txt_path = OUT_DIR / "1_summary.txt"
    txt_path.write_text("\n".join(summary), encoding="utf-8")
    print(f"\n✓ 摘要已写到: {txt_path}")

    (OUT_DIR / "2_st_changes.json").write_text(
        json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "3_wall_changes.json").write_text(
        json.dumps(wall, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "4_floor_ceil_changes.json").write_text(
        json.dumps(floor_ceil, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 60)
    print(" 演示完毕。产物目录:")
    print(f"   {OUT_DIR}/")
    for f in sorted(OUT_DIR.iterdir()):
        print(f"     {f.name} ({f.stat().st_size} bytes)")
    print("=" * 60)


if __name__ == "__main__":
    main()
