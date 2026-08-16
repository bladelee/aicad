# floorplan-mcp — 装修师傅的自然语言 CAD 助手

> 单 Docker 镜像 + MCP 协议，让设计师在 **Goose / OpenWork** 桌面客户端里用自然语言读/改/查装修 DWG。
> 设计依据：`../产品Spec.md` + `../方案-F2-RiskReview-产品设计-用户验证.md`。

## 📖 文档地图（仓库根目录导航）

仓库根有 10+ 份历史方案文档，**新加入的人按这张地图读，不会迷路**：

### ✅ 当前权威（先读这三份）
1. **`../方案-F-容器化.md`** — 架构定调（Docker 单镜像 + 三平台 Docker Desktop）
2. **`../方案-F2-RiskReview-产品设计-用户验证.md`** — 风险/产品/验证三件套
3. **`../产品Spec.md` v1.1** — MVP 细则 + Goose/OpenWork 双前端 + Phase 0/1/3 checklist

### 📋 实施手册（按需读）
- **`../Phase0-启动检查.md`** — Phase 0 跑真实样本的执行手册
- **本目录** `floorplan-mcp/` — 代码实现 + 测试 + 客户端配置
- **`CONTRIBUTING.md`** — 30 分钟读懂 → 1 小时上手改代码（新开发者入门）
- **`floorplan-mcp/usertest/`** — V3 真人测试包（README + task-card + scorecard + aggregate + recruit-email）

### 🎓 元层（理解为什么这么做决策）
- **`../复盘-2026-08-08-Phase0准备.md`** — 经验教训 + 11 个已解决问题 + 12 条最佳实践 + 9 条反模式
- **`../research/chat-to-cad-research.md`** — 竞品调研

### ⚠️ 已归档（顶部带 ⚠️ 标注，不必读）
- `../方案.md` / `../方案-v2.md` / `../方案-v2-review.md` / `../方案-v3-final.md` / `../方案-D-决策.md` / `../方案-E-混合架构.md`
- `../cad_tools.archived/` — v1 早期代码残留（已被 `floorplan-mcp/` 取代）

### ⏸️ 留待 Phase 3
- `../方案-C-BIM.md` — 3D 模型联动（IFC + SketchUp）需求落地时读

---

## 它是什么

```
你的 Windows/macOS/Linux + Docker Desktop         容器
┌────────────────────────────┐   stdio (docker exec)  ┌──────────────────────┐
│  Goose Desktop/CLI         │ ←──────────────────→    │  FreeCAD headless    │
│  OpenWork Desktop          │                        │  + freecad-ai        │
│  + 你的 DWG ~/dwgs/客厅.dwg │                        │  + 5 个装修图工具    │
└────────────────────────────┘                        │  + ODA（你自己装）   │
                                                       │  /data ← bind mount  │
                                                       └──────────────────────┘
```

MVP 走 **stdio 单通道**（用户决策 2026-08-08）：
- Goose 已废弃 SSE，OpenWork 远程模式要 OAuth 复杂，stdio 最简
- Phase 1.5 再加 streamable_http（满足云/远程访问）

用户在对话里说"看一下图 / 客厅面积 / 沙发右移500mm"，
LLM 自动调容器里的工具，返回结构化数据 + PNG。

## 安装（用户侧，一次性）

### 1. 装 Docker Desktop（最新版；ops 确认旧版 17.12 不可）
- Windows / macOS: https://www.docker.com/products/docker-desktop/

### 2. 装 ODA File Converter（DWG↔DXF 必需）
合规原因不打包进镜像，请自行接受 EULA 并安装：
- 下载：https://www.opendesign.com/guestfiles/oda_file_converter
- 详细引导：`./install_oda.sh`

### 3. 配好 ODA 挂载到容器
编辑 `docker-compose.yml`：
```yaml
volumes:
  - "${HOME}/dwgs:/data"
  - "/你的/ODA/安装目录:/opt/oda:ro"   # 取消注释并改路径
environment:
  ODA_FILE_CONVERTER: /opt/oda/ODAFileConverter
```

### 4. 启动容器
```bash
docker compose up -d   # 容器常驻，等客户端 docker exec 拉起
```

### 5. 配 MCP 客户端（二选一或两个都装）
- **Goose Desktop/CLI**：见 `clients/goose.md`
- **OpenWork Desktop**：见 `clients/openwork.md`

### 6. 验证容器内 stdio server 可用
```bash
./scripts/check_stdio_server.sh
```

## 使用

把要处理的 DWG 放到 `~/dwgs/`，在前端对话即可：

> **你**：看一下 `~/dwgs/客厅.dwg` 这张图
> **Goose/OpenWork**：（调 read_floorplan）→ "三室一厅，5 门 12 家具，总面积 89㎡，[渲染图]"
>
> **你**：客厅有多大？
> **Goose/OpenWork**：（调 list_rooms）→ "客厅 23.4 ㎡"
>
> **你**：把客厅沙发往右移 500mm
> **Goose/OpenWork**：（调 move_furniture）→ "已移动，原文件备份到 `客厅.dxf.bak.1`，[前后对比 PNG]"
>
> **你**：撤销
> **Goose/OpenWork**："回滚 .bak.1 即可（详见备份文件名）"

## 用户验证

- **V1 自动化**（容器外可跑，miniconda3 Python 3.13）：`/Users/bladelee/miniconda3/bin/python -m pytest tests/ -v`
  当前 12/12 过：backend 接口 / 安全层 / 分类 / AST 兼容 / stdio fd 重定向 / user_tools 链接
