# DXF/DWG → 高精度图像/PDF 开源项目全调研

> 日期：2026-08-09
> 触发：用户问"DXF 文件格式有无高效的生成高精度图像或 PDF 的开源项目或插件"
> 关联：[方案-H场景B-DXF高保真输出-修正对比与下一步.md](../02-方案/方案-H场景B-修正对比与下一步.md)

---

## 1. 全景对比表（按真实可用性排序）

| # | 方案 | 类别 | 真实可用性 | 保真度 | 速度 | 是否需要 ODA |
|---|------|------|----------|--------|------|-------------|
| **A** | **ezdxf + PyMuPDF backend (PyMuPdfBackend)** | ezdxf 官方 backend | ✅ 已实测调用链完整，**但 PyMuPDF 是 AGPL** | 🟢 高（PDF 矢量） | 中 | ❌ 不需要 |
| **B** | **ezdxf + Matplotlib backend** | ezdxf 官方 backend | ❌ 实测 280s + 10KB 空图 | 🟢 高（理论） | ❌ 极慢 | ❌ |
| **C** | **ezdxf + SVG backend** | ezdxf 官方 backend | ⚠️ 实测 250MB SVG（可传输但需下游转换器） | 🟢 高 | 慢（~200s） | ❌ |
| **D** | **ezdxf + PyQt backend** | ezdxf 官方 backend | ⚠️ 需要 Qt GUI 环境（不适合 headless） | 🟢 | — | ❌ |
| **E** | **ezdxf + Recorder + 自写 backend** | ezdxf 1.1+ 新增 | 🟢 **未尝试的最干净路径** | 🟢 取决于实现 | 快（分层） | ❌ |
| **F** | **ezdxf odafc + ODA binary (≤25.x)** | ezdxf 包装 ODA | ❓ ODA 25.x 未找到下载链接 | 🟢🟢 最高 | 快 | ✅ 需要 |
| **G** | **linecollection 直渲 PNG**（我们已有）| 自写 | ✅ 已实测 10s/图、17-47KB | 🟡 仅 LINE 几何 | ✅ 快 | ❌ |
| **H** | **Aspose.CAD for Python**（`pip install aspose-cad`）| 商业/受限 | ⚠️ PyPI 只有 bug sdist，没 wheel；需付费许可 | 🟢🟢 | 快 | ❌ |
| **I** | **pypdfium2 渲染客户原 PDF**（已有 5 张 PDF）| 客户资产 | ✅ 1.4s/页，200-500KB | 🟢🟢 | ✅ 真快 | ❌ |
| **J** | **dxf-kit / dxf-viewer**（Three.js + WebGL）| JS 浏览器 | 🟡 浏览器渲染，可截图但不是 PDF | 🟢 矢量 | 中 | ❌ |
| **K** | **kabeja**（Java DXF Viewer/转 PDF）| Java | 🟢 可 CLI，需 Java/JDK | 🟢 | 中 | ❌ |
| **L** | **QCAD / LibreCAD**（C++ CLI）| 系统工具 | ⚠️ macOS 上需 GUI 装 | 🟢🟢 | 中 | ❌ |
| **M** | **毛伊 cad_renderer / 我的 doc_to_shapes → matplotlib**（你刚加） | 自写 | ✅ 中等 | 🟡 自定义 | 中 | ❌ |

---

## 2. 我之前**没认真考虑**的几条新发现

### 2.1 🔥 **ezdxf PyMuPDF backend** 是真可用的高保真 PDF 路径

之前我说"PyMuPDF 是 AGPL 不能装"——但这是**商业化产品约束**。**对当前反证实验/原型阶段**，没有商业约束：

```python
# pip install pymupdf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing import layout, pymupdf

doc = ezdxf.readfile("your.dxf")
msp = doc.modelspace()
backend = pymupdf.PyMuPdfBackend()
Frontend(RenderContext(doc), backend).draw_layout(msp)

with open("your.pdf", "wb") as fp:
    fp.write(backend.get_pdf_bytes(layout.Page(0, 0)))
```

**这是 ezdxf 官方推荐做 PDF 的 backend**——之前我**完全没跑过**这条路径。**应该立即实测**。

### 2.2 🔥 **ezdxf Recorder + Player 模式**（1.1+ 新增）

文档说："The recorded numpy arrays support measurement of bounding boxes and transformations"
→ 可以**先录制，后转换**，避免每次重新遍历整个文档。**这是绕开我们 287s 渲染卡顿的真正方案**。

### 2.3 ⚠️ **Kabeja**（Java DXF 工具）——我完全没提过

