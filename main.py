"""
ASGI entrypoint for the Puch AI MCP server.

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8086

Exposes MCP over Streamable HTTP at /mcp/ path.
Only two tools are registered: validate and convert_word_to_pdf.
"""

from __future__ import annotations

import logging
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken
from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles


# Load environment variables from .env
load_dotenv()

# Basic logging config so tool logs are visible
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s - %(message)s')

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"


# Auth Provider (Bearer Token for Puch)
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="puch-client", scopes=["*"], expires_at=None)
        return None


# Initialize MCP server
mcp = FastMCP("Puch MCP Server", auth=SimpleBearerAuthProvider(TOKEN))


# Register only the two required tools
try:
    from tools import validate as validate_tool
    from tools import convert as convert_tool
    from tools import health as health_tool

    validate_tool.register(mcp)
    convert_tool.register(mcp)
    health_tool.register(mcp)
except Exception as e:
    # Non-fatal; surfaces during tool call if needed
    print(f"[tools] Warning: failed to register external tools: {e}")


# Expose ASGI app for uvicorn
# We wrap the MCP app to also serve static files (generated PDFs) at /files
FILES_DIR = os.environ.get("FILES_DIR", "files")
os.makedirs(FILES_DIR, exist_ok=True)

base_app = mcp.http_app()  # This app already serves MCP at /mcp
# Important: pass the FastMCP app's lifespan to the parent app so session manager initializes
app = Starlette(lifespan=base_app.lifespan)
# Mount static first so it's not shadowed by the catch-all mount
app.mount("/files", StaticFiles(directory=FILES_DIR, check_dir=True), name="files")
app.mount("/", base_app)
