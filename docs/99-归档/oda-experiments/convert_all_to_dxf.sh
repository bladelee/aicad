#!/bin/bash
# ODA File Converter 批量转换 DWG → DXF
#
# 用法（ODA 装好后）：
#   bash dwg/convert_all_to_dxf.sh
#
# ODA File Converter 是 GUI 命令行工具，调用方式特殊：
#   ODAFileConverter <input_dir> <output_dir> <ACAD_version> <retry> <audit> <flatten> [-fs <font_mapping_file>]
# 它批量转换整个目录。
#
# 参数详解：
#   input_dir / output_dir：必须是绝对路径
#   ACAD_version：输出 DXF 的版本（如 "ACAD2018/DXF"、"ACAD2013/DXF"）
#   retry/recurse（已废弃）
#   audit：0 不 audit / 1 audit
#   flatten：0 保留 / 1 flatten
#
# 输出版本选择：所有 DWG 混编（既有 R2007 又有 R2018），统一输出 ACAD2018/DXF（最高版本兼容）
# ezdxf 能读 R2018+ (DXF R2018)

set -e

ODA_APP="${ODA_FILE_CONVERTER:-/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_DIR="${SCRIPT_DIR}"
OUTPUT_DIR="${SCRIPT_DIR}/dxf"
AUDIT=0
FLATTEN=0

echo "==========================================="
echo " ODA File Converter 批量转换 DWG → DXF"
echo "==========================================="
echo ""

# 1. 验证 ODA 已就位
if [ ! -x "$ODA_APP" ]; then
    echo "✗ 找不到 ODA File Converter: $ODA_APP"
    echo "  请先装好（https://www.opendesign.com/guestfiles/oda_file_converter）"
    echo "  或自定义路径：ODA_FILE_CONVERTER=/your/path bash $0"
    exit 1
fi
echo "✓ ODA: $ODA_APP"
"$ODA_APP" --version 2>&1 | head -3 || true

# 2. 准备输出目录
mkdir -p "$OUTPUT_DIR"

# 3. 拷贝一份 DWG 到临时输入目录（只用文件名，避免 .pdf/.txt 等干扰）
TEMP_INPUT="$(mktemp -d)"
echo "✓ 临时输入: $TEMP_INPUT"
for f in "$INPUT_DIR"/*.dwg; do
    [ -f "$f" ] || continue
    cp "$f" "$TEMP_INPUT/"
done
DWG_COUNT=$(ls "$TEMP_INPUT"/*.dwg 2>/dev/null | wc -l | tr -d ' ')
echo "✓ 待转换: $DWG_COUNT 张 DWG"

echo ""
echo "==========================================="
echo " 调用 ODA（输出 ACAD2018 DXF）"
echo "==========================================="
echo ""

# ODA 输出版本：ACAD2018/DXF
"$ODA_APP" "$TEMP_INPUT" "$OUTPUT_DIR" "ACAD2018" "0" "$AUDIT" "$FLATTEN" 2>&1 | tail -30

echo ""
echo "==========================================="
echo " 转换结果"
echo "==========================================="
ls -lh "$OUTPUT_DIR"/*.dxf 2>/dev/null || echo "⚠️  无 DXF 输出"

DXF_COUNT=$(ls "$OUTPUT_DIR"/*.dxf 2>/dev/null | wc -l | tr -d ' ')
echo ""
echo "✓ 成功 $DXF_COUNT / $DWG_COUNT 张"

if [ "$DXF_COUNT" -ne "$DWG_COUNT" ]; then
    echo "⚠️  有部分转换失败，建议检查具体文件"
fi

# 4. 清理临时目录
rm -rf "$TEMP_INPUT"

echo ""
echo "DXF 文件已就位："
ls "$OUTPUT_DIR"/*.dxf 2>/dev/null
