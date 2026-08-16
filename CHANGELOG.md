# Changelog

本项目的所有显著变更都记录在此文件。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [v0.3.0] — 2026-08-17  服务器形态（HTTP/SSE + Bearer 鉴权）

### 新增

- **serve-http 入口**（`mcp_server_http_authed.py`）：容器部署公司服务器，设计师 Goose 远程连 `http://<ip>:3000/sse`
  - Bearer Token 鉴权（不带/错 token → 401；未设 `FLOORPLAN_AUTH_TOKEN` 拒绝启动）
  - 复用 freecad-ai SSEServerTransport，子类注入鉴权不改上游
- **docker-compose 双形态**：默认 stdio（本机一体化）；`--profile server` 启 HTTP 服务器模式
- **Goose 远程配置文档**（`clients/goose-remote-http.md`）：服务器 IT 5 分钟部署 + 设计师 2 分钟配置

### 修复（v0.2 遗留暗病，重要！）

- **user_tools 工具发现没生效**：此前硬编码链接目录与 freecad-ai 实际扫描目录（`CONFIG_DIR/tools`，受 `FREECAD_AI_CONFIG_DIR`/XDG 影响）不一致——文件链了但不被发现，只有 53 个内置工具。
  → 改为从 `freecad_ai.config.USER_TOOLS_DIR` 读真实目录（单一事实源）
- **同名包冲突致工具静默丢失**：镜像里 `/opt/floorplan/tools` 与 `/opt/aicad/tools` 同名，`from tools.core ...` 在交叉加载时命中错的包且异常被 loader 吞掉（11 个工具最多只出 6 或 5，互斥）。
  → 专用通道 `_aicad_core` 按路径加载，绕开顶层包名解析
- `floorplan_tools.py` 相对导入在独立文件加载下崩 → 按真实源位置（realpath 解 symlink）加载 `get_backend`

### 验证

- 镜像内 11 工具同时加载 ✓（v0.2 实际只有 6 或 5 被发现，本版真正全量）
- HTTP E2E：无 token 401 ✓ 错 token 401 ✓ 对 token SSE 握手 endpoint 事件 ✓ 服务日志 64 工具 ✓

## [v0.2.0] — 2026-08-16  MCP 工具注册（C4-γ）

### 新增

- **MCP 工具 ×6**（`floorplan-mcp/tools/mcp_renovation_tools.py`）：设计师在 Goose/OpenWork 用自然语言改图
  - `move_wall` — 平移墙体（可选联动同族图层）
  - `move_wall_with_dim` — 移墙 + 同步 DIMENSION 标注
  - `move_wall_with_floor_ceil` — 移墙 + 联动地坪/天花/家具
  - `rename_material` — 材料码全字替换（支持 dry_run 预览）
  - `verify_rename` — 验证替换彻底性
  - `probe_dimensions` — 只读探查墙附近标注
- **stdout 纯净防护**（`tools/core/_stdio_guard.py`）：fd 级重定向，老代码 68 处 print 不再污染 JSON-RPC / CLI JSON 输出
- **分发策略落地**：仓库私有 + ghcr 镜像带凭证分发（PAT read:packages）

### 修复

- `mcp_server_stdio.py` 升级支持链接多个 user_tool 文件（v1 只链 1 个）
- MCP `move_wall` 包装对齐老实现真实签名（sync_layers: bool）

### 验证

- 本地：stdout 纯净 ✓ rename dry_run ✓ probe ✓
- 镜像内：6 工具加载 ✓ move_wall 真实改图 ✓ probe ✓

## [v0.1.0] — 2026-08-16  首个发布原型

### 新增

- **CLI `floorplan`**（7 子命令，全部输出 JSON）
  - `move-wall` — 平移墙体，可选联动同族图层
  - `move-wall-with-dim` — 平移墙体 + 同步 DIMENSION 标注 defpoint（路径 C）
  - `move-wall-floor-ceil` — 平移墙体 + 联动附近地坪/天花/家具（#2）
  - `rename-material` — 材料码全字替换（ST-01→ST-A，不误伤 ST-010/ST-012）
  - `probe` — 只读探查（dimensions 等）
  - `verify` — 验证材料码替换真实成功
  - `restore` — 从备份恢复 DXF
- **Docker 镜像**（ghcr.io）
  - `ghcr.io/bladelee/floorplan-mcp` — 主镜像（FreeCAD 1.0.2 + freecad-ai + ezdxf 1.4 + CLI）
  - `ghcr.io/bladelee/libredwg-cli` — DWG↔DXF 转换器（GPL 隔离，独立分发）
  - `docker run ghcr.io/bladelee/floorplan-mcp move-wall --dxf ... --handle ... --dx 500`
- **CI 发布流水线**（`.github/workflows/release.yml`）
  - tag `v*` 触发：buildx 双镜像 → 三重冒烟（CLI help / 真实改墙 500mm / pytest）→ push ghcr.io → Release 附离线 tar

### 修复

- CLI 子命令相对导入超出顶层包（`from .._argparse_common`）
- 容器内 `/opt/floorplan/tools` 遮蔽挂载的 `/data/tools`（namespace package 问题）→ 补 `tools/__init__.py`
- `move_wall()` 收 str 路径崩溃（老实现假定 `Path`）→ 入口归一化
- **产品级**：`--out` 导致输入 DXF 被原地覆写后"消失" → 加 `out_path` 显式参数 + 空 suffix 兜底

### 验证

- pytest 43 passed（core API + param_expr + doc_to_shapes）
- 真实项目冒烟：19-102 别墅 3-平面图 E6037 墙 +500mm，DIMENSION 14A97E defpoint2 正确同步
- 最小 fixture 冒烟：输入保留 ✓ 墙移 500.0mm ✓ JSON 输出干净 ✓

## [v0.1.0 之前]

见 docs/03-计划与复盘/ 下的历次复盘文档。
