"""任务 #1 + #2 串通的 demo：在 3-平面 改一堵墙 + 同文件地坪天花跟随联动。

这是用户"2 类联动"中**内自洽**类（同文件不同图层）的最小可工作实现。

策略：
  1. 选一条墙（默认 idx=0）：handle + end 端点偏移 dx
  2. 在改墙位置周围 2000mm 范围（"附近"）找该墙的终点为参考点
  3. 在地坪/天花图层里，凡是 insert point / start point / end point 落在该范围内的 LINE/INSERT/TEXT/MTEXT 实体，整体 dx 平移
  4. 自动备份 + 写新文件 + round-trip 验证

注意：本 demo 默认 dx=500 横移，附近的"地坪/天花"几何也跟着横移 500。
  这是"完全匹配式联动"的最朴素实现，对应 Q3 (a) 用户"完全匹配"含义的取一种理解。

跑法（容器内）:
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_edit/move_wall_with_floor_ceil.py"

env 参数:
    DX=500      平移量（默认 500mm）
    NEAR=2000   联动判定半径（默认 2000mm）
    WALL_IDX=0  选用哪条墙（默认第一条）
"""
from __future__ import annotations
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

import ezdxf

INPUT_DXF = Path("/data/workdir/19-102/dxf/3-19-102平面系统图.dxf")
DX = float(os.environ.get("DX", "500"))
NEAR = float(os.environ.get("NEAR", "2000"))
WALL_IDX = int(os.environ.get("WALL_IDX", "0"))

WALL_LAYER = "A原建筑墙体"
FLOOR_LAYERS = [
    "F地坪分缝细线", "F地坪分缝粗线", "F地坪填充",
    "S新铺地坪定位尺寸", "H地坪符号",
]
CEILING_LAYERS = [
    "L天灯", "S天花灯具定位尺寸", "S天花造型定位尺寸",
    "C天花造型线", "C天花格栅细线", "H天花符号",
]
ALL_PARTICIPATING = [WALL_LAYER] + FLOOR_LAYERS + CEILING_LAYERS


def safe_saveas(doc, path: Path):
    original = type(doc)._update_header_vars
    def patched(self):
        try:
            original(self)
        except AttributeError as e:
            print(f"  [warn] 跳过 header materials: {e}")
    type(doc)._update_header_vars = patched
    try:
        doc.saveas(str(path))
    finally:
        type(doc)._update_header_vars = original


def ent_points(ent):
    """抽出实体的所有关键点（用于距离判定）。"""
    pts = []
    try:
        t = ent.dxftype()
        if t == "LINE":
            pts.append(tuple(ent.dxf.start)[:2])
            pts.append(tuple(ent.dxf.end)[:2])
        elif t == "INSERT":
            pts.append(tuple(ent.dxf.insert)[:2])
        elif t in ("TEXT", "MTEXT"):
            pts.append(tuple(ent.dxf.insert)[:2])
        elif t == "CIRCLE":
            pts.append(tuple(ent.dxf.center)[:2])
        elif t == "ARC":
            pts.append(tuple(ent.dxf.center)[:2])
        elif t == "LWPOLYLINE":
            for p in ent.get_points():
                pts.append((p[0], p[1]))
    except Exception:
        pass
    return pts


def shift_ent(ent, dx: float, dy: float):
    """平移一个实体（与 move_wall.shift_line / shift_layer_entities 一致）"""
    try:
        t = ent.dxftype()
        if t == "LINE":
            s, e = ent.dxf.start, ent.dxf.end
            ent.dxf.start = (s[0]+dx, s[1]+dy, s[2])
            ent.dxf.end = (e[0]+dx, e[1]+dy, e[2])
        elif t == "INSERT":
            p = ent.dxf.insert
            ent.dxf.insert = (p[0]+dx, p[1]+dy, p[2])
        elif t in ("TEXT", "MTEXT"):
            p = ent.dxf.insert
            ent.dxf.insert = (p[0]+dx, p[1]+dy, p[2])
        elif t == "CIRCLE" or t == "ARC":
            c = ent.dxf.center
            ent.dxf.center = (c[0]+dx, c[1]+dy, c[2])
        elif t == "LWPOLYLINE":
            pts = [(p[0]+dx, p[1]+dy) + tuple(p[2:]) for p in ent.get_points()]
            ent.set_points(pts)
    except Exception:
        pass


