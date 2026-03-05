"""MCP Server for identity-api."""

import logging

from mcp.server.fastmcp import FastMCP
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# MCP Server
# ============================================================================
mcp = FastMCP("identity-mcp")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers together."""
    return a * b


@mcp.tool()
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


@mcp.tool()
def get_server_info() -> dict:
    """Get information about this MCP server."""
    return {"name": "identity-mcp", "version": "1.0.0", "status": "running"}


# ============================================================================
# ASGI middleware - intercepts /public/hc, passes everything else (including
# lifespan events) straight through to the MCP app.
# ============================================================================
class HealthCheckMiddleware:
    def __init__(self, asgi_app: ASGIApp) -> None:
        self.app = asgi_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == "/public/hc":
            await PlainTextResponse("OK")(scope, receive, send)
        else:
            await self.app(scope, receive, send)


app = HealthCheckMiddleware(mcp.streamable_http_app())
