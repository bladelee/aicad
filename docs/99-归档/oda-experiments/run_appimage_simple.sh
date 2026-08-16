#!/bin/bash
# AppImage 版 ODA 转换（extract 模式，避开 fuse 依赖）
set -e

echo "=== apt 装依赖（含 Xvfb）==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq 2>&1 | tail -1
apt-get install -y -qq \
    ca-certificates \
    libgl1 libglu1-mesa libxkbcommon0 libxkbcommon-x11-0 libxcb-xkb1 \
    libdbus-1-3 libxcb-cursor0 libfontconfig1 \
    xvfb xauth 2>&1 | tail -2

unset QT_QPA_PLATFORM QT_QPA_PLATFORM_PLUGIN_PATH

echo ""
echo "=== extract AppImage（解包后直接跑，不需要 fuse）==="
chmod +x /data/dwg/oda_pkg/oda.AppImage
mkdir -p /tmp/odawork && cd /tmp/odawork
if [ ! -d squashfs-root ]; then
    /data/dwg/oda_pkg/oda.AppImage --appimage-extract >/dev/null 2>&1
fi
echo "extract 完，squashfs-root 顶层:"
ls squashfs-root/ | head -8

# 找 AppRun（AppImage 标准入口）或 ODAFileConverter
APPRUN="squashfs-root/AppRun"
if [ ! -x "$APPRUN" ]; then
    APPRUN=$(find squashfs-root -name "ODAFileConverter" -type f 2>/dev/null | head -1)
fi
echo "APPRUN=$APPRUN"
[ -z "$APPRUN" ] && { echo "✗ 找不到可执行入口"; exit 1; }

echo ""
echo "=== 启动 Xvfb（避开 xcb must connect display 问题）==="
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
Xvfb :1 -screen 0 1024x768x24 -nolisten tcp -ac &
XVFB_PID=$!
sleep 2
export DISPLAY=:1
export XAUTHORITY=

echo ""
echo "=== 跑 ODA 转换（6 个官方 CLI 参数）==="
cd /tmp/odawork
"$APPRUN" /data/dwg /data/dwg/dxf "*.dwg" "ACAD2018 DXF" 0 0 2>&1 | tail -25
EXIT=$?
echo "(ODA exit=$EXIT)"

kill $XVFB_PID 2>/dev/null || true

echo ""
echo "=== DXF 结果 ==="
ls -lh /data/dwg/dxf/
