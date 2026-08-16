"""tools/cli/subcommands/move_wall_dim_cmd.py — `floorplan move-wall-with-dim` 子命令。

包装 tools.core.move_wall_with_dim.move_wall_with_dim（D1 路径 C）
"""
from __future__ import annotations
import argparse
from _argparse_common import print_result_json, fail


def add_parser(sub: argparse._SubParsersAction):
    p = sub.add_parser(
        "move-wall-with-dim",
        help="平移墙 + 同步 DIMENSION defpoint（路径 C）",
        description="平移墙 + 自动同步附近 DIMENSION 的 defpoint/defpoint2",
    )
    p.add_argument("--dxf", required=True, help="DXF 文件路径")
    p.add_argument("--handle", required=True, help="墙 handle")
    p.add_argument("--dx", type=float, default=0.0, help="X 位移 mm")
    p.add_argument("--dy", type=float, default=0.0, help="Y 位移 mm")
    p.add_argument(
        "--near", type=float, default=2000.0,
        help="DIMENSION 同步半径 mm（默认 2000mm）",
    )
    p.add_argument(
        "--out", default="",
        help="输出路径（默认 <原名>_with_dim.dxf）",
    )
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace) -> int:
    try:
        from tools.core import move_wall_with_dim
    except ImportError as e:
        return fail(f"core import 失败: {e}")

    try:
        result = move_wall_with_dim(
            dxf_path=args.dxf,
            handle=args.handle,
            dx=args.dx,
            dy=args.dy,
            near=args.near,
            out_path=args.out or None,
        )
    except Exception as e:
        return fail(f"执行失败: {type(e).__name__}: {e}")

    print_result_json(result)
    return 0 if result.get("ok") else 1
