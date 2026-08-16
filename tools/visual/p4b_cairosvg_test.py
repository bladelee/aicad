"""P4-b：实测 ezdxf SVG → CairoSVG → PDF/PNG（替换 P4 失败的 svglib 路径）

P4 用 svglib 失败了（'NoneType' object has no attribute 'renderScale'，
可能是 ezdxf SVG 输出含 svglib 不识别的元素）。
CairoSVG 基于 pycairo，对 SVG 规范支持更完整。
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _ROOT)

import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page, Settings

OUT_DIR = os.path.join(_ROOT, "tmp_vision/phase_h1")
os.makedirs(OUT_DIR, exist_ok=True)


def dxf_to_svg(dxf_path: str) -> tuple[str, float]:
    t0 = time.time()
    doc = ezdxf.readfile(dxf_path)
    ctx = RenderContext(doc)
    backend = SVGBackend()
    Frontend(ctx, backend).draw_layout(doc.modelspace())
    page = Page(0, 0)
    settings = Settings(fit_page=True)
    svg = backend.get_string(page=page, settings=settings)
    return svg, time.time() - t0


def cairosvg_to_pdf(svg_path: str, out_pdf: str) -> tuple[int, float]:
    """CairoSVG 转 PDF"""
    t0 = time.time()
    import cairosvg
    cairosvg.svg2pdf(url=svg_path, write_to=out_pdf)
    sz = os.path.getsize(out_pdf)
    return sz // 1024, time.time() - t0


def cairosvg_to_png(svg_path: str, out_png: str,
                    dpi: int = 110) -> tuple[int, float, tuple]:
    """CairoSVG 转 PNG（直接拿 PDF 不需要，先试 PNG）"""
    t0 = time.time()
    import cairosvg
    cairosvg.svg2png(url=svg_path, write_to=out_png, dpi=dpi)
    sz = os.path.getsize(out_png)
    from PIL import Image
    img = Image.open(out_png)
    return sz // 1024, time.time() - t0, img.size


def main() -> int:
    dxf_path = os.path.join(_ROOT, "workdir/19-102/dxf/3-19-102平面系统图.dxf")

    print("▶ step 1: ezdxf → SVG")
    try:
        svg, t1 = dxf_to_svg(dxf_path)
        svg_kb = len(svg.encode("utf-8")) // 1024
        print(f"  ✓ SVG: {svg_kb} KB, {t1:.1f}s")
    except Exception as e:
        print(f"  ✗ SVG 失败: {type(e).__name__}: {e}")
        return 1

    tmp_svg = os.path.join(OUT_DIR, "p4b_dxf.svg")
    with open(tmp_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  → SVG 存到 {tmp_svg}")

    print("▶ step 2: CairoSVG → PNG")
    out_png = os.path.join(OUT_DIR, "p4b_dxf.png")
    try:
        size_kb, t2, dims = cairosvg_to_png(tmp_svg, out_png)
        print(f"  ✓ PNG: {size_kb} KB, {dims}, {t2:.1f}s")
    except Exception as e:
        print(f"  ✗ PNG 失败: {type(e).__name__}: {e}")
        return 1

    print("▶ step 3: CairoSVG → PDF")
    out_pdf = os.path.join(OUT_DIR, "p4b_dxf.pdf")
    try:
        size_kb, t3 = cairosvg_to_pdf(tmp_svg, out_pdf)
        print(f"  ✓ PDF: {size_kb} KB, {t3:.1f}s")
    except Exception as e:
        print(f"  ✗ PDF 失败: {type(e).__name__}: {e}")

    print("▶ step 4: pypdfium2 反读 PDF")
    if os.path.exists(out_pdf):
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(out_pdf)
            print(f"  ✓ PDF 可读: {len(pdf)} 页")
            for i, page in enumerate(pdf):
                print(f"    page {i}: {page.get_size()}")
                if i == 0:
                    bmp = page.render(scale=1.0)
                    img = bmp.to_pil()
                    print(f"      反读渲染: {img.size}, mode={img.mode}")
        except Exception as e:
            print(f"  ✗ 反读失败: {type(e).__name__}: {e}")

    # 清理
    try:
        os.remove(tmp_svg)
        print(f"  清理: {tmp_svg}")
    except OSError:
        pass

    print(f"\n✅ 总结: SVG={svg_kb}KB, PNG={size_kb if os.path.exists(out_png) else '?'}KB, "
          f"PDF={size_kb if os.path.exists(out_pdf) else '?'}KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
