# 方案 H — 视觉验证与语义对齐层（PDF 对账 + DIMENSION 解析 + DXF↔PDF 对齐）

> 🆕 **新增方案**（2026-08-09），继承方案 G（已归档）的"视觉验证"方向，但**纠正其根本预设错误**。
> **前置基础**：方案 G 反证实验 + ezdxf TEXT/DIMENSION 实测数据（详见 §2）
> **关系**：与既有方案 A/B/C/F **正交叠加**；与方案 G 关系是"承其方向、纠其预设"
> **一句话**：VLM 的真正价值不在"看图猜结构"，而在 (1) PDF 拆页视觉对账 (2) 改后视觉验收 (3) 给 DXF 几何补"语义标签"（房间名/家具类型）。

---

## 0. 关键认知（方案 G 反证 + ezdxf 实测后的修正）

### 0.1 方案 G 错在哪

方案 G 假设"VLM 看 ezdxf 自渲的 PNG 就能替代/补充结构化 JSON"——反证实验下打 0 分。

**根因**：ezdxf 自渲丢掉了 TEXT/MTEXT/INSERT/HATCH 这些**带语义的实体**，只剩几何骨架 → VLM 看到的是"骨架图"，识别率断崖。

### 0.2 ezdxf 真正能拿出的"语义"（实测 2026-08-09，19-102 平面图 9471 实体）

| 实体类型 | 数量 | 抽出的内容样本 | 实际语义 |
|---------|------|--------------|---------|
| **TEXT** | 516 | `'A原建筑墙体'`, `'07'`, `'0.3'`, `'W新建墙体'` | 🔴 **不是房间名！是图层说明/编号**，没"会客区"这种 |
| **MTEXT** | 226 | `'\\pxsm0.9,qc;-2F'`, `'1F'`, `'-1F'` | 🟡 **天正 TArch 控制码**（楼层/区域），需解码 |
| **DIMENSION** | **1367** | `actual=4000.0, 6200.0` mm | 🟢 **尺寸精确数据**，当前 scan **未解析**（工程缺口） |
| INSERT | 1406 | 块名 + 坐标 | 🟡 家具/门窗，但需识别块名含义 |
| LINE | 2698 | 端点坐标 | 🟢 几何 |
| LWPOLYLINE | 1630 | 端点序列 | 🟢 几何 |
| HATCH | 209 | 填充边界+图案 | 🟡 拼花/材质 |
| ARC/CIRCLE/ELLIPSE | 1315 | 弧形参数 | 🟡 门弧、楼梯 |

### 0.3 ezdxf 拿不到的"语义"（必须 PDF 视觉补）

| 信息 | DXF 是否有 | 谁来读 |
|------|----------|------|
| **房间名**（会客区/餐桌区/厨/卫） | ❌ 没有 | PDF 视觉 |
| **图名/项目号/图框说明** | ❌ 仅有 12 个图层标签 | PDF 视觉 |
| **家具图标含义**（钢琴/沙发/餐桌）| ❌ INSERT 块名不直观 | PDF 视觉 |
| **风格判断**（简欧/现代/中式） | ❌ | PDF 视觉 |
| **真实墙体厚度**（230 vs 200）| 🟡 lineweight 实体存在但通常未被读取 | DXF + 视觉校验 |

### 0.4 方案 H 的核心定位

```
                  ┌──────────────┐
                  │ DXF 几何+图层 │ ──→ 精确坐标系、图层语义、尺寸数字
                  │  (ezdxf 抽取) │
                  └──────┬───────┘
                         │
                  ┌──────▼────────┐    跨图 handle 映射
                  │ 知识图谱层     │ ──→ DE-XX/1EA-XX 编号体系
                  │ (现有+本方案)  │     业务对象标注
                  └──────┬────────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
 ┌──────────┐      ┌──────────┐      ┌──────────┐
 │ VLM 视觉 │      │ 业务模型  │      │ 写操作    │
 │ (PDF拆页)│      │ (承重等级)│      │ (handle)  │
 └──────────┘      └──────────┘      └──────────┘
   用途: 语义对账   用途: 知识补全   用途: 不变
        改后验收         风格判断
```

**VLM 不是结构化的替代，而是补充三件事**：
1. **语义对账**（PDF 视觉 ↔ DXF 几何对齐 → 房间名/家具类型）
2. **改后验收**（改前 PDF + 改后 PNG → 视觉判断改得对不对）
3. **风格/类型识别**（结构化做不到，视觉擅长）

---

## 1. 三个核心场景

### 1.1 场景 A：PDF 视觉对账（Parse-Time）

