"""探针 3：摸清 FreeCAD importDWG 的实际 API。"""
from __future__ import annotations
import inspect
import os
import sys

print(f"python: {sys.version.split()[0]}")

import FreeCAD
print(f"FreeCAD: {FreeCAD.Version()[0:3]}")

import importDWG
print(f"\nimportDWG module: {importDWG.__file__}")
print(f"\n--- importDWG 公开属性 ---")
for n in dir(importDWG):
    if not n.startswith("__"):
        attr = getattr(importDWG, n)
        kind = "function" if callable(attr) else f"{type(attr).__name__}"
        print(f"  {n}: {kind}")

# 找看起来像"转 dxf"或"打开 dwg"的函数
print(f"\n--- 候选 'insert' / 'open' / 'process' 函数签名 ---")
for n in dir(importDWG):
    if n.startswith("__"):
        continue
    attr = getattr(importDWG, n)
    if callable(attr):
        try:
            sig = inspect.signature(attr)
            print(f"  {n}{sig}")
        except (ValueError, TypeError):
            print(f"  {n}(?)")

# 还看是否有 ODAFileConverter 调用
print(f"\n--- importDWG 源码中关于 ODA 的引用 ---")
src_file = importDWG.__file__
if src_file and os.path.exists(src_file):
    with open(src_file, "r", errors="ignore") as f:
        content = f.read()
    # 搜引 ODA / ODAFileConverter 等
    for kw in ["ODAFileConverter", "ODA_FILE_CONVERTER", "ODAFileConverterPath", "odafc", "subprocess"]:
        if kw in content:
            # 找出现位置前后 1 行
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if kw in line:
                    ctx = " | ".join(lines[max(0, i-1):i+2])
                    print(f"  L{i+1} [{kw}] {ctx[:200]}")
                    break  # 每个关键词只显示第一处
