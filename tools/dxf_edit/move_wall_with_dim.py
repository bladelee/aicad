"""D1 实现：跟随墙体同步联动 DIMENSION（路径 C 落地）

算法：
  1. 改 LINE.start/end
  2. 找 DEFPOINT 落在墙端点 ± N mm 内的 DIMENSION
  3. 平移对应的 defpoint / defpoint2
  4. （text='<auto>', AutoCAD 打开后自动按新 defpoint 重算 measurement）

跑法:
    docker run --rm -v "$PWD:/data" -e PYTHONHOME=/opt/FreeCAD/usr -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem --entrypoint=/bin/bash floorplan-mcp:latest -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_edit/move_wall_with_dim.py"
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import ezdxf
from ezdxf.math import Vec2

# 复用 move_wall 的 safe_saveas monkey-patch
sys.path.insert(0, "/data/tools/dxf_edit")
from move_wall import safe_saveas  # type: ignore  # noqa: E402

DXF = Path("/data/workdir/19-102/dxf/3-19-102平面系统图.dxf")
OUT = Path("/data/workdir/19-102/demo_outputs/3_with_dim_sync.dxf")

WALL_HANDLE = "E6037"
DX, DY = 500.0, 0.0  # 墙沿 +X 平移 500mm
NEAR = 2000.0  # mm


def update_dimensions_near_wall(msp, wall_ent: ezdxf.entities.Line, dx: float, dy: float, near: float = NEAR):
    """同步 DEFPOINT 落在墙端点 ±near 范围内、且 defpoint/defpoint2 之一正好在墙端上的 DIMENSION。

    返回：(更新的 dim 数量, 详细日志 list)
    """
    wall_start = Vec2(wall_ent.dxf.start)
    wall_end = Vec2(wall_ent.dxf.end)
    logs = []

    def touches_wall(pt: Vec2) -> bool:
        """defpoint 是否正好落在墙的某个端点上（容差 near）"""
        return (pt - wall_start).magnitude <= near or (pt - wall_end).magnitude <= near

    def on_wall_end(pt: Vec2) -> bool:
        """非常接近墙端点的（更严格）：<= near/4"""
        tol = near / 4
        return (pt - wall_start).magnitude <= tol or (pt - wall_end).magnitude <= tol

    updated = 0
    for d in msp:
        if not d.dxftype().startswith("DIMENSION"):
            continue
        try:
            dp = Vec2(d.dxf.defpoint)
        except Exception:
            continue
        # 只有 defpoint 靠近墙端 的才算
        if not touches_wall(dp):
            continue
        # 进一步要求 defpoint2 也在墙端附近（说明这个 dim 描述的是墙的一段）
        try:
            dp2 = Vec2(d.dxf.defpoint2)
            has_dp2 = True
        except Exception:
            has_dp2 = False
        # 只要其中一端正好在 wall 端点上（近），就同步
        moved_dp = False
        moved_dp2 = False
        if on_wall_end(dp) or touches_wall(dp):
            # 只有"端点正好在墙上"才动，避免误伤路过的标注
            if on_wall_end(dp):
                d.dxf.defpoint = (dp.x + dx, dp.y + dy, d.dxf.defpoint[2] if len(d.dxf.defpoint) > 2 else 0)
                moved_dp = True
        if has_dp2 and on_wall_end(dp2):
            d.dxf.defpoint2 = (dp2.x + dx, dp2.y + dy, d.dxf.defpoint2[2] if len(d.dxf.defpoint2) > 2 else 0)
            moved_dp2 = True
        if moved_dp or moved_dp2:
            updated += 1
            logs.append({
                "handle": d.dxf.handle,
                "text": d.dxf.text,
                "old_defpoint": tuple(round(c, 1) for c in dp),
                "moved_dp": moved_dp,
                "moved_dp2": moved_dp2,
            })
    return updated, logs


def main():
    print("=== D1: E6037 +500mm + DIMENSION 同步 ===\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.readfile(str(DXF))
    msp = doc.modelspace()

    # 1. 找墙
    wall = None
    for e in msp:
        if e.dxftype() == "LINE" and e.dxf.handle == WALL_HANDLE:
            wall = e
            break
    if not wall:
        print(f"⚠️ 找不到墙 {WALL_HANDLE}")
        return
    print(f"墙 {WALL_HANDLE}: start={tuple(round(c,1) for c in wall.dxf.start)} end={tuple(round(c,1) for c in wall.dxf.end)}")
    print(f"平移: dx={DX}, dy={DY}, near 容差={NEAR}mm\n")

    # 2. 同步 DIMENSION
    n, logs = update_dimensions_near_wall(msp, wall, DX, DY, NEAR)
    print(f"DIMENSION 同步: 更新 {n} 个")
    for log in logs:
        print(f"  handle={log['handle']} text={log['text']!r}")
        print(f"    defpoint=(was) {log['old_defpoint']} -> +({DX}, {DY}) [dp={log['moved_dp']}, dp2={log['moved_dp2']}]")

    # 3. 更新墙本体
    wall.dxf.start = (wall.dxf.start[0] + DX, wall.dxf.start[1] + DY, wall.dxf.start[2])
    wall.dxf.end = (wall.dxf.end[0] + DX, wall.dxf.end[1] + DY, wall.dxf.end[2])
    print(f"\n墙本体已平移.")
    # （地坪/天花联动由 move_wall_with_floor_ceil.py 处理, 此处不做以免重复）

    # 4. 保存
    safe_saveas(doc, str(OUT))
    print(f"\n✅ 已保存: {OUT}")
    print(f"   原文件未动.")


if __name__ == "__main__":
    main()
