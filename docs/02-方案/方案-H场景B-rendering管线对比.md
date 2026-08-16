# 方案 H 场景 B 渲染管线对比与重新设计

> 日期：2026-08-09
> 触发：用户指出"转换为 png 似乎有很大风险，dxf 还有哪些输出高精度图像的方案，请重新设计比较下"
> 关联：[方案 H 视觉验证与语义对齐层 §1.2 场景 B](../02-方案/方案-H-视觉验证与语义对齐层.md)、[方案-H场景B-review与原型验证](../02-方案/方案-H场景B-review与原型验证.md)

---

## 0. 问题背景

场景 B（改后视觉验收）的核心需求：
- **改前**：有完整 TEXT/INSERT/HATCH/DIM 的高保真图（验证的"标准答案"）
- **改后**：DXF 改后生成可对比的图像（"待验答案"）
- **目的**：VLM/M3 看图，视觉判断"改得对不对"

之前方案 H §1.2 决策 1 选了"A 默认 + 升级到 C (DXF→PDF)"。**实测发现 DXF→PDF 链路不可行**（svglib/cairosvg 都失败），且 ezdxf SVG 后端本身耗时 200s+ 生成 250MB。**必须重新设计**。

---

## 1. 全 DXF → 高保真图像方案对比表

| # | 方案 | 链路 | 依赖 | 实测耗时(19-102 平面 9471 实体) | 输出大小 | 保真度 | 结论 |
|---|------|------|------|--------------------------|---------|--------|------|
| **A** | **LineCollection 直渲 PNG** | ezdxf 抽 LINE/LWPOLYLINE/POLYLINE → matplotlib LineCollection | ezdxf + matplotlib + Pillow | **9.6s** | **17-47KB** | ⚠️ 仅 LINE | ✅ **可用** |
| B | ezdxf Frontend + matplotlib | ezdxf Frontend → matplotlib | ezdxf + matplotlib | **280s** | 10KB（**空图**） | 全实体 | ❌ **autoscale bbox 被退化实体破坏** |
| C1 | ezdxf SVG → svglib → PDF | ezdxf SVG → svg2rlg → reportlab | ezdxf + svglib + reportlab | 192s SVG + 失败 PDF | SVG 250MB | 全实体 | ❌ **svglib 'NoneType.renderScale' 失败** |
| C2 | ezdxf SVG → CairoSVG → PNG/PDF | ezdxf SVG → cairosvg | ezdxf + cairosvg（**需系统 libcairo**） | 350s SVG + 失败 PNG | SVG 250MB | 全实体 | ❌ **miniconda3 无系统 libcairo** |
| C3 | ezdxf SVG → lxml + 自写 SVG→PNG | ezdxf SVG → 自实现转换 | ezdxf + lxml + cairo | 未实测 | 估算 50-200KB | 全实体 | 🟡 **工作量大，自研转换器** |
| D | ezdxf Frontend + 商业绘图仪后端 | ezdxf Frontend → QCAD/IntelliCAD（需 GUI） | 商业 CAD 软件 | ❌ 无 CLI | — | 全实体 | ❌ **需 GUI，违背 headless** |
| E | **客户原 PDF → pypdfium2 → PNG** | pypdfium2 拆页 | pypdfium2 | **1.4s/页** | 200-500KB | 全保真 | ✅ **但仅适用于客户提供了 PDF 的场景** |
| F | LibreDWG 命令行转换 | DWG/DXF → PDF（libredwg CLI） | libredwg | ❌ 无 CLI | — | — | ❌ **libredwg 无 DXF→PDF 命令** |
| G | ODA File Converter | DWG/DXF → PDF | ODA | ❌ 无 CLI | — | — | ❌ **ODA 27.x 无 CLI 模式** |
| H | CAD 商业 SDK（Aspose.CAD 等云 API） | 上传 → 云转 → 下载 | 云 API + 商业 license | 估算 5-10s/张 | 100-500KB | 全保真 | 🟡 **付费且需网络** |
| I | **PDF 嵌入截图** | DXF → PDF（嵌入 PNG 截图） | ezdxf + ReportLab | 未实测 | ~1MB | 取决于截图 | 🟡 **绕远，没真解决 DXF→PDF** |
| J | **DXF → ImageMagick / GraphicsMagick** | DXF → ImageMagick 直接打开 | 系统装 ImageMagick | ❌ 系统未装 | — | — | ❌ **需先装系统工具** |

