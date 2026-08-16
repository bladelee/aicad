"""最小改墙 demo：在 3-平面系统图.dxf 里找一段"原建筑墙体"，移动一个端点 500mm。

验证：
1. ✅ 找到一段墙 LINE（layer='A原建筑墙体'）
2. ✅ 备份原文件到 .bak
3. ✅ 修改该 LINE 的 end 端点（dx=500）
4. ✅ 保存到新 DXF
5. ✅ round-trip 检查：原 9471 实体 → 改后还是 9471 实体（数量不变）

宿主机用：
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_scan/demo_move_wall.py"

预期结果：workdir/19-102/dxf/3-..._modified.dxf
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path
from collections import Counter

import ezdxf

WALL_LAYER = "A原建筑墙体"
INPUT_DXF = Path("/data/workdir/19-102/dxf/3-19-102平面系统图.dxf")
OUTPUT_DXF = Path("/data/workdir/19-102/dxf/3-19-102平面系统图_modified.dxf")
BACKUP = Path("/data/workdir/19-102/dxf/3-19-102平面系统图.bak1.dxf")


def main():
    print(f"=== move_wall 最小 demo ===")
    print(f"输入: {INPUT_DXF.name}")
    print(f"目标图层: {WALL_LAYER!r}")
    print()

    # 1. 读
    doc = ezdxf.readfile(str(INPUT_DXF))
    msp = doc.modelspace()
    n_before = sum(1 for _ in msp)
    print(f"✓ 已读：{n_before} 个 modelspace 实体")

    # 2. 列出墙体图层的所有 LINE 实体
    walls = []
    for ent in msp:
        if ent.dxftype() == "LINE" and ent.dxf.layer == WALL_LAYER:
            walls.append(ent)
    print(f"✓ 在 {WALL_LAYER!r} 图层找到 {len(walls)} 条 LINE")
    if not walls:
        print("✗ 没找到墙，退出")
        sys.exit(1)

    # 3. 选第一个墙，看一组水平/垂直墙段（取水平最长的，便于直观验证）
    def length_horizontal(e):
        return abs(e.dxf.end[0] - e.dxf.start[0])

    def length_vertical(e):
        return abs(e.dxf.end[1] - e.dxf.start[1])

    # 找水平最长的墙段
    horizontal_walls = [w for w in walls
                        if abs(w.dxf.end[1] - w.dxf.start[1]) < 0.1]
    horizontal_walls.sort(key=length_horizontal, reverse=True)
    if horizontal_walls:
        target = horizontal_walls[0]
        kind = "horizontal"
    else:
        target = walls[0]
        kind = "?"
    print(f"✓ 选定的目标墙（{kind}，第 1 条最长的）:")
    print(f"  handle: {target.dxf.handle}")
    print(f"  start: ({target.dxf.start[0]:.1f}, {target.dxf.start[1]:.1f})")
    print(f"  end  : ({target.dxf.end[0]:.1f}, {target.dxf.end[1]:.1f})")
    print(f"  length: {length_horizontal(target):.1f}（水平分量）")

    # 4. 备份（.bak1.dxf）
    if not BACKUP.exists():
        shutil.copy2(INPUT_DXF, BACKUP)
        print(f"✓ 备份: {BACKUP.name}")
    else:
        print(f"⚠️  备份已存在，跳过: {BACKUP.name}")

    # 5. 改墙：把 end 端点 x +500mm（向右伸长半米）
    # 这是"延伸墙到新位置"的简化版（不改 mid，只改端点）
    original_end = tuple(target.dxf.end)
    new_end = (original_end[0] + 500.0, original_end[1], original_end[2])
    target.dxf.end = new_end
    print(f"\n✓ 改造完成:")
    print(f"  原 end: ({original_end[0]:.1f}, {original_end[1]:.1f})")
    print(f"  新 end: ({new_end[0]:.1f}, {new_end[1]:.1f})")
    print(f"  水平Δ: +500 mm")

    # 6. 保存到新文件，绕开 ezdxf 1.4.4 + libredwg 转出 DXF 触发的 materials bug
    # 报错：AttributeError 'str' has no attribute 'dxf' on _update_header_vars
    #   → self.materials.get("ByLayer").dxf.handle
    # 因为 libredwg 转的 DXF materials 表里 ByLayer 是字符串而非对象。规避：
    # monkey-patch Document._update_header_vars 让它跳过 materials 部分更新
    try:
        original_update = type(doc)._update_header_vars
        # patch：替换为只更新非 materials 部分
        def safe_update_header(self):
            try:
                original_update(self)
            except AttributeError as e:
                # 容忍 materials 表问题
                print(f"  [warn] 跳过 header materials 更新: {e}")
        type(doc)._update_header_vars = safe_update_header
        doc.saveas(str(OUTPUT_DXF))
    finally:
        type(doc)._update_header_vars = original_update
    print(f"\n✓ 保存: {OUTPUT_DXF.name}")

    # 7. round-trip 验证
    print(f"\n=== round-trip 验证 ===")
    doc2 = ezdxf.readfile(str(OUTPUT_DXF))
    msp2 = doc2.modelspace()
    n_after = sum(1 for _ in msp2)
    types_before = Counter(e.dxftype() for e in msp)
    types_after = Counter(e.dxftype() for e in msp2)
    print(f"实体数 (前→后): {n_before} → {n_after}")
    print(f"实体类型分布一致? {types_before == types_after}")
    if types_before != types_after:
        for k in set(types_before) | set(types_after):
            b, a = types_before.get(k, 0), types_after.get(k, 0)
            if b != a:
                print(f"  ⚠️  {k}: {b} → {a}")

    # 8. 找改造后的目标 LINE 确认被改了
    target_handle = target.dxf.handle
    found = False
    for ent in msp2:
        if ent.dxftype() == "LINE" and ent.dxf.handle == target_handle:
            print(f"\n✓ 通过 handle 找到改造后实体:")
            print(f"  start: ({ent.dxf.start[0]:.1f}, {ent.dxf.start[1]:.1f})")
            print(f"  end  : ({ent.dxf.end[0]:.1f}, {ent.dxf.end[1]:.1f})")
            dx = ent.dxf.end[0] - original_end[0]
            dy = ent.dxf.end[1] - original_end[1]
            print(f"  Δ: dx={dx:.1f}, dy={dy:.1f}")
            if abs(dx - 500.0) < 0.1 and abs(dy) < 0.1:
                print(f"  ✅ 改造正确保持！")
            else:
                print(f"  ❌ Δ 和预期不符（dx=500, dy=0）")
            found = True
            break
    if not found:
        print(f"❌ 通过 handle 找不到目标实体")

    print()
    print(f"=== 文件对比 ===")
    print(f"原件大小:     {INPUT_DXF.stat().st_size:>12,} 字节")
    print(f"改后大小:     {OUTPUT_DXF.stat().st_size:>12,} 字节")
    print(f"备份大小:     {BACKUP.stat().st_size:>12,} 字节")


if __name__ == "__main__":
    main()
