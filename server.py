"""MCP Server for identity-api."""

import logging

from fastmcp import FastMCP
from starlette.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# MCP Server
# ============================================================================
mcp = FastMCP("identity-mcp")


@mcp.custom_route("/public/hc", methods=["GET"])
async def health_check(_):
    return PlainTextResponse("OK")


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


app = mcp.http_app()

if __name__ == "__main__":
    mcp.run()
