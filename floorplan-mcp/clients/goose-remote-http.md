# Goose 远程连接配置（v0.3 服务器形态）

> 适用：floorplan-mcp 容器部署在公司 Linux 服务器（`docker compose --profile server up -d`），设计师 Windows/Mac 上的 Goose 通过 HTTP 连。

## 服务器端（IT 一次性，5 分钟）

```bash
# 1. 服务器上拉镜像（需 ghcr 凭证，见 ../docs/01-产品/客户部署使用手册.md）
echo <PAT> | docker login ghcr.io -u bladelee --password-stdin
docker pull ghcr.io/bladelee/floorplan-mcp:v0.3.0

# 2. 生成鉴权 token（发给每位设计师的就是这个）
export FLOORPLAN_AUTH_TOKEN=$(openssl rand -hex 24)
echo "TOKEN: $FLOORPLAN_AUTH_TOKEN"   # 存好，发给设计师

# 3. 起服务（仓库 floorplan-mcp/ 目录下）
cd floorplan-mcp/
FLOORPLAN_AUTH_TOKEN=$FLOORPLAN_AUTH_TOKEN docker compose --profile server up -d

# 4. 防火墙放行 3000（仅公司内网来源）
sudo ufw allow from 10.0.0.0/8 to any port 3000 proto tcp
```

## 设计师端（每人 2 分钟）

Goose → Settings → Extensions → Add MCP Server → Advanced/JSON，粘贴：

```json
{
  "mcpServers": {
    "floorplan": {
      "type": "remote",
      "url": "http://<服务器IP>:3000/sse",
      "headers": {
        "Authorization": "Bearer <IT 发你的 token>"
      }
    }
  }
}
```

保存后 Goose 会自动连上，工具列表里出现 `user_move_wall`、`user_rename_material` 等 11 个装修工具 + 53 个 FreeCAD 工具。

## 验证一句话

> 把测试图里第一堵墙右移 500mm

AI 会调用 `user_move_wall`，输出 JSON 里 `output` 字段就是改后的 DXF 路径（服务器 `/data` 即共享盘 `~/dwgs`）。

## 安全说明

- **Bearer Token 必配**：不带 token 的请求 → 401（服务器拒绝裸奔部署，`FLOORPLAN_AUTH_TOKEN` 未设置时容器直接拒绝启动）
- 图纸目录 `/data` = 服务器 `~/dwgs`（建议按设计师分子目录，当前版本所有人共享同一目录树）
- token 轮换：改服务器 env 里的 `FLOORPLAN_AUTH_TOKEN` 后 `docker compose restart`，设计师同步换 headers

## 常见问题

| 现象 | 处理 |
|------|------|
| Goose 连不上 | 先 `curl -H "Authorization: Bearer <t>" http://<ip>:3000/sse` 看是否 401/超时（防火墙/token）|
| 401 | token 不对或没带 `Bearer ` 前缀 |
| 改完的图在哪 | 服务器 `~/dwgs/`（容器 `/data`），文件名带 `_moved` 等后缀 |
