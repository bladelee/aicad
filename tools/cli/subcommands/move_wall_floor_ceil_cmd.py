"""tools/cli/subcommands/move_wall_floor_ceil_cmd.py — `floorplan move-wall-floor-ceil`

包装 tools.core.move_wall_with_floor_ceil.move_wall_with_floor_ceil（#2）
"""
from __future__ import annotations
import argparse
from .._argparse_common import print_result_json, fail


def add_parser(sub: argparse._SubParsersAction):
    p = sub.add_parser(
        "move-wall-floor-ceil",
        help="平移墙 + 联动附近地坪/天花/家具（#2）",
        description=(
            "平移一段墙 + 把 near 范围内、属 F地坪/C天花/L天灯/J家具 关键词层 "
            "的实体一并平移"
        ),
    )
    p.add_argument("--dxf", required=True)
    p.add_argument(
        "--handle", default="",
        help="墙 handle（与 --wall-idx 二选一）",
    )
    p.add_argument(
        "--wall-idx", type=int, default=-1,
        help="墙序号（在 A原建筑墙体 图层中的第 N 条 LINE；handle 不给时用这个）",
    )
    p.add_argument("--dx", type=float, default=0.0)
    p.add_argument("--dy", type=float, default=0.0)
    p.add_argument(
        "--near", type=float, default=2000.0,
        help="联动半径 mm（默认 2000）",
    )
    p.add_argument(
        "--keywords", default="F地坪,C天花,L天灯,J家具",
        help="联动层关键词，逗号分隔（默认 4 大类）",
    )
    p.add_argument("--out", default="")
    p.add_argument("--backup-dir", default="")
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace) -> int:
    from tools.core import move_wall_with_floor_ceil

    handle = args.handle or None
    wall_idx = args.wall_idx if args.wall_idx >= 0 else None

    keywords = tuple(
        s.strip() for s in args.keywords.split(",") if s.strip()
    ) or None  # None 走默认值

    try:
        result = move_wall_with_floor_ceil(
            dxf_path=args.dxf,
            handle=handle,
            wall_idx=wall_idx,
            dx=args.dx,
            dy=args.dy,
            near=args.near,
            sync_layer_keywords=keywords or ("F地坪", "C天花", "L天灯", "J家具"),
            out_path=args.out or None,
            backup_dir=args.backup_dir or None,
        )
    except Exception as e:
        return fail(f"执行失败: {type(e).__name__}: {e}")

    print_result_json(result)
    return 0 if result.get("ok") else 1
