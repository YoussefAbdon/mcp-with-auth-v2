"""MCP Server for identity-api."""

import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.provider import AccessToken, TokenVerifier
from pydantic import AnyHttpUrl
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Config
# ============================================================================
OAUTH_ISSUER = "https://identity-oauth.noon.com/"
RESOURCE_SERVER_URL = "https://identity-mcp.noon.com/mcp"


# ============================================================================
# Token Verifier (passthrough - for testing only)
# ============================================================================
class PassthroughTokenVerifier(TokenVerifier):
    """Always returns a valid token - for testing only."""

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
mcp = FastMCP(
    "identity-mcp",
    # token_verifier=PassthroughTokenVerifier(),
    # auth=AuthSettings(
    #     issuer_url=AnyHttpUrl(OAUTH_ISSUER),
    #     resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
    #     required_scopes=["family_name", "picture"],
    # ),
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

