# 借鉴 wheel-drawing-tools：参数化图纸模板模式

> **创建**：2026-08-09 11:00
> 关联：项目 https://github.com/Rosyal/wheel-drawing-tools
> **意义**：从这个钢轮参数化出图项目里抽象出 **3 个可以套用到我们装修改造**的核心模式 + 2 处技术细节可直接抄过来

---

## 一、两个项目的本质对照

| 维度 | wheel-drawing-tools（钢轮） | **我们项目（装修联动改造）** |
|------|------|------|
| 业务 | 输入零件参数（PCD/螺孔/中心孔等）→ 自动出图 | 输入修改需求（改墙/换编号）→ 联动改造多张图 |
| 输入形态 | **JSON 参数**（`wheel_input.sample.json`）| 自然语言 → 解析成参数（更难，需要 MCP 工具）|
| 输入渠道 | GUI / CLI（`generate_wheel_from_params.py`）| LLM 客户端 → MCP stdio |
| **改造方式** | 从零生成图纸（绿色） | **改老图纸（棕色）** |
| 输出 | PNG + DXF + DWG | DXF（写回 AutoCAD）|
| 转换工具 | ODA File Converter（Win 桌面）| libredwg（容器编译）|

**本质相同**：都是「参数 → 图纸自动化」，区别只是他们做的是"从源头出图"，我们做的是"在已有图上联动改"。两者都需要**参数化模板 + 数据库 + 引擎**三件套。

---

## 二、3 个值得直接借鉴的抽象

### 模式 1：**图形定义 (shape_definition) + 参数 (parameters) 双层**

这是该项目**最核心**的设计：

```python
# wheel-drawing-tools 的模板：
{
  "shape_definition": [
    {"type": "rect", "x": 0, "y": 0,
     "width": "L", "height": "W"},   # ← 是字符串表达式！
    {"type": "circle", "cx": "L/2", "cy": "W/2", "r": "R"},
    {"type": "text", "x": "L/2", "y": "W+5",
     "text": "L={L}  W={W}"},        # ← {L} 占位符
  ],
  "parameters": [
    {"param_name": "L", "default_value": 100, "unit": "mm",
     "min_value": 10, "max_value": 1000},
    {"param_name": "W", "default_value": 50,  "unit": "mm"},
    {"param_name": "R", "default_value": 10,  "unit": "mm"},
  ]
}
```

**亮点**：
- 几何坐标**用表达式**（`L/2`、`L+10`、`PCD/2*cos(60*pi/180)`）而非字面量
- 文字内容**用占位符**（`{L} x {W}`）
- 参数定义**带边界**（min/max），支持界面校验
- 用 SQLite 持久化（`drawings.db`）

**→ 我们项目的改造方案**：把"墙的几何"也抽象成表达式模板。

例：把 3-平面里一段墙 + 配套尺寸抽象成模板，参数化"dx/dy/wall_length"等，下次改同类墙直接复用。

---

### 模式 2：**`_eval_expr()` 表达式求值 + `_get_num()` 统一取值**

这是个**少见但极巧妙**的实现：

```python
def _eval_expr(expr: Any, params: Dict[str, float]) -> float:
    """将表达式求值，支持参数名、四则运算及 sqrt/cos/sin/pi"""
    if isinstance(expr, (int, float)):
        return float(expr)
    s = str(expr).strip()
    for name, val in params.items():
        s = re.sub(rf"\b{re.escape(name)}\b", str(val), s)
    safe = {"sqrt": math.sqrt, "cos": math.cos, "sin": math.sin, "pi": math.pi}
    try:
        return float(eval(s, {"__builtins__": {}}, safe))
    except Exception:
        return 0.0

def _get_num(attrs: Dict, key: str, params: Dict[str, float], default: float = 0) -> float:
    return _eval_expr(attrs.get(key, default), params)
```

**亮点**：
- **统一接口**：坐标可以是数字、字符串、表达式（`"L/2"`、`"PCD*sin(30*pi/180)"`）全部支持
- 用 Python 原生 `eval` + 受控 namespace（只给 `sqrt/cos/sin/pi`，禁 `__builtins__`）—— 简单且强大
- 失败时返回 0（不让表达式错中断流程）

**→ 我们项目的复用价值**：
- 我们的 `shift_layer_entities(msp, layer, dx, dy)` 目前只支持**数字平移**
- 升级成支持表达式后，可以参数化更复杂的几何变换（如"墙沿法向延伸 0.5W"）
- **直接抄 `_eval_expr` 即可**，10 行代码

---

### 模式 3：**`flatten_shapes(scale, dx, dy)` — 多视图组合模式**

这是处理"一张图纸多个视图"的关键：

```python
def flatten_shapes(shape_definition, params, scale=1.0, dx=0, dy=0):
    """将含表达式的图形求值为常量坐标，便于平移、缩放后合并导出 DXF。"""
    fp = _params_for_eval(params)
    out = []
    for sh in shape_definition:
        # rect, circle, arc, line, text 都做：
        # x = _get_num(sh, "x", fp) * scale + dx
        # y = _get_num(sh, "y", fp) * scale + dy
        # r = _get_num(sh, "r", fp) * scale   # 半径只缩放不平移
        ...
```