**触发**：用户在 user_tool 上调 `read_floorplan` 或 `list_rooms` 时返回 JSON。

**流程**：
1. ezdxf 解析 DXF → 实体列表 + 几何
2. （新增）ezdxf 解析 DIMENSION → 尺寸字典 {handle → (actual_mm, override)}
3. （新增）如果客户同时提供 PDF → pypdfium2 拆页（按客户图号/页码对应）
4. **VLM 跨模态对齐**：拿 DXF JSON + PDF 单页 → 输出"对齐报告"
   - "DXF 报告了 5 个房间区域，PDF 上看到房间名：会客区/吧台/餐桌区/电梯厅/卫生间 → 建立 entity_bbox → room_name 映射"
   - "DXF 报告了 1367 个尺寸，PDF 上看到尺寸数字全部能对应上 → 校验通过"
   - "PDF 上有一处 'BECHSTEIN 钢琴'，DXF 里某个 INSERT 块名是 `*U8127` → 标注该 INSERT = 钢琴"

**工具实现**：
```python
def align_vision_to_dxf(dxf_path, pdf_path, page_idx) -> dict:
    """VLM 跨模态对齐，返回 entity_handle → semantic_label 映射"""
    dxf_json = parse_dxf_to_json(dxf_path)  # 现有
    pdf_page_png = pypdfium2_render_page(pdf_path, page_idx, scale=1.0)
    prompt = build_alignment_prompt(dxf_json, pdf_page_png)
    return call_vlm(prompt, image=pdf_page_png)
```

### 1.2 场景 B：改后视觉验收（Write-Time）

**触发**：每次 `move_entity` / `add_entity` / 改 ST-XX 等写操作完成后。

**4 个核心设计决策**（已与用户对齐）：

| # | 决策 | 默认 → 降级 | 升级条件 |
|---|------|------------|---------|
| 1 | 输入形态 | **A**: 改前/后都用 LineCollection 自渲 PNG（同格式公平对比） | 客户没 PNG → **D**: 改前用设计师原 PDF；精度不够 → **C**: DXF→PDF 全保真 |
| 2 | 验收清单 | **4 维结构化**：几何完整性、几何位置、关联保持、副作用 | — |
| 3 | 改后图来源 | **A**: LineCollection 路径（10s/张） | 客户无 PNG → D；精度不够 → C |
| 4 | 失败行为 | **C**: 半自动——默认报告，AI/LLM 询问可触发回滚（与 `.bak` 配套） | — |

**流程（采用决策 A+A+4维+C）**：
1. 用户原始 PDF（如有，决策 1A 升级条件）→ 改前图（reference）
2. DXF 改前 → LineCollection 直渲 PNG（10s）
3. DXF 改后 → LineCollection 直渲 PNG（10s）
4. **VLM 4 维结构化验收**（prompt 模板固化）：
   - **几何完整性**："改后图中，所有声明要改动的 handle 是否还在？"
   - **几何位置**："改后图中，每个被改 handle 的中心位置是否如 change_record 所述？"
   - **关联保持**："改前图中相邻的两个 handle，改后是否仍相邻？"
   - **副作用**："改后图是否有意外出现/消失的元素？"
5. VLM 返回结构化 JSON → 报告写盘 → LLM 据此决定是否回滚

**降级路径**：
- 客户只给 DWG 不给 PNG → 决策 1 升级到 D（改前图用设计师原 PDF）
- LineCollection 渲染丢了关键细节（如图名/家具图标）→ 升级到 C（DXF→PDF→pypdfium2 单页），需先打通 DXF→PDF 转换（PyMuPDF AGPL 不可用，需评估 svglib/svglib+reportlab 等替代）

**关键设计选择**：
- **不破坏现有架构**：验收是"事后审计"，写操作仍由 move_entity 等 user_tool 完成、`.bak` 仍自动生成；VLM 只决定"建议回滚 vs 建议保留"
- **半自动决策 4C**：默认输出结构化报告，让用户在 LLM 对话里说一句"回滚"就触发撤销——比"自动回滚"安全，比"纯报告"有用
- **同格式对比**：决策 1A 让 VLM 在"几何骨架级"上做对比，避免 PDF-vs-PNG 不对等引入的假阴性

**工具实现**（详见 §3 Phase H-1）：
```python
# tools/visual/verify_change.py
verify_change(
    dxf_before="workdir/19-102/dxf/3-平面系统图.dxf",
    dxf_after="workdir/19-102/dxf/3-平面系统图_moved_500_0.dxf",
    change_record={...},           # 由 move_wall 等工具产出
    pdf_before=None,                # 可选：客户提供 PDF
    mode="stub|inline|http",
    out="tmp_vision/phase_h1/verify_change_p00.json",
) -> dict
```

