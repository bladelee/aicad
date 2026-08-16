"""任务 #10: 试改一个门的宽度（窄 100mm）。

策略：
1. 在门窗图层下找 1 个 INSERT 块（候选 M_* / DOOR_* / 任意窗帘/门 INSERT）
2. 改它的 xscale（假设块定义原宽 W，xscale=s，实际门宽=W × s）
3. 备份 + 写新文件 + round-trip

宿主机：
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_edit/demo_resize_door.py"
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path
from collections import Counter

import ezdxf

TARGET_DXF = Path("/data/workdir/19-102/dxf/3-19-102平面系统图.dxf")
OUTPUT_DXF = Path("/data/workdir/19-102/dxf/3-19-102平面系统图_door_resized.dxf")
BACKUP_DIR = Path("/data/workdir/19-102/backups/door_resize")

DOOR_LAYER = "A原建筑外幕墙，门，窗"


def safe_saveas(doc, path):
    """绕开 ezdxf 1.4.4 materials bug"""
    original = type(doc)._update_header_vars
    def patched(self):
        try:
            original(self)
        except AttributeError as e:
            print(f"  [warn] 跳过 header materials 更新: {e}")
    type(doc)._update_header_vars = patched
    try:
        doc.saveas(str(path))
    finally:
        type(doc)._update_header_vars = original


def main():
    print("=== #10 demo: 试改门宽 ===\n")
    doc = ezdxf.readfile(str(TARGET_DXF))
    msp = doc.modelspace()

    # 1. 找门窗图层下所有 INSERT
    inserts = [e for e in msp
               if e.dxftype() == "INSERT" and e.dxf.layer == DOOR_LAYER]
    print(f"门窗图层 '{DOOR_LAYER}' 下有 {len(inserts)} 个 INSERT")

    # 2. 候选门块：块名带 M / DOOR / 门
    candidates = [e for e in inserts
                  if any(k in (e.dxf.name or "").upper()
                         for k in ("DOOR", "M_", "MC_", "MEN"))]
    print(f" 其中的"门"候选（块名匹配）: {len(candidates)}")
    if candidates:
        # 拿一个样本
        sample = candidates[0]
        print(f"\n  样本块名: {sample.dxf.name}")
    else:
        # 没明确的，拿前几个看看
        if not inserts:
            print("⚠️ 门窗图层无 INSERT，看其他图层")
            # 退而求其次：找块名带 DOOR 的（任何图层）
            all_door_blocks = [e for e in msp
                               if e.dxftype() == "INSERT"
                               and any(k in (e.dxf.name or "").upper()
                                       for k in ("DOOR", "M_"))]
            print(f"全图层块名带 DOOR/M_ 的: {len(all_door_blocks)}")
            if not all_door_blocks:
                # 看所有 INSERT 块名列表找候选
                from collections import Counter
                bcount = Counter(e.dxf.name for e in msp if e.dxftype() == "INSERT")
                print("所有 INSERT 块 top 20:")
                for n, c in bcount.most_common(20):
                    print(f"  {n}: {c}")
                return
            sample = all_door_blocks[0]
            print(f"\n  样本（fallback）: block={sample.dxf.name}, "
                  f"layer={sample.dxf.layer}")

    # 3. 改 sample 的 xscale：变窄 100mm 等价于按比例改 xscale
    # 先看现有 scale
    original_xs = sample.dxf.xscale if sample.dxf.hasattr("xscale") else 1.0
    original_ys = sample.dxf.yscale if sample.dxf.hasattr("yscale") else 1.0
    print(f"\n  原始 xscale={original_xs}, yscale={original_ys}")
    print(f"  insert=({sample.dxf.insert[0]:.1f}, {sample.dxf.insert[1]:.1f})")
    print(f"  rotation={sample.dxf.rotation if sample.dxf.hasattr('rotation') else 0}")

    # 块定义几何 bbox
    try:
        blk = doc.blocks.get(sample.dxf.name)
        pts = []
        for e in blk:
            if e.dxftype() == "LINE":
                pts.append(e.dxf.start[:2])
                pts.append(e.dxf.end[:2])
            elif e.dxftype() == "ARC":
                # 简化用 center
                pts.append(e.dxf.center[:2])
            elif e.dxftype() == "LWPOLYLINE":
                pts.extend(list(e.get_points()))
        if pts:
            xs_ = [p[0] for p in pts]
            ys_ = [p[1] for p in pts]
            orig_width = max(xs_) - min(xs_)
            print(f"\n  块定义 bbox: x[{min(xs_):.1f}, {max(xs_):.1f}] "
                  f"(width={orig_width:.1f})")
            print(f"             y[{min(ys_):.1f}, {max(ys_):.1f}]")
            actual_width = abs(original_xs) * orig_width
            print(f"  当前实际门宽: |xscale| × width = {actual_width:.1f}")

            # 想变成 width-100，求新 xscale
            target_width = actual_width - 100
            new_xs = target_width / orig_width
            print(f"\n  目标宽: {target_width:.1f}（窄 100mm）")
            print(f"  新 xscale: {original_xs:.3f} → {new_xs:.3f}")
            sample.dxf.xscale = new_xs
    except Exception as e:
        print(f"  失败: {e}")
        return

    # 4. 备份
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    n = 1
    while (BACKUP_DIR / f"{TARGET_DXF.stem}.bak{n}.dxf").exists():
        n += 1
    bak = BACKUP_DIR / f"{TARGET_DXF.stem}.bak{n}.dxf"
    shutil.copy2(TARGET_DXF, bak)
    print(f"\n  备份: {bak.name}")

    # 5. 写
    safe_saveas(doc, OUTPUT_DXF)
    print(f"  输出: {OUTPUT_DXF.name}")

    # 6. round-trip
    doc2 = ezdxf.readfile(str(OUTPUT_DXF))
    n_before = sum(1 for _ in msp)
    n_after = sum(1 for _ in doc2.modelspace())
    types_b = Counter(e.dxftype() for e in msp)
    types_a = Counter(e.dxftype() for e in doc2.modelspace())
    diff = {k: (types_b.get(k, 0), types_a.get(k, 0))
            for k in set(types_b) | set(types_a)
            if types_b.get(k, 0) != types_a.get(k, 0)}
    print(f"\n  实体数: {n_before} → {n_after}")
    if diff:
        print(f"  ⚠️ 差异: {diff}")
    else:
        print(f"  ✓ 类型分布完全一致")

    # 通过 handle 找改后的样本
    target_handle = sample.dxf.handle
    for e in doc2.modelspace():
        if e.dxftype() == "INSERT" and e.dxf.handle == target_handle:
            xs2 = e.dxf.xscale if e.dxf.hasattr("xscale") else 1.0
            print(f"\n✓ 通过 handle 找到改后实体:")
            print(f"  xscale: {original_xs:.3f} → {xs2:.3f}")
            print(f"  保持 {xs2:.3f - new_xs:.3f} 是预期")
            break


if __name__ == "__main__":
    main()
