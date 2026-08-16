# C4 设计方案：CLI 统一 + MCP 工具注册

> **创建**：2026-08-09
> **状态**：⚠️ **设计阶段，待用户确认后实施**
> **关联**：用户原话 "C4 支持 cli 是需要的，或者说增加 cli 的支持（不是删掉之前），然后 C4 也要做更大的事情，支持 mcp。需要出设计文档再行动。"

---

## 0. 设计原则（用户三条硬约束）

| # | 用户原话 | 设计含义 |
|---|---------|---------|
| 1 | "C4 支持 cli 是需要的" | **必须做** CLI 统一（argparse） |
| 2 | "增加 cli 的支持（不是删掉之前）" | **叠加**模式：现有 env 变量入口**全部保留**，argparse 只做"上层封装" |
| 3 | "C4 也要做更大的事情，支持 mcp" | **C4+ = CLI + MCP** 双形态：同一个工具底层 API，既可命令行调，也可作为 MCP tool 让 AI 调 |

→ **目标形态**：每个装修改造工具 = 一份 Python 核心 + CLI 入口 + MCP 注册。修改逻辑只写一份，三种调用方式（脚本/CLI/MCP）共享同一核心。

---

## 1. 现状盘点（实测）

| 类别 | 当前形态 | 数量 | 示例 |
|------|---------|------|------|
| 已是 MCP tool（floorplan_tools.py） | freecad-ai 自动发现 | **5** | read_floorplan / list_rooms / move_furniture / render_preview / export_drawing |
| 已是 argparse | 命令行子命令 | **2** | restore_from_bak.py / extract_dimensions.py |
| 仍是 env 变量驱动 | 裸 Python 脚本 | **11** | apply_material_rename / move_wall / move_wall_with_dim / move_wall_with_floor_ceil / move_wall_propagate / demo_resize_door / param_expr / probe_dimensions / verify_rename … |
| 用 docker exec 显式拉 | 没暴露给 MCP | **11** | 同上 |

→ **C4 的核心任务**：把这 11 个工具统一搬到"核心 + CLI + MCP"三形态模型。

---

## 2. 三层架构设计

```
┌──────────────────────────────────────────────────┐
│  对外的三种调用方式（共享同一核心层）             │
└──────────────────────────────────────────────────┘
       ┌───────────────┬───────────────┬─────────┐
       ↓               ↓               ↓         ↓
   [argparse CLI]    [MCP tool]    [Python lib] [旧 env 脚本 (兼容期保留)]
   floorplan run    floorplan_      move_wall()
   --task ...       mcp_server      直接 import
       │               │               │
       └───────────────┴───────────────┘
                       ↓
       ┌────────────────────────────────────────────┐
       │  核心层 (core API, 一份代码)                │
       │  core/move_wall.py      → move_wall(...)   │
       │  core/move_wall_with_dim.py → 同名(...)    │
       │  core/apply_material_rename.py → 同名(...) │
       │  ... 11 个核心函数                         │
       └────────────────────────────────────────────┘
                       ↓
       ┌────────────────────────────────────────────┐
       │  底层基础 (A1/A2 已建好)                    │
       │  param_expr._eval_expr()                   │
       │  doc_to_shapes._doc_to_shapes()            │
       │  safe_saveas() / shift_layer_entities()    │
       │  backends/* (FreeCAD/ezdxf/ifc)            │
       └────────────────────────────────────────────┘
```

### 关键设计决策

1. **核心层 = 纯函数 API**：每个工具一个 `def xxx(dxf_path, ...) -> dict`，不做 IO 隐式行为（不要在核心函数里 `print`/`sys.exit`）。这样 CLI、MCP、单元测试都可调。

2. **CLI = argparse 薄包装**：只负责参数解析 + 路径换算（`~/dwgs/x.dxf` → `/data/x.dxf`）+ 调核心函数 + 打印结果。**逻辑零拷贝**。

3. **MCP = floorplan_tools.py 注册函数**：通过 freecad-ai 的 user_tools 自动发现机制，把核心函数重新用 type hint + docstring 包装一层。

4. **旧 11 个 env 脚本 → 不删，加 deprecation warning**：
   - 加 `warnings.warn("deprecated, use `floorplan run --task ...`", DeprecationWarning)`
   - 内部改直接调 `from core.move_wall import move_wall`，零行为变化
   - 6 个月后下线

---

## 3. 命名与目录结构

### 3.1 目录改造

