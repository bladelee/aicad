"""tools/core/ — C4 核心层。

把散落在 tools/dxf_edit/、tools/dxf_scan/ 的工具暴露成纯函数 API：
无 print / 无 sys.exit / 无全局 env，参数全部显式。

设计依据：docs/C4设计方案-CLI+MCP.md §2

注意：核心层**不重新实现业务逻辑**，只做"重新暴露"。真正的代码仍在老文件里。
这样可以保持 C2 测试（test_param_expr.py / test_doc_to_shapes.py）不被破坏，
同时 C4-β CLI 层 / C4-γ MCP 层 / 单元测试都从 core/ 走统一入口。
"""
from __future__ import annotations

# ─── 基础（A1/A2）────────────────────────────────────────────
from .param_expr import eval_expr, get_num, params_for_eval
from .shapes import doc_to_shapes, filter_shapes_by_layer, shapes_bbox, save_shapes_json

# ─── 改造工具（修改类）──────────────────────────────────────
from .move_wall import move_wall
from .move_wall_with_dim import move_wall_with_dim
from .move_wall_with_floor_ceil import move_wall_with_floor_ceil
from .apply_material_rename import apply_material_rename
from .restore_bak import restore

# ─── 探查工具（只读类）──────────────────────────────────────
from .probe_dimensions import probe_dimensions_near_wall
from .verify_rename import verify_rename

__all__ = [
    # 基础
    "eval_expr",
    "get_num",
    "params_for_eval",
    "doc_to_shapes",
    "filter_shapes_by_layer",
    "shapes_bbox",
    "save_shapes_json",
    # 改造
    "move_wall",
    "move_wall_with_dim",
    "move_wall_with_floor_ceil",
    "apply_material_rename",
    "restore",
    # 探查
    "probe_dimensions_near_wall",
    "verify_rename",
]
