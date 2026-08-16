# 技能：装修图纸自动化改造 SOP（Standard Operating Procedure）

> **创建**：2026-08-09 05:00
> **目的**：把 4 份复盘里反复出现的模式 / 反模式 / 高价值教训，**沉淀成一个可复用的标准操作流程**。下次接任何"装修 DWG 联动改造"类任务时，按此 SOP 走可以少踩 80% 坑。
> **适用范围**：用 ezdxf + Docker + libredwg 处理 AutoCAD/天正/TWT 系 DWG 装修图纸，做改造或信息提取。
> **不适用**：纯 3D（IFC/Revit）、纯渲染（效果图）、原生 AutoCAD ObjectARX 开发。

---

## 0. SOP 总览（执行顺序）

```
┌─ Phase 0：先问 / 先看 ─────────────────────────────┐
│  0.1  要用户原话讲清"5 大要素 + 2 类联动"          │
│  0.2  先扫一遍图纸的真实结构（不要假设）            │
│  0.3  对齐 3 项核心问题（地坪/天花/跨图坐标/匹配含义）│
└──────────────────────────────────────────────────┘
                       ↓
┌─ Phase 1：建图谱（不做改造） ──────────────────────┐
│  1.1  DWG 版本 + 用 ODA? LibreDWG? 决策             │
│  1.2  DWG→DXF 转换（容器化 libredwg）               │
│  1.3  扫描实体类型 / 图层 / 块 / 属性 / 文本        │
│  1.4  建立"图纸内部知识图谱"（哪些图层分别代表啥）  │
│  1.5  建立"跨图关联图谱"（找 Z 立面/节点索引 等）   │
└──────────────────────────────────────────────────┘
                       ↓
┌─ Phase 2：单任务直通（先做正交性高的） ────────────┐
│  2.1  按"正交性 / 数据齐全 / 算法难度 / 现有基础"评分│
│  2.2  先从纯字符串替换类开始（材料编号 类）          │
│  2.3  再做几何变更类（改墙 类）                      │
│  2.4  最后做联动类（内自洽 + 跨视图）                │
└──────────────────────────────────────────────────┘
                       ↓
┌─ Phase 3：复杂联动（依赖前两阶段） ─────────────────┐
│  3.1  内自洽（同文件地坪/天花顺改）                  │
│  3.2  跨视图（平面↔立面↔节点编号联动）              │
│  3.3  几何推理（DIMENSION 重算）                     │
│  3.4  3D / 效果图（视项目需要）                      │
└──────────────────────────────────────────────────┘
```

---

## Phase 0: 先问 / 先看（10-30 分钟）

### 0.1 用户访谈模板（5 必问）

每接一个 DWG 改造任务，**先问**用户这 5 件事（不要假设）：

| # | 问题 | 为什么必问 | 反例（即本 SOP 教训）|
|---|------|------|------|
| 1 | "5 大要素在哪些文件里？目录/材料/平面/立面/节点/效果图分别在哪？" | 避免把"地坪/天花"想成单独 DWG | 用户："地坪天花就在平面图里" → 实测 14 个图层印证 |
| 2 | "图纸是怎么画的？AutoCAD？天正？TWT？还是别的？" | 决定是否要解析 XData/PROXY | 假设"天正=PROXY"实测 PROXY=0，墙就是 LINE |
| 3 | "这套图有没有编号体系（如图号 1-/2-/3-、立面 1EA-XX、节点 DE-XX）？" | 跨图联动靠编号指针，不靠坐标 | 实测发现 `Z节点索引` 块 attrib 含 `DE-XX` 等指针 |
| 4 | "改 A 引起 B 变化，是几何位置完全匹配，还是只更新对应字段？" | 决定算法是几何变换还是字符串重算 | 用户二分法："内自洽要完全匹配，跨视图要对应更新" |
| 5 | "DWG 文件版本？有没有 ODA / AutoCAD 安装可借？" | 决定转换路径 | ODA 27.x 已无 CLI；libredwg 可编译，免 EULA |

→ 拿到用户回答后，**用 5 分钟做实测印证**（不要直接信），把疑问写进"3 项核心问题"待用户最终确认。

