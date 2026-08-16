"""D1: DIMENSION 重算尝试（路径 C 的可行性探查）

目标：看 3-平面里的 DIMENSION 实体长啥样，改墙后能否重算。

策略：
1. 扫 3-平面所有 DIMENSION，看 defpoint/defpoint2/text 字段
2. 找关联 E6037 墙端点 ± N mm 内的 DIMENSION
3. 模拟"墙端点 +500 后 DIMENSION 怎么改"

跑法:
    docker run --rm -v "$PWD:/data" -e PYTHONHOME=/opt/FreeCAD/usr -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem --entrypoint=/bin/bash floorplan-mcp:latest -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_edit/probe_dimensions.py"
"""
from __future__ import annotations
import math
from pathlib import Path

import ezdxf

DXF = Path("/data/workdir/19-102/dxf/3-19-102平面系统图.dxf")


def main():
    print("=== D1: DIMENSION 重算可行性探查 ===\n")
    doc = ezdxf.readfile(str(DXF))
    msp = doc.modelspace()

    # 1. 统计所有 DIMENSION 类型
    dims = [e for e in msp if e.dxftype().startswith("DIMENSION")]
    print(f"3-平面共有 {len(dims)} 个 DIMENSION 实体\n")

    # 2. 看 DIMENSION 的字段分布
    from collections import Counter
    subtype_count = Counter()
    has_text = 0
    has_measurement = 0
    text_samples = []
    for d in dims:
        # d.dxf 是 DXF namespace
        # DIMENSION 子类型在 d.dimtype 或 d.dxf.dimtype
        try:
            dt = d.dxf.dimtype
            subtype_count[f"dimtype={dt}"] += 1
        except:
            subtype_count["no_dimtype"] += 1
        try:
            t = d.dxf.text
            if t and t != "":
                has_text += 1
                if len(text_samples) < 10:
                    text_samples.append(t)
        except:
            pass
        try:
            m = d.dxf.hasattr("measurement")
            if m:
                has_measurement += 1
        except:
            pass

    print(f"dimtype 分布: {dict(subtype_count)}")
    print(f"有显式 text 的: {has_text}")
    print(f"text 样本（前 10）: {text_samples}")
    print()

    # 3. 找 E6037 墙的端点，看附近 DIMENSION
    target_handle = "E6037"
    wall = None
    for e in msp:
        if e.dxftype() == "LINE" and e.dxf.handle == target_handle:
            wall = e
            break
    if not wall:
        print(f"⚠️ 找不到墙 {target_handle}")
        return
    wall_end = wall.dxf.end
    print(f"目标墙 E6037 end: ({wall_end[0]:.0f}, {wall_end[1]:.0f})")
    print()

    # 找其 DEFPOINT 距离 wall_end 小于 2000mm 的 DIMENSION
    NEAR = 2000
    candidate_dims = []
    for d in dims:
        try:
            dp = d.dxf.defpoint
            dist = math.hypot(dp[0] - wall_end[0], dp[1] - wall_end[1])
            if dist < NEAR:
                candidate_dims.append((dist, d))
        except:
            pass

    if not candidate_dims:
        print(f"E6037 end 周围 {NEAR}mm 范围内没有 DEFPOINT（可能 dimtype 不是线性标注）")
        # 试看任意 DIMENSION 的几何位置
        print("\n=== 检查 DIMENSION 的实际位置 ===")
        for d in dims[:5]:
            try:
                dp = d.dxf.defpoint
                dp2 = d.dxf.defpoint2 if d.dxf.hasattr("defpoint2") else None
                print(f"  text={d.dxf.text!r} defpoint={dp[:2]}", end="")
                if dp2:
                    print(f" defpoint2={dp2[:2]}", end="")
                # measurement
                if hasattr(d, "measurement"):
                    try:
                        print(f" measurement={d.measurement}", end="")
                    except:
                        pass
                print()
            except Exception as e:
                print(f"  error: {e}")
        return

    candidate_dims.sort(key=lambda x: x[0])
    print(f"找到 {len(candidate_dims)} 个候选 DIMENSION（DEFPOINT 距墙端 < {NEAR}mm）：")
    for dist, d in candidate_dims[:10]:
        dp = d.dxf.defpoint
        dp2 = d.dxf.defpoint2 if d.dxf.hasattr("defpoint2") else None
        text = d.dxf.text or "<auto>"
        measurement = getattr(d, "measurement", "?")
        print(f"\n  距离 {dist:.0f}mm:")
        print(f"    text={text!r}  measurement={measurement}")
        print(f"    defpoint =({dp[0]:.0f}, {dp[1]:.0f})")
        if dp2:
            print(f"    defpoint2=({dp2[0]:.0f}, {dp2[1]:.0f})")
            actual_dist = math.hypot(dp2[0]-dp[0], dp2[1]-dp[1])
            print(f"    实际距离={actual_dist:.1f}")


if __name__ == "__main__":
    main()
