"""
pdf_to_pages — 把 PDF 按页拆成 PNG（场景 A 视觉对账的输入准备）

依赖：pypdfium2 (Apache-2.0, 无 AGPL 传染)
背景：方案 G 试图用 ezdxf 自渲 PNG，结果丢 TEXT/INSERT/HATCH 大量语义。
      设计师原 PDF 含完整渲染，是视觉对账的高保真输入。
      实测 19-102 平面图 PDF 50 页，每页 200-500KB（scale=1.0/72 DPI），
      单页可上传多模态模型，全 50 页则需按任务选页。

用法：
    # 全拆
    python tools/visual/pdf_to_pages.py \\
        samples/19-102/3-平面系统图-布局.pdf \\
        --out_dir tmp_vision/phase_h0/pdf_plan

    # 只拆 1-3 页（按任务选页）
    python tools/visual/pdf_to_pages.py samples/19-102/3-平面系统图-布局.pdf \\
        --out_dir tmp_vision/phase_h0/pdf_plan --pages 0 1 2

    # 选 scale（72=轻量，108=清晰，144=放大）
    python tools/visual/pdf_to_pages.py samples/19-102/3-平面系统图-布局.pdf \\
        --out_dir tmp_vision/phase_h0/pdf_plan --scale 1.0

    # JPEG 模式（更小文件，但有损）
    python tools/visual/pdf_to_pages.py samples/19-102/3-平面系统图-布局.pdf \\
        --out_dir tmp_vision/phase_h0/pdf_plan --jpeg --jpeg-quality 80

设计依据：方案-H §3 Phase H-0 交付清单
"""
from __future__ import annotations
import argparse
import os

import pypdfium2 as pdfium


def render_pdf(pdf_path: str, out_dir: str,
               pages: list[int] | None = None,
               scale: float = 1.0,
               use_jpeg: bool = False,
               jpeg_quality: int = 85) -> dict:
    """
    拆 PDF 为 PNG/JPEG。返回 summary dict。
    pages: None = 拆全部；否则按指定页码（0-based）拆
    scale: 1.0=72 DPI, 1.5=108 DPI, 2.0=144 DPI
    """
    pdf = pdfium.PdfDocument(pdf_path)
    total_pages = len(pdf)
    if pages is None:
        page_indices = list(range(total_pages))
    else:
        page_indices = [p for p in pages if 0 <= p < total_pages]
        if not page_indices:
            raise ValueError(f"--pages {pages} 全不在有效范围 [0, {total_pages})")

    os.makedirs(out_dir, exist_ok=True)
    ext = "jpg" if use_jpeg else "png"
    written: list[dict] = []
    for i in page_indices:
        page = pdf[i]
        bmp = page.render(scale=scale)
        img = bmp.to_pil()
        out_path = os.path.join(out_dir, f"p{i:02d}.{ext}")
        if use_jpeg:
            img = img.convert("RGB")  # JPEG 不支持 alpha
            img.save(out_path, "JPEG", quality=jpeg_quality, optimize=True)
        else:
            img.save(out_path, "PNG", optimize=True)
        sz = os.path.getsize(out_path)
        written.append({"page": i, "path": out_path, "size_kb": sz // 1024, "dim": img.size})
    total_kb = sum(w["size_kb"] for w in written)
    return {
        "pdf": os.path.basename(pdf_path),
        "total_pages": total_pages,
        "rendered": written,
        "total_size_kb": total_kb,
        "scale": scale,
        "format": ext,
    }


def _cli() -> int:
    p = argparse.ArgumentParser(description="PDF → PNG/JPEG 拆页")
    p.add_argument("pdf", help="PDF 路径")
    p.add_argument("--out_dir", required=True)
    p.add_argument("--pages", nargs="*", type=int, default=None,
                   help="要拆的页码（0-based），省略=全部")
    p.add_argument("--scale", type=float, default=1.0,
                   help="DPI 倍数（1.0=72 DPI 默认）")
    p.add_argument("--jpeg", action="store_true", help="用 JPEG 格式（更小但有损）")
    p.add_argument("--jpeg-quality", type=int, default=85)
    args = p.parse_args()

    summary = render_pdf(
        args.pdf, args.out_dir,
        pages=args.pages,
        scale=args.scale,
        use_jpeg=args.jpeg,
        jpeg_quality=args.jpeg_quality,
    )
    print(f"✅ {summary['pdf']}: "
          f"渲染 {len(summary['rendered'])}/{summary['total_pages']} 页, "
          f"总 {summary['total_size_kb']} KB ({summary['format']} @ scale={summary['scale']})")
    for w in summary["rendered"]:
        print(f"  p{w['page']:02d}: {w['size_kb']} KB  {w['dim']}  {w['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
