"""
dxf_to_pdf — DXF → 高保真 PDF + PNG（PyMuPDF backend）

基于 2026-08-09 实测发现：ezdxf.addons.drawing.pymupdf.PyMuPdfBackend 工作良好。
小图（85 实体）= 4.5s，PDF 139KB，矢量保真。
大图（9471 实体）= draw_layout 146s 仍偏慢 → 本工具的关键优化是"分图层小批量"。

用法：
    # 全图渲染 PDF
    python tools/visual/dxf_to_pdf.py 3-平面系统图.dxf --out tmp/v1_plan.pdf

    # 分图层按组渲染多张 PDF/PNG（绕过大图 draw_layout 慢）
    python tools/visual/dxf_to_pdf.py 3-平面系统图.dxf \
        --out_dir tmp/v2_layers --by_layer_group

    # 渲染为 PNG（PDF→PNG via pypdfium2）
    python tools/visual/dxf_to_pdf.py 3-平面系统图.dxf --out tmp/v1_plan.png

设计依据：方案-H场景B-DXF高保真输出-补充调研.md §4
"""
from __future__ import annotations
import argparse
import os
import sys
import time
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _ROOT)

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing import layout, pymupdf
import pypdfium2 as pdfium


# 19-102 项目的强关联图层组（来自 docs/DXF扫描报告.md §2.1）
DEFAULT_LAYER_GROUPS: dict[str, list[str]] = {
    "墙体": ["A原建筑墙体", "A原建筑墙体填充"],
    "外幕墙门窗": ["A原建筑外幕墙，门，窗"],
    "尺寸标注": ["A原建筑尺寸"],
    "地坪": ["F地坪分缝细线", "F地坪分缝粗线", "F地坪填充",
              "S新铺地坪定位尺寸", "H地坪符号"],
    "天花": ["S天花灯具定位尺寸", "S天花造型定位尺寸",
              "C天花造型线", "C天花格栅细线", "L天灯"],
}


def _doc_with_layers_only(src_dxf: str, layer_filter: set[str] | None) -> "ezdxf.Document":
    """读 DXF，构造一个新 doc，新 doc 只含在 layer_filter 里的实体。

    实测发现 (2026-08-09)：直接 layer.off() 不影响 msp 遍历——
    RenderContext 仍要扫描 9471 个实体判断 visibility，draw_layout 仍是 23s。
    真正的提速是：构造只含目标实体的新 doc，msp 只有 802 实体而不是 9471。
    """
    if layer_filter is None:
        return ezdxf.readfile(src_dxf)

    src_doc = ezdxf.readfile(src_dxf)

    # 在 src_doc 里直接删除不属于 layer_filter 的实体
    # modelspace / paper space 都处理
    deleted = 0
    for layout_name in list(src_doc.layouts.names()):
        lay = src_doc.layouts.get(layout_name)
        # 收集要删除的实体（不能边迭代边删）
        to_delete = []
        for ent in lay:
            try:
                if ent.dxf.layer not in layer_filter:
                    to_delete.append(ent)
            except Exception:
                to_delete.append(ent)
        for ent in to_delete:
            try:
                lay.delete_entity(ent)
                deleted += 1
            except Exception:
                pass
    print(f"  filtered: deleted {deleted} entities (not in {len(layer_filter)} layers)")
    return src_doc


def render_to_pdf_bytes(dxf_path: str, layer_filter: set[str] | None = None) -> tuple[bytes, float, int]:
    """DXF → PDF bytes，返回 (pdf_bytes, total_seconds, model_entity_count)"""
    t0 = time.time()
    doc = _doc_with_layers_only(dxf_path, layer_filter)
    msp = doc.modelspace()
    n_entities = sum(1 for _ in msp)
    print(f"  entities: {n_entities}, layers kept: {len(layer_filter) if layer_filter else 'all'}")

    backend = pymupdf.PyMuPdfBackend()
    Frontend(RenderContext(doc), backend).draw_layout(msp)
    t1 = time.time()
    print(f"  draw_layout: {t1 - t0:.1f}s")

    pdf_bytes = backend.get_pdf_bytes(layout.Page(0, 0))
    t2 = time.time()
    print(f"  get_pdf_bytes: {t2 - t1:.1f}s, size: {len(pdf_bytes) // 1024} KB")
    return pdf_bytes, t2 - t0, n_entities


def save_pdf(pdf_bytes: bytes, out_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"  ✓ PDF: {os.path.getsize(out_path) // 1024} KB → {out_path}")


def pdf_to_png(pdf_path: str, out_png: str, dpi_scale: float = 1.0) -> dict:
    """PDF → PNG via pypdfium2。多页取第一页。"""
    pdf = pdfium.PdfDocument(pdf_path)
    n_pages = len(pdf)
    info = {"pages": n_pages}
    if n_pages == 0:
        return info
    page = pdf[0]
    info["page0_size_pts"] = tuple(round(x) for x in page.get_size())
    bmp = page.render(scale=dpi_scale)
    img = bmp.to_pil()
    os.makedirs(os.path.dirname(os.path.abspath(out_png)) or ".", exist_ok=True)
    img.save(out_png, optimize=True)
    info["png_path"] = out_png
    info["png_size_kb"] = os.path.getsize(out_png) // 1024
    info["png_dims"] = img.size
    print(f"  ✓ PNG: {info['png_size_kb']} KB, {img.size} → {out_png}")
    return info