```
tools/
├── core/                                 ← 新增：核心 API 层（一份代码）
│   ├── __init__.py
│   ├── move_wall.py                      move_wall(dxf, handle|point|idx, dx, dy, ...) -> dict
│   ├── move_wall_with_dim.py             move_wall_with_dim(...) -> dict     [D1]
│   ├── move_wall_with_floor_ceil.py      move_wall_with_floor_ceil(...) -> dict [#2]
│   ├── move_wall_propagate.py            move_wall_propagate(...) -> dict    [#5 实验]
│   ├── apply_material_rename.py          apply_material_rename(...) -> dict  [#6]
│   ├── verify_rename.py                  verify_rename(...) -> dict          [#6 verify]
│   ├── probe_dimensions.py               probe_dimensions(...) -> dict       [D1 探查]
│   └── param_expr.py                     ← 从 tools/dxf_edit/ 搬过来
│
├── cli/                                  ← 新增：CLI 子命令分发
│   ├── __init__.py
│   ├── main.py                           入口 `floorplan` 统一命令
│   ├── _argparse_common.py               参数校验/路径换算公共逻辑
│   └── subcommands/
│       ├── convert_dwg.py                floorplan convert-dwg ...
│       ├── move_wall.py                  floorplan move-wall ...
│       ├── move_wall_dim.py              floorplan move-wall --with-dim
│       ├── rename_material.py            floorplan rename-material ...
│       ├── verify.py                     floorplan verify ...
│       ├── probe.py                      floorplan probe <things>
│       └── demo.py                       floorplan demo [full | png | story]
│
├── mcp/                                  ← 新增：MCP tool 注册（搬家到 floorplan-mcp/tools）
│   ├── user_tools.py                     ← 即今 floorplan-mcp/tools/floorplan_tools.py 扩展
│   └── tool_specs/                       每个 MCP tool 一份独立 spec（便于 freecad-ai 发现）
│
├── dxf_edit/  (旧 11 个 env 脚本)  ← 保留兼容期，标 deprecated
└── dxf_scan/  (旧探查脚本)         ← 保留兼容期
```

### 3.2 命名约定

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 核心函数 | `snake_case` 动词宾语 | `move_wall(...)`、`apply_material_rename(...)` |
| CLI 子命令 | `kebab-case` | `floorplan move-wall`、`floorplan rename-material` |
| MCP tool 名 | `snake_case`，AI 友好 | `mcp__floorplan__move_wall`（freecad-ai 自动前缀）|
| 核心模块 | 同核心函数名 | `tools/core/move_wall.py` |

### 3.3 统一 CLI 命令树

```
floorplan                        显示帮助
floorplan --version              v0.1.0
floorplan --help                 完整子命令清单

# DWG/DXF 转换
floorplan convert-dwg  <dwg>     DWG → DXF
floorplan convert-dwg --all      目录所有 DWG
floorplan convert-dwg --to-dwg   DXF → DWG（需 ODA）

# 改墙（#1/#2/#3 三合一）
floorplan move-wall --dxf <f> --handle 1A2F --dx 500
floorplan move-wall --dxf <f> --handle 1A2F --dx 500 --with-floor-ceil
floorplan move-wall --dxf <f> --handle 1A2F --dx 500 --with-floor-ceil --with-dim
floorplan move-wall --dxf <f> --wall-idx 6 --dx 500 --dy 200
floorplan move-wall --dxf <f> --point "100,200" --dx 500   (附近最近墙)

# 材料码替换
floorplan rename-material --dxf <f> --from ST-01 --to ST-A
floorplan rename-material --dxf <f> --regex 'ST-01(?![0-9A-Z])' --to ST-A
floorplan verify           --dxf <f> --old ST-01 --new ST-A

# DIMENSION 探查（D1）
floorplan probe dimensions --dxf <f> --handle E6037

# 备份/回滚（#5 已有，但走 CLI）
floorplan backup --dxf <f>                       预备份一份
floorplan restore --dxf <f> --bak bak3.dxf       回滚

# 演示
floorplan demo full-story --project workdir/19-102
floorplan demo png        --project workdir/19-102
floorplan demo scan       --project workdir/19-102

# 后台运行模式（云端）
floorplan serve --transport stdio                本地 / 客户端直接 exec
floorplan serve --transport http --port 3000     Phase 1.5 远程
```

---

## 4. CLI 包装示例（核心 + CLI dual API）

以 `move_wall` 为例。新的 `tools/core/move_wall.py` 仅含纯函数，`tools/cli/subcommands/move_wall.py` 是 argparse 薄包装：

### 4.1 核心层（一份代码，三层通用）

