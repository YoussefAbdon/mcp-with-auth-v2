"""
MCP Server with Auth0 Authentication - MCP Inspector Compatible (FIXED)

This server is designed to work with the MCP Inspector OAuth flow.
"""
import asyncio
import httpx
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from jwt import PyJWKClient, decode, exceptions as jwt_exceptions
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, RedirectResponse
from starlette.routing import Route, Mount

from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp.server.auth.settings import AuthSettings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================
AUTH0_DOMAIN = "dev-bm0upkhxllrygh78.us.auth0.com"
AUTH0_AUDIENCE = "https://overdiverse-avowably-julio.ngrok-free.dev"

# Your public server URL
PUBLIC_BASE_URL = "https://overdiverse-avowably-julio.ngrok-free.dev"

# Auth0 URLs
ISSUER = f"https://{AUTH0_DOMAIN}/"
JWKS_URL = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
AUTH0_OPENID_CONFIG = f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration"


# ============================================================================
# Token Verifier
# ============================================================================
class Auth0TokenVerifier(TokenVerifier):
    def __init__(self):
        self.jwks_client = PyJWKClient(JWKS_URL, cache_keys=True)
        logger.info(f"Token verifier initialized for Auth0 domain: {AUTH0_DOMAIN}")

    async def verify_token(self, token: str) -> AccessToken | None:
        logger.debug(f"Verifying token...")
        try:
            signing_key = await asyncio.to_thread(
                self.jwks_client.get_signing_key_from_jwt,
                token,
            )

            payload = decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=AUTH0_AUDIENCE,
                issuer=ISSUER,
            )

            logger.info(f"Token verified for client: {payload.get('azp', 'unknown')}")
            return AccessToken(
                token=token,
                client_id=payload.get("azp", payload.get("sub", "unknown")),
                scopes=payload.get("scope", "").split() if payload.get("scope") else [],
                expires_at=payload.get("exp"),
                resource=AUTH0_AUDIENCE,
            )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None


# ============================================================================
# OAuth Endpoints - Facade to Auth0
# ============================================================================

# Cache for Auth0's OIDC configuration
_auth0_config_cache = None


async def get_auth0_config():
    """Fetch and cache Auth0's OpenID configuration."""
    global _auth0_config_cache
    if _auth0_config_cache is None:
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Fetching Auth0 config from: {AUTH0_OPENID_CONFIG}")
                response = await client.get(AUTH0_OPENID_CONFIG, timeout=10.0)
                response.raise_for_status()
                _auth0_config_cache = response.json()
                logger.info(f"Successfully fetched Auth0 config: {_auth0_config_cache.get('issuer')}")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching Auth0 config: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Auth0 config: {e}")
            raise
    return _auth0_config_cache


