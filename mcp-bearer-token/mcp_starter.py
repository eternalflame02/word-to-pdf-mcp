import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken


# Load environment variables
load_dotenv()

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"


class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="puch-client", scopes=["*"], expires_at=None)
        return None


# MCP server instance
mcp = FastMCP("Puch MCP Server", auth=SimpleBearerAuthProvider(TOKEN))


# Ensure project root is on sys.path so we can import the top-level `tools` package
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


# Register only the two required tools
try:
    from tools import validate as validate_tool
    from tools import convert as convert_tool

    validate_tool.register(mcp)
    convert_tool.register(mcp)
except Exception as e:
    print(f"[tools] Warning: failed to register external tools: {e}")


async def main():
    """Run the MCP server via the streamable-http transport."""
    print("Starting MCP server on http://0.0.0.0:8086")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)


if __name__ == "__main__":
    asyncio.run(main())