### 1.3 场景 C：风格/类型识别（Bootstrap-Time）

**触发**：首次解析新项目时，调用一次作为知识图谱补全。

**流程**：
1. 拿到 PDF 第一张总览图
2. VLM 看图回答：
   - "项目风格：现代极简 / 简欧 / 中式 / 美式"
   - "户型类型：独栋别墅 / 联排 / 平层"
   - "主要材质：木地板 / 大理石 / 瓷砖"
3. 这些标签写入知识图谱，作为业务模型属性

**价值**：结构化数据完全给不出这些"软信息"，但对用户后续决策有用。

---

## 2. 与现有架构的关系

### 2.1 对 FloorplanBackend 接口的扩展（最小化）

```python
# 现有
class FloorplanBackend(Protocol):
    def read(self, path): ...
    def list_rooms(self, path): ...
    def move_entity(self, path, handle, dx, dy, auto_backup=True): ...

# 新增（向后兼容，旧实现不强制实现）
class FloorplanBackend(Protocol):
    # ... 既有方法不变
    def extract_dimensions(self, path) -> list[dict]:
        """新增：抽 DIMENSION 实体，返回 [{handle, layer, actual_mm, override_text, geometry_bbox}]"""
        ...

    def render_change(self, path, out_png, highlight_handles=None) -> str:
        """新增：DXF → PNG，给场景 B 用"""
        ...
```

**关键**：visual 逻辑不进入 backend——视觉由独立的 `visual_tools.py` 调度，与 backend 解耦。

### 2.2 user_tool 的扩展（5 个工具的视觉可选旁路）

```python
# 现有
def read_floorplan(path: str) -> dict:
    """返回结构化 JSON"""

# 新增可选参数
def read_floorplan(
    path: str,
    pdf_path: str | None = None,           # 场景 A
    pdf_page_idx: int = 0,
    vision_align: bool = False,            # 是否调 VLM 对账
    change_verify_png: str | None = None,  # 场景 B（改后验收专用工具）
) -> dict:
    """返回结构化 JSON + 可选 vision_pack: {room_labels, dimension_check, ...}"""
```

### 2.3 与现有工具链的复用

| 资产 | 复用方式 |
|------|---------|
| `cad_tools.archived/renderer.py` 的 `RenderContext` 思路 | ✅ 用于 change_verify_png（已规避 autoscale 问题） |
| `tools/dxf_scan/scan_dxf.py` 的扫描逻辑 | ✅ 增强抽 DIMENSION/TEXT 字段 |
| `docs/室内装修DWG知识图谱.md` 的实体分类 | ✅ 直接喂 VLM 作为 prompt 上下文 |
| `docs/跨图关联图谱实测发现.md` 的 DE-XX 体系 | ✅ 作为 VLM 跨图对齐的"地址词典" |
| 既有 `tools/visual/render_views.py`（LineCollection 直渲）| ✅ 用于场景 B 改后图渲染 |

---

## 3. 实施路径

### Phase H-0：最小可用管线（**半天**，本轮交付）

**目的**：先把场景 A 跑通（PDF 视觉对账），证明方案 H 价值真实存在。

**交付物**：
1. `tools/dxf_scan/extract_dimensions.py`——抽 DIMENSION 实体成 JSON（**补上 1367 个尺寸数字**这个工程缺口）
2. `tools/visual/pdf_to_pages.py`——pypdfium2 拆 PDF 单页（基于已实测的可工作路径）
3. `tools/visual/align_vision_to_dxf.py`——VLM 跨模态对齐工具（写骨架，VLM 调用部分 stub）
4. 更新 `docs/DXF扫描报告.md`——加入 DIMENSION 维度
5. 跑一个端到端 demo：拿 19-102 平面图 DXF + PDF 第 1 页，输出对齐 JSON 草稿

### Phase H-1：场景 B 改后验收（1-2 天）

1. `tools/visual/render_change_png.py`——改后 DXF → PNG（复用 LineCollection 直渲）
2. 写 VLM 验收 prompt 模板
3. 集成到现有 `move_entity` user_tool

### Phase H-2：场景 C + 知识图谱补全（看 H-0 反馈）

1. 风格识别 prompt 模板
2. 把 VLM 输出写回知识图谱 JSON
3. 跨图语义对齐（PDF 上的房间名 → 跨图 DXF 实体）

---

## 4. 风险与边界（必须诚实标注）

