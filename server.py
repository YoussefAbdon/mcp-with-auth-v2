"""
Simple MCP Server - No Authentication (for deployment testing)
"""
import logging
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# MCP Server
# ============================================================================
mcp = FastMCP(
    "simple-mcp-server",
    host="0.0.0.0",
    port=8000,
)


@mcp.resource("demo://ping")
def ping() -> str:
    """Simple ping resource."""
    return "pong"


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
    return f"Hello, {name}! Welcome to the MCP server."


@mcp.tool()
def get_server_info() -> dict:
    """Get information about this MCP server."""
    return {
        "name": "simple-mcp-server",
        "version": "1.0.0",
        "status": "running",
        "tools": ["add", "multiply", "greet", "get_server_info"],
        "resources": ["demo://ping"]
    }


# ============================================================================
# Main
# ============================================================================
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          Simple MCP Server                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  MCP Server - Ready for deployment                                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

Available Tools:
  • add(a, b)           - Add two numbers
  • multiply(a, b)      - Multiply two numbers
  • greet(name)         - Greet someone
  • get_server_info()   - Get server information

Available Resources:
  • demo://ping         - Simple ping resource

Starting server...
""")

    mcp.run(transport='streamable-http')
