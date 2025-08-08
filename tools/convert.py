from __future__ import annotations

import base64
import os
import tempfile
from typing import Any, Dict
from urllib.parse import urlparse

import requests

# pypandoc provides a python wrapper around pandoc and will attempt to download it
# on first use if not present. This keeps the solution cross-platform.
import pypandoc

from fastmcp import FastMCP


def _is_url(path_or_url: str) -> bool:
    try:
        parsed = urlparse(path_or_url)
        return parsed.scheme in {"http", "https"}
    except Exception:
        return False


def _download_docx(url: str) -> str:
    """Download a .docx file from URL into a temp file and return its path."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    fd, tmp_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    with open(tmp_path, "wb") as f:
        f.write(resp.content)
    return tmp_path


def _convert_docx_to_pdf(input_docx: str, output_pdf: str) -> None:
    """Convert docx to pdf using pypandoc (pandoc under the hood)."""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf)) or ".", exist_ok=True)

    # pypandoc will try to locate pandoc; if missing, enable download
    try:
        pypandoc.convert_file(
            source_file=input_docx,
            to="pdf",
            outputfile=output_pdf,
            extra_args=[],
        )
    except OSError:
        # Attempt automatic pandoc download and retry once
        pypandoc.download_pandoc()
        pypandoc.convert_file(
            source_file=input_docx,
            to="pdf",
            outputfile=output_pdf,
            extra_args=[],
        )


def _read_pdf_base64(pdf_path: str) -> str:
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def register(mcp: FastMCP):
    """Register the convert_word_to_pdf tool on the given FastMCP instance."""

    @mcp.tool(
        description="Convert a Word (.docx) file to PDF, from local path or URL, and return as base64"
    )
    async def convert_word_to_pdf(docx_source: str, output_path: str) -> Dict[str, Any]:
        try:
            # Decide if the source is URL or local path
            if _is_url(docx_source):
                tmp_docx = _download_docx(docx_source)
                cleanup_tmp = True
                input_path = tmp_docx
            else:
                input_path = os.path.abspath(docx_source)
                cleanup_tmp = False
                if not os.path.exists(input_path):
                    return {"success": False, "error": f"File not found: {input_path}"}

            # Normalize output path
            output_pdf = os.path.abspath(output_path)

            # Convert docx to pdf
            _convert_docx_to_pdf(input_path, output_pdf)

            # Read base64
            pdf_b64 = _read_pdf_base64(output_pdf)

            return {
                "success": True,
                "message": "Conversion successful",
                "pdf_path": output_pdf,
                "pdf_base64": pdf_b64,
            }
        except requests.RequestException as e:
            return {"success": False, "error": f"Download error: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            # Remove temp file if we created one
            try:
                if 'cleanup_tmp' in locals() and cleanup_tmp:
                    os.remove(tmp_docx)
            except Exception:
                pass
