#!/bin/bash
# 在原 oda-test 镜像里手动修补缺失的依赖（libxkbcommon-x11-0, libxcb-xkb0）
# 并跑 ODA 批量转换。
set -e
set -x

# === 1. 安装 Qt xcb 插件真正缺的 2 个库（根因诊断结论）===
apt-get update -qq 2>&1 | tail -2
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    libxkbcommon-x11-0 libxcb-xkb1 2>&1 | tail -3

# === 2. 确认 ODA 自带 xcb 插件依赖全部就位 ===
echo ""
echo "--- 验证 libqxcb.so 所有依赖都解析 ==="
ldd /usr/bin/ODAFileConverter_27.1.0.0/plugins/platforms/libqxcb.so 2>&1 | grep "not found" || echo "✓ 所有依赖就位"

# === 3. unset 之前可能错设的 QT_QPA_PLATFORM ===
unset QT_QPA_PLATFORM

# === 4. 实测转换 ===
mkdir -p /data/dwg/dxf
echo ""
echo "--- 执行 ODA 批量转换（Xvfb 虚拟显示）---"
xvfb-run -a -s "-screen 0 1024x768x24" \
    ODAFileConverter /data/dwg /data/dwg/dxf "*.dwg" "ACAD2018 DXF" 0 0 2>&1 | tail -30

echo ""
echo "--- 转换结果 ---"
ls -lh /data/dwg/dxf/
