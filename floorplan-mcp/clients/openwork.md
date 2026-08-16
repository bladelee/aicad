# OpenWork 客户端配置（MVP — stdio 单通道，绕过 OAuth）

> 前提：Docker Desktop 已装、floorplan-mcp 容器已 `docker compose up`（容器名 floorplan-mcp）。

## 标准路径：Settings > Extensions > Add Custom App

1. 打开 OpenWork Desktop
2. `Settings` → `Extensions` → `Add Custom App` → 高级模式（Advanced）
3. 填本地 stdio server：

   ```
   Name: floorplan
   Command: docker
   Args: exec -i floorplan-mcp python /opt/floorplan/mcp_server_stdio.py
   ```

4. **不要勾** "Requires OAuth"（我们是本地 stdio，无须 OAuth）
5. 保存

## 接 LLM provider

OpenWork `Settings`：
- "Sign in with ChatGPT"（OpenWork 原生支持）—— 海外/有 ChatGPT 账号
- 或自带 LLM API key：`Settings > LLM Providers > Add` 选 Anthropic/OpenAI/...

## 验证

```bash
./scripts/check_stdio_server.sh   # 测容器内 stdio server 能跑
```

## 已知限制（MVP）

- OpenWork 默认推荐的是 **远程 HTTPS server + OAuth**（"Add Custom App"对应远程模式），
  本地 stdio 是高级用法。**MVP 走 stdio 绕开 OAuth**（产品 Spec §5.4 决策）。
- Phase 1.5 加 streamable_http 后，OpenWork 可切到远程 HTTPS 模式，体验更主线。
