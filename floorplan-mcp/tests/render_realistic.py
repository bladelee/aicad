"""把 mock_realistic.dxf 渲染成 PNG，叠加识别出的房间多边形。

跑：python tests/render_realistic.py
产出：tests/fixtures/mock_realistic_preview.png（仅本地查看用，不入 git）

让你肉眼核对算法识别出的房间形状对不对。
"""
import sys, os
sys.path.insert(0, ".")
os.environ["FLOORPLAN_BACKEND"] = "ezdxf"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 尝试启用中文字体（macOS PingFang / Linux Noto CJK / Windows Microsoft YaHei）
import matplotlib.font_manager as fm
for fontname in ("PingFang SC", "STHeiti", "Heiti SC",
                  "Noto Sans CJK SC", "WenQuanYi Micro Hei",
                  "Microsoft YaHei", "SimHei"):
    if any(fontname.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = [fontname]
        break
plt.rcParams["axes.unicode_minus"] = False
import ezdxf
from shapely.ops import unary_union, polygonize
from shapely.geometry import LineString, Point

doc = ezdxf.readfile("tests/fixtures/mock_realistic.dxf")
msp = doc.modelspace()

# 抽 WALL 线段
walls = [ LineString([(l.dxf.start.x, l.dxf.start.y), (l.dxf.end.x, l.dxf.end.y)])
          for l in msp.query("LINE") if l.dxf.layer == "WALL" ]

# 模拟 close_openings=1000（与 detect_rooms 同逻辑）
seen = set(); eps = []
for s in walls:
    for ep in (s.coords[0], s.coords[-1]):
        k = (round(ep[0], 1), round(ep[1], 1))
        if k not in seen:
            seen.add(k); eps.append(ep)
extras = []
for i, p1 in enumerate(eps):
    for p2 in eps[i+1:]:
        d = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) ** 0.5
        if 0 < d <= 1000:
            extras.append(LineString([p1, p2]))

fig, ax = plt.subplots(figsize=(12, 16))

# 1. 画原墙线（黑实线）
for w in walls:
    xs = [p[0] for p in w.coords]
    ys = [p[1] for p in w.coords]
    ax.plot(xs, ys, "k-", linewidth=2, label="墙" if walls.index(w)==0 else None)

# 2. 画补的虚拟墙（红虚线）
for e in extras:
    xs = [p[0] for p in e.coords]
    ys = [p[1] for p in e.coords]
    ax.plot(xs, ys, "r--", linewidth=1.5, alpha=0.7,
            label="补虚拟墙(close_openings)" if extras.index(e)==0 else None)

# 3. 画识别出的房间多边形（半透明填充）
all_segs = walls + extras
polys = sorted(polygonize(unary_union(all_segs)), key=lambda x: -x.area)
for i, p in enumerate(polys):
    if p.area < 5e5:
        continue
    xs = [pt[0] for pt in p.exterior.coords]
    ys = [pt[1] for pt in p.exterior.coords]
    ax.fill(xs, ys, alpha=0.25, color=f"C{i}")
    cx, cy = p.centroid.x, p.centroid.y
    ax.text(cx, cy, f"Room{i+1}\n{p.area/1e6:.1f}m²",
            ha="center", va="center", fontsize=14, fontweight="bold")

# 4. 画家具 INSERT 位置（蓝点）+ 名称
for ent in msp.query("INSERT"):
    name = ent.dxf.name
    x, y = ent.dxf.insert.x, ent.dxf.insert.y
    color = "c" if name.startswith(("SOFA","BED","TABLE","CHAIR","TV","FRIDGE",
                                       "KITCHEN","TOILET","BATHTUB","WASH","WARDROBE")) else "m"
    ax.plot(x, y, "o", color=color, markersize=6)
    ax.text(x, y-200, name.split("_")[0][:5], fontsize=6, alpha=0.7, ha="center")

ax.set_aspect("equal")
ax.set_facecolor("white")
ax.set_title(f"mock_realistic.dxf 识别出 {len([p for p in polys if p.area>5e5])} 间\n"
             f"总面积 ≈ {sum(p.area for p in polys if p.area>5e5)/1e6:.1f} m² "
             f"(黑=墙,红虚=close_openings 补,填充=识别房间,圈=家具)",
             fontsize=11)
ax.grid(True, alpha=0.3)

out = "tests/fixtures/mock_realistic_preview.png"
fig.savefig(out, dpi=120, bbox_inches="tight", facecolor="white")
print(f"✓ PNG saved: {out}")
