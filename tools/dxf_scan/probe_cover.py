"""任务 #8 调研：目录表的数据结构。

1-封面、目录、设计说明.dxf 在 Layout1 里有 427 个 TEXT。
要识别：
  - 目录的"图号 → 图名"格式（如 "1-封面、目录、设计说明" 编号规律）
  - 标题栏里的"图号字段"
  - 跨图文件命名规律（前缀 1-/2-/3-/4-/5- 是不是图序号）

宿主机用：
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_scan/probe_cover.py"
"""
from __future__ import annotations
import re
from collections import Counter
from pathlib import Path

import ezdxf

# 1-封面存目录，2-材料表存图框
TARGETS = {
    "1-19-102封面、目录、设计说明.dxf": "封面+目录+设计说明",
    "2-19-102材料表.dxf": "材料表（含图框块）",
    "XINLU-A2.dxf": "A2 图框样板",
}
DXF_DIR = Path("/data/workdir/19-102/dxf")

# 正则：典型图号标记（19-102 主项目编号 + 序号）
RE_PROJ_NUM = re.compile(r"\d+\-\d+")
# 19-102 主项目编号
RE_PROJECT = re.compile(r"19\s*[-\_]\s*\d+")
# 标题栏里图名（"图名:" / ".Drawing。" 之类）


def dump_layout_texts(doc, layout_name: str) -> list[tuple[float, float, str]]:
    """返回 layout 内所有 TEXT 的 (x, y, content)，按 y 倒序 / x 正序排"""
    result = []
    try:
        layout = doc.layouts.get(layout_name)
    except Exception:
        return result
    for ent in layout:
        if ent.dxftype() != "TEXT":
            continue
        try:
            p = ent.dxf.insert
            result.append((p[0], p[1], ent.dxf.text or ""))
        except Exception:
            pass
    # 排序：y 从大到小（按表格行），同 y 按 x 升序
    result.sort(key=lambda t: (-t[1], t[0]))
    return result


def main():
    print("=== #8 目录/编号结构调研 ===\n")

    # 1. 1-封面/目录 的所有 TEXT
    p = DXF_DIR / "1-19-102封面、目录、设计说明.dxf"
    doc = ezdxf.readfile(str(p))
    print(f"--- {p.name} ---")
    print(f"  layouts: {[l.name for l in doc.layouts]}")
    for ln in [l.name for l in doc.layouts]:
        texts = dump_layout_texts(doc, ln)
        print(f"\n  Layout '{ln}' 下有 {len(texts)} 个 TEXT（按 y 倒序,x 升序）：")
        for x, y, t in texts[:60]:  # 只打前 60
            mark = "★" if RE_PROJECT.search(t) or RE_PROJ_NUM.search(t) else " "
            print(f"    {mark} ({x:>7.0f},{y:>7.0f}) {t!r}")

    # 2. 2-材料表（含图框块）的 INSERT
    print("\n\n--- 2-19-102材料表.dxf ---")
    p = DXF_DIR / "2-19-102材料表.dxf"
    doc = ezdxf.readfile(str(p))
    for layout in doc.layouts:
        inserts = [(e.dxf.insert, e.dxf.name) for e in layout
                   if e.dxftype() == "INSERT"]
        print(f"  {layout.name} 下 {len(inserts)} 个 INSERT:")
        for ins, name in inserts:
            print(f"    ({ins[0]:>7.0f},{ins[1]:>7.0f}) block={name}")

    # 3. XINLU-A2 图框样板的 TEXT
    print("\n--- XINLU-A2.dxf (图框样板) ---")
    p = DXF_DIR / "XINLU-A2.dxf"
    doc = ezdxf.readfile(str(p))
    msp_texts = dump_layout_texts(doc, "Model")
    print(f"  Model 下 {len(msp_texts)} 个 TEXT:")
    for x, y, t in msp_texts[:30]:
        print(f"    ({x:>7.0f},{y:>7.0f}) {t!r}")


if __name__ == "__main__":
    main()
