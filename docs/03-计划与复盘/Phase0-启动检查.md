# Phase 0 启动检查 — 环境就绪 + 已验证项

> **日期**：2026-08-08
> **状态**：骨架已写完并跑了 9/9 单元 + 1 集成测试（不依赖 Docker/真实样本的部分全过）
> **阻塞项**：Docker 17.12 太老 + 等用户提供 2 个真实装修 DWG

---

## 1. 已通过的验证（不依赖外部环境）

用 miniconda3 Python 3.13.5（确认路径 `/Users/bladelee/miniconda3/bin/python`）：

```
pytest tests/ -v                         →  9/9 PASSED
python tests/integration_ezdxf.py        →  全链路通过
  - 合成 8000x6000 含内墙 3 房间 DXF
  - EzdxfBackend.read()  →  准确识别 3 房间（30/9/9 m²，总面积 48 m²）
  - render_preview()     →  生成 PNG（v1 破图层 bug 已修，用 RenderContext 副本）
  - move_entity()        →  生成 *.bak.1 自动备份
```

**这是 Phase 0 之前最关键的预警信号**：v1 那套"闭合 lwpolyline = 房间"在同样的独立 LINE 段样本下会识别出 **0 个房间**；shapely polygonize **精准识别 3 个房间**。即：备选 A 在合成样本上已经证明房间识别能力，比 FreeCAD Arch Space 的不确定性低。

### 1.1 测试发现的真 bug（已修）

`test_classify_block_name` 第一次跑挂了：`BED_1800` 被误判为 `door`。

根因：`DOOR_KEYWORDS` 含 `"D_"`，命中 `BE**D_**1800`。
修复（`backends/freecad_backend.py::_classify`）：先匹配细粒度家具类型，门/窗兜底。
新增锁定测试：`W_POOL → window`（已知误命中，待 Phase 1 映射表缓解）。

这是 review v1 时 P2 风险的活体证据——**单关键词匹配脆弱**，Phase 1 必须上"块几何 + 名称 + 图层"三维特征 + 用户映射表。

---

## 2. 环境（来自 /Users/bladelee/project/ops）

| 项 | 现状 | 评估 |
|----|------|------|
| Python 3.13.5 (miniconda3) | ✅ `/Users/bladelee/miniconda3/bin/python` | 可用，跑测试成功 |
| 系统 python3 | ⚠️ Xcode 残留（损坏） | 不用 |
| Homebrew | ⚠️ 损坏（ops/troubleshooting 问题 1） | 不影响本方案 |
| **Docker** | 🔴 **17.12.0-ce（2017-12）+ Compose 1.18.0，守护进程未运行** | **Phase 0 硬阻塞** |
| macOS | 12.7.6 Monterey | Docker Desktop 新版要求 mac 12+，OK |

ops/troubleshooting.md 问题 4 自己也明确："Docker 17.12.0-ce → 建议版本：最新，下载 Docker Desktop"。

---

## 3. 阻塞项处置：Docker 升级

### 3.1 为什么 17.12 不行（影响本方案的具体点）

| 问题 | 后果 |
|------|------|
| Compose v1（1.18）→ 我们 `docker-compose.yml` 用 v2 语法（`services:` 顶层 + `mem_limit`） | compose 跑不起来 |
| BuildKit 不支持 | Dockerfile 里 `wget | tar` 等指令可能 fail 或慢 |
| 无 Apple Silicon 兼容（你是 Intel i7-5557U，勉强度过） | — |
| 8 年安全/功能 gap | 整体不稳定 |

### 3.2 升级步骤（参考 ops/troubleshooting.md 问题 3、4）

由于本机 Homebrew 也损坏，最稳的路径是**直接下载 Docker Desktop installer**：

```bash
# 1. 下载（手动或 curl，任选）
#    https://www.docker.com/products/docker-desktop
#    选 "Mac with Intel chip"（你是 i7-5557U）

# 2. 卸载旧的 17.12（避免冲突）
sudo rm -rf /usr/local/bin/docker /usr/local/bin/docker-compose
sudo rm -rf /Applications/Docker.app   # 如果存在
rm -rf ~/.docker                       # 可选，清理旧配置

# 3. 装新的（双击 .dmg 拖到 Applications，启动后授权）
open -a Docker

# 4. 验证（新版应 >= 4.30, engine >= 25.0）
docker --version
docker compose version    # 注意 v2 是 "docker compose"，不是 "docker-compose"
docker info
```

### 3.3 升级后做的第一件事

```bash
cd /Users/bladelee/project/cad/floorplan-mcp
docker compose build     # 构镜像（提取 FreeCAD AppImage + freecad-ai）
docker compose up        # 起 SSE server :3000

# 在 Claude Desktop 配 SSE（见 README）→ 测一个 read_floorplan
```

---

## 4. 还需要你提供的两件外部输入

| # | 输入 | 用途 | 现状 |
|---|------|------|------|
| 1 | **升级 Docker 到最新** | 跑容器化 MVP / Phase 0 验证 | 🔴 阻塞 |
| 2 | **2 个真实装修 DWG**（放 `~/dwgs/`） | Phase 0 的房间识别准确率验证 | 🔴 阻塞 |

提供后我能立即做：
- `docker compose run --rm floorplan-mcp python3 /opt/floorplan/scripts/phase0_verify.py /data`
- 出 Phase 0 报告（round-trip 实体保真 + 房间识别准确率）
- 决定主/备：≥70% 准确率 → FreeCAD 主；< 70% → 切 ezdxf+shapely

---

## 5. 不依赖 Docker 我马上能继续做的事（候选）

| 任务 | 价值 | 依赖 |
|------|------|------|
| ✅ 已完成：骨架 + 单元/集成测试 + Phase 0 脚本 + README | — | — |
| 加更多合成 DXF 边界用例（不规则户型、L 形、缺墙） | 提高 shapely 房间识别信心 | 仅 Python |
| 把 `_classify` 升级成三维特征分类器（块几何 bbox + 名称 + 图层） | 提前解决 P2 关键词脆弱性 | 仅 Python |
| 写 FreeCAD `_detect_rooms` 的多房间识别（现只识别 1 个） | 修复 freecad_backend 已知 bug | 仅 Python（容器跑） |
| 写 product spec 文档（用户故事细化 + Claude Desktop 配置截图位） | V3 测试准备 | 无 |

---

## 6. 关于 review v1 时的判断被验证

- ✅ "v1 房间识别算法不成立" → 合成样本证明：v1 算法在独立 LINE 段下得 0 房间，shapely 得 3 房间
- ✅ "v1 renderer 破图层 bug" → 我们用 `RenderContext(doc)` 副本彻底避开
- ✅ "P2 关键词匹配脆弱" → 测试当场抓住 `BED_1800` 被误判为门
- ✅ "freecad-ai user_tools 不走安全层" → `_safety.with_transaction` + `.bak` 已自带

骨架的关键设计决策都已被测试或合成样本验证，剩下的是 Docker 环境和真实 DWG。

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 初版 | 2026-08-08 | 骨架就绪 + 9 单元 + 1 集成全过；记录 BED_1800 bug 修复；Docker 升级为唯一阻塞 |
