"""tools/cli/_argparse_common.py — 子命令共用工具。"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# 让 tools.core 可被 import（CLI 入口可能被 docker 当 /opt/FreeCAD/usr/bin/python
# 直接调，不一定带 PYTHONPATH）
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def print_result_json(result: dict) -> None:
    """把核心函数返回的 dict 美化打印到 stdout。"""
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def fail(msg: str, code: int = 1) -> int:
    """统一的失败出口（stderr + exit code）。"""
    print(f"ERROR: {msg}", file=sys.stderr)
    return code


def add_dxf_arg(p: argparse.ArgumentParser, required: bool = True):
    """--dxf PATH 参数（公共）。"""
    p.add_argument(
        "--dxf", required=required, type=str,
        help="DXF 文件路径（容器内 /data/... 或本机相对路径）",
    )


def add_out_arg(p: argparse.ArgumentParser, default_suffix: str = "_out"):
    """--out PATH 参数（默认字段）。"""
    p.add_argument(
        "--out", default="", type=str,
        help=f"输出路径（留空=自动 <原名>{default_suffix}.dxf）",
    )


def add_backup_arg(p: argparse.ArgumentParser):
    p.add_argument(
        "--backup-dir", default="", type=str,
        help="备份目录路径（留空=不备份）",
    )
