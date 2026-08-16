"""B2: 把改造前后的 DXF 渲染成 PNG 对比图。

策略：用 ezdxf + matplotlib 渲染 "改前 / 改后" 的墙 + 填充区域，
重点高亮被改动的墙（红色），其他保持灰色。

输出（4 张 PNG）：
  b2_1_material_before.png       #6 改前 ST-01 分布概览
  b2_2_material_after.png        #6 改后 ST-A 分布概览
  b2_3_wall_before.png           #1 改前墙 + 填充
  b2_4_wall_after.png            #1 改后墙 + 填充

跑法（在 floorplan-mcp 容器内，或 miniconda 也行）：
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/gen_demo_png.py"
"""
from __future__ import annotations
import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Arc
from matplotlib.lines import Line2D

import ezdxf

DXF_DIR = Path("/data/workdir/19-102/dxf")
OUT_DIR = Path("/data/workdir/19-102/demo_outputs/png")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def render_wall_area(dxf_path: Path, out_png: Path, target_handle: str = "E6037",
                     window: int = 5000, title: str = ""):
    """渲染墙 E6037 周围 ±window 范围内的 LINE/INSERT"""
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    # 找目标墙拿中心
    target_ent = None
    for e in msp:
        if e.dxftype() == "LINE" and e.dxf.handle == target_handle:
            target_ent = e
            break
    if not target_ent:
        print(f"  ⚠️ handle={target_handle} 未找到，跳过")
        return
    cx = (target_ent.dxf.start[0] + target_ent.dxf.end[0]) / 2
    cy = (target_ent.dxf.start[1] + target_ent.dxf.end[1]) / 2

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    # 收集窗口内的实体
    WALL_LAYER = "A原建筑墙体"
    FILL_LAYER = "A原建筑墙体填充"

    for ent in msp:
        if ent.dxftype() != "LINE":
            continue
        # 取线的中点
        sx, sy = ent.dxf.start[0], ent.dxf.start[1]
        ex, ey = ent.dxf.end[0], ent.dxf.end[1]
        mx, my = (sx+ex)/2, (sy+ey)/2
        # 不在窗口内跳过
        if abs(mx - cx) > window or abs(my - cy) > window:
            continue
        # 颜色：目标墙=红，墙=蓝，其他=灰
        if ent.dxf.handle == target_handle:
            color, lw = "red", 3
        elif ent.dxf.layer == WALL_LAYER:
            color, lw = "blue", 1.5
        elif ent.dxf.layer == FILL_LAYER:
            color, lw = "green", 1.0
        else:
            color, lw = "gray", 0.5
        ax.add_line(Line2D([sx, ex], [sy, ey], color=color, linewidth=lw))

    # 标注目标墙
    if target_ent:
        sx, sy = target_ent.dxf.start[0], target_ent.dxf.start[1]
        ex, ey = target_ent.dxf.end[0], target_ent.dxf.end[1]
        mx, my = (sx+ex)/2, (sy+ey)/2
        ax.annotate(f"目标墙\nhandle={target_handle}\n"
                    f"端点=({sx:.0f},{sy:.0f})→({ex:.0f},{ey:.0f})",
                    xy=(mx, my), xytext=(mx, my + 300),
                    fontsize=9, ha="center",
                    arrowprops=dict(arrowstyle="->", color="red"),
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.8))

    ax.set_xlim(cx - window, cx + window)
    ax.set_ylim(cy - window, cy + window)
    ax.set_aspect("equal")
    ax.set_title(title or dxf_path.name, fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")

    out = OUT_DIR / out_png
    fig.savefig(str(out), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {out.name} ({out.stat().st_size // 1024} KB)")


def render_st_overview(dxf_path: Path, out_png: Path, find_code: str,
                       title: str = ""):
    """渲染 ST 编号在 3-平面里的分布（红点 = 命中位置）"""
    import re
    PAT = re.compile(find_code + r"(?![0-9A-Z])")
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    xs, ys = [], []
    for layout in doc.layouts:
        for ent in layout:
            if ent.dxftype() == "INSERT":
                try:
                    for a in ent.attribs:
                        v = (a.dxf.text or "") + " " + (a.dxf.tag or "")
                        if PAT.search(v):
                            xs.append(ent.dxf.insert[0])
                            ys.append(ent.dxf.insert[1])
                            break
                except:
                    pass

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    if xs:
        ax.scatter(xs, ys, c="red", s=15, alpha=0.6, label=f"{find_code} ({len(xs)} 处)")
        ax.legend()
    else:
        ax.text(0.5, 0.5, f"未找到 {find_code}", ha="center", transform=ax.transAxes)
    ax.set_aspect("equal")
    ax.set_title(title or f"{dxf_path.name} - {find_code}", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")

    out = OUT_DIR / out_png
    fig.savefig(str(out), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {out.name} ({out.stat().st_size // 1024} KB, {len(xs)} 命中)")


def main():
    print("=== B2: 生成 PNG 对比图 ===\n")

    # 1. ST 替换 before/after（在 3-平面看分布）
    print("[1/4] ST-01 改前分布 (3-平面):")
    render_st_overview(DXF_DIR / "3-19-102平面系统图.dxf",
                       "b2_1_st01_before.png", "ST-01", "改前：ST-01 在 3-平面的分布")
    print("[2/4] ST-A 改后分布 (3-平面):")
    render_st_overview(DXF_DIR / "3-19-102平面系统图_ST-01_to_ST-A.dxf",
                       "b2_2_sta_after.png", "ST-A", "改后：ST-A 在 3-平面的分布")

    # 2. 改墙 before/after（聚焦 E6037 周围 5000mm）
    print("\n[3/4] 改墙前 (3-平面, E6037 周围 5000mm):")
    render_wall_area(DXF_DIR / "3-19-102平面系统图.dxf",
                     "b2_3_wall_before.png", "E6037", 5000,
                     "改前：墙 E6037 周围 5000mm（红线=目标墙）")
    print("[4/4] 改墙后 (3-平面, E6037 周围 5000mm):")
    render_wall_area(DXF_DIR / "3-19-102平面系统图_demo_moved500.dxf",
                     "b2_4_wall_after.png", "E6037", 5000,
                     "改后：墙 E6037 整体 +500mm（红线=目标墙新位置）")

    print(f"\n✓ 全部完成。输出到: {OUT_DIR}/")


if __name__ == "__main__":
    main()
