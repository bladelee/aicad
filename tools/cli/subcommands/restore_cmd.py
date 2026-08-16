"""tools/cli/subcommands/restore_cmd.py — `floorplan restore`

从备份恢复 DXF（包装 tools.core.restore_bak.restore / list_backups）
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from .._argparse_common import print_result_json, fail


# 让老 restore_from_bak.py 可 import（即使 core 包取不到也兜底）
_LEGACY_DIR = Path(__file__).resolve().parent.parent.parent / "dxf_edit"
if str(_LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(_LEGACY_DIR))


def add_parser(sub: argparse._SubParsersAction):
    p = sub.add_parser(
        "restore", help="从备份恢复 DXF",
        description="把 dxf 文件回滚到一个 .bak 备份版本",
    )
    sub2 = p.add_subparsers(dest="what", required=True, metavar="{list|from}")

    pl = sub2.add_parser("list", help="列出某个 DXF 的所有备份")
    pl.add_argument("--dxf", required=True)
    pl.set_defaults(func=_run_list)

    pf = sub2.add_parser("from", help="用指定 bak 恢复")
    pf.add_argument("--dxf", required=True)
    pf.add_argument(
        "--bak", required=True,
        help="要恢复到的 bak 路径（或填 latest 自动取最新）",
    )
    pf.set_defaults(func=_run_from)


def _get_api():
    """优先 core，兜底直 import 老 restore_from_bak。"""
    try:
        from tools.core.restore_bak import (
            list_backups, restore, pick_latest_backup,
        )
        return list_backups, restore, pick_latest_backup
    except ImportError:
        from restore_from_bak import (  # type: ignore[import-not-found]
            list_backups, restore, pick_latest_backup,
        )
        return list_backups, restore, pick_latest_backup


def _run_list(args: argparse.Namespace) -> int:
    list_backups, _, _ = _get_api()
    try:
        backups = list_backups(Path(args.dxf))
    except Exception as e:
        return fail(f"{type(e).__name__}: {e}")
    items = []
    for b in backups:
        if isinstance(b, dict):
            items.append({k: str(v) if isinstance(v, Path) else v
                          for k, v in b.items()})
        else:
            items.append({"path": str(b)})
    print_result_json({"backups": items, "count": len(items)})
    return 0


def _run_from(args: argparse.Namespace) -> int:
    _, restore, pick_latest_backup = _get_api()
    if args.bak.lower() == "latest":
        latest = pick_latest_backup(Path(args.dxf))
        if not latest:
            return fail("找不到任何备份")
        bak_path: Path = latest
    else:
        bak_path = Path(args.bak)
        if not bak_path.exists():
            return fail(f"bak 不存在: {bak_path}")
    try:
        result = restore(Path(args.dxf), bak_path)
    except Exception as e:
        return fail(f"{type(e).__name__}: {e}")
    print_result_json(
        {"ok": True, "restored_from": str(bak_path), "result": str(result)}
    )
    return 0
