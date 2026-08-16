# Changelog

本项目的所有显著变更都记录在此文件。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [SemVer](https://semver.org/lang/zh-CN/)。

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