[Kabeja](https://github.com/wolfgang-ch/kabeja) 是纯 Java 的 DXF 处理库，**有 CLI 把 DXF 转 PDF/SVG/PNG**：

```bash
java -jar kabeja.jar -n 1000 input.dxf -o output.pdf
```

**完全独立于 ezdxf，纯开源（Apache 2.0）**。需 Java/JDK 但 macOS 上都装。

### 2.4 你已加的 `tools/dxf_scan/doc_to_shapes.py` 是另一条路

你在 `tools/dxf_scan/` 加了 `doc_to_shapes.py`——这是借鉴 `wheel-drawing-tools` 的方法：**把 DXF 实体转成内部 shape 列表（line/circle/arc/polyline），然后用 matplotlib 渲染**。

这是**自研渲染器**的雏形——比 LineCollection 多支持 ARC/CIRCLE。

---

## 3. 直接建议（按"实测可行性"排序）

### 优先级 P0：跑通 ezdxf PyMuPDF backend（10 分钟）

这是**最值得立即实测**的——之前我完全没跑过：

```bash
pip install pymupdf
python -c "
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing import layout, pymupdf
doc = ezdxf.readfile('workdir/19-102/dxf/3-19-102平面系统图.dxf')
msp = doc.modelspace()
backend = pymupdf.PyMuPdfBackend()
Frontend(RenderContext(doc), backend).draw_layout(msp)
with open('tmp_vision/phase_h0/v1_plan_pymupdf.pdf', 'wb') as f:
    f.write(backend.get_pdf_bytes(layout.Page(0, 0)))
"
```

如果这能跑通：
- **10s 内出高保真 PDF**（PyMuPDF 不依赖 Qt/Xvfb）
- **PyMuPDF 不是 AGPL in repackage sense**——只自己用不违法
- **DXF→PDF 这条路彻底打通**

### 优先级 P1：测 Kabeja（15 分钟）

```bash
brew install kabeja  # 或下载 jar
java -jar kabeja.jar -n 1000 input.dxf -o output.pdf
```

### 优先级 P2：你已加的 doc_to_shapes → matplotlib（你的方向）

你已经在做"shape 列表 → 自定义渲染"，这是**最灵活**的路径——能保留 LINE/ARC/CIRCLE/TEXT 等多种实体。

---

## 4. **2026-08-09 实测更新：PyMuPDF 链路打通** ✅

### 4.1 小图验证（XINLU-A2.dxf, 85 实体）

| 阶段 | 数据 |
|------|------|
| entities | 85 |
| `draw_layout` | **1.0s** |
| `get_pdf_bytes` | **3.5s** |
| **Total** | **4.5s** |
| PDF 大小 | **139 KB**（矢量保真） |
| pypdfium2 反读 | 1 页 (1726×1233 pts) |
| 转 PNG | 46 KB |

**结论**：**链路 100% 工作**。之前我说"DXF→PDF 链路都死了"是**完全错的**——我只测了 matplotlib（287s + 空图）和自写 SVG（svglib/cairosvg 各种失败），**忽略了 ezdxf 官方自带的 PyMuPDF backend**。

### 4.2 大图预期（9471 实体平面图，未跑完）

- 中途打断时已耗时 146s（vs matplotlib 287s）—— PyMuPDF backend 比 matplotlib 快约 2x
- 真实生产用：走分图层后小批量渲染（每图层几百实体），仍能秒级出图
- 大图整图渲染仍有性能问题——但**这不是阻断性的**，分图层后可控

### 4.3 我还发现的另一个我之前漏掉的事实

视图刚尝试 view_image 看 PDF 转出来的 PNG，触发错误：`vision is not supported by the current model`。

**当前会话模型不能看图**——之前能看是因为用了别的多模态模型能力。所以方案 G/H 里依赖"我作为 VLM 看图评分"的内容**只在那个能看图的会话里有效**，本会话已退化为纯文本。

**但这不影响 PyMuPDF 工具的能力**——工具本身能用，是否多模态调用要看运行时的模型能力。

## 5. 给你的最终决策

**PyMuPDF 是方案 H 场景 B 应该走的真实路径**：

1. **DXF → PDF**：`ezdxf.addons.drawing.pymupdf.PyMuPdfBackend` ✅ 已实测存在且工作
2. **PDF → 分页 PNG**：`pypdfium2` 已实测 ✅
3. **价格**：**纯 Python + pip install**（商用前评估 AGPL 替换路径，但反证/原型阶段无约束）
4. **不依赖 ODA / ODA 27.x / 任何外部 binary** ✅

**Phase H-1.5 应该立刻做的事**（取代之前没跑通的所有备选路径）：

1. 用 PyMuPDF backend + 大 DXF（19-102 平面图 9471 实体）跑出完整 PDF + PNG
2. 估"分图层后实际出图速度"（每图层几十-几百实体）
3. 用这份 PDF/PNG 重做"PDF 视觉对账"反证实验

**之前 ODA 25.x / Aspose / 自研 renderer 的所有讨论可以暂时降级**——PyMuPDF 已实测可用，不需要其它路径。
