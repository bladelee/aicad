#!/bin/bash
# 在 ubuntu 容器里从 PPA 装 libredwg 并测试转换（不需要 ODA）。
# 用法（宿主机）:
#   docker run --rm -v "$PWD/dwg:/data" -v "$PWD/test_libredwg.sh:/test.sh:ro" \
#       --entrypoint=/bin/bash ubuntu:22.04 -lc "bash /test.sh"
set -e

echo "=== APT 准备 ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq software-properties-common wget gnupg lsb-release 2>&1 | tail -2

# libredwg 团队提供 PPA，但只针对 Ubuntu。我们用源码编译更通用。
echo ""
echo "=== 装编译依赖 ==="
apt-get install -y -qq \
    build-essential git autoconf automake libtool texinfo \
    pkg-config python3 swig pcre2-utils libpcre2-dev libxslt1-dev 2>&1 | tail -2

echo ""
echo "=== clone libredwg 源码 ==="
cd /opt
# 用 GitHub mirror（更快）
git clone --depth 1 https://github.com/LibreDWG/libredwg.git 2>&1 | tail -2

cd libredwg
echo ""
echo "=== autoreconf ==="
sh autogen.sh 2>&1 | tail -3

echo ""
echo "=== configure ==="
./configure --disable-shared --enable-write >/tmp/cfg.log 2>&1 && echo "configure OK" || (tail -10 /tmp/cfg.log; exit 1)

echo ""
echo "=== make (并行) ==="
MAKE_FLAGS="-j$(nproc)"
make $MAKE_FLAGS >/tmp/make.log 2>&1 && echo "make OK" || (tail -20 /tmp/make.log; exit 1)
make install >/tmp/install.log 2>&1 || (tail -5 /tmp/install.log; exit 1)
ldconfig

echo ""
echo "=== 验证 dwg2dxf ==="
which dwg2dxf
dwg2dxf --version 2>&1 | head -3 || true

echo ""
echo "=== 测试转换 5 张 DWG ==="
mkdir -p /data/dxf_out
for f in /data/*.dwg; do
    name=$(basename "$f" .dwg)
    out="/data/dxf_out/${name}.dxf"
    echo ""
    echo "--- $name ---"
    dwg2dxf -y -o "$out" "$f" 2>&1 | tail -3 || echo "失败"
    if [ -f "$out" ]; then
        echo "✓ 成功: $out ($(wc -c < "$out") 字节)"
    fi
done

echo ""
echo "=== 最终 DXF 输出 ==="
ls -lh /data/dxf_out/
