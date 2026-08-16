#!/bin/bash
# 在已有 oda-test 镜像里手动完成 ODA 转换。
# 这是为了不依赖 Dockerfile 改动而做的"调试版"。
# 用法（宿主机）:
#   docker run --rm -v "$PWD:/data" --entrypoint=/bin/bash oda-test /data/dwg/run_oda.sh
set -e
set -x  # 调试模式，每条命令都打印

# === 1. libxcb-util soname 修复（Ubuntu22=so.1, ODA 写死 so.0）===
if [ ! -e /usr/lib/x86_64-linux-gnu/libxcb-util.so.0 ] && [ -e /usr/lib/x86_64-linux-gnu/libxcb-util.so.1 ]; then
    ln -sf /usr/lib/x86_64-linux-gnu/libxcb-util.so.1 /usr/lib/x86_64-linux-gnu/libxcb-util.so.0
    echo "✓ libxcb-util.so.0 symlink 建好"
fi

# === 2. 安装 xvfb（原 oda-test 镜像没装）===
echo "--- apt update + xvfb ---"
apt-get update -qq 2>&1 | tail -2
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xvfb 2>&1 | tail -2

# === 3. 卸掉我们曾经错设的 QT_QPA_PLATFORM ===
unset QT_QPA_PLATFORM

# === 4. 先看 ODA 自带的 xcb 插件能否在 Xvfb 下加载 ===
echo "--- 测试 ODA 启动 ---"
xvfb-run -a -s "-screen 0 1024x768x24" ODAFileConverter --help 2>&1 | head -10 || echo "(--help 退出 $?)"
echo ""

# === 5. 真刀真枪跑批量转换（6 个官方 CLI 参数）===
mkdir -p /data/dwg/dxf
echo "--- 执行批量转换 ---"
xvfb-run -a -s "-screen 0 1024x768x24" ODAFileConverter /data/dwg /data/dwg/dxf "*.dwg" "ACAD2018 DXF" 0 0 2>&1 | tail -25
echo "(退出 $?)"

# === 6. 结果 ===
echo ""
echo "--- 转换结果 ---"
ls -lh /data/dwg/dxf/