### 0.2 5 分钟数据分布扫一遍（不要假设）

**永远先扫一遍**，**再决定算法**：

```python
# 一键扫：实体类型分布 + 含"墙/门/地坪/天花"关键词的图层
import ezdxf
from collections import Counter
doc = ezdxf.readfile("xxx.dxf")
msp = doc.modelspace()
print(Counter(e.dxftype() for e in msp).most_common(10))
print([l.dxf.name for l in doc.layers if any(k in l.dxf.name for k in
      ["墙","门","窗","地坪","天花","吊顶","立面","节点","索引","尺寸"])])
```

**反例**：本 SOP 第 1 个重大错判是"门是 INSERT"，原因就是没扫类型分布先假设了。实测发现门是 `LINE 401 + ARC 307 + LWPOLYLINE 228` 拼出来。

### 0.3 3 项核心问题模板（与用户最终对齐）

写份 `docs/3项核心问题-待用户确认.md`，包含：

- Q1: 地坪/天花完整图层清单（候选实测 + 用户确认遗漏）
- Q2: 跨图坐标对应（实测是否含 Z 索引块编号指针）
- Q3: "完全匹配"和"对应更新"具体含义

**不要急着开工**，先把这 3 项确认完。

---

## Phase 1: 建图谱（30-60 分钟）

### 1.1 DWG 版本识别 + 转换工具选择

```python
# 读 DWG 头 6 字节就能识别版本
DWG_MAGIC = {b'AC1015':'R2000', b'AC1018':'R2004', b'AC1021':'R2007',
             b'AC1024':'R2010', b'AC1027':'R2013', b'AC1032':'R2018+'}
with open(dwg, 'rb') as f: ver = DWG_MAGIC.get(f.read(6), 'unknown')
```

**转换工具优先级**（按合规性 + 跨平台）：

| 优先级 | 工具 | 优势 | 缺陷 |
|------|------|------|------|
| 1️⃣ | **libredwg 编译进 Docker**（推荐，永久记忆里有 Dockerfile）| 完全开源免 EULA；CLI 模式 headless 友好 | 编译 5-10 分钟；R2018+ 写字段可能丢 REGION |
| 2️⃣ | ODA File Converter（用户已装）| 业界事实标准 | 27.x 已无 CLI 模式，纯 GUI；macOS 要求 13+ |
| 3️⃣ | ezdxf_acc（商业）| 直接读 DWG | 收费，不在 PyPI |

→ **80% 场景选 libredwg**。你的 `tools/dwg_to_dxf/Dockerfile.libredwg` 已是模板。

### 1.2 DWG → DXF 批量转换（一条命令）

```bash
for f in samples/<project>/*.dwg; do
  docker run --rm -v "$PWD:/data" libredwg-cli \
    -y -o "/data/workdir/<project>/dxf/$(basename "${f%.dwg}").dxf" "/data/$f"
done
```

**报错语义解读**：
- `Warning: Unknown object, skipping eed/reactors/xdic` → 可忽略（扩展数据字典，与几何无关）
- `Warning: Unstable Class object 536 DIMASSOC` → 标注关联对象，业务无影响
- `Warning: Unstable Class object 527 ACDB_BLOCKREPRESENTATION_DATA` → 块表示，可忽略

### 1.3 全谱扫描脚本（产关联图谱 JSON）

直接用 `tools/dxf_scan/scan_dxf.py`，它已经过实战打磨，能扫：
- 所有 layouts（不止 modelspace）—— 解决"封面/材料表 0 实体"问题
- 实体类型 / 图层 / 块定义 / 块使用 / 文本 / 属性
- 跨图公共图层 + 跨图公共块 + ST-XX 材料编号模式

**输出**：`workdir/<project>/scan_report.json`，可直接 grep 看。

### 1.4 探针套件（5 个必备）