- **V1 集成**（合成 DXF 走 EzdxfBackend 全链路）：`python tests/integration_ezdxf.py` —— 校准 shapely 房间识别
- **V1 人工**（Phase 0）：`python scripts/phase0_verify.py /data`（需 Docker + 真实样本）
- **V3 真人测试协议**：见 `../产品Spec.md` §4

## 后端切换（架构关键）

5 个 user_tool 通过 `FLOORPLAN_BACKEND` 环境变量切后端，**代码/客户端零改动**：

| 值 | 后端 | 何时用 |
|----|------|--------|
| `freecad`（默认） | FreeCAD BIM + Arch Space | MVP 主路径 |
| `ezdxf` | ezdxf + shapely polygonize | Phase 0 若 Arch Space 失败（合成 DXF 已验证 3 房间识别正确） |
| `ifc` | IfcOpenShell | 未来 Phase 3 3D 联动 |

## Transport 路线

| Phase | Transport | 用途 |
|-------|-----------|------|
| **MVP（当前）** | `stdio` | Goose/OpenWork 通过 `docker exec` 调容器；最简、避 SSE 废弃 + OAuth 复杂 |
| Phase 1.5 | + `streamable_http` | 远程访问、OpenWork 主线模式 |
| Phase 2+ | + `HTTPS + OAuth` | 多用户 / 云形态 |

## 项目结构

```
floorplan-mcp/
├── Dockerfile                 # 单镜像：FreeCAD extract + freecad-ai + stdio 入口 + 工具
├── docker-compose.yml         # bind mount + 内存限制（MVP 不开 ports）
├── entrypoint.sh              # 容器常驻等 docker exec
├── mcp_server_stdio.py        # ★ MVP stdio 入口：fd 重定向 + user_tools 链接 + MCPServer
├── install_oda.sh             # ODA 合规引导（不打包进镜像）
├── clients/
│   ├── goose.md               # Goose Desktop/CLI 配置（config.yaml stdio 扩展）
│   └── openwork.md            # OpenWork Desktop 配置（Add Custom App 高级模式）
├── tools/
│   ├── __init__.py            # get_backend() 按 env 选后端
│   ├── floorplan_backend.py   # Protocol 接口（A/B/C 都实现它）
│   └── floorplan_tools.py     # 5 个 user_tool（AST 自动发现注入 freecad-ai）
├── backends/
│   ├── _safety.py             # ⚠️ R2 必备：transaction + .bak（freecad-ai 不保护 user_tools）
│   ├── freecad_backend.py     # 主：Arch Space 房间识别
│   ├── ezdxf_backend.py       # 备：shapely polygonize（合成 DXF 已验证）
│   └── ifc_backend.py         # 未来：3D 联动
├── scripts/
│   ├── phase0_verify.py       # Phase 0 假设验证（需 Docker + 样本）
│   └── check_stdio_server.sh  # stdio server 自检
└── tests/
    ├── test_safety_and_backend.py  # 9 项：backend 选择 / .bak / transaction / 分类 / AST
    ├── test_stdio_entry.py         # 3 项：fd 重定向 / user_tools 链接 / 幂等
    └── integration_ezdxf.py        # 集成：合成 DXF 走 EzdxfBackend 全链路
```

## 已知限制 / 风险（详见产品Spec §9）

- **房间识别招牌风险（R1）**：Arch Space 在真实图未验证，Phase 0 是闸门，跌破 70% 切 ezdxf（shapely 已在合成样本上准确识别 3 房间）
- **round-trip 实体丢失（R3）**：默认 ODA，CI 持续对照
- **ODA EULA（R4）**：不打包，用户自行安装
- **user_tools 不享受 freecad-ai 安全层（R2）**：我们用 `_safety.with_transaction` 自带 transaction + .bak
- **freecad-ai SSE server 对 Goose 不可用（R5）**：MVP 走 stdio 绕开；Phase 1.5 加 streamable_http
- **国内访问 LLM**：Goose 多 provider（含国产/Ollama 本地），OpenWork 偏 ChatGPT OAuth

## 开发

> **New contributors：先读 `CONTRIBUTING.md`（30 分钟读懂 → 1 小时上手改代码）。**

```bash
# V1 单元测试（无需 FreeCAD/Docker，miniconda3 Python 可跑）—— 现 46/46
/Users/bladelee/miniconda3/bin/python -m pytest tests/ -v

# 集成测试（合成 DXF，验证 shapely 房间识别）
/Users/bladelee/miniconda3/bin/python tests/integration_ezdxf.py

# 真实结构样本压力测（含门洞/HATCH/DIMENSION/AXIS）
/Users/bladelee/miniconda3/bin/python tests/fixtures_realistic.py
/Users/bladelee/miniconda3/bin/python -m pytest tests/test_realistic_fixtures.py -v

# 容器内 Phase 0 验证（需 Docker + 真实样本）
docker compose run --rm floorplan-mcp python3 /opt/floorplan/scripts/phase0_verify.py /data
```

## 下一步

1. 用户提供 2 个真实装修 DWG 到 `~/dwgs/`
2. `docker compose up -d` + 装好客户端（Goose/OpenWork）
3. `check_stdio_server.sh` + `phase0_verify.py /data`
4. 触发/不触发备选 A
5. 进 Phase 1 MVP，跑 5 个用户故事（V2）
6. V3 真人用户测试（3-5 个设计师，详见产品Spec §4）