| 风险 | 评级 | 说明 / 缓解 |
|------|------|-----------|
| **VLM 跨模态对齐的稳定性** | 🟡 中 | 不同模型对齐质量差异大；先小范围试 M3/GPT-4V/Gemini |
| **PDF 多页选错页** | 🟡 中 | 客户可能给错 PDF；场景 A 需"我先选页，让用户确认" |
| **pypdfium2 性能** | 🟢 已确认 | 实测 1.4s/页，1 个平面图 PDF 50 页 ~70 秒，可接受 |
| **场景 B 改后图缺失 TEXT/DIMENSION** | 🟡 中 | LineCollection 路径本就丢这些，验收 VLM 看到的也是"骨架"——**对验收有帮助但不完美**。可考虑混合渲染（LINE 用 LineCollection + TEXT/DIM 叠加文字标签）|
| **场景 A 中 VLM 错位对齐** | 🟡 中 | VLM 可能把"会客区"标错位置；需人工校对 UI，或 confidence 阈值低于 X 时强制 confirm |
| **AGPL 传染风险** | 🟢 规避 | 不引 PyMuPDF；pypdfium2 是 Apache-2.0；ezdxf MIT |
| **LLM 视觉上下文限制** | 🟡 中 | M3 1M context 但图像有像素限制；单页 200-500KB 可控，≥4MB 可能拒收 |

### 与既有方案的兼容边界（守护不破）
- 既有 `FloorplanBackend` 接口**只新增不修改**——所有现有 5 个 user_tool **不破坏**签名
- 视觉可选旁路，关闭后行为 100% 等同原方案
- pypdfium2 是 Apache-2.0，**不传染商业产品**

---

## 5. 关于"DXF vs PDF 精度"的回答（直接对方案 G 反思的回答）

方案 G 时期我以为"PDF 视觉读到的所有东西 DXF 都拿不到"——这是错的。

**真实精度对比**（以 19-102 平面图为例）：

| 信息项 | PDF 视觉 | DXF 结构化 | 真实差距 |
|--------|---------|-----------|---------|
| 几何位置（mm 精度）| 🟡 视觉估读 ±10mm | 🟢 DXF 精确 ±0mm | DXF 优 100x |
| 尺寸数字（4900）| 🟢 直接读 | 🟢 DIMENSION 实体（**当前 scan 未解析**）| 平手（需补 DXF） |
| 房间名 | 🟢 视觉直读 | ❌ DXF 没这种字符串 | **PDF 唯一** |
| 家具类型 | 🟢 视觉直读（图标库） | 🟡 INSERT 块名需解析 | PDF 强 |
| 墙体类型（原建筑/新建/装饰）| 🟡 视觉判粗细不可靠 | 🟢 图层名直接给 | DXF 优 |
| 跨图对应（DE-XX） | 🟡 视觉读编号 | 🟢 索引块属性直接读 | DXF 优 |
| 风格（简欧/现代） | 🟢 视觉判定 | ❌ | **PDF 唯一** |

**结论**：PDF 和 DXF **不是替代关系，是精度互补**。方案 H 必须把两者**对齐到一起**才是最终目标。

---

## 6. 关联文档（不重复）

| 文档 | 用途 |
|------|------|
| [`方案-G-多模态双视角.md`](../99-归档/方案-G-多模态双视角.md) | 已归档，提供反证数据 |
| [`docs/室内装修DWG知识图谱.md`](../05-知识沉淀/室内装修DWG知识图谱.md) | 5 大要素分类 + 跨图实体分布 |
| [`docs/跨图关联图谱实测发现.md`](../05-知识沉淀/跨图关联图谱实测发现.md) | DE-XX/1EA-XX 编号体系 |
| [`docs/DXF扫描报告.md`](../05-知识沉淀/DXF扫描报告.md) | 现有 scan 输出，本方案增强 DIMENSION 维度 |
| [`复盘-2026-08-09-DWG转换与图纸摸底.md`](../03-计划与复盘/复盘-2026-08-09-DWG转换与图纸摸底.md) | DWG→DXF 链路经验 |
| `/memories/ezdxf-render-bench.md` | ezdxf Frontend 慢+autoscale bbox 退化的实测（防重蹈） |

---

## 7. Phase H-0 立即交付清单

按你"两个并行"的指示，同时做：
1. ✅ 本文档完成
2. ⏳ `tools/dxf_scan/extract_dimensions.py`（抽 DIMENSION 实体）
3. ⏳ `tools/visual/pdf_to_pages.py`（pypdfium2 拆页工具）
4. ⏳ `tools/visual/align_vision_to_dxf.py`（VLM 对账骨架）
5. ⏳ 端到端 demo 跑一次

预计完成时间：半天（这部分由我后续执行）。