| 探针 | 位置 | 何时用 |
|------|------|------|
| `tools/dxf_scan/probe_xdata.py` | 探天正/PROXY/XData | 决定要不要解析自定义对象 |
| `tools/dxf_scan/probe_doors.py` | 探门的实体形态 | 决定 #10 算法 |
| `tools/dxf_scan/probe_cover.py` | 探封面/目录的数据 | 决定 #8 算法 |
| `tools/dxf_scan/probe_index_blocks.py` | 探 Z 立面/节点索引块 attrib | **跨图联动的关键！** |
| 自写（按需） | 比如 `probe_<xxx>.py` | 针对特定任务 |

### 1.5 图谱输出（2 份必备文档）

写这两份文档，把图谱定下来：

1. **`docs/室内装修DWG知识图谱.md`** — 5 大要素在每张 DWG 里的分布
2. **`docs/跨图关联图谱实测发现.md`** — 编号指针体系（DE-XX / 1EA-XX 等）

**这两份图谱定下来之前，禁止动改造代码**。

---

## Phase 2: 单任务直通（按正交性 + 简单度）

### 2.1 任务评分公式

```
综合分 = 正交性 × 1.0 + 数据齐全度 × 1.0 + (5 - 算法难度) × 1.0 + 现有基础 × 1.0
```

按分数从高到低做。**正交性 5 分**意味着不依赖其他任务，可独立完成。

### 2.2 标准模板（每个任务都走这个 4 件套）

```
1. probe_<entity>.py           # 先探数据形态
2. demo_<action>.py            # 跑 1 个最小 demo
3. <task_name>.py              # 封装成可参数化函数
4. verify_<task_name>.py       # 写验证脚本
```

每个工具都用 `safe_saveas()` 包装（绕开 ezdxf 1.4.4 materials bug），**否则写时会炸**。

### 2.3 已沉淀的可复用工具

| 工具 | 位置 | 复用场景 |
|------|------|------|
| `safe_saveas()` | `tools/dxf_edit/move_wall.py` | **所有写 DXF 流程的前置** |
| `shift_layer_entities(msp, layer, dx, dy)` | `tools/dxf_edit/move_wall.py` | 所有"按图层平移"场景（#2、#4、#5）|
| `apply_material_rename(OLD, NEW)` | `tools/dxf_edit/apply_material_rename.py` | 所有"标签字符串跨图替换"场景 |
| `move_wall(handle/point/idx, dx, dy, mode, sync_layers)` | `tools/dxf_edit/move_wall.py` | 所有"改墙"场景 |
| scan + probe 系列 | `tools/dxf_scan/` | 所有探查场景 |

### 2.4 DRY_RUN 模式（修改类任务必备）

```python
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
if DRY_RUN:
    print("  [DRY RUN] 不写文件")
else:
    safe_saveas(doc, out_path)
```

**实战教训**：ST-01 替换实测 1085 处，比 scan 看到的 357 多 3 倍（scan 只扫 value 漏了 tag）。**如果不是 DRY_RUN 先验证，会漏改 728 处**。

### 2.5 round-trip 验证模板

```python
# 改前 / 改后对比
types_before = Counter(e.dxftype() for e in msp)
types_after = Counter(e.dxftype() for e in new_msp)
diff = {k: (types_before.get(k,0), types_after.get(k,0)) for k in set(types_before)|set(types_after) if types_before.get(k,0) != types_after.get(k,0)}
print(f"实体数: {n_before} → {n_after}, 类型差异: {diff}")
# 通过 handle 找改造对象确认改对了
for e in new_msp:
    if e.dxf.handle == target_handle:
        ...
```

**容忍 REGION 3D 实体丢失**：libredwg 转出的 REGION (ACIS)，ezdxf 写回会丢，这是 ezdxf 已知缺陷。2D 业务（墙/门/标注）不依赖 REGION，所以**可以容忍**。如果业务依赖 3D REGION，需要 Phase 3 处理。

---

## Phase 3: 复杂联动（依赖前两阶段）

### 3.1 内自洽（同文件不同图层联动）模板

例：#2 改墙后地坪天花顺改（**同 3-平面文件内**）

