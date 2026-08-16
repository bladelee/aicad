#!/bin/bash
# Qt xcb 插件加载失败的根因诊断（开 QT_DEBUG_PLUGINS=1）
set -e

# symlink + 装 xvfb（一次到位）
ln -sf /usr/lib/x86_64-linux-gnu/libxcb-util.so.1 /usr/lib/x86_64-linux-gnu/libxcb-util.so.0 || true
apt-get update -qq 2>&1 | tail -2
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xvfb 2>&1 | tail -2

# 找 ODA 自带的 Qt 插件目录
echo "=== 1. 找 Qt xcb 插件位置 ==="
find /usr -name "libqxcb*" 2>/dev/null | head -5

echo ""
echo "=== 2. ldd 看 xcb 插件缺哪些库 ==="
XCB_PLUGIN=$(find /usr -name "libqxcb.so" 2>/dev/null | head -1)
echo "xcb 插件路径：$XCB_PLUGIN"
if [ -n "$XCB_PLUGIN" ]; then
    ldd "$XCB_PLUGIN" 2>&1 | grep -E "not found|=>" | head -20
fi

echo ""
echo "=== 3. 看 ODAFileConverter_27.1.0.0 目录里的 Qt 插件配置 ==="
ls /usr/bin/ODAFileConverter_27.1.0.0/platforms/ 2>/dev/null || true
ls /usr/bin/ODAFileConverter_27.1.0.0/platformplugins/ 2>/dev/null || true
ls /usr/bin/ODAFileConverter_27.1.0.0/plugins/ 2>/dev/null || true
ls /usr/bin/ODAFileConverter_27.1.0.0/plugins/platforms/ 2>/dev/null || true

echo ""
echo "=== 4. 用 QT_DEBUG_PLUGINS=1 让 Qt 自己说为啥不行 ==="
export QT_DEBUG_PLUGINS=1
export QT_QPA_PLATFORM=xcb
unset QT_QPA_PLATFORM
xvfb-run -a -s "-screen 0 1024x768x24" ODAFileConverter 2>&1 | grep -E "xcb|loaded|loaded library|Cannot|cannot|This application|not find" | head -25