def main():
    print("=== #1 + #2 串通: 改墙 → 地坪天花顺改 ===")
    print(f"  输入: {INPUT_DXF.name}")
    print(f"  参数: dx={DX}, near={NEAR}, wall_idx={WALL_IDX}")

    doc = ezdxf.readfile(str(INPUT_DXF))
    msp = doc.modelspace()
    n_before = sum(1 for _ in msp)
    print(f"  Model 实体数: {n_before}")

    # 1. 选墙
    walls = [e for e in msp
             if e.dxftype() == "LINE" and e.dxf.layer == WALL_LAYER]
    wall = walls[WALL_IDX]
    print(f"\n  目标墙: handle={wall.dxf.handle}, "
          f"layer={wall.dxf.layer}")
    print(f"  原 start = {tuple(round(c,1) for c in wall.dxf.start)}")
    print(f"  原 end   = {tuple(round(c,1) for c in wall.dxf.end)}")

    # 2. 改墙（整段平移）
    s = tuple(wall.dxf.start)
    e = tuple(wall.dxf.end)
    wall.dxf.start = (s[0]+DX, s[1], s[2])
    wall.dxf.end = (e[0]+DX, e[1], e[2])
    print(f"  新 end   = {tuple(round(c,1) for c in wall.dxf.end)} (dx=+{DX})")

    # 3. 计算墙线中点作为"附近判据"的中心
    cx = (s[0] + e[0]) / 2
    cy = (s[1] + e[1]) / 2
    NEAR_SQ = NEAR ** 2
    print(f"  附近判定圆心: ({cx:.0f}, {cy:.0f}), 半径 {NEAR}")

    # 4. 在地坪 + 天花图层里找落在"附近"的实体，平移
    affected = Counter()
    for ent in msp:
        if ent.dxf.layer not in FLOOR_LAYERS + CEILING_LAYERS:
            continue
        for px, py in ent_points(ent):
            if (px - cx) ** 2 + (py - cy) ** 2 <= NEAR_SQ:
                # 落入附近范围，平移整个实体
                shift_ent(ent, DX, 0)
                affected[ent.dxf.layer] += 1
                break  # 一个实体只 shift 一次

    print(f"\n  联动实体数 = {sum(affected.values())}")
    for ln, n in sorted(affected.items()):
        print(f"    {ln}: {n}")

    # 5. 备份
    BACKUP_DIR = Path("/data/workdir/19-102/backups/wall_floor_ceil")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    n = 1
    while (BACKUP_DIR / f"{INPUT_DXF.stem}.bak{n}.dxf").exists():
        n += 1
    bak = BACKUP_DIR / f"{INPUT_DXF.stem}.bak{n}.dxf"
    shutil.copy2(INPUT_DXF, bak)
    print(f"\n  备份: {bak.name}")

    # 6. 写
    out = INPUT_DXF.with_name(f"{INPUT_DXF.stem}_wall_floor_ceil.dxf")
    safe_saveas(doc, out)
    print(f"  输出: {out.name}")

    # 7. round-trip
    doc2 = ezdxf.readfile(str(out))
    n_after = sum(1 for _ in doc2.modelspace())
    types_b = Counter(e.dxftype() for e in msp)
    types_a = Counter(e.dxftype() for e in doc2.modelspace())
    diff = {k: (types_b.get(k, 0), types_a.get(k, 0))
            for k in set(types_b) | set(types_a)
            if types_b.get(k, 0) != types_a.get(k, 0)}
    print(f"\n  实体数: {n_before} → {n_after}")
    if diff:
        print(f"  类型差异: {diff}")
    else:
        print(f"  ✓ 类型分布完全一致")

    # 通过 handle 找改造对象
    target_handle = wall.dxf.handle
    for e in doc2.modelspace():
        if e.dxf.handle == target_handle:
            delta = e.dxf.end[0] - e[0] if False else (e.dxf.end[0] - e.dxf.start[0] - (s[0]-e[0] if False else 0))
            print(f"\n  ✓ 目标墙改后 end  = {tuple(round(c,1) for c in e.dxf.end)}")
            break


if __name__ == "__main__":
    main()
