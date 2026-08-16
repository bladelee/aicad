"""tools/cli/subcommands/ — C4-β floorplan CLI 子命令集合。

文件命名约定：<x>_cmd.py 对应 `floorplan <x>` 命令（_cmd 后缀避免和 Python 关键词冲突）。
每个文件必须导出 add_parser(sub: argparse._SubParsersAction)。
"""
