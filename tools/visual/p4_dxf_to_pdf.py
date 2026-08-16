"""P4 原型：实测 ezdxf SVG → svglib → reportlab DXF→PDF 链路

目标：验证 R5（决策 1A → C 升级路径可行性）
如果 OK：场景 B 升级路径解锁
如果失败：场景 B 暂不实现（或仅保留决策 1A 极有限场景）

链路：
    ezdxf SVGBackend → SVG 字符串 → svglib.svg2rlg → reportlab 写 PDF
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
    """ezdxf SVG 后端 → SVG 字符串 + 耗时"""
    t0 = time.time()
    doc = ezdxf.readfile(dxf_path)
    ctx = RenderContext(doc)
    backend = SVGBackend()
    Frontend(ctx, backend).draw_layout(doc.modelspace())
    page = Page(0, 0)
    settings = Settings(fit_page=True)
    svg = backend.get_string(page=page, settings=settings)
    return svg, time.time() - t0


def svg_to_pdf(svg_path: str, out_pdf: str) -> tuple[int, float]:
    """svglib → reportlab 写 PDF，返回文件大小 KB + 耗时

    svglib.svg2rlg 只接受文件路径或 file-like 对象，不接受字符串。
    """
    t0 = time.time()
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    drawing = svg2rlg(svg_path)  # 必须是路径
    renderPDF.drawToFile(drawing, out_pdf)
    sz = os.path.getsize(out_pdf)
    return sz // 1024, time.time() - t0


def main() -> int:
    dxf_path = os.path.join(_ROOT, "workdir/19-102/dxf/3-19-102平面系统图.dxf")

    print("▶ P4 step 1: ezdxf SVG 后端")
    try:
        svg, t1 = dxf_to_svg(dxf_path)
        svg_kb = len(svg.encode("utf-8")) // 1024
        print(f"  ✓ SVG 生成: {svg_kb} KB, {t1:.1f}s")
    except Exception as e:
        print(f"  ✗ SVG 生成失败: {type(e).__name__}: {e}")
        return 1

    # 先存临时 SVG 文件（svglib 需要文件路径）
    tmp_svg = os.path.join(OUT_DIR, "p4_dxf.svg")
    with open(tmp_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  → SVG 已存到 {tmp_svg}（{os.path.getsize(tmp_svg)//1024} KB）")

    print("▶ P4 step 2: svglib → reportlab")
    out_pdf = os.path.join(OUT_DIR, "p4_dxf_to_pdf.pdf")
    try:
        size_kb, t2 = svg_to_pdf(tmp_svg, out_pdf)
        print(f"  ✓ PDF 输出: {size_kb} KB, {t2:.1f}s, path={out_pdf}")
    except Exception as e:
        print(f"  ✗ PDF 转换失败: {type(e).__name__}: {e}")
        # 留 SVG 用于诊断
        return 1

    print("▶ P4 step 3: pypdfium2 反读验证")
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(out_pdf)
        print(f"  ✓ PDF 可读: {len(pdf)} 页")
        if len(pdf) > 0:
            page = pdf[0]
            print(f"    page 0: {page.get_size()}")
            bmp = page.render(scale=1.0)
            img = bmp.to_pil()
            print(f"    反读渲染: {img.size}, mode={img.mode}")
    except Exception as e:
        print(f"  ✗ PDF 反读失败: {type(e).__name__}: {e}")

    # 清理临时 SVG（保留 PDF 给后续用）
    try:
        os.remove(tmp_svg)
        print(f"  清理临时 SVG: {tmp_svg}")
    except OSError:
        pass

    print(f"\n✅ P4 完成。SVG={svg_kb}KB, PDF={size_kb}KB, 总耗时={t1+t2:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