async def oauth_authorization_server_metadata(request: Request) -> Response:
    """
    RFC 8414 - OAuth 2.0 Authorization Server Metadata
    
    The MCP Inspector requests this endpoint to discover OAuth endpoints.
    """
    logger.info(f"GET /.well-known/oauth-authorization-server from {request.client}")
    
    try:
        # Get Auth0's OpenID configuration
        auth0_config = await get_auth0_config()
        
        # Build the response with the endpoints MCP Inspector needs
        metadata = {
            "issuer": auth0_config.get("issuer", ISSUER),
            "authorization_endpoint": auth0_config.get("authorization_endpoint"),
            "token_endpoint": auth0_config.get("token_endpoint"),
            "jwks_uri": auth0_config.get("jwks_uri"),
            "scopes_supported": auth0_config.get("scopes_supported", ["openid", "profile", "email"]),
            "response_types_supported": auth0_config.get("response_types_supported", ["code"]),
            "response_modes_supported": auth0_config.get("response_modes_supported", ["query"]),
            "grant_types_supported": auth0_config.get("grant_types_supported", ["authorization_code", "refresh_token"]),
            "token_endpoint_auth_methods_supported": auth0_config.get(
                "token_endpoint_auth_methods_supported", 
                ["client_secret_post", "client_secret_basic", "none"]
            ),
            "code_challenge_methods_supported": auth0_config.get(
                "code_challenge_methods_supported",
                ["S256"]
            ),
        }
        
        logger.info(f"Returning OAuth metadata with issuer: {metadata['issuer']}")
        return JSONResponse(metadata, headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Type": "application/json"
        })
        
    except Exception as e:
        logger.error(f"Error in oauth_authorization_server_metadata: {e}", exc_info=True)
        return JSONResponse(
            {
                "error": "server_error", 
                "error_description": f"Failed to fetch Auth0 configuration: {str(e)}"
            },
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


async def oauth_protected_resource_metadata(request: Request) -> Response:
    """
    RFC 9728 - OAuth 2.0 Protected Resource Metadata
    
    This tells clients where to find the Authorization Server.
    """
    logger.info(f"GET /.well-known/oauth-protected-resource from {request.client}")
    
    try:
        metadata = {
            "resource": PUBLIC_BASE_URL,
            "authorization_servers": [ISSUER],
            "scopes_supported": ["openid", "profile", "email"],
            "bearer_methods_supported": ["header"],
        }
        
        logger.info(f"Returning protected resource metadata")
        return JSONResponse(metadata, headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Type": "application/json"
        })
    except Exception as e:
        logger.error(f"Error in oauth_protected_resource_metadata: {e}", exc_info=True)
        return JSONResponse(
            {"error": "server_error", "error_description": str(e)},
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


async def oauth_openid_configuration(request: Request) -> Response:
    """
    OpenID Connect Discovery - some clients request this instead.
    """
    logger.info(f"GET /.well-known/openid-configuration from {request.client}")
    
    try:
        auth0_config = await get_auth0_config()
        return JSONResponse(auth0_config, headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Type": "application/json"
        })
    except Exception as e:
        logger.error(f"Error in openid_configuration: {e}", exc_info=True)
        return JSONResponse(
            {"error": "server_error", "error_description": str(e)},
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


async def register_endpoint(request: Request) -> Response:
    """
    Dynamic Client Registration endpoint.
    """
    logger.info(f"POST /register from {request.client}")
    
    return JSONResponse(
        {
            "error": "registration_not_supported",
            "error_description": (
                "Auth0 does not support dynamic client registration. "
                "Please register your application in the Auth0 dashboard at "
                f"https://manage.auth0.com/dashboard and use the client_id provided."
            ),
        },
        status_code=400,
        headers={"Content-Type": "application/json"}
    )


async def authorize_endpoint(request: Request) -> Response:
    """
    Authorization endpoint - redirect to Auth0.
    """
    logger.info(f"GET /authorize from {request.client}")
    logger.info(f"Query params: {request.query_params}")
    
    try:
        # Get query parameters and forward to Auth0
        query_string = str(request.query_params)
        auth0_config = await get_auth0_config()
        auth0_authorize = auth0_config.get("authorization_endpoint")
        
        redirect_url = f"{auth0_authorize}?{query_string}"
        logger.info(f"Redirecting to Auth0: {redirect_url}")
        
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        logger.error(f"Error in authorize_endpoint: {e}", exc_info=True)
        return JSONResponse(
            {"error": "server_error", "error_description": str(e)},
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


async def token_endpoint(request: Request) -> Response:
    """
    Token endpoint - proxy to Auth0.
    """
    logger.info(f"POST /token from {request.client}")
    
    try:
        auth0_config = await get_auth0_config()
        auth0_token = auth0_config.get("token_endpoint")
        
        # Forward the request to Auth0
        body = await request.body()
        logger.debug(f"Token request body: {body.decode('utf-8', errors='ignore')}")
        
        headers = {
            "Content-Type": request.headers.get("Content-Type", "application/x-www-form-urlencoded")
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                auth0_token,
                content=body,
                headers=headers,
                timeout=10.0
            )
            
            logger.info(f"Auth0 token response status: {response.status_code}")
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except Exception as e:
        logger.error(f"Token endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {"error": "server_error", "error_description": str(e)},
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


# ============================================================================
# MCP Server
# ============================================================================
mcp = FastMCP(
    "simple-auth-mcp",
    host="0.0.0.0",
    port=8000,
    token_verifier=Auth0TokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(ISSUER),
        resource_server_url=AnyHttpUrl(PUBLIC_BASE_URL),
    ),
)


@mcp.resource("demo://ping")
def ping() -> str:
    return "pong"


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}! You are authenticated via Auth0."


# ============================================================================
# Application Setup
# ============================================================================
@asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    """Manage application lifecycle."""
    logger.info("=" * 80)
    logger.info("Starting MCP server with Auth0...")
    logger.info("=" * 80)
    
    # Pre-fetch Auth0 config
    try:
        config = await get_auth0_config()
        logger.info(f"✓ Auth0 configuration loaded successfully")
        logger.info(f"  Issuer: {config.get('issuer')}")
        logger.info(f"  Authorization endpoint: {config.get('authorization_endpoint')}")
        logger.info(f"  Token endpoint: {config.get('token_endpoint')}")
    except Exception as e:
        logger.error(f"✗ Failed to load Auth0 configuration: {e}")
        logger.error("  Server will start but OAuth will not work!")
    
    async with mcp.session_manager.run():
        logger.info("✓ MCP session manager started")
        logger.info("=" * 80)
        yield
    
    logger.info("Server shutting down...")


# Health check endpoint
async def health_check(request: Request) -> Response:
    """Simple health check endpoint."""
    return JSONResponse({"status": "ok", "service": "mcp-auth0-server"})


# Define routes
oauth_routes = [
    # Health check
    Route("/health", health_check, methods=["GET"]),
    
    # OAuth Authorization Server Metadata (RFC 8414)
    Route("/.well-known/oauth-authorization-server", oauth_authorization_server_metadata, methods=["GET"]),
    
    # Protected Resource Metadata (RFC 9728)
    Route("/.well-known/oauth-protected-resource", oauth_protected_resource_metadata, methods=["GET"]),
    Route("/.well-known/oauth-protected-resource/mcp", oauth_protected_resource_metadata, methods=["GET"]),
    
    # OpenID Connect Discovery
    Route("/.well-known/openid-configuration", oauth_openid_configuration, methods=["GET"]),
    
    # OAuth endpoints (facade to Auth0)
    Route("/register", register_endpoint, methods=["POST"]),
    Route("/authorize", authorize_endpoint, methods=["GET"]),
    Route("/token", token_endpoint, methods=["POST"]),
]

# Create app with CORS
app = Starlette(
    routes=[
        *oauth_routes,
        # Mount MCP app - handles both /mcp and /mcp/ 
        Mount("/mcp", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["Mcp-Session-Id", "WWW-Authenticate"],
        )
    ],
)


# ============================================================================
# Main
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                 MCP Server with Auth0 - MCP Inspector Compatible             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Server URL:      {PUBLIC_BASE_URL:<56} ║
║  MCP Endpoint:    {PUBLIC_BASE_URL + '/mcp/v1/sse':<56} ║
║  Auth0 Domain:    {AUTH0_DOMAIN:<56} ║
╚══════════════════════════════════════════════════════════════════════════════╝

Available Endpoints:
  GET  /health                                  (Health Check)
  GET  /.well-known/oauth-authorization-server  (OAuth AS Metadata) ← MCP Inspector checks this
  GET  /.well-known/oauth-protected-resource    (Protected Resource Metadata)
  GET  /.well-known/openid-configuration        (OIDC Discovery)
  POST /register                                (Dynamic Client Registration)
  GET  /authorize                               (Redirects to Auth0)
  POST /token                                   (Proxies to Auth0)
  *    /mcp/v1/sse                              (MCP SSE Endpoint)

⚠️  IMPORTANT SETUP STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Create an application in Auth0 Dashboard:
   → Go to: https://manage.auth0.com/dashboard
   → Create a "Single Page Application" or "Native Application"
   
2. Configure your Auth0 Application:
   → Allowed Callback URLs: http://localhost:6274/oauth/callback
   → Allowed Web Origins: http://localhost:6274
   → Allowed Logout URLs: http://localhost:6274
   
3. Get your credentials:
   → Copy the Client ID
   → Copy the Domain (should be: {AUTH0_DOMAIN})
   
4. In MCP Inspector:
   → Server URL: {PUBLIC_BASE_URL}
   → Use the Client ID from Auth0
   → Client Secret: (leave empty for public clients)

Testing the server:
  curl {PUBLIC_BASE_URL}/health
  curl {PUBLIC_BASE_URL}/.well-known/oauth-authorization-server

Starting server on http://0.0.0.0:8000...
""")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
