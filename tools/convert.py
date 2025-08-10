from __future__ import annotations

import base64
import logging
import os
import tempfile
import time
import uuid
from typing import Any, Dict
from urllib.parse import urlparse

import requests
import shutil

# pypandoc provides a python wrapper around pandoc and will attempt to download it
# on first use if not present. This keeps the solution cross-platform.
import pypandoc
from importlib import import_module

from fastmcp import FastMCP


# File extension constants
DOCX_EXT = ".docx"
PDF_EXT = ".pdf"

logger = logging.getLogger("puch.mcp.give_pdf")

def _is_url(path_or_url: str) -> bool:
    try:
        parsed = urlparse(path_or_url)
        return parsed.scheme in {"http", "https"}
    except Exception:
        return False


def _download_docx(url: str) -> str:
    """Download a .docx file from URL into a temp file and return its path."""
    logger.info("download:url start", extra={"url": url})
    t0 = time.perf_counter()
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    fd, tmp_path = tempfile.mkstemp(suffix=DOCX_EXT)
    os.close(fd)
    with open(tmp_path, "wb") as f:
        f.write(resp.content)
    dur = (time.perf_counter() - t0) * 1000
    logger.info("download:url done", extra={"bytes": len(resp.content), "ms": round(dur, 1)})
    return tmp_path


def _download_docx_by_id(file_id: str) -> str:
    """Download a .docx using an ID and a configured URL template.

    Requires env PUCH_DOWNLOAD_URL_TEMPLATE, e.g.,
    https://puch.example/api/files/{id}
    Optionally adds Authorization: Bearer <PUCH_API_TOKEN> if set.
    """
    template = os.environ.get("PUCH_DOWNLOAD_URL_TEMPLATE")
    if not template:
        raise RuntimeError(
            "Attachment provided as ID but PUCH_DOWNLOAD_URL_TEMPLATE is not set. "
            "Set it to a URL template like https://host/api/files/{id} or pass file_base64/docx_source."
        )
    url = template.format(id=file_id)
    headers = {}
    token = os.environ.get("PUCH_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    logger.info("download:id start", extra={"id": str(file_id)})
    t0 = time.perf_counter()
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    fd, tmp_path = tempfile.mkstemp(suffix=DOCX_EXT)
    os.close(fd)
    with open(tmp_path, "wb") as f:
        f.write(resp.content)
    dur = (time.perf_counter() - t0) * 1000
    logger.info("download:id done", extra={"id": str(file_id), "bytes": len(resp.content), "ms": round(dur, 1)})
    return tmp_path


def _convert_docx_to_pdf(input_docx: str, output_pdf: str) -> None:
    """Convert docx to pdf using pypandoc (pandoc under the hood)."""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf)) or ".", exist_ok=True)

    # pypandoc will try to locate pandoc; if missing, enable download
    t0 = time.perf_counter()
    try:
        logger.info("convert start", extra={"input": os.path.basename(input_docx)})
        pypandoc.convert_file(
            source_file=input_docx,
            to="pdf",
            outputfile=output_pdf,
            extra_args=[],
        )
    except OSError:
        # Attempt automatic pandoc download and retry once
        logger.info("pandoc:download start")
        pypandoc.download_pandoc()
        logger.info("pandoc:download done")
        try:
            pypandoc.convert_file(
                source_file=input_docx,
                to="pdf",
                outputfile=output_pdf,
                extra_args=[],
            )
        except Exception as e:
            # If LaTeX engine is missing, fall back to docx2pdf (Windows/MS Word)
            logger.warning("pandoc convert failed, trying docx2pdf", extra={"error": str(e)})
            _convert_with_docx2pdf(input_docx, output_pdf)
    except Exception as e:
        # Unknown error - try docx2pdf as a last resort
        logger.warning("convert error, trying docx2pdf fallback", extra={"error": str(e)})
        _convert_with_docx2pdf(input_docx, output_pdf)
    dur = (time.perf_counter() - t0) * 1000
    logger.info("convert done", extra={"output": os.path.basename(output_pdf), "ms": round(dur, 1)})


