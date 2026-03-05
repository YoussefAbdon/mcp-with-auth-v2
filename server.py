"""MCP server for simple-mcp."""

import os
from typing import Annotated
from urllib.parse import urlencode

from fastmcp import FastMCP
from pydantic import Field
from starlette.responses import PlainTextResponse, RedirectResponse

mcp = FastMCP("simple-mcp")


@mcp.custom_route("/public/hc", methods=["GET"])
async def health_check(request):
    return PlainTextResponse("OK")


@mcp.custom_route("/inspector", methods=["GET"])
async def inspector_redirect(request):
    if os.getenv("ENV") not in ("dev", "local"):
        return PlainTextResponse("Not available", status_code=404)

    service_name = os.getenv("SERVICE_NAME", "localhost")
    server_url = f"http://{service_name}/mcp"
    params = urlencode(
        {
            "transport": "streamable-http",
            "serverUrl": server_url,
            "MCP_PROXY_FULL_ADDRESS": "https://mcp-inspector.noondv.com/proxy",
        }
    )
    return RedirectResponse(f"https://mcp-inspector.noondv.com/?{params}")


@mcp.tool()
def add(
    a: Annotated[int, Field(description="First number.")],
    b: Annotated[int, Field(description="Second number.")],
) -> int:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def multiply(
    a: Annotated[int, Field(description="First number.")],
    b: Annotated[int, Field(description="Second number.")],
) -> int:
    """Multiply two numbers together."""
    return a * b


@mcp.tool()
def greet(
    name: Annotated[str, Field(description="Name to greet.")],
) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


@mcp.tool()
def get_server_info() -> dict:
    """Get information about this MCP server."""
    return {"name": "simple-mcp", "version": "1.0.0", "status": "running"}


app = mcp.http_app(stateless_http=True)
