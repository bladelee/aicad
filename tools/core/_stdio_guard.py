"""tools/core/_stdio_guard.py — stdout 纯净防护（MCP/CLI 双保险）。

背景：
  老实现（dxf_edit/dxf_scan）里有 68 处 print()，输出到 stdout。
  - MCP 场景：stdio transport 的 stdout 只能是 JSON-RPC，混入日志即协议崩
  - CLI 场景：JSON 输出被日志污染，机器不可读

方案（零侵入）：
  with guard_stdout():
      result = move_wall(...)      # 期间所有 print 落 stderr
  # 出了 with，stdout 恢复，后续输出干净

MVP 取舍：不逐个改老文件的 68 个 print（大 diff 易引入回归），
在包装层统一拦截。后续重构老实现时再逐文件清理。
"""
from __future__ import annotations

import contextlib
import os
import sys


@contextlib.contextmanager
def guard_stdout():
    """stdout → stderr 的 fd 级重定向（MCP/CLI 共用入口）。

    fd 级重定向意味着 C 扩展（FreeCAD banner 等）的输出也会被拦下。
    异常安全：finally 恢复。

    用法：
        from tools.core._stdio_guard import guard_stdout
        with guard_stdout():
            result = core_fn(...)   # 老代码的 print 全落 stderr
        print(json.dumps(result))   # 干净 JSON
    """
    sys.stdout.flush()
    saved_fd = os.dup(1)
    os.dup2(2, 1)                    # fd 1 → fd 2 (stderr)
    old_sys_stdout = sys.stdout
    sys.stdout = sys.stderr          # Python 层也指向 stderr（双保险）
    try:
        yield
    finally:
        try:
            sys.stderr.flush()
        except Exception:
            pass
        os.dup2(saved_fd, 1)         # 恢复真 stdout
        os.close(saved_fd)
        sys.stdout = old_sys_stdout  # 恢复原对象（不新建 fdopen，避免嵌套冲突）


__all__ = ["guard_stdout"]
