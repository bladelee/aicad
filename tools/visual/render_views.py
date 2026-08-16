"""
render_views — 方案 G 反证实验（Phase G-0）最小渲染器

⚠️ 关键转折（2026-08-09 实测）：
   ezdxf Frontend + matplotlib backend 在这种规模真实图上完全不可用：
   - draw_layout 9471 实体 = 233s，最终 10KB 空图（autoscale 被 7.8e98 退化实体破坏）
   - 换 SVG backend 也好不到哪（160s + 256MB SVG，更糟）
   本渲染器绕开 ezdxf Frontend，直接按图层把 LINE/LWPOLYLINE/POLYLINE 抽出来，
   用 matplotlib 原生 LineCollection 渲染：
   - 平面图全图层 ~10s（含读 DXF），分图层只渲墙层 9.6s
   - 比原 Frontend 路径快 28 倍，且 bbox 手动设避开退化实体
   代价：只渲 LINE 类实体，文字/标注/填充不显示
        —— 对反证实验"墙体/门窗关联"任务 100% 够用
        —— 若要全实体全保真，回 ezdxf Frontend（成本 280s/张）

设计依据：方案-G-多模态双视角.md §4 §7
（本文档与方案 G 文档的"复用 renderer.py Frontend"假设后期会同步更新）
"""
from __future__ import annotations
import argparse
import os

import ezdxf
import matplotlib
matplotlib.use("Agg")  # 无 GUI 后端
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

# 19-102 项目的强关联图层组（来自 docs/DXF扫描报告.md §2.1）
# 完整词匹配，绝不用短前缀（memory: desktop-mcp-agent-patterns 反模式）
DEFAULT_LAYER_GROUPS: dict[str, list[str]] = {
    "墙体": ["A原建筑墙体", "A原建筑墙体填充"],
    "外幕墙门窗": ["A原建筑外幕墙，门，窗"],
    "尺寸标注": ["A原建筑尺寸"],
}


def _setup_cjk_font() -> None:
    """让标题/标签里的中文不显示成方块。"""
    candidates = [
        "PingFang SC", "Heiti SC", "Hiragino Sans GB",
        "Arial Unicode MS", "SimHei", "Microsoft YaHei",
    ]
    from matplotlib import font_manager as fm
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = [name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            return
    plt.rcParams["axes.unicode_minus"] = False


_setup_cjk_font()


def _load(dxf_path: str):
    try:
        return ezdxf.readfile(dxf_path)
    except ezdxf.DXFStructureError as e:
        raise SystemExit(f"❌ DXF 结构错误 {dxf_path}: {e}")
    except FileNotFoundError:
        raise SystemExit(f"❌ 文件不存在: {dxf_path}")


def collect_line_segs(layout, layer_filter: set[str] | None = None) -> dict[str, list]:
    """
    从 layout 抽 LINE/LWPOLYLINE/POLYLINE 实体，返回 {图层: [seg, seg, ...]}
    seg = ((x0,y0), (x1,y1))
    layer_filter: 只收集这些图层（None = 全部）
    """
    out: dict[str, list] = {}
    for e in layout:
        try:
            layer = e.dxf.layer
        except Exception:
            continue
        if layer_filter is not None and layer not in layer_filter:
            continue
        et = e.dxftype()
        try:
            if et == "LINE":
                s, ee = e.dxf.start, e.dxf.end
                out.setdefault(layer, []).append(((s.x, s.y), (ee.x, ee.y)))
            elif et == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in e.get_points()]
                if getattr(e, "closed", False):
                    pts.append(pts[0])
                for i in range(len(pts) - 1):
                    out.setdefault(layer, []).append((pts[i], pts[i+1]))
            elif et == "POLYLINE":
                # 不含 PROXY
                if not hasattr(e, "vertices"):
                    continue
                pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
                if e.is_closed:
                    pts.append(pts[0])
                for i in range(len(pts) - 1):
                    out.setdefault(layer, []).append((pts[i], pts[i+1]))
        except Exception:
            continue
    return out


def _draw_segs(ax, segs_by_layer: dict[str, list], color_map=None):
    """把 segs_by_layer 画到 ax，每层一个 LineCollection；返回 bbox"""
    all_xs, all_ys = [], []
    for layer, slist in segs_by_layer.items():
        if not slist:
            continue
        color = (color_map or {}).get(layer, "black")
        lc = LineCollection(slist, linewidths=1.2, color=color)
        ax.add_collection(lc)
        for seg in slist:
            all_xs.extend([seg[0][0], seg[1][0]])
            all_ys.extend([seg[0][1], seg[1][1]])
    if not all_xs:
        return None
    return min(all_xs), min(all_ys), min(all_xs) + (max(all_xs) - min(all_xs)), min(all_ys) + (max(all_ys) - min(all_ys))


def _set_lims(ax, bbox) -> None:
    """手动设 xlim/ylim，绕开 autoscale 被退化实体破坏的问题"""
    x0, y0, x1, y1 = bbox
    if x1 <= x0 or y1 <= y0:
        return
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.margins(0.02)


def _iter_layouts_to_render(doc):
    """优先 modelspace；若 msp 空则回退第一个非 Model layout"""
    yield doc.modelspace(), "Model"
    try:
        msp_empty = sum(1 for _ in doc.modelspace()) == 0
    except Exception:
        msp_empty = True
    if msp_empty:
        for name in doc.layouts.names():
            if name != "Model":
                yield doc.layout(name), name
                return


