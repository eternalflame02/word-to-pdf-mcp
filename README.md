## Word-to-PDF MCP Server for Puch AI (WhatsApp)

This repository provides a minimal, production-lean MCP server tailored for Puch AI on WhatsApp. It exposes a small set of tools over MCP via HTTP:

- validate: Returns your configured WhatsApp number (without +) for a quick connectivity check.
- give pdf: Converts a .docx to PDF (from URL, local path, or attachment ID) and returns a downloadable link.
- health: Reports server diagnostics (config, storage, and converter readiness) to debug issues quickly.

Generated PDFs are served from the built-in static endpoint at /files, so the tool returns a URL you can tap in WhatsApp.

## Requirements

- Windows or Linux; tested primarily on Windows
- Python 3.11+
- Internet access for URL downloads and initial pandoc download
- Optional: Microsoft Word on Windows (for docx2pdf fallback)

Conversion engines:

- Primary: pandoc via pypandoc (auto-downloads pandoc if missing). On some platforms, PDF output may require a LaTeX engine (e.g., MiKTeX).
- Fallback on Windows: docx2pdf (uses installed Microsoft Word, no LaTeX needed).

## Setup

1. Create and activate a virtual environment (PowerShell):

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

2. Configure environment (.env):

Create a file named .env in the project root with at least:

```env
AUTH_TOKEN=your_secret_token_here
MY_NUMBER=919876543210
FILES_DIR=files
BASE_URL=https://<your-ngrok-subdomain>.ngrok-free.app
INCLUDE_BASE64=false

# If Puch sends attachment IDs in puch_file_data, set a template for downloading:
PUCH_DOWNLOAD_URL_TEMPLATE=https://api.puch.ai/v1/files/{id}/download
# Set only if your download endpoint needs auth; otherwise leave blank
PUCH_API_TOKEN=
```

Notes:

- MY_NUMBER must be digits only: country code + number, no plus (e.g., 919876543210).
- AUTH_TOKEN is used as a Bearer token by Puch; keep it secret.
- BASE_URL must match your public domain (e.g., from ngrok). No trailing spaces/hidden characters.
- FILES_DIR is where PDFs are stored and served from /files.
- INCLUDE_BASE64=false is recommended for WhatsApp; large base64 can be unwieldy.

## Run the server

```powershell
uvicorn main:app --host 0.0.0.0 --port 8086
```

Endpoints:

- MCP: http://localhost:8086/mcp/
- Files (static): http://localhost:8086/files/

You’ll see logs like 307 Temporary Redirect (normal for /mcp → /mcp/), 200 OK, 202 Accepted.

## Expose with ngrok (for Puch)

```powershell
ngrok http 8086
```

Copy the HTTPS forwarding URL from ngrok and set BASE_URL accordingly in .env, then restart the server.

## Connect from WhatsApp (Puch)

In your Puch WhatsApp chat:

```
/mcp connect https://<your-ngrok-domain>/mcp <your_bearer_token>
/mcp call validate
```

If connected, validate returns your MY_NUMBER without +.

## Tools

### 1) validate

Description: Confirms connectivity and returns the configured phone number without a plus sign.

Usage:

```
/mcp call validate
```

Response (example):

```
919876543210
```

### 2) give pdf

Description: Convert a Word (.docx) file to PDF and return a downloadable link. Accepts:

- URL (http/https)
- Local path (on the server)
- Attachment ID from Puch (puch_file_data) when PUCH_DOWNLOAD_URL_TEMPLATE is configured

Inputs (JSON object):

- docx_source (string, optional): URL or local path to the .docx
- file_base64 (string, optional): base64 of .docx (not typically used with Puch)
- puch_file_data (string, optional): attachment ID provided by Puch
- filename (string, optional): Preferred output name (e.g., "resume.docx"); PDF name is derived
- output_path (string, optional): Explicit path to write the PDF; otherwise saved under FILES_DIR

Examples:

URL-based conversion:

```
/mcp call "give pdf" {"docx_source": "https://example.com/sample.docx"}
```

Attachment via caption (ID-based):

- Send a .docx as an attachment in WhatsApp.
- Use a caption like:

```
/mcp call "give pdf" {"filename": "myfile.docx"}
```

When Puch passes an attachment ID in puch_file_data, the server fetches the .docx using PUCH_DOWNLOAD_URL_TEMPLATE (and PUCH_API_TOKEN if required).

Success response:

```json
{
  "success": true,
  "url": "https://<BASE_URL>/files/<derived-name>.pdf"
}
```

Error response:

```json
{ "success": false, "error": "<message>" }
```

Notes:

- The server publishes PDFs to FILES_DIR and serves them at BASE_URL/files/<name>.pdf.
- If BASE_URL isn’t set, the tool returns an error because it can’t provide a public link.
- Conversion path: pandoc (primary) → docx2pdf fallback on Windows if pandoc/LaTeX fails.

### 3) health

Description: Returns diagnostics to help troubleshoot.

Usage:

```
/mcp call health {}
```

Response (example):

```json
{
  "ok": true,
  "checks": {
    "BASE_URL": { "set": true, "value": "https://<your-ngrok>.ngrok-free.app" },
    "FILES_DIR": { "path": "files", "writable": true },
    "pandoc": { "module": true, "version": "3.1.12" },
    "docx2pdf": { "module": true },
    "PUCH_DOWNLOAD_URL_TEMPLATE": "https://api.puch.ai/v1/files/{id}/download",
    "PUCH_API_TOKEN_set": false
  }
}
```

## Logging and observability

The converter logs key steps with durations and sizes:

- download:id/url start/done (bytes, ms)
- convert start/done (ms), with a fallback note if docx2pdf is used
- publish done (file, url)
- give_pdf start/done with a small correlation ID

Logs are printed at INFO level by default. Adjust logging in main.py if you want a different verbosity.

## Windows specifics

- If pandoc PDF output fails due to a missing LaTeX engine, the server automatically falls back to docx2pdf (requires MS Word).
- If you prefer pandoc-only, install a LaTeX engine such as MiKTeX.
- Paths in output_path should be absolute to avoid surprises.

## Common pitfalls and fixes

- 401 Unauthorized when connecting from Puch:
  - Make sure you pass the correct AUTH_TOKEN and the /mcp endpoint URL; remove hidden/non-breaking spaces.
- 404 Not Found on /.well-known:
  - Expected if you try to browse OIDC urls; the server isn’t an OAuth provider.
- 307 Temporary Redirect on /mcp:
  - Normal; /mcp redirects to /mcp/.
- Attachment conversion errors:
  - Ensure PUCH_DOWNLOAD_URL_TEMPLATE is set to the endpoint that returns raw .docx bytes.
  - If your endpoint requires a bearer token, set PUCH_API_TOKEN too.
- No link returned:
  - Set BASE_URL in .env to your public domain (e.g., ngrok URL) and restart the server.
- Large files in chat:
  - Keep INCLUDE_BASE64=false so the server returns only a URL, not base64.

## Quick manual test (optional)

Download a file by ID (if public or presigned):

```powershell
Invoke-WebRequest -Uri "https://api.puch.ai/v1/files/726726433567771/download" -OutFile test.docx
```

If this works, set PUCH_DOWNLOAD_URL_TEMPLATE accordingly and retry give pdf.

## License

MIT

```

```