---

## 2. 关键认知：保真度 vs 成本的权衡

把上面按"保真度"和"成本"画成二维：

```
保真度
  ↑
  │  E (PDF) ●                       ● C3 (lxml自写)
  │                              ● H (云 API)
  │  
  │  B (ezdxf Frontend) ●
  │
  │  D (商业GUI) ●
  │
  │  A (LineCollection) ●
  │              ↑
  │              │
  └────────────────────────────────────→ 成本
       10s 1MB               200s 250MB  需付费
       (极低成本)              (高成本)   (商业)
```

**关键洞察**：
1. **保真度高 + 低成本 = 不存在**（至少在 macOS + miniconda3 环境下）
2. **A 方案（LineCollection）是性价比最优解**——9.6s + 17-47KB，代价是丢语义
3. **E 方案（设计师原 PDF）是真高保真，但客户不一定提供**
4. **C 链路（D 方案升级路径）**全部堵死，**方案 H 原决策 1 的 C 升级路径不可行**

---

## 3. 重新设计：分层取舍

### 3.1 核心原则

> **改前/后图的"公平对比"优先于"绝对保真"。**
**改前用设计师原 PDF（高保真） → 改后只能用 ezdxf 直渲（低保真） → 两边"不对等"。**

但**这个不对等是有用的**：VLM 在做改后验收时：
- 看**改前 PDF**：高保真，能识别房间名、尺寸、ST-XX
- 看**改后骨架图**：只能看几何是否"几何完整"（线段数/位置是否对应）

→ **VLM 在改后图上根本不需要看 TEXT（设计意图已在改前图被识别）；改后图只用来确认"几何对得上"**。

这是反直觉但**很关键的洞察**：场景 B 的真正价值不是"看图找差异"，而是"确认 geometry_consistent"。

### 3.2 三层渲染策略（推荐）

| 场景 | 改前 | 改后 | 评估能力 | 备注 |
|------|------|------|---------|------|
| **A. 客户有 PDF** | pypdfium2 拆单页 | ezdxf LineCollection | 弱（仅几何）但可校验 | 默认 |
| **B. 客户无 PDF 但需高保真** | （无） | （无）→ 暂不支持场景 B | — | 不接 |
| **C. 客户无 PDF 接受低保真** | ezdxf LineCollection | ezdxf LineCollection | 弱（仅几何） | 退回 A 路径同格式对比 |
| **D. 关键帧加保真增强** | pypdfium2 + ezdxf 叠加 | ezdxf 基础 + TEXT 标注层 | 中 | 关键区域加注 |

**关键洞察：A 路径（设计师 PDF + ezdxf LineCollection）已经够用**——
- 改前 PDF 保真度高，给 VLM 完整语义
- 改后 LineCollection 仅几何，VLM 只能校验"几何一致"
- 但场景 B 的本质就是"几何一致"验收——这恰好契合

### 3.3 升级路径（不依赖任何 DXF→PDF 工具）

**核心**：**在 ezdxf 基础上自己加 TEXT/DIMENSION/INSERT 的简单渲染层**，不依赖 ezdxf Frontend。

**自研"最小 CAD 渲染器"思路**：

