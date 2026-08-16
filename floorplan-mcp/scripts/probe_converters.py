"""探针 4：FreeCAD importDWG 的 3 个转换器哪个能用？

按优先级试：libredwg（开源）→ qcad → ODA（商业）。
"""
from __future__ import annotations
import os
import sys

print(f"python: {sys.version.split()[0]}")

import importDWG

print("\n" + "=" * 60)
print("1. 测 get_libredwg_converter（首选，免 EULA）")
print("=" * 60)
for typ in ("dwg2dxf", "dxf2dwg"):
    try:
        conv = importDWG.get_libredwg_converter(typ)
        print(f"  ✓ {typ}: {conv}")
    except Exception as e:
        print(f"  ✗ {typ}: {type(e).__name__}: {str(e)[:120]}")

print("\n" + "=" * 60)
print("2. 测 get_qcad_converter")
print("=" * 60)
try:
    conv = importDWG.get_qcad_converter()
    print(f"  ✓ qcad converter: {conv}")
except Exception as e:
    print(f"  ✗ qcad: {type(e).__name__}: {str(e)[:120]}")

print("\n" + "=" * 60)
print("3. 测 get_oda_converter")
print("=" * 60)
try:
    conv = importDWG.get_oda_converter()
    print(f"  ✓ oda converter: {conv}")
except Exception as e:
    print(f"  ✗ oda: {type(e).__name__}: {str(e)[:120]}")

print("\n" + "=" * 60)
print("4. 直接调用 convertToDxf 试转换")
print("=" * 60)
DWG = "/data/2-19-102材料表.dwg"
if os.path.exists(DWG):
    print(f"  输入: {DWG}")
    try:
        result = importDWG.convertToDxf(DWG)
        print(f"  ✓ convertToDxf 返回: {result}")
        # convertToDxf 通常生成同名 .dxf
        dxf_path = DWG.replace(".dwg", ".dxf")
        if os.path.exists(dxf_path):
            print(f"  ✓ 生成 DXF: {dxf_path} ({os.path.getsize(dxf_path)} 字节)")
        else:
            # 看返回值是不是路径
            if result and os.path.exists(result):
                print(f"  ✓ 返回值是路径: {result} ({os.path.getsize(result)} 字节)")
            else:
                print(f"  ⚠️  返回值: {result}, 但同名 dxf 也不存在")
    except Exception as e:
        print(f"  ✗ convertToDxf 失败: {type(e).__name__}: {str(e)[:200]}")
else:
    print(f"  skip: {DWG} 不存在")
