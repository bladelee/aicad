"""P1 原型脚本：渲改前/改后骨架图，供 M3 视觉评审用。
不调 VLM——VLM 评审在另一个 chat 里完成。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _ROOT)

from tools.visual.render_views import view_overview

os.makedirs(os.path.join(_ROOT, "tmp_vision/phase_h1"), exist_ok=True)

before = os.path.join(_ROOT, "workdir/19-102/dxf/3-19-102平面系统图.dxf")
after = os.path.join(_ROOT, "workdir/19-102/dxf/3-19-102平面系统图_moved_500_0.dxf")

out_before = os.path.join(_ROOT, "tmp_vision/phase_h1/verify_p1_before.png")
out_after = os.path.join(_ROOT, "tmp_vision/phase_h1/verify_p1_after.png")

print("▶ rendering BEFORE...")
view_overview(before, out_before)
print(f"  ✓ {out_before} ({os.path.getsize(out_before)//1024} KB)")

print("▶ rendering AFTER...")
view_overview(after, out_after)
print(f"  ✓ {out_after} ({os.path.getsize(out_after)//1024} KB)")

print("\n✅ P1 渲染完成。下一步：M3 看这两张图，按 4 维清单打分。")