```python
# tools/core/move_wall.py
from __future__ import annotations
from pathlib import Path
from typing import Optional

def move_wall(
    dxf_path: str | Path,
    handle: Optional[str] = None,
    point: Optional[tuple[float, float]] = None,
    wall_idx: Optional[int] = None,
    dx: float = 0.0,
    dy: float = 0.0,
    mode: str = "shift",
    sync_layers: tuple[str, ...] = (),
    near: float = 2000.0,
    backup_dir: Optional[str | Path] = None,
    with_dim: bool = False,
) -> dict:
    """平移一堵墙，可选同步周边地坪/天花/DIMENSION 标注。

    参数优先级（按精确度高低取其一）：handle > point > wall_idx
    Returns 最低契约 {"ok": bool, "wall_handle": str,
                      "before": {start,end}, "after": {start,end},
                      "synced_layer_count": int, "synced_dim_count": int,
                      "backup_path": str | None,
                      "warnings": [..]}
    """
    dxf_path = Path(dxf_path)
    # ... 完整逻辑（搬自现有 tools/dxf_edit/move_wall.py）
    return result
```

### 4.2 CLI 薄包装

```python
# tools/cli/subcommands/move_wall.py
import argparse, json
from tools.core.move_wall import move_wall


def add_parser(sub: argparse._SubParsersAction):
    p = sub.add_parser("move-wall", help="平移一堵墙，可选联动地坪/天花/DIMENSION")
    p.add_argument("--dxf", required=True, help="DXF 文件路径")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--handle", help="墙实体 handle (hex 字符串如 1A2F)")
    g.add_argument("--point", help="附近最近墙 ≈ 'x,y'")
    g.add_argument("--wall-idx", type=int, help="墙序号（gles walls 列表的第 N 条）")
    p.add_argument("--dx", type=float, default=0.0, help="横向移动 mm")
    p.add_argument("--dy", type=float, default=0.0, help="纵向移动 mm")
    p.add_argument("--mode", default="shift", choices=["shift", "stretch"])
    p.add_argument("--sync-layers", default="", help="同步层关键词，逗号分隔")
    p.add_argument("--near", type=float, default=2000.0, help="同步半径 mm")
    p.add_argument("--with-dim", action="store_true", help="同步 DIMENSION defpoint")
    p.add_argument("--out", default="", help="另存为（默认原地改）")
    p.add_argument("--backup-dir", default="move_wall_bak")
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace):
    point = None
    if args.point:
        x, y = (float(c) for c in args.point.split(","))
        point = (x, y)
    result = move_wall(
        dxf_path=args.dxf,
        handle=args.handle,
        point=point,
        wall_idx=args.wall_idx,
        dx=args.dx, dy=args.dy,
        mode=args.mode,
        sync_layers=tuple(s for s in args.sync_layers.split(",") if s),
        near=args.near,
        backup_dir=args.backup_dir or None,
        with_dim=args.with_dim,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

### 4.3 MCP 注册（freecad-ai 自动发现）

```python
# tools/mcp/user_tools.py （= 扩展后的 floorplan-mcp/tools/floorplan_tools.py）
from tools.core.move_wall import move_wall as _move_wall_core
from . import get_backend


def move_wall(
    path: str,
    handle: str,
    dx_mm: float,
    dy_mm: float,
    with_floor_ceil: bool = False,
    with_dimension: bool = False,
    near_mm: float = 2000.0,
) -> dict:
    """在装修图上平移一堵墙，可选同步周边的地坪/天花/DIMENSION 标注。

    适用于：用户说"要把这堵墙向右挪 500mm""加长这堵墙""移动墙后地坪天花跟一起改"
    不要用于：移动家具或门——调 move_furniture；只查图——read_floorplan。

    用户典型口语：
      - "把 1A2F 那堵墙向右移 500mm"
      - "把卧室这堵墙挪开 800mm，地坪天花也跟着改"
      - "墙端再延伸 1 米，把标注也调好"

    Args:
        path: DWG/DXF 容器内路径
        handle: 墙的 handle（16 进制字符串如 '1A2F'）
        dx_mm: X 方向位移（mm，向右为正）
        dy_mm: Y 方向位移（mm，向上为正）
        with_floor_ceil: True 时同时联动周边地坪/天花实体
        with_dimension: True 时同步附近 DIMENSION 的 defpoint/defpoint2
        near_mm: 同步半径（mm，默认 2000 = 2 米）
    """
    return _move_wall_core(
        dxf_path=path,
        handle=handle,
        dx=dx_mm, dy=dy_mm,
        sync_layers=("F地坪", "C天花", "L天灯", "J家具") if with_floor_ceil else (),
        near=near_mm,
        with_dim=with_dimension,
    )


