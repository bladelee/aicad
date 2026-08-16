"""诊断：3-平面的"墙图层"和"地坪/天花图层" 是否在同一坐标系？
之前 wall 在 y=-943781 周围，但地坪天花图层实体可能在别的地方。
"""
from pathlib import Path
from collections import Counter
import ezdxf

DXF = Path("/data/workdir/19-102/dxf/3-19-102平面系统图.dxf")

WALL_LAYER = "A原建筑墙体"
FLOOR_LAYERS = ["F地坪分缝细线", "F地坪分缝粗线", "F地坪填充",
                "S新铺地坪定位尺寸", "H地坪符号"]
CEILING_LAYERS = ["L天灯", "S天花灯具定位尺寸", "S天花造型定位尺寸",
                  "C天花造型线", "C天花格栅细线", "H天花符号"]


def bbox_of_layer(msp, layers_set):
    xs, ys, count = [], [], 0
    for ent in msp:
        if ent.dxf.layer not in layers_set:
            continue
        count += 1
        try:
            t = ent.dxftype()
            if t == "LINE":
                xs.extend([ent.dxf.start[0], ent.dxf.end[0]])
                ys.extend([ent.dxf.start[1], ent.dxf.end[1]])
            elif t == "INSERT":
                xs.append(ent.dxf.insert[0]); ys.append(ent.dxf.insert[1])
            elif t in ("TEXT", "MTEXT"):
                xs.append(ent.dxf.insert[0]); ys.append(ent.dxf.insert[1])
            elif t in ("CIRCLE", "ARC"):
                xs.append(ent.dxf.center[0]); ys.append(ent.dxf.center[1])
            elif t == "LWPOLYLINE":
                for p in ent.get_points():
                    xs.append(p[0]); ys.append(p[1])
        except Exception:
            pass
    if not xs:
        return None, 0
    return (min(xs), max(xs), min(ys), max(ys)), count


doc = ezdxf.readfile(str(DXF))
msp = doc.modelspace()

print("=== 3-平面 各相关图层的坐标 bbox + 实体数 ===\n")

bbox_w, n_w = bbox_of_layer(msp, {WALL_LAYER})
print(f"墙图层 ({WALL_LAYER}): {n_w} 实体")
if bbox_w:
    print(f"  X[{bbox_w[0]:.0f}, {bbox_w[1]:.0f}] (跨度 {bbox_w[1]-bbox_w[0]:.0f})")
    print(f"  Y[{bbox_w[2]:.0f}, {bbox_w[3]:.0f}] (跨度 {bbox_w[3]-bbox_w[2]:.0f})")

bbox_f, n_f = bbox_of_layer(msp, set(FLOOR_LAYERS))
print(f"\n地坪图层 (5 个): {n_f} 实体")
if bbox_f:
    print(f"  X[{bbox_f[0]:.0f}, {bbox_f[1]:.0f}] (跨度 {bbox_f[1]-bbox_f[0]:.0f})")
    print(f"  Y[{bbox_f[2]:.0f}, {bbox_f[3]:.0f}] (跨度 {bbox_f[3]-bbox_f[2]:.0f})")

bbox_c, n_c = bbox_of_layer(msp, set(CEILING_LAYERS))
print(f"\n天花图层 (6 个): {n_c} 实体")
if bbox_c:
    print(f"  X[{bbox_c[0]:.0f}, {bbox_c[1]:.0f}] (跨度 {bbox_c[1]-bbox_c[0]:.0f})")
    print(f"  Y[{bbox_c[2]:.0f}, {bbox_c[3]:.0f}] (跨度 {bbox_c[3]-bbox_c[2]:.0f})")

# 第 0 条墙的具体位置（之前我们改的是这条）
walls = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == WALL_LAYER]
w0 = walls[0]
cx = (w0.dxf.start[0] + w0.dxf.end[0]) / 2
cy = (w0.dxf.start[1] + w0.dxf.end[1]) / 2
print(f"\n目标墙 idx=0 center: ({cx:.0f}, {cy:.0f})")
print(f"\n该中心是否在墙 bbox 内: {'是' if bbox_w[0] <= cx <= bbox_w[1] else '否'}")
print(f"该中心是否在地坪 bbox 内: {'是' if bbox_f and bbox_f[0] <= cx <= bbox_f[1] and bbox_f[2] <= cy <= bbox_f[3] else '否'}")
print(f"该中心是否在天花 bbox 内: {'是' if bbox_c and bbox_c[0] <= cx <= bbox_c[1] and bbox_c[2] <= cy <= bbox_c[3] else '否'}")

# 找其他墙，看哪条墙附近真有地坪/天花实体
print(f"\n=== 找哪条墙附近真有地坪/天花实体 ===")
import math
near_dist = 2000
candidates = []
for i, w in enumerate(walls[:50]):
    cx = (w.dxf.start[0] + w.dxf.end[0]) / 2
    cy = (w.dxf.start[1] + w.dxf.end[1]) / 2
    # 在地坪/天花图层里找最近的实体
    min_d_f = min([math.hypot(p[0]-cx, p[1]-cy)
                   for e in msp if e.dxf.layer in FLOOR_LAYERS
                   for p in ([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])] if e.dxftype()=="LINE" else
                             [(e.dxf.insert[0], e.dxf.insert[1])] if e.dxftype() in ("INSERT","TEXT","MTEXT") else
                             [(e.dxf.center[0], e.dxf.center[1])] if e.dxftype() in ("CIRCLE","ARC") else [])], default=99999)
    if min_d_f < near_dist:
        candidates.append((i, w.dxf.handle, min_d_f))
print(f"前 50 条墙里有 {len(candidates)} 条在地坪实体 <2000mm 范围内")
for i, h, d in candidates[:10]:
    print(f"  墙 #{i} (handle={h}): 距离最近地坪 = {d:.0f}")
