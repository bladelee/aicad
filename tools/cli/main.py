"""floorplan — 装修图纸自动化命令行（C4-β 入口）。

子命令结构（详见各 subcommands/*.py）：
    floorplan --help
    floorplan --version
    floorplan move-wall --dxf <f> --handle <h> --dx 500 [--sync] [--with-dim]
    floorplan move-wall-with-dim --dxf <f> --handle <h> --dx 500
    floorplan move-wall-floor-ceil --dxf <f> --handle <h> --dx 500 --near 2000
    floorplan rename-material --dxf <f> --from ST-01 --to ST-A [--dry-run]
    floorplan probe dimensions --dxf <f> --handle <h>
    floorplan verify --dxfs a.dxf b.dxf --from ST-01 --to ST-A
    floorplan restore list --dxf <f>
    floorplan restore from --dxf <f> --bak <path or latest>

每个子命令的输出都是 JSON（机器可读），方便 shell pipeline。

包装 Docker 后调用形态：
    docker run --rm -v "$PWD:/data" floorplan-mcp:latest \\
        move-wall --dxf /data/3-平面.dxf --handle E6037 --dx 500 --with-dim
"""
from __future__ import annotations
import argparse
import sys
import importlib.util
from pathlib import Path

# 让 subcommands 能 import
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

__version__ = "0.1.0"


def _load_subcommand(module_name: str):
    """动态加载 subcommand 模块，返回其 add_parser 函数。"""
    full = f"subcommands.{module_name}"
    mod_path = _HERE / "subcommands" / f"{module_name}.py"
    if not mod_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(full, mod_path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    # 让 subcommand 模块内能 from _argparse_common import ... / from cli._argparse_common import ...
    # 把 subcommands 目录也加 sys.path（这样 `from _argparse_common import ...` 也能走通）
    sub_dir = _HERE / "subcommands"
    if str(sub_dir) not in sys.path:
        sys.path.insert(0, str(sub_dir))
    # 也把 cli 顶层加进去（相对 import `from .._argparse_common` 走法）
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.add_parser


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="floorplan",
        description="装修图纸自动化 CLI（C4 v0.1）",
        epilog="每个子命令均输出 JSON。示例：floorplan move-wall --dxf x.dxf --handle 1A2F --dx 500",
    )
    parser.add_argument("--version", action="version", version=f"floorplan {__version__}")

    sub = parser.add_subparsers(dest="cmd", required=True, metavar="<command>")

    # 一一注册
    for name in (
        "move_wall_cmd",
        "move_wall_dim_cmd",
        "move_wall_floor_ceil_cmd",
        "rename_material_cmd",
        "probe_cmd",
        "verify_cmd",
        "restore_cmd",
    ):
        add_parser_fn = _load_subcommand(name)
        if add_parser_fn:
            add_parser_fn(sub)

    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help(sys.stderr)
        return 2
    return func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
