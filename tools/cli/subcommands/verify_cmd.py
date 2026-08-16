"""tools/cli/subcommands/verify_cmd.py — `floorplan verify`

包装 tools.core.verify_rename.verify_rename
"""
from __future__ import annotations
import argparse
from pathlib import Path
from _argparse_common import print_result_json, fail


def add_parser(sub: argparse._SubParsersAction):
    p = sub.add_parser(
        "verify", help="验证材料码替换是否真的成功",
        description="扫一批 DXF，确认 old_code 已清空、new_code 已到位",
    )
    p.add_argument(
        "--dxfs", nargs="+", required=True,
        help="DXF 路径列表（可多个）",
    )
    p.add_argument("--from", dest="old_code", default="ST-01")
    p.add_argument("--to", dest="new_code", default="ST-A")
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace) -> int:
    # 支持 glob 展开（防止 shell 把通配符传进来）
    paths: list[str] = []
    for p in args.dxfs:
        if any(c in p for c in "*?["):
            paths.extend(str(x) for x in Path(".").glob(p))
        else:
            paths.append(p)
    if not paths:
        return fail("没有匹配到任何 DXF 文件")

    from tools.core import verify_rename
    try:
        result = verify_rename(paths, old_code=args.old_code, new_code=args.new_code)
    except Exception as e:
        return fail(f"执行失败: {type(e).__name__}: {e}")

    print_result_json(result)
    return 0 if result.get("overall_ok") else 2  # 验证不通过用 exit=2
