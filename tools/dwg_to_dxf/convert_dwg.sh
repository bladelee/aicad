#!/bin/bash
# 用 libredwg-cli Docker 镜像批量转换 DWG → DXF
#
# 用法：
#   cd /Users/bladelee/project/cad
#   bash tools/dwg_to_dxf/convert_dwg.sh samples/19-102 workdir/19-102/dxf
#
# 前置：libredwg-cli 镜像已构建
#   docker build -f tools/dwg_to_dxf/Dockerfile.libredwg -t libredwg-cli tools/dwg_to_dxf/
#
# 输入：
#   $1 = SOURCE_DIR（含 *.dwg，默认 samples/19-102）
#   $2 = OUT_DIR    （输出 .dxf，默认 workdir/19-102/dxf）

set -e

IN="${1:-samples/19-102}"
OUT="${2:-workdir/19-102/dxf}"

if [ ! -d "$IN" ]; then
    echo "✗ 源目录不存在: $IN"
    exit 1
fi

# 检查 docker 镜像
if ! docker images libredwg-cli --format "{{.Repository}}" | grep -q libredwg-cli; then
    echo "✗ libredwg-cli 镜像不存在，请先 build："
    echo "  docker build -f tools/dwg_to_dxf/Dockerfile.libredwg -t libredwg-cli tools/dwg_to_dxf/"
    exit 1
fi

mkdir -p "$OUT"

# 找所有 .dwg
DWG_COUNT=$(find "$IN" -maxdepth 1 -name "*.dwg" | wc -l | tr -d ' ')
if [ "$DWG_COUNT" -eq 0 ]; then
    echo "✗ $IN 下无 .dwg 文件"
    exit 1
fi

echo "=== 开始转换 $DWG_COUNT 张 DWG （$(date)）==="
echo ""

for f in "$IN"/*.dwg; do
    name=$(basename "$f" .dwg)
    echo "→ $name.dwg"
    docker run --rm -v "$PWD:/data" libredwg-cli \
        -y -o "/data/$OUT/${name}.dxf" "/data/$f" 2>&1 \
        | grep -E "Reading|Writing|Error|error" | head -5
done

echo ""
echo "✓ 完成 $(date)"
echo "=== 输出 ==="
ls -lh "$OUT"
