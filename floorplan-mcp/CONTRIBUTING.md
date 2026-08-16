# CONTRIBUTING — floorplan-mcp

> 目标：让一个新加入的人 **1 小时内从读懂到能改代码**。
> 读完 → 跑得通测试 → 改第一个 user_tool 走 PR 流程即可。

---

## 0. 30 分钟读完：必读路径

按这个顺序读，**不要从 README 开始**（README 是给用户看的）：

| # | 文档 | 读什么 | 时间 |
|---|------|-------|------|
| 1 | `../产品Spec.md` v1.1 §0-3 | 这产品是啥 / 双前端 / 5 工具契约 / Phase 划分 | 10 min |
| 2 | `../复盘-2026-08-08-Phase0准备.md` **TL;DR + §三 已解决问题** | 知道哪些坑已踩过、为何这样设计 | 10 min |
| 3 | `./README.md` 的"文档地图""项目结构" | 文件布局 + 模块职责 | 5 min |
| 4 | `./tools/floorplan_tools.py`（5 个 docstring） | 看 user_tool 怎么写 | 5 min |

读完应该能答：
- MVP 走 **stdio 单通道**（不是 SSE/eventual streamable_http）—— 为什么？（复盘 §三 P0 跨平台 transport）
- 房间识别 = **共享 shapely `rooms_detect.py`**（不是 Arch Space）—— 为什么？（复盘 §三 P0 v1 算法错）
- 写工具必须自带 `.bak` —— 为什么？（R2：freecad-ai user_tools 不走 _with_undo）

---

## 1. 环境准备（10 分钟）

| 依赖 | 用途 | 装法 |
|------|------|------|
| **Python ≥3.10**（项目用 3.13） | 跑代码 + 单测 | 本机或 miniconda3 |
| Docker Desktop（最新版） | 跑容器（生产/集成测） | https://docker.com |
| ODA File Converter | DWG↔DXF（DWG 路径） | https://opendesign.com |

```bash
# 一次性装 Python 依赖（pytest + ezdxf + shapely + matplotlib）
python -m pip install pytest ezdxf shapely matplotlib

# 跑通全部 46 个测试（无需 FreeCAD/Docker，单测全在容器外可跑）
cd floorplan-mcp
python -m pytest tests/ -v
```

若 46/46 全过 → 环境 OK，可以做开发。

---

## 2. 项目结构速记

```
floorplan-mcp/
├── tools/                     user_tool 入口（LLM 调用的 5 个工具）
│   ├── __init__.py            get_backend() 按 env 切后端
│   ├── floorplan_backend.py   Protocol 接口（A/B/C 都实现它）
│   └── floorplan_tools.py     ★ 改 5 工具的 docstring/参数都在此
├── backends/
│   ├── rooms_detect.py        ★ 共享 shapely 房间识别（改算法在此）
│   ├── _safety.py             ★ 共享 transaction + .bak（写工具必经此）
│   ├── freecad_backend.py     主后端（FreeCAD + 关键词表）
│   ├── ezdxf_backend.py       备后端（ezdxf + shapely）
│   └── ifc_backend.py         未来 Phase 3
├── mcp_server_stdio.py        ★ MVP transport 入口
├── clients/                   用户侧的 Goose/OpenWork 配置说明
├── scripts/                   phase0_verify.py + check_stdio_server.sh
├── tests/                     46 测试 + fixtures/ + fixtures_realistic.py
└── usertest/                  V3 真人测试包（README/task-card/scorecard/aggregate/recruit）
```

★ 表示最常改的几个文件。

---

## 3. 五条最常做的修改 + 怎么改

### 3.1 改 user_tool 的 description（最常见，影响 LLM 路由）

**位置**：`tools/floorplan_tools.py` 各函数 docstring

**规则**（详见 `../产品Spec.md` §3.4 + `tests/test_tool_descriptions.py` 钉死）：
- 必须含"不要用于"段落（路由负例）
- 必须含"用户典型口语："（≥3 条，让 LLM 听懂用户口语）
- 必须"Args:" 段（参数契约）
- 路径参数说明用容器内 /data 路径

**改完跑**：`python -m pytest tests/test_tool_descriptions.py` 自动 lint。

### 3.2 调整房间识别（算法 + 阈值）

**位置**：`backends/rooms_detect.py::detect_rooms`

参数：
- `min_area_m2=0.5`：过滤小于此面积的碎片
- `close_openings_mm=1000.0`：**关键**——真实图门洞导致墙不闭合，距离 ≤ 此值的端点补虚拟墙。Phase 0 真实样本到来时要校准。

**改完跑**：
- `python -m pytest tests/test_rooms_detect.py tests/test_rooms_edge_cases.py tests/test_realistic_fixtures.py`

⚠️ 改 `detect_rooms` 必须同时跑 7 边界用例 + 6 真实 fixture（共 13 个），房间识别是招牌功能，别一处改崩全局。

### 3.3 加 / 改家具分类关键词

