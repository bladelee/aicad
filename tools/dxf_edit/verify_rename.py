"""验证 #6 替换效果：扫改后的 3 张 DXF 看 ST-01 是否真的清空，ST-A 是否到位。"""
import re
from collections import Counter
from pathlib import Path
import ezdxf

ST01 = re.compile(r"ST\-01(?![0-9A-Z])")
STA = re.compile(r"ST\-A(?![0-9A-Z])")

DXF_DIR = Path("/data/workdir/19-102/dxf")
FILES = [
    "3-19-102平面系统图_ST-01_to_ST-A.dxf",
    "4-19-102立面图_ST-01_to_ST-A.dxf",
    "5-19-102节点_ST-01_to_ST-A.dxf",
]


def scan(doc):
    """返回 {'ST-01': n, 'ST-A': n}"""
    counts = Counter()
    for layout in doc.layouts:
        for ent in layout:
            if ent.dxftype() == "INSERT":
                try:
                    for a in ent.attribs:
                        for k in ("tag", "text"):
                            v = getattr(a.dxf, k, "") or ""
                            counts["ST-01_match"] += len(ST01.findall(v))
                            counts["ST-A_match"] += len(STA.findall(v))
                except Exception:
                    pass
            elif ent.dxftype() == "TEXT":
                v = ent.dxf.text or ""
                counts["ST-01_match"] += len(ST01.findall(v))
                counts["ST-A_match"] += len(STA.findall(v))
            elif ent.dxftype() == "MTEXT":
                try:
                    v = ent.text or ""
                    counts["ST-01_match"] += len(ST01.findall(v))
                    counts["ST-A_match"] += len(STA.findall(v))
                except Exception:
                    pass
    return counts


print("=== #6 改造结果验证 ===\n")
total_st01 = 0
total_sta = 0
for fn in FILES:
    p = DXF_DIR / fn
    if not p.exists():
        print(f"  ✗ 缺: {fn}")
        continue
    doc = ezdxf.readfile(str(p))
    c = scan(doc)
    total_st01 += c["ST-01_match"]
    total_sta += c["ST-A_match"]
    status = "✓" if c["ST-01_match"] == 0 else "⚠️"
    print(f"  {status} {fn[:30]:32}: ST-01={c['ST-01_match']:4}, ST-A={c['ST-A_match']:4}")

print(f"\n总计: ST-01 残留={total_st01}, ST-A 新数={total_sta}")
if total_st01 == 0 and total_sta > 0:
    print("✅ #6 任务验证通过：ST-01 全部替换为 ST-A")
else:
    print(f"❌ #6 异常：残留 {total_st01}")
