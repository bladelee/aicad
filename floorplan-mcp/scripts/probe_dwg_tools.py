"""探针 2：容器内是否有任何能读 DWG 的工具？"""
from __future__ import annotations
import os
import subprocess
import sys


def try_libredwg():
    """LibreDWG（libredwg-python）"""
    print("--- 1. LibreDWG python binding ---")
    try:
        import libredwg
        print(f"  ✓ libredwg 可用：{getattr(libredwg, '__version__', '?')}")
        return True
    except ImportError as e:
        print(f"  ✗ 无 libredwg python binding: {e}")
    # 命令行
    r = subprocess.run(["which", "dwg2dxf"], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  ✓ dwg2dxf 命令可用：{r.stdout.strip()}")
        return True
    print("  ✗ 无 dwg2dxf 命令")
    return False


def try_freecad_importdwg():
    """FreeCAD 的 importDWG 模块（基于 ODA）"""
    print("\n--- 2. FreeCAD importDWG ---")
    try:
        import FreeCAD
        print(f"  ✓ FreeCAD 可用：{FreeCAD.Version()}")
    except Exception as e:
        print(f"  ✗ FreeCAD 不可用: {type(e).__name__}: {e}")
        return False

    # FreeCAD importDWG 模块
    try:
        import importDWG
        print(f"  ✓ importDWG 模块可用")
        return True
    except ImportError as e:
        print(f"  ✗ importDWG 不可用: {e}")
        # 看是否有 ODAFileConverter 系统依赖
        r = subprocess.run(
            ["which", "ODAFileConverter"], capture_output=True, text=True
        )
        print(f"  ODAFileConverter 命令: {r.stdout.strip() if r.returncode==0 else '不可用'}")
        return False


def test_dwg_read_with_freecad():
    """真刀真枪试：让 FreeCAD 读一个 DWG"""
    print("\n--- 3. FreeCAD 实读 DWG 测试 ---")
    dwg = "/data/2-19-102材料表.dwg"
    if not os.path.exists(dwg):
        print(f"  skip: {dwg} 不存在")
        return
    try:
        import FreeCAD
        import Mesh  # noqa
        FreeCAD.Console.PrintLog = lambda *a, **k: None  # 静音

        # FreeCAD 打开 DWG 实际还是走 importDWG
        import importDWG
        # 直接调底层：转 DXF 再打开
        out = "/tmp/test.dxf"
        try:
            importDWG.process(dwg, out)
            print(f"  ✓ importDWG.process 转换成功 → {out}")
            if os.path.exists(out):
                print(f"    DXF 文件大小: {os.path.getsize(out)} 字节")
        except Exception as e:
            print(f"  ✗ importDWG.process 失败: {type(e).__name__}: {str(e)[:200]}")
    except Exception as e:
        print(f"  ✗ FreeCAD 测试失败: {type(e).__name__}: {str(e)[:200]}")


def try_gdal_or_other():
    """其他可能的 DWG 读库"""
    print("\n--- 4. 其他 DWG 库探测 ---")
    for mod in ["aspose-cad", "dxfgrabber", "LibreDWG"]:
        try:
            __import__(mod)
            print(f"  ✓ {mod} 可用")
        except ImportError:
            pass


if __name__ == "__main__":
    print(f"python: {sys.version.split()[0]}")
    try_libredwg()
    try_freecad_importdwg()
    test_dwg_read_with_freecad()
    try_gdal_or_other()