**位置**：`backends/freecad_backend.py` 顶部的 `FURNITURE_KEYWORDS`（**单一真源**，主备 backend 都用）

**规则**：短前缀（`D_`/`W_`）天然脆弱——`BED_1800` 会命中 `D_`。`_classify` 是"先匹配具体家具 → 门/窗兜底"，别改顺序。

**改完跑**：`python -m pytest tests/test_safety_and_backend.py::test_classify_block_name_full_keywords`

⚠️ 别在 `cad_tools.archived/` 里改——那是死代码。

### 3.4 改 backend 实现

- 增改 5 个工具的内部实现 → `backends/freecad_backend.py`（默认）+ 同步 `ezdxf_backend.py`（备）
- 加新 backend → 实现 `FloorplanBackend` Protocol + 在 `tools/__init__.py::get_backend()` 加分支 + 在 ifc_backend 之类插入
- **写工具必经**：`backends/_safety.py::with_transaction` + `make_backup`，freecad-ai 不保护 user_tools（详见复盘 §三）

### 3.5 改 transport 入口

- 现在 MVP stdio 单通道：`mcp_server_stdio.py`
- Phase 1.5 加 streamable_http：在 `Dockerfile` + `entrypoint.sh` 同时启动 HTTP server
- 客户端配置改 `clients/goose.md` / `clients/openwork.md`

---

## 4. 提 PR 流程

不强制，但建议：

1. **先开 issue**（除非改动很小）说明动机 + 对应 `复盘-*.md` 哪条最佳实践
2. 改动**必须配套测试**：
   - 改算法 → 加边界用例
   - 改 description → update lint（自动跑）
   - 改 backend → 至少合成 DXF 集成测
3. 跑 `python -m pytest tests/` 全绿（当前 46 测）
4. PR 描述含：动机 / 改动点 / 测试如何验证 / 是否影响产品Spec §3.3 工具契约

---

## 5. 关键约定（别踩的坑）

| 反直觉 | 别踩 |
|--------|-----|
| freecad-ai 有 `_with_undo` 保护 user_tools | ❌ 不保护（设计文档说了但代码没兑现）。自带 `_safety.with_transaction` |
| Goose client 支持 SSE | ❌ SSE 已废弃。MVP 走 stdio |
| 测试 capsys 测底层 fd 重定向 | ❌ pytest 替换 Python 层 sys.stdout 跟 fd 不通。用 os.pipe |
| `bed/tools/blocks.py` 改关键词 | ❌ 是 archived 死代码。改 `floorplan-mcp/backends/freecad_backend.py` |
| Arch Space 识别房间 | ❌ v0 用过只产 1 房间。房间单一真源是 shapely `rooms_detect.py` |
| MVP 同时做多个 transport | ❌ stdio 单通道起步。streamable_http 是 Phase 1.5 |
| 默认 Phase 0 备 backend = Arch Space | ❌ 真实样本前不要预设。两个 backend 都走 shapely 算法 |

详见 `../复盘-2026-08-08-Phase0准备.md §四/§五`。

---

## 6. 怎么加测试

| 测试类型 | 写在哪 | 例子 |
|---------|-------|------|
| 单元（纯函数） | `tests/test_xxx.py` | `test_rooms_detect.py`（典型）|
| 边界用例 | `tests/test_rooms_edge_cases.py` 加 `CASES["..."]` | 已有 7 个真实结构形态 |
| 真实 fixture | `tests/fixtures_realistic.py` 加 `make_mock_xxx()` + `tests/test_realistic_fixtures.py` 加 assert | 已有 simple/realistic/messy |
| description lint | `tests/test_tool_descriptions.py`（自动钉死模板） | — |

**总原则**：纯函数测试不要起 FreeCAD/Docker，就行。要让 `.py` 在普通 Python 3.10+ 跑起来。

---

## 7. 文档治理

仓库有 10+ 份方案文档，新旧关系靠文件顶部 banner：

- ✅ 当前权威（3 份）：`方案-F-容器化.md` / `方案-F2-*.md` / `产品Spec.md`
- ⚠️ 已归档（6 份）：v1 / v2 / v2-review / v3-final / D / E
- ⏸️ 待 Phase 3：`方案-C-BIM.md`
- 📒 复盘：按阶段多份，命名 `复盘-YYYY-MM-DD-{阶段}.md`

**新方案/经验别加在已归档文档里**，要么改 F2 / 产品Spec，要么写新一份复盘。

---

## 8. 问题/卡壳

慢慢补这份文件。遇到下面情况请更新 CONTRIBUTING：

- 同一个问题被两个人问（说明文档没说清，补 §1/§5）
- 踩了一个新坑（追加到 §5 反直觉 + 写入新复盘）

测试卡住先看：
```bash
python -m pytest tests/ -v        # 看哪个挂
python tests/integration_ezdxf.py # 完整链路合成样本
python tests/fixtures_realistic.py 2>&1 | tail -5  # 重新生成 fixture
```
