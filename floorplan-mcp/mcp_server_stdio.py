"""floorplan-mcp 的 stdio server 入口（MVP 唯一 transport）。

按用户决策（2026-08-08）：MVP 单 stdio 通道，跑通再扩 streamable_http。
此脚本在容器内跑，被前端（Goose/OpenWork）通过 docker exec 拉起。

职责（确定性高、无副作用）：
  1. 把 5 个装修图 user_tool 链到 freecad-ai 的 USER_TOOLS_DIR（让自动发现）
  2. 处理 stdout —— FreeCAD C++ banner 会污染，需把 banner 转 stderr
  3. 调用 freecad-ai 的 StdioServerTransport + create_default_registry

为什么不用 freecad-ai 自带的 mcp_server_entry.py 直接：
  自带脚本依赖 bash 'exec 3>&1 1>&2' 做 fd 重定向（Linux/macOS 专属）。
  本脚本用 Python 原生 os.dup2 实现等价效果，跨平台（Windows 容器也行）。
"""

from __future__ import annotations
import os
import sys
import shutil
from pathlib import Path

USER_TOOLS_DIR = Path(
    os.environ.get(
        "USER_TOOLS_DIR",
        str(Path.home() / ".config/FreeCAD/FreeCADAI/tools"),
    )
)
OUR_TOOL_FILES = [
    Path(os.environ.get(
        "FLOORPLAN_TOOLS_FILE",
        "/opt/floorplan/tools/floorplan_tools.py",
    )),
    # v0.2 (C4-γ)：装修改造工具（move_wall / rename_material / ...）
    Path(os.environ.get(
        "RENOVATION_TOOLS_FILE",
        "/opt/floorplan/tools/mcp_renovation_tools.py",
    )),
]


def link_user_tools():
    """把我们的 user_tool 文件链接到 freecad-ai 自动发现目录。"""
    USER_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    linked = []
    for src in OUR_TOOL_FILES:
        if not src.exists():
            print(f"[floorplan-mcp] 跳过（不存在）: {src}", file=sys.stderr)
            continue
        target = USER_TOOLS_DIR / src.name
        if not target.exists():
            try:
                target.symlink_to(src)
            except OSError:
                # 某些文件系统不支持 symlink，退化为复制
                shutil.copy2(src, target)
        linked.append(target)
    return linked


def redirect_stdout_stderr():
    """把 fd 1 暂时重定向到 stderr，让 FreeCAD C++ banner 不污染 stdout。

    MCP stdio 协议要求 stdout 只能是 JSON-RPC 行，但 FreeCAD 启动会喷 banner。
    freecad-ai 自带 mcp_server_entry.py 用 bash 'exec 3>&1 1>&2' 解决（平台相关）。
    我们用 os.dup2 原生实现，避 bash 依赖（Windows 容器也跑）。

    在 FreeCAD 导入完成后再恢复 stdout 给 JSON-RPC。
    """
    saved_stdout = os.dup(1)
    os.dup2(2, 1)        # 让 fd 1 暂指向 stderr
    sys.stdout = sys.stderr
    return saved_stdout


def restore_stdout(saved_fd: int):
    os.dup2(saved_fd, 1)
    os.close(saved_fd)
    sys.stdout = os.fdopen(1, "w")


def main():
    # 确保 /opt/floorplan 在 PYTHONPATH
    our_root = Path("/opt/floorplan")
    if our_root.is_dir() and str(our_root) not in sys.path:
        sys.path.insert(0, str(our_root))

    link_user_tools()
    print(f"[floorplan-mcp] user_tools linked at {USER_TOOLS_DIR}", file=sys.stderr)
    print(f"[floorplan-mcp] backend = {os.environ.get('FLOORPLAN_BACKEND', 'freecad')}",
          file=sys.stderr)

    # 找到 freecad-ai 的安装路径
    fa_root = Path(os.environ.get("FREECAD_AI_ROOT", "/opt/freecad-ai"))
    if str(fa_root) not in sys.path:
        sys.path.insert(0, str(fa_root))

    saved = redirect_stdout_stderr()
    try:
        import FreeCAD  # noqa
        if not FreeCAD.ActiveDocument:
            FreeCAD.newDocument("Unnamed")
        restore_stdout(saved)

        from freecad_ai.tools.setup import create_default_registry
        from freecad_ai.mcp.server import MCPServer

        registry = create_default_registry(include_mcp=False)
        # 确认我们的工具被发现（debug 用）
        names = [t.name for t in registry.list_tools()]
        sys.stderr.write(f"[floorplan-mcp] registered tools: {names}\n")
        sys.stderr.flush()

        server = MCPServer(registry)
        server.run()  # 阻塞，处理 stdin/stdout 的 JSON-RPC
    except Exception:
        # 异常情况下也要恢复 stdout，否则客户端拿不到错误
        try:
            restore_stdout(saved)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
