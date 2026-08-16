"""任务 #6: 材料编号联动替换（ST-01 → ST-A）

把 3 张主图（平面/立面/节点）中所有出现 ST-01 的位置（块属性 tag、value，
以及 TEXT/MTEXT 文本）全部替换成 ST-A。

实测分布（scan_report.json）:
  ST-01: 357 处命中, 跨 3 张图: ['3-平面系统图', '4-立面图', '5-节点']

用法（容器内）:
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_edit/apply_material_rename.py"

参数（环境变量）:
    OLD_CODE=ST-01   默认 ST-01
    NEW_CODE=ST-A    默认 ST-A
    DRY_RUN=1        只打印不写文件（默认 0=真改）

输出：workdir/19-102/dxf/<原文件名>_<OLD>_<NEW>.dxf
"""
from __future__ import annotations
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import ezdxf

OLD_CODE = os.environ.get("OLD_CODE", "ST-01")
NEW_CODE = os.environ.get("NEW_CODE", "ST-A")
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

DXF_DIR = Path("/data/workdir/19-102/dxf")
# 3 张含 ST-01 的主图
TARGET_FILES = [
    DXF_DIR / "3-19-102平面系统图.dxf",
    DXF_DIR / "4-19-102立面图.dxf",
    DXF_DIR / "5-19-102节点.dxf",
]

# 全字匹配（避免 ST-01 误命中 ST-010）
# 用 word boundary
ST_PATTERN = re.compile(re.escape(OLD_CODE) + r"(?![0-9A-Z])")


def safe_save(doc, path):
    """绕开 ezdxf 1.4.4 materials 字典 bug"""
    original = type(doc)._update_header_vars
    def patched(self):
        try:
            original(self)
        except AttributeError as e:
            print(f"  [warn] 跳过 header materials 更新: {e}")
    type(doc)._update_header_vars = patched
    try:
        doc.saveas(str(path))
    finally:
        type(doc)._update_header_vars = original


def replace_in_text(text: str) -> tuple[str, int]:
    """替换 OLD_CODE 为 NEW_CODE, 返回 (新字符串, 替换次数)"""
    if not text:
        return text, 0
    new_text, n = ST_PATTERN.subn(NEW_CODE, text)
    return new_text, n


def process_dxf(dxf_path: Path) -> dict:
    """返回 {替换总数, 按类型计数}"""
    name = dxf_path.stem
    print(f"\n--- {name} ---")
    doc = ezdxf.readfile(str(dxf_path))

    before_count = Counter()
    after_count = Counter()
    type_replacements = Counter()

    # 扫所有 layouts
    for layout in doc.layouts:
        for ent in layout:
            etype = ent.dxftype()

            # 1. INSERT 块属性
            if etype == "INSERT":
                try:
                    for attrib in ent.attribs:
                        for attr_name in ("tag", "text"):
                            try:
                                val = getattr(attrib.dxf, attr_name) or ""
                                if OLD_CODE in val:
                                    new_val, n = replace_in_text(val)
                                    if n > 0:
                                        setattr(attrib.dxf, attr_name, new_val)
                                        type_replacements[f"INSERT.{attr_name}"] += n
                                        before_count[OLD_CODE] += n
                                        after_count[NEW_CODE] += n
                            except Exception:
                                pass
                except Exception:
                    pass

            # 2. TEXT
            elif etype == "TEXT":
                try:
                    txt = ent.dxf.text or ""
                    if OLD_CODE in txt:
                        new_txt, n = replace_in_text(txt)
                        if n > 0:
                            ent.dxf.text = new_txt
                            type_replacements["TEXT"] += n
                            before_count[OLD_CODE] += n
                            after_count[NEW_CODE] += n
                except Exception:
                    pass

            # 3. MTEXT（plain text）
            elif etype == "MTEXT":
                try:
                    txt = ent.text or ""
                    if OLD_CODE in txt:
                        new_txt, n = replace_in_text(txt)
                        if n > 0:
                            ent.text = new_txt
                            type_replacements["MTEXT"] += n
                            before_count[OLD_CODE] += n
                            after_count[NEW_CODE] += n
                except Exception:
                    pass

    total = sum(type_replacements.values())
    print(f"  替换: {total} 处, 分布={dict(type_replacements)}")

    if total == 0:
        print(f"  (本图无 ST-01 出现)")
        return {"total": 0, "by_type": {}}

    # 写文件
    if DRY_RUN:
        print(f"  [DRY RUN] 不写文件")
    else:
        out_name = f"{name}_{OLD_CODE}_to_{NEW_CODE}.dxf"
        out_path = DXF_DIR / out_name
        # 备份原文件首次执行时（防止反复执行覆盖）
        bak_path = DXF_DIR / f"{name}.bak_ST.dxf"
        if not bak_path.exists():
            shutil.copy2(dxf_path, bak_path)
            print(f"  备份: {bak_path.name}")
        safe_save(doc, out_path)
        print(f"  写出: {out_path.name}")

    return {"total": total, "by_type": dict(type_replacements)}


def main():
    print(f"=== #6 材料编号联动替换 ===")
    print(f"  {OLD_CODE} → {NEW_CODE}")
    print(f"  DRY_RUN = {DRY_RUN}")
    print(f"  目标 {len(TARGET_FILES)} 张图:")

    # 先验证 ST_PATTERN 不误命中
    test_strs = ["ST-01", "ST-010", "ST-011A", "ST-01A", "ST-1"]
    print(f"\n  正则自检（{ST_PATTERN.pattern}）:")
    for s in test_strs:
        m = ST_PATTERN.search(s)
        print(f"    {s!r:12} → {'命中' if m else '不命中（正确）'}")

    results = {}
    total_repl = 0
    for p in TARGET_FILES:
        if not p.exists():
            print(f"\n⚠️  跳过（不存在）: {p.name}")
            continue
        r = process_dxf(p)
        results[p.name] = r
        total_repl += r.get("total", 0)

    print(f"\n=== 总计 ===")
    print(f"  总替换: {total_repl} 处")
    print(f"  文件分布: {[(k, v['total']) for k, v in results.items()]}")

    if DRY_RUN:
        print(f"\n  [DRY RUN] 未写文件。设 DRY_RUN=0 真改。")
    else:
        print(f"\n  ✓ 输出: *_{OLD_CODE}_to_{NEW_CODE}.dxf")


if __name__ == "__main__":
    main()
