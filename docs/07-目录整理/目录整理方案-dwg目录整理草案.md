# 项目目录整理方案（dwg 目录混乱）

> **目的**：dwg 目录的原始数据、转换结果、文档、测试脚本、Dockerfile 混在一起，需要重新组织。本方案给出最终目标结构和迁移步骤。
> **状态**：草案（待用户确认后执行）
> **创建日期**：2026-08-09

---

## 1. 当前混乱状况盘点

### 1.1 `dwg/` 目录现状

```
dwg/
├── .backup/                          # 早期备份（自己造的）
├── oda_pkg/                          # 早期实验副产品（oda.AppImage + oda.deb，已弃用）
├── dxf/                              # libredwg 转换产物 + scan_report.json
│   ├── *.dxf (6 张)
│   └── scan_report.json
│
│  ── 原始数据（用户给的，不能动） ─────
├── 1-19-102封面、目录、设计说明.dwg
├── 2-19-102材料表.dwg
├── 3-19-102平面系统图.dwg
├── 4-19-102立面图.dwg
├── 5-19-102节点.dwg
├── XINLU-A2.dwg
├── 12.pdf
├── 19-102别墅1027.pdf
├── 3-19-102平面系统图 布局.pdf
├── 4-19-102立面图 Model.pdf
├── 5-19-102节点 地坪天花墙身 (1).pdf
├── 要求.txt                          # 用户给的真实任务清单
│
│  ── 文档（我写的） ─────────────────
├── DXF扫描报告.md
├── 任务-讨论.md
├── 格式转换-实战记录.md
│
│  ── 代码（脚本/Dockerfile）─────────
├── Dockerfile.libredwg               # ✅ 当前有效
├── Dockerfile.test                   # ODA 实验残骸（已弃用）
├── scan_dxf.py                       # ✅ 当前有效
├── convert_all_to_dxf.sh             # ODA 时代产物（已弃用）
├── probe_qt_xcb.sh                   # ODA 调试脚本（已弃用）
├── run_appimage.sh                   # ODA 调试脚本（已弃用）
├── run_appimage_simple.sh            # ODA 调试脚本（已弃用）
├── run_oda.sh                        # ODA 调试脚本（已弃用）
├── run_oda_v3.sh                     # ODA 调试脚本（已弃用）
├── run_oda_with_fix.sh               # ODA 调试脚本（已弃用）
└── test_libredwg.sh                  # libredwg 早期实验（已弃用）
```

**核心问题**：
1. **原始数据**（dwg/pdf/要求.txt）和**代码**混在一起，不合规
2. **大量已废弃的 ODA 调试脚本**没清理（8 个 .sh）
3. **Dockerfile 和 scan 脚本在原始数据旁**，本应在工程目录里
4. **文档**也混在数据里，按项目规范应该在 `research/` 或专用 `docs/`

### 1.2 workspace 根目录现状

```
cad/                                  # 项目根
├── 产品Spec.md + 复盘 + Phase0 + 一堆方案.md   # 设计文档
├── 计划-工作.md                       # 计划看板
├── 研究方案总览.md                    # 文案
│
├── floorplan-mcp/                    # 主代码仓库
├── ops/                              # 工程运维文档（Docker 安装/排错手册）
├── cad_tools.archived/               # 已归档的 v1 代码（保留）
├── dwg/                              # 🔴 混乱点
├── research/                         # 调研笔记
└── (tests/ 空了)
```

---

## 2. 整理后目标结构

