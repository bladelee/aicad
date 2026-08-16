#!/bin/bash
# 容器 entrypoint：把我们的 user_tools 链接进 freecad-ai 的发现目录，
# 然后启动 freecad-ai 的 SSE MCP server（同时把 FreeCAD 跑在同一个进程）。
#
# 调用方式（来自 docker compose）:
#   docker run -v ~/dwgs:/data -p 3000:3000 floorplan-mcp
#
# Phase 0 我们要验证的两件事（见 方案-F2 §1）:
#   1. FreeCAD -c headless 能 import freecad-ai + 跑 mcp_server_http.py
#   2. 我们的 user_tools 被自动发现

set -e

# ── C4-δ：透传 CLI 子命令 ──
# 支持三种形态：
#   docker run floorplan-mcp move-wall ...          （CLI 子命令，推荐）
#   docker run floorplan-mcp floorplan move-wall ... （容错，重复前缀自动去掉）
#   docker run floorplan-mcp /opt/FreeCAD/usr/bin/python -m pytest ...
#                                                    （绝对路径 = 任意命令直 exec）
# 无参数 / serve → 保持原 MCP 常驻行为
if [ "$#" -gt 0 ] && [ "$1" != "serve" ]; then
    case "$1" in
        /*|./*) exec "$@" ;;                      # 绝对/相对路径：原样 exec
        floorplan) shift; exec floorplan "$@" ;;  # 容错重复前缀
        *) exec floorplan "$@" ;;                  # CLI 子命令透传
    esac
fi

TOOLS_DIR="${HOME}/.config/FreeCAD/FreeCADAI/tools"
mkdir -p "${TOOLS_DIR}"

echo "==> backend: ${FLOORPLAN_BACKEND:-freecad}"
echo "==> transport: stdio (MVP 默认；streamable_http 待 Phase 1.5)"
echo "==> user_tools dir: ${TOOLS_DIR}"

# MVP 单 stdio 通道：容器常驻供 docker exec 调用
# 客户端配置（Goose/OpenWork）见 clients/*.md，是
#   docker exec -i floorplan-mcp python /opt/floorplan/mcp_server_stdio.py
# 这里一开始先睡住，撑住容器运行（docker exec 会另起进程跑 stdio server）
echo "==> 容器已就绪，等待 docker exec 拉起 stdio server"

# 引导用户安装 ODA（详见 install_oda.sh；MVP 默认不阻塞，仅打印提示）
if ! command -v ODAFileConverter >/dev/null 2>&1 \
        && [ -z "${ODA_FILE_CONVERTER}" ]; then
    echo "==> [提示] 未检测到 ODA File Converter。"
    echo "    DWG↔DXF 转换将不可用。请按 /opt/install_oda.sh 引导安装，"
    echo "    然后通过 -v <oda_dir>:/opt/oda 挂载进容器并设 ODA_FILE_CONVERTER。"
fi

# 容器保持运行（MVP：不在此进程直接跑 stdio server，由客户端 docker exec 拉起）
# 后续若要 streamable_http Phase 1.5，再在此分支启动 HTTP server
tail -f /dev/null
