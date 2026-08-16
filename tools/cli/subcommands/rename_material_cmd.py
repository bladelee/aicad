"""tools/cli/subcommands/rename_material_cmd.py — `floorplan rename-material`

包装 tools.core.apply_material_rename.apply_material_rename（#6）
"""
from __future__ import annotations
import argparse
from _argparse_common import print_result_json, fail


def add_parser(sub: argparse._SubParsersAction):
    p = sub.add_parser(
        "rename-material",
        help="材料码替换（#6 ST-01 → ST-A 全字匹配）",
        description=(
            "把 DXF 内所有材料码 --from 替换为 --to，全字匹配 "
            "（ST-01 不会误伤 ST-010）。范围：INSERT.attribs + TEXT + MTEXT"
        ),
    )
    p.add_argument("--dxf", required=True)
    p.add_argument("--from", dest="old_code", required=True,
                   help="旧材料码（如 ST-01）")
    p.add_argument("--to", dest="new_code", required=True,
                   help="新材料码（如 ST-A）")
    p.add_argument("--out", default="",
                   help="输出路径（默认 <原名>_<old>_to_<new>.dxf）")
    p.add_argument("--backup-dir", default="",
                   help="备份目录（留空不备份）")
    p.add_argument("--dry-run", action="store_true",
                   help="只统计，不写文件")
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace) -> int:
    from tools.core import apply_material_rename
    try:
        result = apply_material_rename(
            dxf_path=args.dxf,
            old_code=args.old_code,
            new_code=args.new_code,
            out_path=args.out or None,
            backup_dir=args.backup_dir or None,
            dry_run=args.dry_run,
        )
    except Exception as e:
        return fail(f"执行失败: {type(e).__name__}: {e}")

    print_result_json(result)
    return 0 if result.get("ok") else 1