**亮点**：
- 把"参数化图形"先 **flatten** 成"绝对坐标图形"，再加 `dx, dy` 平移和 `scale` 缩放
- 一个视图（如轮幅正视）flatten 后，整体平移到图纸右侧；另一个视图（C-C 剖视）平移到左侧
- 最终拼接出**多视图工程图**

**→ 我们项目的复用价值**：

对应我们的 #4/#5/#9 跨视图联动 — 一段平面的墙已经 flatten 好，要叠加到立面/节点图的对应位置时，就可以用 `flatten_shapes(scale, dx, dy)` 把局部模型整体搬运过去。

```python
# 我们的潜在场景：把改过的墙线搬到立面视图左下角
flat = flatten_shapes([wall_shape_definition], params, scale=0.5, dx=200, dy=100)
add_to_elevation_view(flat)
```

---

## 三、2 处可直接照抄的代码细节

### 3.1 `_doc_to_shapes`：从 DXF 反向提取图形列表

```python
# cad_dxf.py 里
def _doc_to_shapes(doc) -> List[Dict]:
    """从 ezdxf 文档对象提取图形列表（LINE, CIRCLE, ARC, LWPOLYLINE）"""
```

**这个功能正好解决我们 #1 改墙任务里的"一段墙打包成可重放图形"需求**。

我们之前 `probe_layer_bbox.py` 是手写 LINE/CIRCLE/ARC/LWPOLYLINE 的点提取，wheel 项目**已经封装好了**，直接复用。

### 3.2 `dwg_template_fill.py` — DWG 文本占位符替换

```python
# 模板中预先放置 {{图号}} 占位符，运行时按 JSON 替换
_txt(msp, ..., "{{型号}}    规格型号：{{规格型号}}")

# 实际填充：
def _replace_one(text: str, key: str, value: str) -> str:
    # 在 TEXT/MTEXT text 里替换 {{key}} 为 value
```

**正好对应**我们的 #6 ST-01→ST-A 联动！wheel 项目的思路 **更优雅**：
- 我们当前是"扫描所有实体找 ST-01→ 替换"
- wheel 项目是"在模板里预留 `{{材料编号}}` 占位符，参数化填值"

**→ 改造方案**：未来如果用户接受"改造前先在图纸里打占位符"，就能像 wheel 项目一样**优雅参数化**（不用每次扫图）。但是 MVP 阶段要保持当前方案（不能要求用户改源图加占位符）。

---

## 四、对本项目产品化设计的 3 点启发

### 启发 1：**建立"装修要素参数化模板库"**

| 钢轮项目 | ↔ 装修项目 |
|------|------|
| 钢轮模板（PCD/螺孔/中心孔）| **房间模板**（墙长/墙高/门宽/窗高）|
| 表格模板（BOM 表）| **材料表模板**（ST-XX→ST-YY 映射）|
| 标题栏模板（图号/日期/单位） | **图框模板**（项目号/图号/图名）|

→ 长期看应该沉淀**装修要素模板库**，类似 wheel 项目用 SQLite 存。但 MVP 阶段先用当前方式（直接扫老图改）。

### 启发 2：**LLM 应该解析自然语言成 JSON 参数**

| 钢轮项目 | ↔ 装修项目 |
|------|------|
| 用户填 GUI 表 / 写 JSON | **用户用自然语言："把客厅西墙往南移 500mm"** |
| JSON 是 LLM 输出后的形态 | **MCP tool 应该拿到自然语言 parse 成参数 JSON** |

→ 我们项目相比 wheel 的核心**提升点**：用 LLM 把自然语言转成结构化参数（如 `{"action": "move_wall", "wall_handle": "E6037", "dx": 500}`），再喂给 floorplan_mcp 工具。

### 启发 3：**母版+参数 与 改造 的边界要清晰**

钢轮项目是"从母版生新图"，**没有"改造"概念**（每次都是新建一张完整图）。

我们项目是"在已有图上改"，**必需保留原图的所有未涉及实体**（图框、标题栏、目录文字 Φ）。这是 wheel 项目**没有**的复杂度：
- 我们必须用 `ezdxf.readfile()` 读老图 → 改局部 → `saveas`
- wheel 项目可以用 `ezdxf.new()` 从零起新图

这印证了我们**当前 MVP 路线**（直接改老图）的正确性。但产品化阶段可以**借鉴模板思路**做某些场景（如新建标准房间模块贴回去）。

---

## 五、可落地到我们项目的 3 个具体动作

