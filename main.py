"""
ASGI entrypoint for the Puch AI MCP server.

Run with:
  uvicorn main:app --host 0.0.0.0 --port 8086

Exposes MCP over Streamable HTTP at /mcp/ path.
"""

from __future__ import annotations

import os
import sys
import base64
import io
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, ImageContent, TextContent
from pydantic import BaseModel, Field, AnyUrl

import markdownify
import httpx
import readabilipy


# Load environment variables from .env
load_dotenv()

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"


class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None


class Fetch:
    """Small helper for fetching/searching content."""

    USER_AGENT = "Puch/1.0 (Autonomous)"

    @classmethod
    async def fetch_url(cls, url: str, user_agent: str, force_raw: bool = False) -> tuple[str, str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, follow_redirects=True, headers={"User-Agent": user_agent}, timeout=30)
            except httpx.HTTPError as e:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"))

            if response.status_code >= 400:
                raise McpError(
                    ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url} - status code {response.status_code}")
                )

            page_raw = response.text

        content_type = response.headers.get("content-type", "")
        is_page_html = "text/html" in content_type

        if is_page_html and not force_raw:
            return cls.extract_content_from_html(page_raw), ""

        return (
            page_raw,
            f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n",
        )

    @staticmethod
    def extract_content_from_html(html: str) -> str:
        ret = readabilipy.simple_json.simple_json_from_html_string(html, use_readability=True)
        if not ret or not ret.get("content"):
            return "<error>Page failed to be simplified from HTML</error>"
        content = markdownify.markdownify(ret["content"], heading_style=markdownify.ATX)
        return content

    @staticmethod
    async def google_search_links(query: str, num_results: int = 5) -> list[str]:
        ddg_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        links: list[str] = []

        async with httpx.AsyncClient() as client:
            resp = await client.get(ddg_url, headers={"User-Agent": Fetch.USER_AGENT})
            if resp.status_code != 200:
                return ["<error>Failed to perform search.</error>"]

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", class_="result__a", href=True):
            href = a["href"]
            if "http" in href:
                links.append(href)
            if len(links) >= num_results:
                break

        return links or ["<error>No results found.</error>"]


# Initialize MCP
mcp = FastMCP("Puch MCP Server", auth=StaticTokenVerifier({
    TOKEN: {
        "client_id": "puch_client", 
        "scopes": ["read", "write"]
    }
}))


# Built-in tool: job_finder
JobFinderDescription = RichToolDescription(
    description="Smart job tool: analyze descriptions, fetch URLs, or search jobs based on free text.",
    use_when="Use this to evaluate job descriptions or search for jobs using freeform goals.",
    side_effects="Returns insights, fetched job descriptions, or relevant job links.",
)


@mcp.tool(description=JobFinderDescription.model_dump_json())
async def job_finder(
    user_goal: Annotated[str, Field(description="The user's goal (can be a description, intent, or freeform query)")],
    job_description: Annotated[str | None, Field(description="Full job description text, if available.")] = None,
    job_url: Annotated[AnyUrl | None, Field(description="A URL to fetch a job description from.")] = None,
    raw: Annotated[bool, Field(description="Return raw HTML content if True")] = False,
) -> str:
    if job_description:
        return (
            f"📝 **Job Description Analysis**\n\n"
            f"---\n{job_description.strip()}\n---\n\n"
            f"User Goal: **{user_goal}**\n\n"
            f"💡 Suggestions:\n- Tailor your resume.\n- Evaluate skill match.\n- Consider applying if relevant."
        )

    if job_url:
        content, _ = await Fetch.fetch_url(str(job_url), Fetch.USER_AGENT, force_raw=raw)
        return f"🔗 **Fetched Job Posting from URL**: {job_url}\n\n---\n{content.strip()}\n---\n\nUser Goal: **{user_goal}**"

    if "look for" in user_goal.lower() or "find" in user_goal.lower():
        links = await Fetch.google_search_links(user_goal)
        return f"🔍 **Search Results for**: _{user_goal}_\n\n" + "\n".join(f"- {link}" for link in links)

    raise McpError(
        ErrorData(code=INVALID_PARAMS, message="Provide a job description, a job URL, or a search query in user_goal.")
    )


# Built-in tool: make image black and white
MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION = RichToolDescription(
    description="Convert an image to black and white and save it.",
    use_when="Use this tool when the user provides an image URL and requests it to be converted to black and white.",
    side_effects="The image will be processed and saved in a black and white format.",
)


@mcp.tool(description=MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION.model_dump_json())
async def make_img_black_and_white(
    puch_image_data: Annotated[str, Field(description="Base64-encoded image data to convert to black and white")] = None,
) -> list[TextContent | ImageContent]:
    import base64
    import io
    from PIL import Image

    try:
        image_bytes = base64.b64decode(puch_image_data)
        image = Image.open(io.BytesIO(image_bytes))
        bw_image = image.convert("L")

        buf = io.BytesIO()
        bw_image.save(buf, format="PNG")
        bw_bytes = buf.getvalue()
        bw_base64 = base64.b64encode(bw_bytes).decode("utf-8")

        return [ImageContent(type="image", mimeType="image/png", data=bw_base64)]
    except Exception as e:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))


# Add project root to sys.path to ensure `tools` module can be found
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# External tools: validate and convert_word_to_pdf
from tools import convert as convert_tool
from tools import validate as validate_tool

print("Registering external tools...")
validate_tool.register(mcp)
print("✓ Validate tool registered")
convert_tool.register(mcp)
print("✓ Convert tool registered")

# Debug FastMCP object to see available attributes
print("FastMCP attributes:", [attr for attr in dir(mcp) if not attr.startswith('__')])

# Try to get tools using the available methods
try:
    tools = mcp.get_tools()
    print(f"Available tools via get_tools(): {[tool.name for tool in tools]}")
except Exception as e:
    print(f"Error getting tools via get_tools(): {e}")

try:
    tools_list = mcp._list_tools()
    print(f"Available tools via _list_tools(): {tools_list}")
except Exception as e:
    print(f"Error getting tools via _list_tools(): {e}")

# Check tool manager
if hasattr(mcp, '_tool_manager'):
    print(f"Tool manager: {mcp._tool_manager}")
    if hasattr(mcp._tool_manager, 'tools'):
        print(f"Tools in manager: {list(mcp._tool_manager.tools.keys())}")
    elif hasattr(mcp._tool_manager, '_tools'):
        print(f"Tools in manager (_tools): {list(mcp._tool_manager._tools.keys())}")
    else:
        print(f"Tool manager attributes: {[attr for attr in dir(mcp._tool_manager) if not attr.startswith('_')]}" )

# Expose ASGI app for uvicorn
app = mcp.http_app()  # Default path: /mcp/

print("Server setup complete. Available at http://0.0.0.0:8086/mcp/")