# ...... 同样模式包装：rename_material / move_wall_with_floor_ceil / verify / probe_dimensions
```

→ freecad-ai 通过 AST 扫描发现这些函数，按 type hint **自动生成 MCP tool schema**，
直接注册到 stdio server。客户用 Goose/OpenWork 一句"把 1A2F 那堵墙向右移 500mm"就触发。

---

## 5. 实施 Phase 划分

| Phase | 工作内容 | 工作量 | 依赖 |
|------|---------|------:|------|
| **C4-α 核心层重构** | 把 11 个 env 工具拆成 `core/` 纯函数 + 老 env 脚本（调核心）| **1 天** | 无 |
| **C4-β CLI 子命令** | 写 `tools/cli/main.py` + 11 个 subcommand | **1 天** | C4-α |
| **C4-γ MCP tool 注册** | 扩展 `floorplan_tools.py`，每个核心函数套一个 MCP wrapper | **0.5 天** | C4-α |
| **C4-δ 镜像入口改造** | Dockerfile 把 `floorplan` 命令加入 PATH（`/usr/local/bin/floorplan`）| **0.5 天** | C4-β |
| **C4-ε 测试** | 单元测试新增 `test_cli_main.py`（subcommand 分发、参数校验）| **0.5 天** | C4-β |
| **总计** |  | **3.5 天** | |

**实施顺序**：α → β → γ → δ → ε，可按 Phase 出 PR。

---

## 6. 用户使用形态对比（实施前后）

### Before（现在）

```bash
# 客户/同事要这样跑：
docker run --rm -v "$PWD:/data" \
  -e PYTHONHOME=/opt/FreeCAD/usr \
  -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
  -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
  --entrypoint=/bin/bash floorplan-mcp:latest -lc \
  "/opt/FreeCAD/usr/bin/python /data/tools/dxf_edit/move_wall_with_dim.py"
```

### After（C4 后）

**形态 A** — Shell / CI（CLI 子命令）：
```bash
docker run --rm -v "$PWD:/data" floorplan-mcp:latest \
  move-wall --dxf /data/3-平面.dxf --handle E6037 --dx 500 --with-dim
```

**形态 B** — Goose/OpenWork 自然语言（MCP tool）：
```
设计师 → Goose: "把 1A2F 那堵墙向右移 500mm，地坪天花跟着改"
Goose  → 调用 MCP tool move_wall(handle="1A2F", dx_mm=500,
                                with_floor_ceil=True)
→ 1 秒返回结果 + 备份路径
```

**形态 C** — Python 库（开发者 / 集成测试）：
```python
from tools.core.move_wall import move_wall
result = move_wall("3-平面.dxf", handle="E6037", dx=500, with_dim=True)
```

---

## 7. 风险

| 风险 | 影响 | 应对 |
|-----|------|-----|
| freecad-ai 自动发现对**复杂 type hint** 失败 | MCP 工具注册不上 | 已知 freecad-ai 只支持 `float/int/str/bool`；包装层只能用这 4 类。`Optional/Union/tuple` 要在 wrapper 里**降级到 str**，例如 `--point "x,y"` 用字符串 |
| 客户用 AI 把"墙端延伸 1 米"理解为 `dx=1000` 是错的 | 输出图纸不对 | tool description 里写清楚 dx/dy 是**位移**而非延伸；设计师的口语靠 LLM 推理 |
| 旧 env 脚本仍然有人用 | 删了会断 | 兼容期**保留 + deprecation warning**，6 个月后再移 |
| 同名代码搬迁产生 import 异常 | 测试失败 | 用 `mv` + `git mv` 一并搬，配套改一次 `from tools.dxf_edit.move_wall import ...` 引用 |

---

## 8. 验收标准

完成 C4 的标志（全部满足才算 Done）：

1. ✅ 11 个 env 工具 → 全部 `core/` + `cli/subcommands/` 双形态
2. ✅ 旧 env 脚本仍可跑（输出 deprecation warning 但行为不变）
3. ✅ `floorplan --help` 列出所有子命令
4. ✅ `floorplan move-wall --dxf .dxf --handle 1A2F --dx 500 --with-dim` 跑通并输出 JSON
5. ✅ `floorplan_tools.py` 里 wrapper 函数被 freecad-ai **自动发现**（启动 stdio server 看到 tool 列表里出现 `move_wall / rename_material` 等）
6. ✅ `tools/cli/test_cli_main.py` 单元测试全过
7. ✅ 已有 C2 测试（34 个）不被破坏

---

## 9. 已决策（2026-08-09 用户已勾选）

- [x] **决策 1**：核心层目录名 `core/`（默认采纳）
- [x] **决策 2**：✅ **MVP 优先做 CLI 形态**（C4-α → C4-β → C4-δ，共 1.5 天）
  - MCP 形态（C4-γ）作为下一步（v0.2 路线）
- [ ] **决策 3**：旧 env 脚本 6 个月下线 OK，还是要永久保留？（可后续决）

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1 | 2026-08-09 | 创建：C4 完整设计（核心层 + CLI + MCP 三层模型）|
