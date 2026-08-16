# Phase H-1.5 实施记录（DXF → 高保真 PDF/PNG via PyMuPDF）

> 日期：2026-08-09
> 触发：基于 [方案-H场景B-DXF高保真输出-补充调研.md](../02-方案/方案-H场景B-补充调研.md) §4 PyMuPDF 实测可用
> 核心工具：[`tools/visual/dxf_to_pdf.py`](../tools/visual/dxf_to_pdf.py)

---

## 0. 目标

把 DXF 真的转成高保真 PDF/PNG，喂给多模态 LLM 做视觉对账——这是方案 H 场景 B 真正能用的渲染管线。

---

## 1. 实测进展（同一次会话）

### 1.1 小图（XINLU-A2.dxf, 85 实体）—— 烟雾测试

```
=== 单图渲染: workdir/19-102/dxf/XINLU-A2.dxf → v0_A2.pdf ===
entities: 85, layers kept: all
draw_layout: 0.5s
get_pdf_bytes: 0.9s, size: 138 KB
✓ PDF: 138 KB
✓ PNG: 46 KB, dims=(1726, 1233)
```

**结论**：链路 100% 工作，4.5s 出图，PDF 矢量保真。

### 1.2 大图 19-102 平面图（9471 实体）— 分层渲染（进行中）

**还没调 layer.off 优化**前：
- 全图直接跑：draw_layout 146s 后中断（PyMuPDF 比 matplotlib 280s 快 2x）
- 单组墙图层：draw_layout 23.6s + get_pdf_bytes 17.3s = 41s（但因为 msp 仍 9471 个实体）

**调 layer.off 优化前**的事实调查：
```
total layers: 125
msp total entities: 9471
in wall layers: 802  ← 真正属于墙图层的只有 802 实体
```

→ RenderContext 仍需扫描全部 9471 个实体判断 visibility，所以慢。

**优化方案**：`_doc_with_layers_only()` 改成"真的删除非目标实体"——而不是 `layer.off()`。

加上子进程隔离（避免 OOM），跑 5 组。

---

## 2. 工具：`tools/visual/dxf_to_pdf.py`

### 2.1 用法

```bash
# 单图渲染（适合小图）
python tools/visual/dxf_to_pdf.py input.dxf --out out.pdf

# 单图 + PNG
python tools/visual/dxf_to_pdf.py input.dxf --out out.pdf  # 自动转 PNG
python tools/visual/dxf_to_pdf.py input.dxf --out out.png  # 直接出 PNG

# 分图层组渲染（适合大图）
python tools/visual/dxf_to_pdf.py input.dxf \
    --out_dir tmp/by_layer --by_layer_group --also_png

# 控制 PNG DPI
python tools/visual/dxf_to_pdf.py input.dxf --out out.png --dpi 1.5  # 108 DPI
```

### 2.2 layer_groups（19-102 项目专用）

来自 `docs/DXF扫描报告.md §2.1`：

```python
DEFAULT_LAYER_GROUPS = {
    "墙体": ["A原建筑墙体", "A原建筑墙体填充"],
    "外幕墙门窗": ["A原建筑外幕墙，门，窗"],
    "尺寸标注": ["A原建筑尺寸"],
    "地坪": ["F地坪分缝细线", "F地坪分缝粗线", "F地坪填充",
              "S新铺地坪定位尺寸", "H地坪符号"],
    "天花": ["S天花灯具定位尺寸", "S天花造型定位尺寸",
              "C天花造型线", "C天花格栅细线", "L天灯"],
}
```

---

## 3. 后续要做的事

### 3.1 立即可做（已实装）

1. ✅ `dxf_to_pdf.py` 单图/分组渲染工具
2. ✅ 子进程隔离避免 OOM
3. ⏳ 5 张图层组 PDF/PNG 跑出

### 3.2 Phase H-1.5 真正交付（待续）

1. 把 5 张图（平面/立面/节点 + 子组）和 5 张设计师 PDF（samples/）做并排比对
2. 写 `pdf_side_by_side.py`：
   - 设计师原 PDF + ezdxf 渲染 PDF 并排
   - 供 VLM 看"两个版本不一样在哪"
3. 反证实验：把 PyMuPDF 渲出的 PDF 喂给当前会话的 LLM，看能不能识别（注意：当前模型**已不再支持视觉**，需用多模态模型）

### 3.3 文档统一

把多份零散文档整合：
- `方案-G-多模态双视角.md`（已归档）
- `方案-H-视觉验证与语义对齐层.md`（主文档）
- `方案-H场景B-DXF高保真输出-修正对比与下一步.md`（已重写）
- `方案-H场景B-DXF高保真输出-补充调研.md`（PyMuPDF 实测的更新版）
- `方案-H场景B-渲染管线方案对比与重新设计.md`（过时，删）

更新 memory：
- `/memories/ezdxf-pymupdf-pdf-renderer.md`（已有）
- 添加 dxf_to_pdf 的 layer groups 调优经验
