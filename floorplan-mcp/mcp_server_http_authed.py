"""floorplan-mcp 的 HTTP/SSE server 入口（v0.3 — 容器上服务器形态）。

复用 freecad-ai 的 SSEServerTransport + MCPServer，叠加：
  1. Bearer Token 鉴权（子类化注入，不改上游）
  2. 我们的两个 user_tools 文件（floorplan_tools + mcp_renovation_tools）
  3. headless FreeCAD（容器内 offscreen，无 GUI 线程跳板 → 直接线程执行器）

客户端（Goose）配置：
    {
      "mcpServers": {
        "floorplan": {
          "type": "remote",
          "url": "http://<server>:3000/sse",
          "headers": { "Authorization": "Bearer <FLOORPLAN_AUTH_TOKEN>" }
        }
      }
    }

环境变量：
    MCP_HOST            — 监听地址（默认 0.0.0.0，服务器形态要远程可达）
    MCP_PORT            — 端口（默认 3000）
    FLOORPLAN_AUTH_TOKEN — 必填鉴权 token（不设置则拒绝启动：暴露公网零鉴权太危险）
                          多人共享场景：inner-office 每人发一个，或全体共用一个（v0.3 简化）

跑法（容器内）：
    docker run -d -p 3000:3000 -v ~/dwgs:/data \
      -e FLOORPLAN_AUTH_TOKEN=<secret> \
      ghcr.io/bladelee/floorplan-mcp:v0.3.0 serve-http
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ── 路径引导（容器 / 宿主仓库直跑皆可）──
for _root in ("/opt/floorplan", "/opt/aicad", "/opt/freecad-ai",
              str(Path(__file__).resolve().parents[2])):
    if Path(_root).is_dir() and _root not in sys.path:
        sys.path.insert(0, _root)


def main() -> int:
    token = os.environ.get("FLOORPLAN_AUTH_TOKEN", "")
    if not token:
        print("FATAL: FLOORPLAN_AUTH_TOKEN 未设置。", file=sys.stderr)
        print("  HTTP 形态必须带鉴权（零鉴权暴露改图能力 = 任何人可删改图纸）。", file=sys.stderr)
        print("  生成建议: openssl rand -hex 24", file=sys.stderr)
        return 2

    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "3000"))

    # 1. 链接 user_tools（与 stdio 入口同一套逻辑）
    from mcp_server_stdio import link_user_tools  # type: ignore
    linked = link_user_tools()
    print(f"[floorplan-http] user_tools linked: {[p.name for p in linked]}",
          file=sys.stderr)

    # 2. headless FreeCAD + registry
    import FreeCAD  # noqa
    if not FreeCAD.ActiveDocument:
        FreeCAD.newDocument("Unnamed")

    from freecad_ai.tools.setup import create_default_registry
    registry = create_default_registry(include_mcp=False)
    names = [t.name for t in registry.list_tools()]
    print(f"[floorplan-http] registered tools ({len(names)}): "
          f"{[n for n in names if n in ('move_wall', 'rename_material', 'probe_dimensions', 'read_floorplan')]}",
          file=sys.stderr)

    # 3. transport：子类注入 Bearer 鉴权（上游只有 Host/Origin 白名单，不够公网用）
    from freecad_ai.mcp.transport import SSEServerTransport

    class AuthedSSETransport(SSEServerTransport):
        """在 _request_allowed 基础上叠加 Authorization: Bearer 校验。

        401（而非 403）区分"没带凭证"与"Origin 不对"，方便客户端排障。
        """

        def _check_bearer(self, headers) -> bool:
            auth = headers.get("Authorization", "")
            return auth == f"Bearer {token}"

    # 上游 RequestHandler 在 _authorized() 里调 transport._request_allowed(host, origin)，
    # 不带 headers — 所以把 token 校验塞进 _request_allowed（拿不到原 headers，
    # 但 handler 的 self.headers 不可达）→ 更稳的注入点：包 _make_server 的 handler。
    # 这里采用最小侵入：monkey-patch 类的 _request_allowed 保持上游行为，
    # 真正校验在下面 RequestHandler 层做。

    orig_make_server = AuthedSSETransport._make_server

    def _make_server_with_auth(self):
        server = orig_make_server(self)

        # 找到上游构造的 handler 类，包一层 do_GET/do_POST 前置校验
        handler_cls = server.RequestHandlerClass

        def with_auth(method_name):
            orig = getattr(handler_cls, method_name)

            def wrapped(self_handler):
                if not self._check_bearer(self_handler.headers):
                    self_handler.send_response(401)
                    self_handler.send_header(
                        "WWW-Authenticate", 'Bearer realm="floorplan-mcp"')
                    self_handler.end_headers()
                    return
                return orig(self_handler)

            return wrapped

        handler_cls.do_GET = with_auth("do_GET")
        handler_cls.do_POST = with_auth("do_POST")
        return server

    AuthedSSETransport._make_server = _make_server_with_auth

    # 4. 起服务（阻塞）
    from freecad_ai.mcp.server import MCPServer
    transport = AuthedSSETransport(host=host, port=port)
    server = MCPServer(registry, transport=transport)
    print(f"[floorplan-http] SSE server on http://{host}:{port}/sse "
          f"(auth: Bearer token, {len(token)} chars)", file=sys.stderr)
    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
