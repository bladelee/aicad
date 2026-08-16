#!/usr/bin/env python3
"""
gen_vision_pack — 一键生成方案 G 反证实验（Phase G-0）所需的全部 PNG 素材

产出（写到 tmp_vision/<任务标签>/）：
    v1_overview_plan.png           平面图全图概览
    v1_overview_elevation.png      立面图全图概览
    v2_plan_layers/<组名>.png     平面图分图层（墙体/门窗/标注）
    v3_plan_vs_elevation.png      平面+立面跨图并排
    v3_plan_vs_node.png           平面+节点跨图并排
    PACK遗迹.md                    列表+用途说明（供贴到多模态前端时引用）

设计依据：方案-G-多模态双视角.md §7
判据基准：与任务 #2（平面改墙→立面顺改）对照
"""
from __future__ import annotations
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _ROOT)

from tools.visual.render_views import (  # noqa: E402
    view_overview, view_by_layer, view_side_by_side,
)

DXF_DIR = os.path.join(_ROOT, "workdir", "19-102", "dxf")
OUT_DIR = os.path.join(_ROOT, "tmp_vision", "phase_g0")


def _t(label: str, fn, *a, **k):
    t0 = time.time()
    print(f"▶ {label} ...", flush=True)
    try:
        r = fn(*a, **k)
        dt = time.time() - t0
        print(f"  ✓ {label} ({dt:.1f}s)", flush=True)
        return r
    except Exception as e:
        dt = time.time() - t0
        print(f"  ✗ {label} 失败 ({dt:.1f}s): {type(e).__name__}: {e}", flush=True)
        return None


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    plan = os.path.join(DXF_DIR, "3-19-102平面系统图.dxf")
    elev = os.path.join(DXF_DIR, "4-19-102立面图.dxf")
    node = os.path.join(DXF_DIR, "5-19-102节点.dxf")

    manifest: list[tuple[str, str, str]] = []  # (path, type, purpose)

    # V1 全图概览 ×2
    p = os.path.join(OUT_DIR, "v1_overview_plan.png")
    if _t("V1 平面图概览", view_overview, plan, p):
        manifest.append((p, "V1 全图", "平面图整体结构（房间布局、墙、门窗、家具、标注）"))
    p = os.path.join(OUT_DIR, "v1_overview_elevation.png")
    if _t("V1 立面图概览", view_overview, elev, p):
        manifest.append((p, "V1 全图", "立面图整体结构（墙体立面表达、材料标注 ST-XX）"))

    # V2 平面图分图层
    out_dir = os.path.join(OUT_DIR, "v2_plan_layers")
    outs = _t("V2 平面图分图层", view_by_layer, plan, out_dir) or []
    for o in outs:
        name = os.path.basename(o)
        manifest.append((o, "V2 分图层", f"平面图单图层组：{os.path.splitext(name)[0].split('__')[-1]}"))

    # V3 跨图并排（核心：反证实验主对照视图）
    p = os.path.join(OUT_DIR, "v3_plan_vs_elevation.png")
    if _t("V3 平面+立面 并排", view_side_by_side, [plan, elev], p):
        manifest.append((p, "V3 跨图并排", "平面图 vs 立面图——验证 VLM 能否看出对应关系"))
    p = os.path.join(OUT_DIR, "v3_plan_vs_node.png")
    if _t("V3 平面+节点 并排", view_side_by_side, [plan, node], p):
        manifest.append((p, "V3 跨图并排", "平面图 vs 节点图——验证 VLM 能否看出对应关系"))

    # 写一个清单 md，便于贴到多模态前端时引用
    md = [f"# 方案 G 反证实验 PNG 清单\n",
          f"生成目录：`{OUT_DIR}`\n",
          f"共 {len(manifest)} 张\n\n"]
    for i, (path, typ, purpose) in enumerate(manifest, 1):
        rel = os.path.relpath(path, _ROOT)
        sz = os.path.getsize(path) // 1024 if os.path.exists(path) else 0
        md.append(f"### {i}. [{typ}] {os.path.basename(path)} ({sz} KB)\n")
        md.append(f"- 路径：`{rel}`\n")
        md.append(f"- 用途：{purpose}\n\n")
    with open(os.path.join(OUT_DIR, "PACK清单.md"), "w") as f:
        f.writelines(md)
    print(f"\n✅ 共生成 {len(manifest)} 张 PNG，清单见 {os.path.join(OUT_DIR, 'PACK清单.md')}")
    return 0 if manifest else 1


if __name__ == "__main__":
    raise SystemExit(main())