```python
class MinCADRenderer:
    """专为 VLM 视觉验收设计的极简 CAD 渲染器
    比 ezdxf Frontend 快 10x+，保真度刚好够用
    """
    def render(dxf_path, out_png, highlight_handles=None):
        doc = ezdxf.readfile(dxf_path)
        ax = init_axes(...)
        # 1. LINE/LWPOLYLINE/POLYLINE → LineCollection（已有，10s）
        # 2. CIRCLE/ARC/ELLIPSE → matplotlib.patches（直接画）
        # 3. TEXT/MTEXT → matplotlib.text（画字符，可能缺字体，但能定位）
        # 4. INSERT → 在 insert 点画个小方块+ 块名标注
        # 5. HATCH → 跳过（只在视觉上不重要）
        # 6. DIMENSION → 跳尺寸数字（结构化 JSON 已含）
        ax.set_xlim(...); ax.set_ylim(...)
        fig.savefig(out_png)
```

**预期**：渲染时间 12-15s（vs ezdxf Frontend 280s），文件 50-200KB，**含 TEXT 字符**（房间名/尺寸）+ INSERT 块名标注。

**开发成本**：半天实现 + 半天测。

### 3.4 不做方案 C 升级路径的明确决定

| 原方案 H §1.2 决策 | 重新设计后 |
|----------------|-----------|
| 1A 默认 → 1D（PDF）→ 1C（DXF→PDF）升级 | **1A 是默认和唯一路径**，无升级（**C 链路全部堵死**）|
| 3A 默认 → 3D（PDF）→ 3C（DXF→PDF）升级 | **3A 是默认和唯一路径**，无升级 |

---

## 4. 重新设计的实施路径

### Phase H-1（重设计版）

#### 4.1 实现 `MinCADRenderer`（半天）

```python
# tools/visual/min_cad_renderer.py
class MinCADRenderer:
    def render(dxf_path, out_png, dpi=110, highlight=None):
        """专用 VLM 验收的极简渲染器：LINE + 简单圆弧 + TEXT 标签"""
```

#### 4.2 `tools/visual/verify_change.py`（半天）

实现场景 B 的核心工具：
```python
def verify_change(
    dxf_before: str,
    dxf_after: str,
    change_record: dict,
    out: str,
) -> dict:
    """4 维结构化验收报告（不含 VLM 调用，纯结构对账）"""
```

#### 4.3 与 VLM 集成的 `verify_change_vlm.py`（半天）

封装"4 维结构化验收 + VLM 视觉补充"。

### Phase H-2（如 Phase H-1 验证有效）

- 自研渲染器扩展到 INSERT 图块图标、HATCH 填充
- 集成到 floorplan-mcp user_tool
- P2 restore_from_bak 已经在 Phase H-1 实现

---

## 5. 决策结论

| 旧决策 | 新决策 | 理由 |
|--------|--------|------|
| DXF→PDF 全保真升级路径 | **不存在**（svglib/cairosvg 都失败） | 实测证明链路不通 |
| 默认用 LineCollection | **保留** | 性价比最优 |
| 三级升级路径（A→D→C） | **简化成一级**（只用 A） | 升级路径被实测堵死 |
| 改后图精度依赖 ezdxf Frontend | **改用自研 MinCADRenderer** | ezdxf Frontend 280s + 10KB 空图，无法用 |

**关键决定**：
1. **方案 H §1.2 决策 1 简化为只走 A 路径**（LineCollection）
2. **不再追求 DXF→PDF**——这条路不可行
3. **新增 Phase H-1.5：自研 MinCADRenderer**——解决 ezdxf Frontend 不可用 + LineCollection 丢语义的折中
4. **Phase H-1 验收能力上限 = 几何一致性**（不是语义完整性）——这是诚实的定位

---

## 6. 下一步

请用户确认：
1. **接受"几何一致性"作为场景 B 的价值上限**（而不是"完整保真"）？
2. **Phase H-1 实现优先级**：先 MinCADRenderer（半天），还是先 verify_change.py（半天）？
3. **反证实验 P1 已证明 VLM 看骨架图 4 维都 0 分**——还要继续场景 B 吗？

如果继续：按 Phase H-1 实施（自研渲染器 + verify_change），1 天交付。
如果放弃：场景 B 整体归档，方案 H 退化为只剩场景 A（PDF 对账）+ 场景 C（风格识别）。