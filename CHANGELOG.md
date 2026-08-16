# Changelog

本项目的所有显著变更都记录在此文件。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [SemVer](https://semver.org/lang/zh-CN/)。

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
