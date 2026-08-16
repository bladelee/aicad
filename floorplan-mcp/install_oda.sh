#!/bin/bash
# ODA File Converter 合规引导安装脚本
#
# 为什么需要：DWG↔DXF 转换的事实标准，FreeCAD 内部也是用它。
#
# 为什么不打包进镜像：ODA EULA 明确禁止再分发。
# Docker 镜像若包含 ODA 即等于再分发，构成违规。
# 合规做法：终端用户自行接受 ODA EULA 并安装，再挂载进容器使用。
#
# 步骤：
#   1. 用户去 https://www.opendesign.com/guestfiles/oda_file_converter 注册下载
#   2. 选对应平台的安装包（Linux .sh / Win .exe / mac .dmg）
#   3. 本地安装到某目录（如 ~/ODAFileConverter 或 /opt/ODAFileConverter）
#   4. 在 docker-compose.yml volumes 挂载该目录：
#        - "/your/oda/install/dir:/opt/oda:ro"
#   5. 在 environment 启用：
#        ODA_FILE_CONVERTER: /opt/oda/ODAFileConverter
#   6. docker compose up

set -e
echo "==> ODA File Converter 安装引导"
echo
echo "ODA 是 DWG 转换的事实标准，但 EULA 禁止再分发，故无法打包进镜像。"
echo "请按以下步骤自行安装："
echo
echo "  1. 访问: https://www.opendesign.com/guestfiles/oda_file_converter"
echo "  2. 注册账号（免费）并下载对应平台安装包"
echo "  3. 安装到本机某目录（例如 ~/ODAFileConverter）"
echo "  4. 编辑 docker-compose.yml 挂载该目录并设置 ODA_FILE_CONVERTER 环境变量"
echo
echo "详见方案-F-容器化.md §4（合规）。"
echo
read -p "已安装好 ODA？请输入 ODA 可执行文件绝对路径（直接回车跳过）: " ODA_PATH

if [ -n "${ODA_PATH}" ] && [ -x "${ODA_PATH}" ]; then
    echo "==> 检测到: ${ODA_PATH}"
    echo "    请确保 docker-compose.yml volumes 含:"
    echo "      - \"$(dirname ${ODA_PATH}):/opt/oda:ro\""
    echo "    并设置:"
    echo "      ODA_FILE_CONVERTER: /opt/oda/$(basename ${ODA_PATH})"
else
    echo "==> 未提供有效路径，本脚本仅打印引导。完成安装后再启动容器。"
fi