| 行动 | 工作量 | 价值 | 状态 |
|------|------|------|------|
| **A1：抄 `_eval_expr()` + `_get_num()` + `flatten_shapes()`** 到 `tools/dxf_edit/` | 30 分钟 → 实际约 1 小时 | 解锁参数化坐标操作（如表达式驱动的平移/缩放），并升级 `move_wall.py` 支持表达式 dx/dy | ✅ **2026-08-09 完成**（见下） |
| **A2：抄 `_doc_to_shapes()`** 到 `tools/dxf_scan/` | 1 小时 → 实际约 1.5 小时 | 把 probe_layer_bbox 里散写的提取代码统一，便于生成"局部图形可重放包"；并扩展支持 HATCH | ✅ **2026-08-09 完成**（见下） |
| **加 SQLite 模板表**（参考 `database.py`）| 半天 | 沉淀"装修要素模板库"（如默认墙模板/门模板/材料表模板），方便 LLM 调用 | ⏸ MVP 阶段不做 |

### A1 / A2 完成产出（2026-08-09）

**A1 产出**「`tools/dxf_edit/`」
- 新建 `param_expr.py`：`eval_expr` / `get_num` / `params_for_eval` / `flatten_shapes`（去掉前导下划线、加 docstring/中文注释、保留 `eval` 沙箱：禁 `__builtins__`，只放 `sqrt/cos/sin/pi`）
- 新建 `test_param_expr.py`：15 个 case（含三角/除零/sandbox 安全），无需 pytest 直跑
- 升级 `move_wall.py`：`dx`/`dy` 既可传数字（向后兼容）也可传表达式字符串；新增 `params` 入参；返回值含 `dx_resolved` / `dy_resolved` 便于审计
- 集成验证：`tmp_vision/phase_g0/_test_move_wall_expr.py`（4 场景，跑真实 19-102 3-平面图）

**A2 产出**「`tools/dxf_scan/`」
- 新建 `doc_to_shapes.py`：`get_xy` / `doc_to_shapes` / `dxf_to_shapes` / `save_shapes_json` / `filter_shapes_by_layer` / `shapes_bbox`；扩展支持 HATCH（wheel 原版不支持，本项目 A原建筑墙体填充 就是 HATCH 图层必须扫出来）；CLI 一步把任意 DXF 转成"可重放包" JSON
- 新建 `test_doc_to_shapes.py`：19 个 case（涵 LINE/CIRCLE/ARC/LWPOLYLINE/HATCH、按图层过滤、bbox、JSON 序列化）
- 端到端验证：真实 19-102 3-平面 → `A原建筑墙体 + A原建筑墙体填充` 共抽出 2108 个 shape（line 2085 + circle 23，10 个 HATCH 共产出 40 条边界 line）

### ezdxf 1.4.4 关键行为差异（A2 实现过程踩到，永久记下）
- `e.dxf.get(key)` 对**当前实体类型不存在的属性**会抛 `DXFAttributeError`（不是返回 None）—— `get_xy` 必须 try/except，wheel 原版只在 1.0.x 工作正常
- `LWPOLYLINE.get_points("xy")` 返回 `np.float64`，JSON 序列化前要显式 `float(...)`
- 关闭 LWPOLYLINE 用 `dxfattribs={"closed": True}` 或 `pl.closed = True`（property，写入 OK）
- `HATCH` 边界：`PolylinePath` 用 `path.vertices`（**属性**，不是方法）+ `path.is_closed`；`EdgePath` 用 `edge.start/end`（仅 LineEdge 等有）

→ MVP 演示阶段不必要做第 3 个；**第 1、2 个立刻做**收益高。

---

## 六、不能直接复用的地方（差异点）

| 钢轮项目做了 | 我们做不了 | 为什么 |
|------|------|------|
| 全新图纸从零生成（`ezdxf.new`） | 必须保留原图所有非改造实体 | 装修有大量上下文（家具/装饰/标注），不能从零重画 |
| 用于绿色出图，不涉及"老图改造"   | 我们做的是棕色改造 | 业务本质不同 |
| 简单几何组合（钢轮就圆+矩形几个）| 多个图层 + 上万个实体 | 复杂度差 1 个量级 |
| 跨视图靠 flatten + dx/dy 简单拼 | 跨视图靠**Z 索引块编号** | 我们的关联更弱，但更隐式 |

---

## 七、本份文档对路线图的影响

写入了**方案-I**（产品化路线图）的修订项：

1. **Phase B（产品化 ≤3 周）**：抄 `_eval_expr` + `_doc_to_shapes`，升级算法
2. **Phase C（≤2 月）**：建装修要素模板库（SQLite），对齐 wheel 项目的"模板 + 参数"模型
3. **Phase D（≥2 月）**：LLM 解析自然语言 → JSON 参数（与 wheel 项目的 GUI 输入对应）

详见 `方案-I-10项联动改造-产品化路线图.md`。

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1 | 2026-08-09 11:00 | 创建：从 wheel-drawing-tools 学到 3 个模式 + 2 处代码 + 3 点产品启发 |
| v2 | 2026-08-09 18:00 | **完成 A1 + A2 落地**：新增 `tools/dxf_edit/param_expr.py` + `tools/dxf_scan/doc_to_shapes.py`，升级 `move_wall.py` 表达式支持；附 34 个单测全绿，真实 19-102 图纸端到端验证通过；记录 ezdxf 1.4.4 关键行为差异 |
