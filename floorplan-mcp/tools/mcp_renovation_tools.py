"""MCP user_tools — 装修图纸改造工具（v0.2 / C4-γ）。

把 tools/core 的改造能力（v0.1 CLI 已验证的同一份核心）注册成 MCP tool，
让设计师在 Goose/OpenWork 里用自然语言改图：
  "把 E6037 那堵墙右移 500mm"          → move_wall
  "ST-01 全部换成 ST-A"                → rename_material
  "改完墙把标注也更新"                  → move_wall_with_dim
  "看看 E6037 附近有哪些尺寸标注"        → probe_dimensions

freecad-ai user_tools 约束（自动 AST 发现）：
  - 公开函数（不以 _ 开头）、有 type hints、docstring 作为 tool 描述
  - 参数类型仅 float/int/str/bool（复杂结构 → str 传 JSON/逗号分隔）
  - 返回 dict

安全（R2）：所有写操作走 core 层 → out_path 显式输出（不覆写输入）；
备份能力保留（backup_dir）。stdout 由 guard_stdout 防护，JSON-RPC 不被污染。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 容器内 core/CLI 层在 /opt/aicad（见 Dockerfile C4-δ COPY）；
# 本地仓库直跑时在仓库根。两处都试探，找到为止。
for _root in (os.environ.get("AICAD_ROOT", "/opt/aicad"), str(Path(__file__).resolve().parents[2])):
    if Path(_root).is_dir() and (_root not in sys.path):
        sys.path.insert(0, _root)

from tools.core._stdio_guard import guard_stdout

# core 层 import 包在 guard 外（import 期老模块也可能 print）
with guard_stdout():
    from tools.core import (
        move_wall as _move_wall_core,
        move_wall_with_dim as _move_wall_dim_core,
        move_wall_with_floor_ceil as _move_wall_fc_core,
        apply_material_rename as _rename_core,
        verify_rename as _verify_core,
        probe_dimensions_near_wall as _probe_dims_core,
    )


def move_wall(
    path: str,
    handle: str,
    dx_mm: float = 0.0,
    dy_mm: float = 0.0,
    mode: str = "translate",
    sync_layers: bool = False,
    out_path: str = "",
    backup_dir: str = "",
) -> dict:
    """在装修图上平移一堵墙（LINE 实体），返回 before/after 坐标与联动统计。

    适用于：用户说"把 X 墙右移/上移 N mm""挪一下这堵墙""这面墙移过去"。
    联动（sync_layers=True）会把 F地坪/C天花/L天灯/J家具 同族图层一起平移。

    不要用于：改标注数字——调 move_wall_with_dim；
              改材料编号——调 rename_material；
              查图——调 read_floorplan / probe_dimensions。

    用户典型口语：
      - "把 E6037 那堵墙向右移 500mm"
      - "这堵墙下移 200，地坪天花跟着动"
      - "把 handle 1A2F 的墙挪 300mm"

    Args:
        path: DXF 文件路径（容器内 /data/...）
        handle: 墙 LINE 实体的 handle（16 进制字符串，如 "E6037"）
        dx_mm: X 位移（毫米，正=向右）
        dy_mm: Y 位移（毫米，正=向上）
        mode: "translate"（整体平移）或 "stretch"（拉伸端点）
        sync_layers: True 时联动同族图层（地坪/天花/灯具/家具）
        out_path: 输出路径（空 = 自动 <原名>_moved.dxf，绝不覆写输入）
        backup_dir: 备份目录（空 = 不备份）
    """
    with guard_stdout():
        return _move_wall_core(
            dxf_path=path, handle=handle,
            dx=dx_mm, dy=dy_mm, mode=mode,
            sync_layers=sync_layers,
            out_path=out_path or None,
            backup_dir=backup_dir or None,
        )


def move_wall_with_dim(
    path: str,
    handle: str,
    dx_mm: float = 0.0,
    dy_mm: float = 0.0,
    near_mm: float = 2000.0,
    out_path: str = "",
) -> dict:
    """平移一堵墙，并同步跟随的尺寸标注（DIMENSION defpoint），数字随墙自动更新。

    适用于：用户说"改墙后标注也要对""墙挪了把尺寸标注一起改""标注跟墙联动"。
    原理：把落在墙端附近的 DIMENSION 的 defpoint 平移同样的量，
    AutoCAD 打开后按新 defpoint 重算测量值。

    不要用于：只移墙不管标注——调 move_wall 更简单；
              改材料编号——调 rename_material。

    用户典型口语：
      - "把 E6037 墙右移 500，尺寸标注跟着更新"
      - "挪墙并同步标注"

    Args:
        path: DXF 文件路径（容器内 /data/...）
        handle: 墙 LINE 实体 handle
        dx_mm: X 位移（毫米，正=向右）
        dy_mm: Y 位移（毫米，正=向上）
        near_mm: DIMENSION 同步半径（毫米，默认 2000）
        out_path: 输出路径（空 = 自动 <原名>_with_dim.dxf）
    """
    with guard_stdout():
        return _move_wall_dim_core(
            dxf_path=path, handle=handle,
            dx=dx_mm, dy=dy_mm, near=near_mm,
            out_path=out_path or None,
        )


def move_wall_with_floor_ceil(
    path: str,
    handle: str,
    dx_mm: float = 0.0,
    dy_mm: float = 0.0,
    near_mm: float = 2000.0,
    out_path: str = "",
) -> dict:
    """平移一堵墙，并联动附近的地坪/天花/灯具/家具实体（半径内一起移）。

    适用于：用户说"墙挪了之后地面天花一起改""联动改"。
    会把 near_mm 半径内 F地坪/C天花/L天灯/J家具 图层的实体平移同样的量。

    不要用于：联动标注——调 move_wall_with_dim；
              一次性全联动——调 move_wall(sync_layers=True)。

    用户典型口语：
      - "把这堵墙右移 500，地坪天花跟着改"
      - "墙挪 800，附近的家装一起动"

    Args:
        path: DXF 文件路径（容器内 /data/...）
        handle: 墙 LINE 实体 handle
        dx_mm: X 位移（毫米，正=向右）
        dy_mm: Y 位移（毫米，正=向上）
        near_mm: 联动半径（毫米，默认 2000）
        out_path: 输出路径（空 = 自动 <原名>_fc.dxf）
    """
    with guard_stdout():
        return _move_wall_fc_core(
            dxf_path=path, handle=handle,
            dx=dx_mm, dy=dy_mm, near=near_mm,
            out_path=out_path or None,
        )


def rename_material(
    path: str,
    old_code: str,
    new_code: str,
    out_path: str = "",
    dry_run: bool = False,
) -> dict:
    """把图中所有材料编号 old_code 全字替换为 new_code（不误伤 ST-010/ST-012）。

    适用于：用户说"材料表改编号了，图里全部换""ST-01 都改成 ST-A"。
    替换范围：所有布局的 INSERT 属性(tag/值) + TEXT + MTEXT。
    dry_run=True 时只统计不写文件（先看会改多少处再真改）。

    不要用于：查某编号出现多少次——dry_run=True 即可；
              改墙——调 move_wall。

    用户典型口语：
      - "把 ST-01 全部替换成 ST-A"
      - "材料编号 3 区改成 5 区"
      - "先看看有多少处 ST-01"（配 dry_run）

    Args:
        path: DXF 文件路径（容器内 /data/...）
        old_code: 旧材料码（如 "ST-01"）
        new_code: 新材料码（如 "ST-A"）
        out_path: 输出路径（空 = 自动 <原名>_<old>_to_<new>.dxf）
        dry_run: True 只统计不写文件
    """
    with guard_stdout():
        return _rename_core(
            dxf_path=path, old_code=old_code, new_code=new_code,
            out_path=out_path or None, dry_run=dry_run,
        )


def verify_rename(
    path: str,
    old_code: str,
    new_code: str,
) -> dict:
    """验证材料码替换是否彻底：旧码应为 0 处，新码应有预期数量。

    适用于：替换完成后用户想确认"都改干净了吗"；或怀疑有漏改时。

    不要用于：执行替换——调 rename_material。

    用户典型口语：
      - "确认一下 ST-01 都改完了吗"
      - "还有没有漏掉的编号"

    Args:
        path: DXF 文件路径（容器内 /data/...）
        old_code: 旧材料码
        new_code: 新材料码
    """
    with guard_stdout():
        return _verify_core(
            dxf_path=path, old_code=old_code, new_code=new_code,
        )


def probe_dimensions(
    path: str,
    handle: str,
    near_mm: float = 2000.0,
) -> dict:
    """只读探查：列出某堵墙附近（near_mm 内）的尺寸标注及到墙端距离。

    适用于：用户问"这堵墙边上有哪些标注""标注离墙多远"，
    或 move_wall_with_dim 前想预览会联动哪些标注。

    不要用于：改标注——调 move_wall_with_dim；
              其他只读查询——read_floorplan。

    用户典型口语：
      - "E6037 附近有什么尺寸标注"
      - "看看这堵墙周围 1 米内的标注"

    Args:
        path: DXF 文件路径（容器内 /data/...）
        handle: 墙 LINE 实体 handle
        near_mm: 查询半径（毫米，默认 2000）
    """
    with guard_stdout():
        return _probe_dims_core(
            dxf_path=path, handle=handle, near=near_mm,
        )
