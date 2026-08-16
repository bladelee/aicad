"""tools/cli/subcommands/move_wall_cmd.py — `floorplan move-wall` 子命令。

包装 tools.core.move_wall.move_wall
"""
from __future__ import annotations
import argparse
from .._argparse_common import print_result_json, fail


def add_parser(sub: argparse._SubParsersAction):
    p = sub.add_parser(
        "move-wall",
        help="平移一堵墙。可选联动同族图层 (--sync)",
        description="平移墙 LINE，可选同步 F地坪/C天花 等同族图层",
    )
    p.add_argument("--dxf", required=True, help="DXF 文件路径")
    p.add_argument(
        "--handle", required=True,
        help="墙 LINE 实体的 handle（如 E6037；用 mcp__floorplan__read_floorplan 查）",
    )
    p.add_argument("--dx", type=float, default=0.0, help="X 位移 mm（正=向右）")
    p.add_argument("--dy", type=float, default=0.0, help="Y 位移 mm（正=向上）")
    p.add_argument(
        "--mode", default="translate", choices=["translate", "stretch"],
        help="translate=整体平移，stretch=拉伸端点（默认 translate）",
    )
    p.add_argument(
        "--sync", action="store_true",
        help="同步 F地坪 / C天花 / L天灯 / J家具 等同族图层实体",
    )
    p.add_argument("--out", default="", help="输出路径（默认 <原名>_moved.dxf）")
    p.add_argument(
        "--backup-dir", default="",
        help="备份目录（默认不备份；给目录则自动写一份 .bak）",
    )
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace) -> int:
    try:
        from tools.core import move_wall
    except ImportError as e:
        return fail(f"core 包 import 失败: {e}")

    try:
        result = move_wall(
            dxf_path=args.dxf,
            handle=args.handle,
            dx=args.dx,
            dy=args.dy,
            mode=args.mode,
            sync_layers=args.sync,
            backup_dir=args.backup_dir or None,
            output_suffix="_moved" if not args.out else "",
        )
    except Exception as e:
        return fail(f"执行失败: {type(e).__name__}: {e}")

    # move_wall 用 output_suffix 模式，如果用户给了 --out 就重命名
    if args.out and result.get("output") and result["output"] != args.out:
        import shutil
        shutil.move(result["output"], args.out)
        result["output"] = args.out

    print_result_json(result)
    return 0 if result.get("ok", True) else 1
