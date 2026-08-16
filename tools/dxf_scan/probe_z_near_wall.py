"""快速看 3-平面的所有 Z 索引块的坐标，找出离 wall_idx=6 (cx=206902, cy=-908615) 最近的几个"""
import ezdxf
doc = ezdxf.readfile("/data/workdir/19-102/dxf/3-19-102平面系统图.dxf")
msp = doc.modelspace()

target_cx, target_cy = 206902, -908615
candidates = []

for ent in msp:
    if ent.dxf.layer not in ("Z节点索引", "Z立面索引"):
        continue
    if ent.dxftype() != "INSERT":
        continue
    px, py = ent.dxf.insert[0], ent.dxf.insert[1]
    d = ((px - target_cx) ** 2 + (py - target_cy) ** 2) ** 0.5
    codes = []
    try:
        for a in ent.attribs:
            if a.dxf.tag in ("1EA-07", "1EA-08"):
                codes.append(f"{a.dxf.tag}={a.dxf.text}")
    except Exception:
        pass
    candidates.append((d, ent.dxf.layer, px, py, codes))

candidates.sort()
print(f"=== 3-平面 Z 索引块（按到目标墙中心距离排序，前 20）===")
print(f"目标墙中心: ({target_cx}, {target_cy})\n")
for d, layer, px, py, codes in candidates[:20]:
    print(f"  距离 {d:>10.0f}  位置 ({px:>9.0f}, {py:>10.0f})  图层={layer}")
    for c in codes:
        print(f"      {c}")
print(f"\n总共 Z 索引 INSERT: {len(candidates)}")
