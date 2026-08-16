"""tools/cli/ — C4 CLI 子命令分发。

入口点：tools/cli/main.py 里 main() → 注册所有 subcommand → argparse 分发 → 调 tools/core/*

设计依据：docs/C4设计方案-CLI+MCP.md §3.3

使用形态（封装为 docker entrypoint 后）：
    floorplan --help
    floorplan move-wall --dxf 3-平面.dxf --handle 1A2F --dx 500
    floorplan rename-material --dxf 3-平面.dxf --from ST-01 --to ST-A
    floorplan probe dimensions --dxf 3-平面.dxf --handle E6037
    floorplan demo full-story --project workdir/19-102
"""