def _convert_with_docx2pdf(input_docx: str, output_pdf: str) -> None:
    """Fallback converter using docx2pdf (requires MS Word on Windows)."""
    try:
        docx2pdf = import_module("docx2pdf")
    except Exception as e:
        raise RuntimeError("docx2pdf not installed; install and retry") from e
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf)) or ".", exist_ok=True)
    logger.info("docx2pdf start", extra={"input": os.path.basename(input_docx)})
    docx2pdf.convert(input_docx, output_pdf)
    logger.info("docx2pdf done", extra={"output": os.path.basename(output_pdf)})


def _read_pdf_base64(pdf_path: str) -> str:
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _write_temp_docx_from_base64(b64: str) -> str:
    """Write base64 docx content to a temp file and return its path."""
    fd, tmp_path = tempfile.mkstemp(suffix=DOCX_EXT)
    os.close(fd)
    with open(tmp_path, "wb") as f:
        f.write(base64.b64decode(b64))
    return tmp_path


def _looks_like_base64(s: str) -> bool:
    try:
        # validate=True ensures characters outside base64 alphabet raise
        base64.b64decode(s, validate=True)
        return True
    except Exception:
        return False


def _resolve_input_path(docx_source: str | None, attachment_b64: str | None) -> tuple[str, bool] | tuple[None, None]:
    """Return (input_path, cleanup_tmp) or (None, None) if invalid."""
    if attachment_b64:
        tmp_path = _write_temp_docx_from_base64(attachment_b64)
        return tmp_path, True
    if docx_source:
        if _is_url(docx_source):
            tmp_docx = _download_docx(docx_source)
            return tmp_docx, True
        abs_path = os.path.abspath(docx_source)
        if os.path.exists(abs_path):
            return abs_path, False
        return None, None
    return None, None


def _resolve_output_pdf_path(files_dir: str, filename: str | None, input_path: str, output_path: str | None) -> str:
    if output_path:
        return os.path.abspath(output_path)
    # Derive from provided filename or input path
    if filename:
        base_name_no_ext = os.path.splitext(filename)[0]
    else:
        fallback_name = os.path.basename(input_path) or f"output{DOCX_EXT}"
        base_name_no_ext = os.path.splitext(fallback_name)[0]
    return os.path.abspath(os.path.join(files_dir, f"{base_name_no_ext}{PDF_EXT}"))


def _publish_and_url(files_dir: str, output_pdf: str, base_url: str | None) -> tuple[str, str | None]:
    filename = os.path.basename(output_pdf) or f"output{PDF_EXT}"
    public_pdf_path = os.path.abspath(os.path.join(files_dir, filename))
    if os.path.abspath(output_pdf) != public_pdf_path:
        shutil.copy2(output_pdf, public_pdf_path)
    file_url = f"{base_url.rstrip('/')}/files/{filename}" if base_url else None
    logger.info("publish done", extra={"file": filename, "url": file_url})
    return public_pdf_path, file_url


def _safe_remove(path: str | None):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _get_config() -> tuple[str, str | None, bool]:
    # Prefer FILES_DIR; default to /tmp on Vercel, else local 'files'
    if os.environ.get("FILES_DIR"):
        files_dir = os.environ["FILES_DIR"]
    else:
        files_dir = "/tmp/files" if os.environ.get("VERCEL") == "1" else "files"
    os.makedirs(files_dir, exist_ok=True)
    base_url = os.environ.get("BASE_URL")  # e.g., https://<ngrok-domain>
    include_b64 = os.environ.get("INCLUDE_BASE64", "false").lower() == "true"
    return files_dir, base_url, include_b64


def _success_result(file_url: str, pdf_b64: str | None) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "success": True,
        "url": file_url,
    }
    if pdf_b64 is not None:
        out["pdf_base64"] = pdf_b64
    return out


