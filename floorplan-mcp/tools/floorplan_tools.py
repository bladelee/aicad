"""5 个装修图 user_tools。

freecad-ai 的 user_tools 机制会通过 AST 解析发现这些函数，
按 type hint 自动生成 MCP tool schema。约束：
  - 函数必须公开（不以 _ 开头）、有 type hints、有 docstring（作 tool 描述）
  - 参数类型仅支持 float/int/str/bool
  - 返回 dict（自动映射到 ToolResult）或 str

⚠️ R2 重要：freecad-ai 的 user_tools handler 不走 _with_undo，
所以写工具（move_entity 等改文件的操作）必须在 backend 里自带
transaction + .bak。详见 backends/_safety.py。

每个函数的路径都是容器内绝对路径（如 /data/客厅.dwg），
宿主通过 docker bind mount 把 ~/dwgs 挂到 /data。
"""

from __future__ import annotations

# v0.3 修复：freecad-ai user_tools 是"独立文件加载"（无父包），相对导入必崩。
# 回退方案按文件位置加载本目录的 __init__.py 拿 get_backend。
# ⚠️ 绝不能 `from tools import ...`：会与镜像里另一个同名包 /opt/aicad/tools
# 冲突（sys.modules 缓存污染，导致 mcp_renovation_tools 的 tools.core 解析错+静默丢工具）。
try:
    from . import get_backend  # type: ignore
except ImportError:
    import importlib.util as _iu
    import os as _os
    # ⚠️ 用 realpath 解 symlink：本文件可能经 USER_TOOLS_DIR 的软链被加载，
    # 直接 dirname 会指向链接目录（那里没有 __init__.py，FileNotFoundError）。
    _src = _os.path.realpath(_os.path.abspath(__file__))
    _init = _os.path.join(_os.path.dirname(_src), "__init__.py")
    _spec = _iu.spec_from_file_location("_floorplan_pkg_init", _init)
    _pkg = _iu.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_pkg)  # type: ignore[union-attr]
    get_backend = _pkg.get_backend


def read_floorplan(path: str) -> dict:
    """读取并理解一张装修 DWG/DXF，返回图层/墙体/门窗/家具/房间/统计信息。

    适用于：用户第一次提到这张图、想"看看有什么"、
    或想问"户型有几个房间""有哪些家具""一共有多少门窗"时调用。
    也用于在 move_furniture 前获取可用 handle 列表。

    不要用于：只问"客厅面积多大"——那调 list_rooms 更便宜（read 会一次返回全部）
              ；要导出图——调 export_drawing；要画新图——本工具不支持（无 add 工具）。

    用户典型口语：
      - "看一下 客厅.dwg 这张图"
      - "这个户型有什么？"
      - "图里都有哪些家具？"

    Args:
        path: DWG/DXF 文件容器内绝对路径（如 /data/客厅.dwg）；用户给 ~/dwgs/...
              时换算成 /data/...
    """
    return get_backend().read(path)


def list_rooms(path: str) -> dict:
    """列出所有房间，每个含名称、面积（m²）、边界、内含家具。同时返回总面积。

    适用于：用户问"几个房间""X 房/客厅 多大""X 房间里有什么家具"等面积/统计类查询。

    不要用于：看整图结构——read_floorplan 更全；移动家具——move_furniture；
              画新房间——不支持。

    用户典型口语：
      - "客厅面积多大？"
      - "户型有几个房间？"
      - "卧室里有什么家具？"
      - "总面积多少？"

    Args:
        path: DWG/DXF 文件容器内绝对路径
    """
    rooms = get_backend().list_rooms(path)
    return {
        "count": len(rooms),
        "rooms": rooms,
        "total_area_m2": round(sum(r.get("area_m2", 0) for r in rooms), 2),
    }


def move_furniture(
    path: str,
    handle_or_name: str,
    dx_mm: float,
    dy_mm: float,
    auto_backup: bool = True,
) -> dict:
    """在装修图上把某个实体（家具/门/窗等）平移一段距离。修改前自动备份 *.bak.N。

    适用于：用户说"把 X 向 Y 移 N mm""靠墙""挪一点"等修改意图。

    不要用于：查询——调 list_rooms / read_floorplan；
              旋转——MVP 不支持（用户可问"能不能转"时答暂不支持）；
              改完后撤销——告诉用户文件被备份在 backup_path，无需调用本工具。

    用户典型口语：
      - "把沙发往右移 500mm"
      - "沙发靠墙"（靠墙需预先算方向，由你（LLM）根据 read_floorplan 推算 dx/dy）
      - "门往左挪 200"
      - "电视柜再下来一点"

    Args:
        path: DWG/DXF 文件容器内绝对路径
        handle_or_name: 实体 handle（如 "1A2F"）或 块名+序号（如 "SOFA_3P#2"）。
                        不确定时先调 read_floorplan 看可用的 handle
        dx_mm: X 方向位移（毫米，正值向右）
        dy_mm: Y 方向位移（毫米，正值向上）
        auto_backup: True 时写前自动备份（强烈保持 True）；写操作必须可回滚
    """
    return get_backend().move_entity(
        path, handle_or_name, dx_mm, dy_mm, auto_backup=auto_backup
    )


def render_preview(
    path: str,
    output_png: str,
    highlight: str = "",
) -> dict:
    """把装修图渲染成 PNG 预览图，可选高亮某些实体。

    适用于：用户说"给我看图""画一下""看一眼"或修改后想看结果时调用。
    高亮用于"把 X 圈出来""指示 X 在哪"。

    不要用于：导出 DWG/PDF——调 export_drawing；
              看结构数据——read_floorplan 返 JSON 更准确。

    用户典型口语：
      - "给我看图"
      - "把门高亮"
      - "改完之后画一张给我"

    Args:
        path: DWG/DXF 文件容器内绝对路径
        output_png: 输出 PNG 路径（建议放 /data 下，宿主能直接看到；
                    用户给 ~/dwgs/x.png 时换算成 /data/x.png）
        highlight: 要高亮的实体 handle，多个用逗号分隔（如 "1A2F,3B4C"），可空
    """
    hl = [h.strip() for h in highlight.split(",") if h.strip()] if highlight else None
    png = get_backend().render_preview(path, output_png, highlight_handles=hl)
    return {"png_path": png}


def export_drawing(
    path: str,
    target_format: str,
    output_path: str,
    acad_version: str = "ACAD2018",
) -> dict:
    """把当前图导出为 DWG/PDF/DXF 格式文件，落到 output_path。

    适用于：用户说"导出/保存为 DWG/PDF""给我一份 PDF"。

    不要用于：渲染 PNG 预览——调 render_preview；
              修改图——调 move_furniture。

    用户典型口语：
      - "导出 DWG"
      - "存成 PDF"
      - "给我一份 dxf 格式"

    Args:
        path: 输入 DWG/DXF 容器内路径
        target_format: 目标格式（dwg / pdf / dxf，三选一）
        output_path: 输出文件容器内路径（用户给 ~/dwgs/x.dwg 时换算 /data/x.dwg）
        acad_version: DWG 版本（ACAD2010/ACAD2018 等），仅 DWG 输出时生效
    """
    out = get_backend().export(path, target_format, acad_version=acad_version)
    # 若 backend 用自己的命名，统一搬到用户指定位置
    import os, shutil
    if out and os.path.isfile(out) and os.path.abspath(out) != os.path.abspath(output_path):
        shutil.move(out, output_path)
    return {"output_path": output_path}
