from fastmcp import FastMCP
import os
from dotenv import load_dotenv

# Load env so the tool can read MY_NUMBER
load_dotenv()

MY_NUMBER = os.environ.get("MY_NUMBER")

# Expose a function that can be registered with FastMCP

def register(mcp: FastMCP):
    """
    Registers the validate tool with the given FastMCP instance.
    The tool returns the owner's phone number (no plus sign), e.g., "919876543210".
    """

    @mcp.tool(description="Validate server and return owner's phone number")
    async def validate() -> str:
        # Ensure the number is configured and formatted properly
        if not MY_NUMBER:
            return "<error>MY_NUMBER not configured</error>"
        return MY_NUMBER.strip().replace("+", "")
