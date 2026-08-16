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
    """把核心函数返回的 dict 美化打印到 stdout（唯一 stdout 输出点）。"""
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def run_core(fn, **kwargs) -> int:
    """CLI 统一执行入口：guard_stdout 包住 core 调用，stdout 只留纯 JSON。

    老实现里 68 处 print 会污染 stdout；fd 级重定向到 stderr 后，
    print_result_json 是唯一的 stdout 写入者（机器可读）。
    失败走 fail()（stderr + exit 1）。
    """
    from tools.core._stdio_guard import guard_stdout
    try:
        with guard_stdout():
            result = fn(**kwargs)
    except Exception as e:  # noqa: BLE001 — CLI 边界统一报错
        return fail(f"执行失败: {type(e).__name__}: {e}")
    print_result_json(result)
    return 0 if result.get("ok", True) else 1


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