```python
move_wall(...) # 在 3-平面 改了墙
# 找改墙位置附近的"地坪图层"和"天花图层"实体
WALL_LAYERS = ["A原建筑墙体"]
FLOOR_LAYERS = ["F地坪分缝细线", "F地坪分缝粗线", "F地坪填充",
                "S新铺地坪定位尺寸", "H地坪符号"]
CEILING_LAYERS = ["L天灯", "S天花灯具定位尺寸", "S天花造型定位尺寸",
                  "C天花造型线", "C天花格栅细线", "H天花符号"]
# 在墙线 bbox ± tolerance 范围内找上述图层实体
# 按相同 dx/dy 平移（用 shift_layer_entities）
```

注意："附近"的定义**需要用户确认**（Q1 的核心）。

### 3.2 跨视图（跨文件编号指针联动）模板

例：#5 改墙后节点图顺改（**3-平面 ↔ 5-节点 跨文件**）

```python
# 1. 从 3-平面 改墙位置周围找 Z 节点索引块
for e in msp:
    if e.dxf.layer == "Z节点索引":
        for a in e.attribs:
            if a.dxf.tag in ("1EA-07","1EA-08"):
                target_code = a.dxf.text  # "DE-02" 等
                # 2. 去 5-节点 找含相同编号的实体
                for e2 in doc_5.modelspace():
                    if has_text_or_attrib(e2, target_code):
                        # 这就是对应位置，做对应改造
```

→ 跨图联动**不需要做坐标近似匹配**！编号指针是最稳的"地址"。

### 3.3 几何推理（DIMENSION 重算，最难）

如果改墙后要重算 DIMENSION 的标注值：
1. 找 DIMENSION 关联的几何（DEFPOINT 是关键点）
2. 几何变化后用 shapely 重新算距离
3. 更新 DIMENSION 的 measurement 字段

**这是独立的算法工作**，建议 Phase 3.3 单独做，不与 3.1 / 3.2 并发。

### 3.4 3D / 效果图

当前工具链（libredwg + ezdxf）**无法处理 3D REGION 写回**（写时丢字段），效果图需要 IfcOpenShell 或 AutoCAD 原生。Phase 3.4 单独评估。

---

## 通用反模式（永久记忆，避免重复踩）

| # | 反模式 | 修正策略 |
|---|------|------|
| 1 | 凭网上"工程行规"假设图纸结构 | 用户原话 + 实测双重确认 |
| 2 | 用网上"6 参数 CLI"文档指导新工具版本 | `--help` 自检一次再决定 |
| 3 | 想用 ODA File Converter 跑 headless 容器 | ODA 27.x 已无 CLI，转 libredwg |
| 4 | shell heredoc 嵌套引号（docker run + python EOF）| 写独立 .py 文件挂载跑 |
| 5 | 先动文件再写备份（容易覆盖）| `safe_saveas` + `backup_with_rotate` 自动 |
| 6 | 改完不验证就交付 | `verify_<task>.py` 量化 round-trip |
| 7 | 大文件 read+write 不加超时 | 大 DXF (10MB+) 建议 timeout 600s 起步 |
| 8 | 目录结构散乱 | 用 `samples/workdir/tools/docs` 四层 + 软链兼容 |
| 9 | 探查脚本扫所有 layouts 全 attribs 太慢 | 优先扫 modelspace，必要时再扩 layouts |
| 10 | 用 `docker build | tail -N` 看进度 | 改用 `tee /tmp/build.log`，或 `docker system df | grep Build` |

---

## 关键工具版本兼容性（永久记忆）

| 工具 | 版本 | 关键约束 |
|------|------|------|
| **ODA File Converter** | 27.1+ | 纯 GUI，无 CLI 模式；macOS 需 13+；Linux .deb/AppImage 装得上但 headless 跑不了 |
| **libredwg** | 0.14.x（git head）| 编译要 `sed -i '/git fetch.*tags/d' autogen.sh`；`--disable-python --disable-perl` |
| **ezdxf** | 1.4.4 | 写 libredwg 转的 DXF 触发 materials bug，要 monkey-patch；写时丢 REGION |
| **Docker Desktop** | 4.35.0 在 macOS 12.7.6 上 | 4.36+ 需 macOS 13；按构建号下载 `desktop.docker.com/mac/main/amd64/172550/Docker.dmg` |
| **floorplan-mcp** | 4.35 镜像内 FreeCAD 1.0.2 + ezdxf 1.4.4 | PYTHONHOME 必须设；`/opt/FreeCAD/usr/bin/python` 不是 `python3` |

