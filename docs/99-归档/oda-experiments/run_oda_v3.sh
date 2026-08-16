#!/bin/bash
# 正确姿势：手动启 Xvfb 在固定 DISPLAY :99，再传给子进程，让 ODA 拿得到鉴权。
set -e
unset QT_QPA_PLATFORM

# 1. 删老 socket 残留
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99

# 2. 启 Xvfb 在 :99（关闭鉴权 -ac，最简）
echo "--- start Xvfb :99 ---"
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp -ac &
XVFB_PID=$!
sleep 2

# 3. 验证 X 服务真活着
export DISPLAY=:99
export XAUTHORITY=
echo "DISPLAY=$DISPLAY"

# 4. 跑 ODA
echo "--- run ODA ---"
ODAFileConverter /data/dwg /data/dwg/dxf "*.dwg" "ACAD2018 DXF" 0 0 2>&1 | tail -25 || true
echo "(exit $?)"

# 5. 杀 Xvfb
kill $XVFB_PID 2>/dev/null || true

# 6. 结果
echo ""
echo "--- result ---"
ls -lh /data/dwg/dxf/
