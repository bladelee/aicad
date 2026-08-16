#!/bin/bash
# 验证 floorplan-mcp 容器内 stdio server 能跑通（无需真实 MCP 客户端）。
#
# 用法（容器已起后）：
#   ./floorplan-mcp/scripts/check_stdio_server.sh
#
# 它向容器送一个 MCP initialize 请求，看是否回合法 JSON-RPC。

set -e

CONTAINER="${FLOORPLAN_CONTAINER:-floorplan-mcp}"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "❌ 容器 ${CONTAINER} 未运行。先 cd floorplan-mcp && docker compose up -d"
    exit 1
fi

# MCP initialize 请求（一行 JSON-RPC）
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"check","version":"0.0.1"}}}'

echo "==> 发 initialize 到 ${CONTAINER} ..."
echo "看返回里有没有 serverInfo.floorplan 字样（证明跑到我们的 stdio server）"

# 容器内启动 stdio server，stdin 喂 INIT
RESULT=$(echo "${INIT}" | docker exec -i "${CONTAINER}" \
    python /opt/floorplan/mcp_server_stdio.py 2>/dev/null | head -1 || true)

if echo "${RESULT}" | grep -q '"jsonrpc"'; then
    echo "✓ stdio server 返回合法 JSON-RPC:"
    echo "${RESULT}" | head -c 400
    echo ""
    if echo "${RESULT}" | grep -qi 'floorplan\|FreeCAD'; then
        echo "✓ 已注册 freecad-ai 服务"
    fi
    exit 0
else
    echo "❌ 没拿到合法 JSON-RPC，原始输出前 400 字:"
    echo "${RESULT}" | head -c 400
    exit 2
fi