---

## 项目内可复用资产清单（直接下一份任务复用）

### 工具代码（11 个 .py + 1 .sh + 2 Dockerfile）

```
tools/
├── dwg_to_dxf/
│   ├── Dockerfile.libredwg   # libredwg 编译镜像，所有项目可复用
│   ├── convert_dwg.sh        # 批量转换脚本
│   └── README.md
├── dxf_scan/                 # 探针 + 全谱扫描
│   ├── scan_dxf.py           # 全谱扫描（含 layouts / 跨图分析）
│   ├── probe_xdata.py        # 天正/PROXY/XData 探针
│   ├── probe_doors.py        # 门探针
│   ├── probe_cover.py        # 封面/目录探针
│   ├── probe_index_blocks.py # 跨图索引块探针（高复用）
│   ├── probe_tasks.py        # 综合任务可行性探针
│   ├── demo_move_wall.py     # 改墙 demo
│   └── verify_roundtrip.py   # round-trip 验证
└── dxf_edit/                 # 改造工具
    ├── apply_material_rename.py  # 标签字符串跨图替换（高复用）
    ├── move_wall.py              # 改墙（含 shift_layer_entities 通用函数）
    ├── verify_rename.py          # #6 验证
    ├── demo_resize_door.py       # #10 demo（已废弃，因门非 INSERT）
```

### 文档模板（5 份核心模板可直接复用）

```
docs/
├── 室内装修DWG知识图谱.md            # Phase 1.5 输出模板
├── 跨图关联图谱实测发现.md           # Phase 1.5 输出模板
├── 3项核心问题-待用户确认.md         # Phase 0.3 模板
├── 10项任务执行排序.md               # Phase 2.1 评分模板
├── 10项任务最终执行报告.md           # Phase 2 输出模板
└── 目录整理方案.md                  # Phase 0 目录重构模板
```

### Docker 镜像（持久资产）

| 镜像 | 用途 | 大小 |
|------|------|------|
| `libredwg-cli:latest` | DWG→DXF 转换 | 1.02 GB |
| `floorplan-mcp:latest` | ezdxf + FreeCAD Python 环境 | 3.47 GB |

新项目只需 `cp -r samples /new_proj/` 然后改路径，**所有工具镜像不用重新 build**。

---

## 永久记忆文件沉淀（3 个核心 memory）

| 文件 | 用途 |
|------|------|
| `/memories/dwg-to-dxf-conversion.md` | 转换工具链 + 国内网络编译 + ezdxf 已知 bug |
| `/memories/repo/freecad-ai-findings.md` | freecad-ai 安全层真相 + 容器化要点 |
| `/memories/repo/frontend-clients.md` | Goose/OpenWork transport 真相 |

---

## 接新任务的 30 分钟前置清单（checklist）

接装修 DWG 改造类新任务时，按此跑一遍：

```
□ 1. 问用户 5 大要素 + 2 类联动（Phase 0.1）
□ 2. 用 5 行 ezdxf 扫一遍实体类型 + 关键图层（Phase 0.2）
□ 3. 把疑问写进 docs/3项核心问题-待用户确认.md（Phase 0.3）
□ 4. 检查 DWG 版本（Phase 1.1 6 字节魔数）
□ 5. cp samples / new_proj；建 samples/workdir/tools/docs 四层
□ 6. 用 tools/dwg_to_dxf/convert_dwg.sh 批量转 DXF
□ 7. 跑 tools/dxf_scan/scan_dxf.py 产 scan_report.json
□ 8. 跑 probe_xdata / probe_index_blocks（验证 PROXY + 跨图指针）
□ 9. 写 docs/室内装修DWG知识图谱.md
□ 10. 与用户确认图谱正确后再开工
```

完成 checklist 后，**项目就回退到 Phase 2 单任务直通**——可以批量生产脚本。

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1 | 2026-08-09 05:00 | 初版：基于 4 份复盘（2026-08-08 ~ 2026-08-09）综合 出 4 阶段 SOP + 10 反模式 + 30 分钟前置 checklist |
