"""装修图纸自动化工具包（本地 tools.core / tools.cli 的宿主包）。

加这个 __init__.py 的原因（2026-08-16 排障记录）：
  floorplan-mcp 容器的 PYTHONPATH 含 /opt/floorplan（那里也有一个带
  __init__.py 的 tools 包）。Python 的规则是 regular package 优先于
  namespace package —— 若本目录无 __init__.py，`import tools` 会被
  /opt/floorplan/tools 抢走，导致 `from tools.core import ...` 报
  No module named 'tools.core'。
  加上本文件后，/data 在 sys.path[0]，本包优先命中，tools.core 可用。
"""
