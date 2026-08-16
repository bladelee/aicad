# Goose 客户端配置（MVP — stdio 单通道）

> 前提：Docker Desktop 已装、floorplan-mcp 容器已 `docker compose up`（容器名 floorplan-mcp）。

## 方式 1：Desktop 配置文件

`~/.config/goose/config.yaml`（macOS/Linux）或 Windows 等价路径，加：

```yaml
extensions:
  floorplan:
    type: stdio
    name: floorplan
    description: 装修图 MCP 工具：读/查/改/导出 DWG/DXF
    cmd: docker
    args:
      - exec
      - "-i"
      - floorplan-mcp
      - python
      - /opt/floorplan/mcp_server_stdio.py
    timeout: 300
```

然后重启 Goose Desktop。对话里说"看一下 ~/dwgs/客厅.dwg"即可。

## 方式 2：CLI

```bash
# 装 goose CLI（https://github.com/aaif-goose/goose）
curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh | bash

# 在 ~/.config/goose/config.yaml 加同上 extensions 块，或用 session:
goose session
# 进入会话后说：看一下 /data/客厅.dwg（容器内路径）
```

## 接 LLM provider（Goose 多 provider，国内友好）

`config.yaml` 顶层加 provider（任选）：

```yaml
# Anthropic
provider:
  type: anthropic
  api_key: ${ANTHROPIC_API_KEY}
  model: claude-sonnet-4.5

# 或 Ollama（本地，免费、国内友好）
# provider:
#   type: ollama
#   model: qwen2.5:32b
```

## 验证

```bash
./scripts/check_stdio_server.sh   # 测容器内 stdio server 能跑
```
