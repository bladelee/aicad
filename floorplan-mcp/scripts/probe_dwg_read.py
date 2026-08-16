"""一次性探针：检查容器内 ezdxf 是否能直接读 DWG（免 ODA）。

宿主机用：
    docker run --rm \
        -v "$PWD/dwg:/data" \
        -v "$PWD/floorplan-mcp/scripts/probe_dwg_read.py:/probe.py:ro" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /probe.py"
"""
from __future__ import annotations
import sys
import ezdxf

print(f"ezdxf version: {ezdxf.__version__}")
print(f"python: {sys.version.split()[0]}")
print()

# 1. ezdxf.addons.odafy 是否存在
try:
    from ezdxf.addons import odafy
    print(f"✓ ezdxf.addons.odafy 存在: {odafy.__file__}")
    HAS_ODAFY = True
except ImportError as e:
    print(f"✗ ezdxf.addons.odafy 不存在: {e}")
    HAS_ODAFY = False

# 2. ezdxf 是否带 ODA SDK（内嵌版）
try:
    import ezdxf_acc  # ezdxf 1.4+ 的 ODA 加速包
    print(f"✓ ezdxf_acc 可用（内嵌 ODA SDK）")
    HAS_ACC = True
except ImportError:
    print(f"○ ezdxf_acc 不可用（开源版 ezdxf，需外部 ODA）")
    HAS_ACC = False

# 3. 直接试读 DWG
DWG_FILES = [
    "/data/2-19-102材料表.dwg",          # 小文件先试
    "/data/XINLU-A2.dwg",
    "/data/1-19-102封面、目录、设计说明.dwg",
    "/data/3-19-102平面系统图.dwg",
    "/data/4-19-102立面图.dwg",
    "/data/5-19-102节点.dwg",
]

print()
print(f"{'='*60}")
print(f"试读各 DWG 文件")
print(f"{'='*60}")
import os
for dwg in DWG_FILES:
    if not os.path.exists(dwg):
        print(f"  [skip] {dwg}: 文件不存在")
        continue
    size_mb = os.path.getsize(dwg) / 1024 / 1024
    print(f"\n--- {os.path.basename(dwg)} ({size_mb:.1f} MB) ---")
    try:
        doc = ezdxf.readfile(dwg)
        print(f"  ✓ 读取成功")
        print(f"    dxfversion: {doc.dxfversion}")
        print(f"    encoding: {doc.encoding}")
        msp = doc.modelspace()
        print(f"    modelspace 实体数: {sum(1 for _ in msp)}")
        layers = list(doc.layers)
        print(f"    图层数: {len(layers)}")
        if len(layers) > 0:
            print(f"    前 8 层: {[l.dxf.name for l in layers[:8]]}")
        blocks = list(doc.blocks)
        block_names = [b.name for b in blocks if not b.name.startswith('*')]
        print(f"    块定义数 (非匿名): {len(block_names)}")
        if block_names:
            print(f"    前 8 块: {block_names[:8]}")
    except Exception as e:
        print(f"  ✗ 读取失败: {type(e).__name__}: {str(e)[:200]}")