def _render_ax_from_doc(ax, doc, layer_filter=None, color_map=None):
    """便利函数：从 doc 抽 segs 画到 ax，返回 bbox"""
    bbox = None
    for layout, _name in _iter_layouts_to_render(doc):
        segs = collect_line_segs(layout, layer_filter=layer_filter)
        bb = _draw_segs(ax, segs, color_map=color_map)
        if bbox is None and bb:
            bbox = bb
    return bbox


# ───────────────── V1 全图概览 ─────────────────
def view_overview(dxf_path: str, out: str, dpi: int = 110, figsize=(18, 13)) -> str:
    """V1 全图概览：抽所有图层的 LINE 实体绘一张"""
    doc = _load(dxf_path)
    fig = plt.figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(1, 1, 1)
    ax.set_facecolor("white")
    bbox = _render_ax_from_doc(ax, doc)
    ax.set_aspect("equal")
    if bbox:
        _set_lims(ax, bbox)
    ax.axis("off")
    ax.set_title(f"[V1 全图概览] {os.path.basename(dxf_path)}", fontsize=12)
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    fig.savefig(out, dpi=dpi, bbox_inches="tight", facecolor="white", pad_inches=0.1)
    plt.close(fig)
    return out


# ───────────────── V2 分图层视图 ─────────────────
def view_by_layer(
    dxf_path: str,
    out_dir: str,
    layer_groups: dict[str, list[str]] | None = None,
    dpi: int = 120,
) -> list[str]:
    """V2 分图层：按图层组分别渲染，每组一张"""
    doc = _load(dxf_path)
    groups = layer_groups or DEFAULT_LAYER_GROUPS
    os.makedirs(out_dir, exist_ok=True)
    results: list[str] = []
    base = os.path.splitext(os.path.basename(dxf_path))[0]
    for group_name, layer_names in groups.items():
        existing = {ln for ln in layer_names if ln in doc.layers}
        if not existing:
            print(f"  ⚠️ 组 [{group_name}] 图层都不存在 {layer_names}，跳过")
            continue
        fig = plt.figure(figsize=(18, 13), facecolor="white")
        ax = fig.add_subplot(1, 1, 1)
        ax.set_facecolor("white")
        bbox = _render_ax_from_doc(ax, doc, layer_filter=existing)
        ax.set_aspect("equal")
        if bbox:
            _set_lims(ax, bbox)
        ax.axis("off")
        safe = group_name.replace("/", "_")
        out = os.path.join(out_dir, f"{base}__{safe}.png")
        n_segs = sum(sum(len(v) for v in
                         collect_line_segs(L, existing).values())
                     for L, _ in _iter_layouts_to_render(doc))
        ax.set_title(
            f"[V2 分图层:{group_name}] {base}\nlayers={sorted(existing)} | segs={n_segs}",
            fontsize=11,
        )
        fig.savefig(out, dpi=dpi, bbox_inches="tight", facecolor="white", pad_inches=0.1)
        plt.close(fig)
        print(f"  ✓ {out}")
        results.append(out)
    return results


# ───────────────── V3 跨图并排 ─────────────────
def view_side_by_side(
    dxf_paths: list[str],
    out: str,
    dpi: int = 100,
    each_figsize=(12, 9),
) -> str:
    """V3 跨图并排：每张图独立 xlim/ylim，横向拼接"""
    assert len(dxf_paths) >= 2
    fig, axes = plt.subplots(
        1, len(dxf_paths),
        figsize=(each_figsize[0] * len(dxf_paths), each_figsize[1]),
        facecolor="white",
    )
    if len(dxf_paths) == 2:
        axes = [axes[0], axes[1]]
    legend = []
    for ax, path in zip(axes, dxf_paths):
        ax.set_facecolor("white")
        doc = _load(path)
        bbox = _render_ax_from_doc(ax, doc)
        ax.set_aspect("equal")
        if bbox:
            _set_lims(ax, bbox)
        ax.axis("off")
        name = os.path.basename(path)
        ax.set_title(name, fontsize=11)
        legend.append(name)
    fig.suptitle("[V3 跨图并排] " + "  vs  ".join(legend), fontsize=13)
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    fig.savefig(out, dpi=dpi, bbox_inches="tight", facecolor="white", pad_inches=0.1)
    plt.close(fig)
    return out


# ───────────────── CLI ─────────────────
def _cli() -> int:
    p = argparse.ArgumentParser(description="方案 G 反证实验最小渲染器")
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("overview", help="V1 全图概览")
    p1.add_argument("--dxf", required=True)
    p1.add_argument("--out", required=True)
    p1.add_argument("--dpi", type=int, default=110)

    p2 = sub.add_parser("by_layer", help="V2 分图层视图")
    p2.add_argument("--dxf", required=True)
    p2.add_argument("--out_dir", required=True)

    p3 = sub.add_parser("side_by_side", help="V3 跨图并排")
    p3.add_argument("--dxfs", nargs="+", required=True)
    p3.add_argument("--out", required=True)

    args = p.parse_args()
    if args.cmd == "overview":
        out = view_overview(args.dxf, args.out, dpi=args.dpi)
    elif args.cmd == "by_layer":
        outs = view_by_layer(args.dxf, args.out_dir)
        out = f"{len(outs)} 张 PNG 写到 {args.out_dir}"
    elif args.cmd == "side_by_side":
        out = view_side_by_side(args.dxfs, args.out)
    else:
        p.error("unknown command")
    print(f"✅ done: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