```
cad/                                  # 项目根（不变）
│
├── 产品Spec.md / 方案*.md / 复盘*.md / 计划-工作.md  # 不动
│
├── samples/                          # 🆕 原始样本数据（不可写区）
│   ├── 19-102/                       # 子项目：19-102 别墅
│   │   ├── 1-封面、目录、设计说明.dwg
│   │   ├── 2-材料表.dwg
│   │   ├── 3-平面系统图.dwg
│   │   ├── 4-立面图.dwg
│   │   ├── 5-节点.dwg
│   │   ├── XINLU-A2.dwg
│   │   ├── *.pdf                     # 同项目 PDF
│   │   └── 要求.txt                  # 用户给的真实任务
│   └── README.md                     # 说明：放用户原始数据，勿手改
│
├── workdir/                          # 🆕 工作区（可写的中间产物）
│   └── 19-102/                       # 按项目分目录
│       ├── dxf/                      # libredwg 转的 DXF（6 张）
│       ├── scan_report.json          # scan_dxf.py 产出
│       ├── backups/                  # 改图前的 .bak 文件
│       └── (后续 phase 0 测试产物放这)
│
├── tools/                            # 🆕 独立工具脚本（不属于 floorplan-mcp 的）
│   ├── dwg_to_dxf/                   # DWG 转换工具
│   │   ├── Dockerfile.libredwg       # ✅ 移过来（当前有效）
│   │   ├── convert_dwg.sh            # 简化的转换入口
│   │   └── README.md                 # 用 docker run libredwg-cli 一行转 dwg→dxf
│   └── dxf_scan/                     # DXF 结构扫描工具
│       ├── scan_dxf.py               # ✅ 移过来（当前有效）
│       └── README.md                 # 扫描产出关联图谱的用法说明
│
├── research/                         # 不动（原 research 还在这）
│   ├── chat-to-cad-research.md
│   └── ...
│
├── ops/                              # 不动（运维文档全部在这）
│
├── floorplan-mcp/                    # 不动（主代码库）
│
├── cad_tools.archived/               # 不动（已归档 v1 代码）
│
└── docs/                             # 🆕 项目文档归档（之前散落的）
    ├── 格式转换-实战记录.md           # 从 dwg/ 移过来
    ├── DXF扫描报告.md                 # 从 dwg/ 移过来
    └── 任务-讨论.md                   # 从 dwg/ 移过来（决策讨论性质）
```

### 关键原则

