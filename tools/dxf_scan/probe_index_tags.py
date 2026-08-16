"""把所有 Z 立面索引 / Z 节点索引 INSERT 块的 attrib tag 全部统计清楚。
之前实测只看了样本，现在要做完整的 tag 闭包。

输出：
  1. 每个 Z 索引块的 attrib tag 列表（去重）
  2. 各 tag 对应的 value 样本（5 个）
  3. 编号族 DE/DE-W/FU/1EA/PT 等各自出现了多少次
"""
from __future__ import annotations
import re
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf

DXF_DIR = Path("/data/workdir/19-102/dxf")
TARGET_FILES = {
    "3-19-102平面系统图.dxf": ["Z立面索引", "Z节点索引"],
    "4-19-102立面图.dxf": ["Z节点索引", "Z立面索引"],
    "5-19-102节点.dxf": ["Z节点索引", "Z立面索引"],
}
INDEX_LAYERS = ["Z立面索引", "Z节点索引"]

# 编号族归类
CODE_PATTERNS = {
    "DE-WXX": re.compile(r"^DE-W\d+", re.IGNORECASE),  # 墙身节点
    "DE-XX": re.compile(r"^DE-\d+", re.IGNORECASE),    # 普通节点
    "FU-XX": re.compile(r"^FU-\d+", re.IGNORECASE),    # 家具
    "1EA-XX": re.compile(r"^1EA-\d+", re.IGNORECASE),  # 立面
    "EA-XX": re.compile(r"^EA-\d+", re.IGNORECASE),    # 立面（其他前缀）
    "PT-XX": re.compile(r"^PT-\d+", re.IGNORECASE),    # ?
}


def main():
    print("=" * 70)
    print(" Z 索引 INSERT 的 attrib tag 完整统计")
    print("=" * 70)

    for fname, layers_to_check in TARGET_FILES.items():
        p = DXF_DIR / fname
        if not p.exists():
            continue
        doc = ezdxf.readfile(str(p))
        name = fname.split("-19-102")[-1] or fname
        print(f"\n--- {name} (modelspace) ---")

        for layer in layers_to_check:
            if layer not in [l.dxf.name for l in doc.layers]:
                continue

            # 收集 tag -> [values]
            tag_values = defaultdict(list)
            n_inserts = 0
            for ent in doc.modelspace():
                if ent.dxftype() != "INSERT":
                    continue
                if ent.dxf.layer != layer:
                    continue
                n_inserts += 1
                try:
                    for a in ent.attribs:
                        tag = a.dxf.tag if a.dxf.hasattr("tag") else "?"
                        val = a.dxf.text if a.dxf.hasattr("text") else ""
                        tag_values[tag].append(val)
                except Exception:
                    pass

            if n_inserts == 0:
                continue

            print(f"\n  [图层 {layer!r}] 共 {n_inserts} 个 INSERT")
            for tag, vals in tag_values.items():
                # 统计 value 模式分布
                samples = sorted(set(vals))[:5]
                # 统计编号族
                families = Counter()
                for v in vals:
                    for fam, pat in CODE_PATTERNS.items():
                        if pat.search(v):
                            families[fam] += 1
                            break
                    else:
                        families["其他/数字"] += 1
                print(f"    tag {tag!r:20} → {len(vals):3} 个值; "
                      f"top 编号族: {dict(families.most_common(3))}; "
                      f"样本: {samples}")


if __name__ == "__main__":
    main()
