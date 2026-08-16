"""单元测试 mcp_server_stdio.py 的纯逻辑（无 FreeCAD/Docker 依赖）。

跑：python -m pytest tests/test_stdio_entry.py

覆盖：
  - stdout redirect/restore 的对称性（不破坏后续 print/JSON-RPC）
  - user_tools 链接逻辑（symlink 失败回退 copy）
"""

from __future__ import annotations
import os
import sys
import io
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_stdout_redirect_restore_roundtrip():
    """redirect → restore 后，向 fd 1 写真恢复到原位置（用 pipe 直接验，不依赖 capsys）。

    pytest 的 capsys 替换的是 Python 层 sys.stdout；我们 redirect_stdout_stderr
    动的是底层 fd 1，两者不同步。这里用 os.pipe + os.dup2 当 ground truth。
    """
    import mcp_server_stdio as entry

    # 把 fd 1 暂指到一个 pipe 的写端，全链路直接看字节流
    r, w = os.pipe()
    orig_stdout = os.dup(1)
    try:
        os.dup2(w, 1)
        saved = entry.redirect_stdout_stderr()
        # 重定向期间，Python print 走的是 sys.stdout（已被改成 sys.stderr），
        # 直接 fd 1 写也应到 stderr —— 这里不测，只测 restore 后
        entry.restore_stdout(saved)
        os.write(1, b"after-restore-via-fd1\n")
        os.close(1)
        # 让 fd 1 一会儿还原
        os.dup2(orig_stdout, 1)
        # 读 pipe，应只有 "after-restore-via-fd1"
        data = os.read(r, 4096)
        assert b"after-restore-via-fd1" in data
    finally:
        # 复原 fd 1
        try:
            os.dup2(orig_stdout, 1)
        except OSError:
            pass
        os.close(orig_stdout)
        for fd in (r, w):
            try:
                os.close(fd)
            except OSError:
                pass


def test_link_user_tools_creates_symlink_or_copy(tmp_path, monkeypatch):
    """link_user_tools 在目标目录生成可被 import 的 floorplan_tools.py。"""
    import mcp_server_stdio as entry

    # 准备一个假源文件
    src = tmp_path / "fake_tools.py"
    src.write_text("def read_floorplan(path: str) -> dict:\n    return {}\n")
    target_dir = tmp_path / "tools"
    monkeypatch.setattr(entry, "USER_TOOLS_DIR", target_dir)
    monkeypatch.setattr(entry, "OUR_TOOL_FILE", src)

    target = entry.link_user_tools()
    assert target.exists()
    # 内容可读
    assert "read_floorplan" in target.read_text()


def test_link_user_tools_is_idempotent(tmp_path, monkeypatch):
    """重复跑不报错（已存在则不重做）。"""
    import mcp_server_stdio as entry

    src = tmp_path / "fake_tools.py"
    src.write_text("def f(x: int) -> int:\n    return x\n")
    target_dir = tmp_path / "tools"
    monkeypatch.setattr(entry, "USER_TOOLS_DIR", target_dir)
    monkeypatch.setattr(entry, "OUR_TOOL_FILE", src)

    entry.link_user_tools()
    entry.link_user_tools()  # 第二次不应抛错
    assert (target_dir / "fake_tools.py").exists()