def register(mcp: FastMCP):
    """Register the convert_word_to_pdf tool on the given FastMCP instance."""

    @mcp.tool(
        name="give pdf",
        description=(
            "Convert a Word (.docx) file to PDF from attachment, URL, or local path. "
            "Saves the PDF to FILES_DIR and returns a downloadable file URL."
        ),
    )
    async def give_pdf(
        docx_source: str | None = None,
        output_path: str | None = None,
        file_base64: str | None = None,
        puch_file_data: str | None = None,
        filename: str | None = None,
    ) -> Dict[str, Any]:
        try:
            req_id = uuid.uuid4().hex[:8]
            # Config for publishing
            files_dir, base_url, include_b64 = _get_config()
            logger.info(
                "give_pdf start",
                extra={
                    "req": req_id,
                    "has_docx_source": bool(docx_source),
                    "has_file_base64": bool(file_base64),
                    "has_puch_file_data": bool(puch_file_data),
                    "filename": filename,
                    "output_path": bool(output_path),
                },
            )

            # Decide if the source is attachment (base64), URL, or local path
            attachment_b64 = file_base64 or (puch_file_data if (puch_file_data and _looks_like_base64(puch_file_data)) else None)

            # If puch_file_data is present but not base64, treat as an attachment ID
            input_path = None
            cleanup_tmp = False
            if puch_file_data and not attachment_b64:
                try:
                    logger.info("source:id", extra={"req": req_id, "id": str(puch_file_data)})
                    tmp = _download_docx_by_id(str(puch_file_data))
                    input_path, cleanup_tmp = tmp, True
                except Exception as e:
                    logger.error("source:id error", extra={"req": req_id, "error": str(e)})
                    return {"success": False, "error": str(e)}

            # Fallback to normal resolution if we don't already have an input path
            if not input_path:
                input_path, cleanup_tmp = _resolve_input_path(docx_source, attachment_b64)
                if input_path:
                    if attachment_b64:
                        src_type = "attachment_b64"
                    elif docx_source and _is_url(docx_source):
                        src_type = "url"
                    else:
                        src_type = "path"
                    logger.info(
                        "source:resolved",
                        extra={
                            "req": req_id,
                            "type": src_type,
                        },
                    )
            if not input_path:
                if docx_source:
                    logger.error("resolve error:not found", extra={"req": req_id, "path": docx_source})
                    return {"success": False, "error": f"File not found: {docx_source}"}
                logger.error("resolve error:no input", extra={"req": req_id})
                return {"success": False, "error": "Provide a docx_source (URL/path) or file_base64 (attachment), or configure PUCH_DOWNLOAD_URL_TEMPLATE for attachment IDs."}

            # Normalize output path (where conversion always writes)
            output_pdf = _resolve_output_pdf_path(files_dir, filename, input_path, output_path)

            # Convert docx to pdf
            _convert_docx_to_pdf(input_path, output_pdf)

            # Publish/copy into files_dir for static serving
            public_pdf_path, file_url = _publish_and_url(files_dir, output_pdf, base_url)
            if not file_url and not include_b64:
                # Without BASE_URL and base64 disabled, we can't return a usable artifact
                if cleanup_tmp:
                    _safe_remove(input_path)
                logger.error("publish error:no BASE_URL and base64 disabled", extra={"req": req_id})
                return {"success": False, "error": "Set BASE_URL or set INCLUDE_BASE64=true to receive the PDF as base64."}

            # Optional base64 for compatibility (can be large for WhatsApp)
            pdf_b64 = _read_pdf_base64(public_pdf_path) if include_b64 else None

            result = _success_result(file_url or "", pdf_b64)
            # Cleanup temp input if needed
            if cleanup_tmp:
                _safe_remove(input_path)
            logger.info("give_pdf done", extra={"req": req_id, "url": file_url, "base64": bool(pdf_b64)})
            return result
        except Exception as e:
            # Attempt cleanup on error as well
            if 'cleanup_tmp' in locals() and cleanup_tmp:
                _safe_remove(locals().get('input_path'))
            logger.exception("give_pdf exception", extra={"error": str(e)})
            return {"success": False, "error": str(e)}
