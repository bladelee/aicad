"""Round-trip 验证：对比原 DXF 与 modified DXF，确认改造保持且数量不变。"""
from collections import Counter
import ezdxf

ORIG = "/data/workdir/19-102/dxf/3-19-102平面系统图.dxf"
MODIFIED = "/data/workdir/19-102/dxf/3-19-102平面系统图_modified.dxf"
TARGET_HANDLE = "E6037"

orig = ezdxf.readfile(ORIG)
mod = ezdxf.readfile(MODIFIED)
o_ms = orig.modelspace()
m_ms = mod.modelspace()

o_count = sum(1 for _ in o_ms)
m_count = sum(1 for _ in m_ms)
o_types = Counter(e.dxftype() for e in o_ms)
m_types = Counter(e.dxftype() for e in m_ms)

print(f"原文件实体数 : {o_count}")
print(f"改后实体数   : {m_count}")
print(f"实体数一致   : {o_count == m_count}")
print(f"类型分布一致 : {o_types == m_types}")

if o_types != m_types:
    for k in set(o_types) | set(m_types):
        a, b = o_types.get(k, 0), m_types.get(k, 0)
        if a != b:
            print(f"  ⚠️  {k}: {a} → {b}")

print()
print(f"=== handle={TARGET_HANDLE} 改造前后对比 ===")
for tag, ents in [("原", o_ms), ("改", m_ms)]:
    found = False
    for e in ents:
        if e.dxftype() == "LINE" and e.dxf.handle == TARGET_HANDLE:
            s = tuple(round(c, 1) for c in e.dxf.start)
            t = tuple(round(c, 1) for c in e.dxf.end)
            print(f"  {tag}: start={s}, end={t}, layer={e.dxf.layer}")
            found = True
            break
    if not found:
        print(f"  {tag}: 未找到 handle={TARGET_HANDLE}")

print()
print(f"文件大小对比:")
import os
o_size = os.path.getsize(ORIG)
m_size = os.path.getsize(MODIFIED)
print(f"  原     : {o_size:>12,} 字节")
print(f"  改后   : {m_size:>12,} 字节")
print(f"  缩减   : {o_size - m_size:>12,} 字节 ({(1 - m_size/o_size)*100:.1f}%)")