1. **原始数据只读**：`samples/` 下的 dwg/pdf 永远不动（备份是 `workdir/<project>/backups/` 的职责）
2. **生成产物隔离**：`workdir/` 装所有"程序跑出来的中间物"（DXF、报告、备份）
3. **工具脚本归类**：工具以"功能"分组（dwg_to_dxf / dxf_scan），未来加新工具（如 dxf_edit、material_replace）就放新目录
4. **文档归 docs/**：把散落在 dwg/ 下的文档全部归 `docs/`，避免和数据混
5. **保持向后兼容**：根级 `方案*.md`、`产品Spec.md` 是用户已熟悉的位置，不动

---

## 3. 迁移步骤（精细到每条命令）

> 一次性原子操作；用 `git mv`（如纳入 git）或 `mv` 保历史。下面按依赖顺序。

### Step 1: 创建新目录骨架

```bash
cd /Users/bladelee/project/cad
mkdir -p samples/19-102
mkdir -p workdir/19-102/{dxf,backups}
mkdir -p tools/dwg_to_dxf
mkdir -p tools/dxf_scan
mkdir -p docs
```

### Step 2: 移动原始数据 → samples/（重命名为清晰名）

```bash
# DWG（去掉"19-102"前缀，因为目录名已含项目）
mv "dwg/1-19-102封面、目录、设计说明.dwg" "samples/19-102/1-封面、目录、设计说明.dwg"
mv "dwg/2-19-102材料表.dwg"               "samples/19-102/2-材料表.dwg"
mv "dwg/3-19-102平面系统图.dwg"           "samples/19-102/3-平面系统图.dwg"
mv "dwg/4-19-102立面图.dwg"               "samples/19-102/4-立面图.dwg"
mv "dwg/5-19-102节点.dwg"                 "samples/19-102/5-节点.dwg"
mv "dwg/XINLU-A2.dwg"                     "samples/19-102/XINLU-A2图框.dwg"

# PDF（同上，保留可读名）
mv "dwg/12.pdf"                            "samples/19-102/12-概览.pdf"
mv "dwg/19-102别墅1027.pdf"                "samples/19-102/19-102别墅-完整版.pdf"
mv "dwg/3-19-102平面系统图 布局.pdf"       "samples/19-102/3-平面系统图-布局.pdf"
mv "dwg/4-19-102立面图 Model.pdf"          "samples/19-102/4-立面图-Model.pdf"
mv "dwg/5-19-102节点 地坪天花墙身 (1).pdf" "samples/19-102/5-节点-地坪天花墙身.pdf"

# 用户任务书
mv "dwg/要求.txt"                          "samples/19-102/任务-要求.txt"

# .backup 一并移走
mv dwg/.backup samples/19-102/_原始备份 2>/dev/null || true
```

### Step 3: 移动 DXF 产物 → workdir/

```bash
mv dwg/dxf/*.dxf workdir/19-102/dxf/
mv dwg/dxf/scan_report.json workdir/19-102/
rmdir dwg/dxf
```

### Step 4: 移动有效工具脚本 → tools/

```bash
# 有效的
mv dwg/Dockerfile.libredwg tools/dwg_to_dxf/
mv dwg/scan_dxf.py         tools/dxf_scan/

# 新写一个简化的转换入口（替代循环脚本）
cat > tools/dwg_to_dxf/convert_dwg.sh <<'EOF'
#!/bin/bash
# 用 docker libredwg-cli 把 dwg 目录所有 DWG 转 DXF
# 用法：bash tools/dwg_to_dxf/convert_dwg.sh <sample_dir> <out_dir>
set -e
IN="${1:-samples/19-102}"
OUT="${2:-workdir/19-102/dxf}"
mkdir -p "$OUT"
for f in "$IN"/*.dwg; do
    name=$(basename "$f" .dwg)
    echo "→ $name"
    docker run --rm -v "$PWD:/data" libredwg-cli \
        -y -o "/data/$OUT/${name}.dxf" "/data/$f" 2>&1 | tail -3
done
echo "✓ 全部转换完成：$OUT"
ls -lh "$OUT"
EOF
chmod +x tools/dwg_to_dxf/convert_dwg.sh
```

### Step 5: 移动文档 → docs/

```bash
mv dwg/格式转换-实战记录.md docs/
mv dwg/DXF扫描报告.md docs/
mv dwg/任务-讨论.md docs/
```

### Step 6: 清理废弃产物（这是清理的"价值"所在）

```bash
# ODA 已彻底放弃，所有相关文件归档后删
mkdir -p docs/_archived/oda-experiments
mv dwg/oda_pkg docs/_archived/oda-experiments/    # AppImage + deb 不删（保留作 fallback 证据）
mv dwg/Dockerfile.test docs/_archived/oda-experiments/
mv dwg/convert_all_to_dxf.sh docs/_archived/oda-experiments/
mv dwg/probe_qt_xcb.sh docs/_archived/oda-experiments/
mv dwg/run_appimage.sh docs/_archived/oda-experiments/
mv dwg/run_appimage_simple.sh docs/_archived/oda-experiments/
mv dwg/run_oda.sh docs/_archived/oda-experiments/
mv dwg/run_oda_v3.sh docs/_archived/oda-experiments/
mv dwg/run_oda_with_fix.sh docs/_archived/oda-experiments/
mv dwg/test_libredwg.sh docs/_archived/oda-experiments/

# 最后 dwg/ 应该空了，删掉
rmdir dwg
```

### Step 7: 修代码里的硬编码路径

> ⚠️ **关键**：scan_dxf.py / convert_dwg.sh / 各文档都引用了 `dwg/` 旧路径，必须改。

| 旧路径 | 新路径 |
|--------|--------|
| `/data/dwg/dxf/*.dxf` (scan_dxf.py) | `/data/workdir/19-102/dxf/*.dxf` |
| `dwg/格式转换-实战记录.md` | `docs/格式转换-实战记录.md` |
| `dwg/DXF扫描报告.md` | `docs/DXF扫描报告.md` |
| `dwg/dxf/` | `workdir/19-102/dxf/` |
| `dwg/要求.txt` | `samples/19-102/任务-要求.txt` |

scan_dxf.py 里：
```python
# 之前
in_dir = Path("/data/dwg/dxf")
# 改为
in_dir = Path("/data/workdir/19-102/dxf")
```

### Step 8: 写一份 samples/README.md 说明数据来源

```bash
cat > samples/README.md <<'EOF'
# 样本数据

本目录存放用户提供的**原始 DWG 工程图**（只读区，不动）。

## 19-102 别墅项目（2026-08-09 用户提供）

- 5 张工程 DWG（封面/目录、材料表、平面系统图、立面图、节点）+ 1 张图框样板 (XINLU-A2)
- 配套 PDF（导出预览，参考用）
- 用户原始任务清单：`任务-要求.txt`（10 项联动改造需求）

每个项目目录建议结构：
- *.dwg：原始 DWG
- *.pdf：原始导出预览
- 任务-要求.txt：原始用户需求
- _原始备份/：文件系统级原始副本（保险）
EOF
```

---

## 4. 迁移后效果（直观对比）

### 4.1 整理前 vs 整理后

| 维度 | 整理前 | 整理后 |
|------|-------|--------|
| dwg/ 目录文件数 | 28 | 0（删掉） |
| 原始数据位置 | `dwg/` 散放 | `samples/19-102/` 干净 |
| 生成产物位置 | `dwg/dxf/` | `workdir/19-102/dxf/` |
| 工具脚本位置 | `dwg/*.sh`/`*.py` | `tools/dwg_to_dxf/`、`tools/dxf_scan/` |
| 文档位置 | `dwg/*.md` | `docs/` |
| ODA 残骸 | 8 个 .sh + AppImage 混数据 | `docs/_archived/oda-experiments/` |

### 4.2 一个用户的"快速发现"任务

> "我想看 5 张图都改成 DXF 没了"

整里前：在 dwg/ 找 30 秒
整理后：`ls workdir/19-102/dxf/` 1 秒

> "我想看扫描报告"

整理前：在 dwg/ 找文档
整理后：`ls docs/` 一目了然

---

## 5. 风险与回滚

### 5.1 风险点

1. **路径硬编码**：scan_dxf.py / convert_dwg.sh / 计划-工作.md / 文档可能引用旧路径 → Step 7 必须改全
2. **oda_pkg 占空间**（135MB）：移到 archived 没问题，但可以从 samples/ 让用户清楚意识到 ODA 已死
3. **docker 镜像 build context 路径变化**：Dockerfile.libredwg 用了 `COPY oda_pkg/oda.AppImage ...` 但新版已不用 oda（改 libredwg 源码编译），不依赖该路径

### 5.2 回滚

如果整理有副作用，回滚成本：

```bash
git checkout -- .   # 如已 commit 可一键回滚
# 或如果没用 git，再跑一次迁移的逆命令（mv 回原位）
```

**建议**：执行前先 `git status` 看是否纳入 git，若没纳入先 `git init && git add -A && git commit -m "before restructure"`。

---

## 6. 命名规范（永久）

新增样本/产物时按本规范：

| 类型 | 位置 | 命名约定 |
|------|------|---------|
| 用户原始 DWG | `samples/<项目名>/N-中文名.dwg` | N 是图序号，"中文名"对应图纸用途 |
| 用户原始 PDF | `samples/<项目名>/N-中文名.pdf` | 同上 |
| 用户原始需求 | `samples/<项目名>/任务-要求.txt` | 固定义名 |
| 转换产物 DXF | `workdir/<项目名>/dxf/N-中文名.dxf` | 与 DWG 同名 |
| 扫描报告 | `workdir/<项目名>/scan_report.json` | 固定义名 |
| 改图前备份 | `workdir/<项目名>/backups/*.bak.{N}` | 加序号，多次改 N 递增 |
| 工具脚本 | `tools/<工具名>/` | 每个工具有独立目录 + README.md |

---

## 7. 决策点（请用户拍板）

待用户回答：

1. **samples/ 项目子目录名**：用 `19-102`（项目内编号）还是用 `别墅19-102`（更描述性）？
2. **是否真的删 `dwg/` 目录**？建议保留 → 改成 `dwg/` 加 .gitignore 不动？还是删干净只留 samples/？
3. **oda_pkg 135MB**：是移到 `docs/_archived/`（保留）还是彻底删除（已彻底失败）？删除可省 135MB。

确认后我立即执行 Step 1–8（5 分钟内完成）。
