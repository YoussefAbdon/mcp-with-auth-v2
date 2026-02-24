"""
Simple MCP Server with Auth0 OAuth Authentication
"""
import logging
import asyncio
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.provider import AccessToken, TokenVerifier
from pydantic import AnyHttpUrl
from jwt import PyJWKClient, decode, InvalidTokenError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Hardcoded Config
# ============================================================================
AUTH0_DOMAIN = "identity-oauth.noon.com"
AUTH0_AUDIENCE = "https://web-production-8b5fa.up.railway.app/mcp"
RESOURCE_SERVER_URL = "https://web-production-8b5fa.up.railway.app/mcp"


# ============================================================================
# Auth0 Token Verifier
# ============================================================================
class Auth0TokenVerifier(TokenVerifier):
    """Verifies OAuth tokens issued by Auth0."""

    def __init__(self, domain: str, audience: str):
        self.domain = domain
        self.audience = audience
        self.algorithms = ["RS256"]
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self.issuer = f"https://{domain}"
        self.jwks_client = PyJWKClient(self.jwks_url)

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        try:
            signing_key = await asyncio.to_thread(
                self.jwks_client.get_signing_key_from_jwt, token
            )
            payload = decode(
                token,
                signing_key.key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iat": True,
                    "verify_exp": True,
                    "verify_iss": True,
                },
            )
            scopes = []
            if "scope" in payload:
                scopes = payload["scope"].split()
            elif "permissions" in payload:
                scopes = payload["permissions"]

            return AccessToken(
                token=token,
                client_id=payload.get("azp") or payload.get("client_id", "unknown"),
                scopes=scopes,
                expires_at=payload.get("exp"),
                resource=self.audience,
            )
        except InvalidTokenError as e:
            logger.error(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None


# ============================================================================
# MCP Server
# ============================================================================
token_verifier = Auth0TokenVerifier(domain=AUTH0_DOMAIN, audience=AUTH0_AUDIENCE)

mcp = FastMCP(
    "simple-mcp-server",
    host="0.0.0.0",
    port=8000,
    token_verifier=token_verifier,
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(f"https://{AUTH0_DOMAIN}"),
        resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
        required_scopes=["profile:write", "email:read", "address:read"],
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
