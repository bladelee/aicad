"""tools/cli/subcommands/probe_cmd.py — `floorplan probe dimensions`

包装 tools.core.probe_dimensions.probe_dimensions_near_wall
"""
from __future__ import annotations
import argparse
from _argparse_common import print_result_json, fail


def add_parser(sub: argparse._SubParsersAction):
    p = sub.add_parser(
        "probe", help="只读探查（不改文件）",
        description="探查图纸信息（不改文件）",
    )
    sub2 = p.add_subparsers(dest="probe_what", required=True,
                            metavar="{dimensions}")

    dims = sub2.add_parser(
        "dimensions",
        help="探查墙端 ±N 范围内的 DIMENSION 实体（D1 用的）",
    )
    dims.add_argument("--dxf", required=True)
    dims.add_argument(
        "--handle", default="",
        help="墙 handle（与 --wall-idx 二选一）",
    )
    dims.add_argument(
        "--wall-idx", type=int, default=-1,
        help="墙序号",
    )
    dims.add_argument(
        "--near", type=float, default=2000.0,
        help="探查半径 mm（默认 2000）",
    )
    dims.set_defaults(func=_run_dimensions)


def _run_dimensions(args: argparse.Namespace) -> int:
    from tools.core import probe_dimensions_near_wall
    handle = args.handle or None
    wall_idx = args.wall_idx if args.wall_idx >= 0 else None
    if not handle and wall_idx is None:
        return fail("--handle 或 --wall-idx 必给其一")
    try:
        result = probe_dimensions_near_wall(
            dxf_path=args.dxf, handle=handle, wall_idx=wall_idx,
            near=args.near,
        )
    except Exception as e:
        return fail(f"执行失败: {type(e).__name__}: {e}")

    print_result_json(result)
    return 0 if result.get("ok") else 1
