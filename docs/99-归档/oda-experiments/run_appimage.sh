#!/bin/bash
# AppImage ODA 转换流程：extract → 跑 → 出 DXF
# AppImage 自带 Qt6 全套运行时，无需手动装 xcb 等依赖。
set -e

APPIMG=/data/.oda_pkg/oda.AppImage
WORK=/tmp/oda_extract
mkdir -p "$WORK"
cd "$WORK"

echo "=== 1. extract AppImage ==="
if [ ! -d squashfs-root ]; then
    "$APPIMG" --appimage-extract >/dev/null 2>&1
fi
ls squashfs-root/ | head -10

echo ""
echo "=== 2. 找 ODAFileConverter 二进制 ==="
BIN=$(find squashfs-root -name "ODAFileConverter" -type f 2>/dev/null | head -1)
echo "BIN: $BIN"
[ -z "$BIN" ] && { echo "✗ 找不到 ODAFileConverter 二进制"; exit 1; }

echo ""
echo "=== 3. 先看依赖全不全 ==="
ldd "$BIN" 2>&1 | grep "not found" | head -10 || echo "✓ 依赖全 OK"

echo ""
echo "=== 4. 跑 ODA CLI 转换 ==="
# AppImage 解包后通常需要把 lib/ 加入 LD_LIBRARY_PATH
RUN_DIR=$(dirname "$BIN")
LIB_DIR=$(find squashfs-root -name "libQt6Core.so.6" 2>/dev/null | head -1)
if [ -n "$LIB_DIR" ]; then
    export LD_LIBRARY_PATH="$(dirname "$LIB_DIR"):$LD_LIBRARY_PATH"
    echo "LD_LIBRARY_PATH+=$LD_LIBRARY_PATH"
fi

# 为防止 ODA 是 GUI 应用卡住：unset QT_QPA_PLATFORM，让 Qt 选默认
unset QT_QPA_PLATFORM

# ODA CLI 6 参数：in out filter version recurse audit
"$BIN" /data/dwg /data/dwg/dxf "*.dwg" "ACAD2018 DXF" 0 0 2>&1 | tail -25
echo "(exit $?)"

echo ""
echo "=== 5. 转换结果 ==="
ls -lh /data/dwg/dxf/
