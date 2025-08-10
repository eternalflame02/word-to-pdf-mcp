from __future__ import annotations

import os
from typing import Any, Dict

from fastmcp import FastMCP


def _gather_health_sync() -> Dict[str, Any]:
    info: Dict[str, Any] = {"ok": True, "checks": {}}

    # BASE_URL check
    base_url = os.environ.get("BASE_URL")
    info["checks"]["BASE_URL"] = {
        "set": bool(base_url),
        "value": base_url or "",
    }

    # FILES_DIR check
    files_dir = os.environ.get("FILES_DIR", "files")
    files_dir_ok = False
    try:
        os.makedirs(files_dir, exist_ok=True)
        test_path = os.path.join(files_dir, ".write_test")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_path)
        files_dir_ok = True
    except Exception as e:
        info["ok"] = False
        info["checks"]["FILES_DIR_error"] = str(e)
    info["checks"]["FILES_DIR"] = {"path": files_dir, "writable": files_dir_ok}

    # Pandoc availability
    try:
        import pypandoc  # type: ignore
        ver = None
        try:
            ver = pypandoc.get_pandoc_version()
        except Exception:
            pass
        info["checks"]["pandoc"] = {
            "module": True,
            "version": str(ver) if ver else None,
        }
    except Exception:
        info["checks"]["pandoc"] = {"module": False}

    # docx2pdf availability
    try:
        import importlib

        importlib.import_module("docx2pdf")
        info["checks"]["docx2pdf"] = {"module": True}
    except Exception:
        info["checks"]["docx2pdf"] = {"module": False}

    # Attachment ID download config
    info["checks"]["PUCH_DOWNLOAD_URL_TEMPLATE"] = os.environ.get("PUCH_DOWNLOAD_URL_TEMPLATE", "")
    info["checks"]["PUCH_API_TOKEN_set"] = bool(os.environ.get("PUCH_API_TOKEN"))

    return info


def register(mcp: FastMCP):
    """Register a lightweight health diagnostics tool."""

    @mcp.tool(name="health", description="Return server health, config, and converter readiness diagnostics")
    async def health() -> Dict[str, Any]:
        return _gather_health_sync()
