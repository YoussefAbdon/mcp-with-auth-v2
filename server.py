"""
Simple MCP Server with Auth0 OAuth Authentication
"""
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.provider import AccessToken, TokenVerifier
from pydantic import AnyHttpUrl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Hardcoded Config
# ============================================================================
AUTH0_DOMAIN = "identity-oauth.noon.com"
AUTH0_AUDIENCE = "https://web-production-8b5fa.up.railway.app/mcp"
RESOURCE_SERVER_URL = "https://web-production-8b5fa.up.railway.app/mcp"


# ============================================================================
# Token Verifier (always succeeds - for testing)
# ============================================================================
class PassthroughTokenVerifier(TokenVerifier):
    """Always returns a valid token - for deployment testing only."""

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        return AccessToken(
            token=token,
            client_id="test-client",
            scopes=["family_name", "picture"],
            expires_at=None,
            resource=RESOURCE_SERVER_URL,
        )


# ============================================================================
# MCP Server
# ============================================================================
token_verifier = PassthroughTokenVerifier()

mcp = FastMCP(
    "simple-mcp-server",
    host="0.0.0.0",
    port=8000,
    token_verifier=token_verifier,
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(f"https://{AUTH0_DOMAIN}/"),
        resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
        required_scopes=["family_name", "picture"],
    ),
)


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
        "auth": "Auth0 OIDC",
    }


if __name__ == "__main__":
    print("Starting MCP Server with Auth0 OAuth...")
    mcp.run(transport="streamable-http")