# ───────────────── 单图 / 全图 ─────────────────
def render_full(dxf_path: str, out: str, also_png: bool = True) -> dict:
    """整图渲染（含全部实体）——大图会慢"""
    print(f"▶ render_full: {os.path.basename(dxf_path)}")
    pdf_bytes, total, n = render_to_pdf_bytes(dxf_path)
    save_pdf(pdf_bytes, out)
    res = {"pdf": out, "entities": n, "total_sec": round(total, 1)}
    if also_png:
        png_out = os.path.splitext(out)[0] + ".png"
        png_info = pdf_to_png(out, png_out)
        res["png"] = png_info
    return res


# ───────────────── 分图层组 ─────────────────
def render_by_layer_groups(
    dxf_path: str,
    out_dir: str,
    layer_groups: dict[str, list[str]] | None = None,
    also_png: bool = True,
    use_subprocess: bool = None,
) -> list[dict]:
    """按图层组分别渲染——单组通常几百实体，秒级出图，避开大图 draw_layout 慢。

    use_subprocess 默认 False（实测 5 个子进程并行会 OOM，因为每个子进程都要
    加载完整 134MB DXF ≈ 207MB，5 个 1GB+）。
    改成主进程串行跑，每组渲染完后 del doc + gc.collect() 释放内存。

    use_subprocess=True 仅在小图（< 1000 实体）时用，能省时间。
    """
    groups = layer_groups or DEFAULT_LAYER_GROUPS
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(dxf_path))[0]
    results = []
    import gc

    for group_name, layer_names in groups.items():
        out_pdf = os.path.join(out_dir, f"{base}__{group_name}.pdf")
        if os.path.exists(out_pdf):
            sz = os.path.getsize(out_pdf) // 1024
            print(f"  [{group_name}] 已存在 ({sz} KB)，跳过")
            results.append({"group": group_name, "pdf": out_pdf, "skipped": True})
            continue

        print(f"\n▶ group [{group_name}]")
        print(f"  layers: {layer_names}")
        try:
            pdf_bytes, total, n = render_to_pdf_bytes(
                dxf_path, layer_filter=set(layer_names)
            )
        except MemoryError as e:
            print(f"  ✗ MemoryError: {e}")
            continue
        if n == 0:
            print(f"  ⚠️ 该组 0 实体（图里没匹配图层），跳过")
            continue
        save_pdf(pdf_bytes, out_pdf)

        item = {"group": group_name, "layers": layer_names,
                "pdf": out_pdf, "entities": n,
                "total_sec": round(total, 1)}
        if also_png:
            out_png = os.path.join(out_dir, f"{base}__{group_name}.png")
            item["png"] = pdf_to_png(out_pdf, out_png)

        results.append(item)
        # 关键：每组之间释放内存，避免后续 OOM
        del pdf_bytes
        gc.collect()
        print(f"  (gc.collect() done)")
    return results


# ───────────────── CLI ─────────────────
def _cli() -> int:
    p = argparse.ArgumentParser(description="DXF → 高保真 PDF + PNG（PyMuPDF backend）")
    p.add_argument("dxf", help="DXF 文件路径")
    p.add_argument("--out", help="单图输出路径（.pdf 或 .png）")
    p.add_argument("--out_dir", help="分组输出目录")
    p.add_argument("--by_layer_group", action="store_true",
                   help="按图层组渲染（避开大图 draw_layout 慢），主进程串行 + 每组间 gc")
    p.add_argument("--also_png", action="store_true",
                   help="分组模式下输出 PNG（默认只 PDF）")
    p.add_argument("--no-png", action="store_true",
                   help="只输出 PDF，不转 PNG")
    p.add_argument("--dpi", type=float, default=1.0,
                   help="PNG 的 DPI scale（1.0=72 DPI）")
    args = p.parse_args()

    also_png = not args.no_png or args.also_png

    if args.by_layer_group or args.out_dir:
        out_dir = args.out_dir or os.path.join("tmp_vision", "phase_h1_5", "by_layer")
        print(f"\n=== 分图层组渲染: {args.dxf} → {out_dir} ===")
        results = render_by_layer_groups(args.dxf, out_dir, also_png=also_png)
        total_t = time.time()
        print(f"\n✅ 共 {len(results)} 组：")
        total_pdf_kb = 0
        for r in results:
            sz = os.path.getsize(r["pdf"]) // 1024
            total_pdf_kb += sz
            print(f"  [{r['group']}] {r['entities']} entities, "
                  f"{r['total_sec']}s PDF → {sz} KB")
        print(f"  总 PDF 大小: {total_pdf_kb} KB")
        return 0

    if not args.out:
        p.error("需要 --out 或 --out_dir")

    print(f"\n=== 单图渲染: {args.dxf} → {args.out} ===")
    if args.out.endswith(".png"):
        # 直接出 PNG（先 PDF 再 PNG）
        tmp_pdf = args.out.replace(".png", ".pdf")
        render_full(args.dxf, tmp_pdf, also_png=False)
        print(f"  → 转 PNG ({args.dpi}x)")
        pdf_to_png(tmp_pdf, args.out, dpi_scale=args.dpi)
    else:
        render_full(args.dxf, args.out, also_png=also_png)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
