## Word-to-PDF MCP Server (Puch AI)

This repository contains a minimal MCP server for Puch AI (WhatsApp) with two tools:

- validate: returns your WhatsApp number for server verification (no plus sign)
- convert_word_to_pdf: converts a .docx file (local or URL) to PDF and returns it as base64

### Requirements

- Python 3.11+
- Internet access if converting from a URL
- Pandoc (pypandoc will auto-download); for PDF generation, a LaTeX engine may be required (e.g., MiKTeX on Windows)

### Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configure

Create a `.env` file in the project root:

```env
AUTH_TOKEN=your_secret_token_here
MY_NUMBER=919876543210
```

Notes:

- `MY_NUMBER` must be in `{country_code}{number}` format without "+".
- Keep `AUTH_TOKEN` secret; Puch will use it as a Bearer token.

### Run the server

```powershell
uvicorn main:app --host 0.0.0.0 --port 8086
```

Endpoint: `http://localhost:8086/mcp/`

### Expose with ngrok (required by Puch)

```powershell
ngrok http 8086
```

### Connect from WhatsApp (Puch AI)

In your Puch chat:

```
/mcp connect https://<your-ngrok-domain>/mcp <your_bearer_token>
/mcp call validate
/mcp call convert_word_to_pdf {"docx_source": "https://example.com/sample.docx", "output_path": "output.pdf"}
```

### Tool: convert_word_to_pdf

Inputs:

- `docx_source` (str): Local path or URL to a .docx file
- `output_path` (str): Path where the PDF will be saved

Success Response:

```
{
   "success": true,
   "message": "Conversion successful",
   "pdf_path": "<absolute path>",
   "pdf_base64": "<base64 string>"
}
```

Error Response:

```
{ "success": false, "error": "<message>" }
```

### Troubleshooting

- PDF build fails: install a LaTeX engine (e.g., MiKTeX on Windows) so Pandoc can generate PDFs.
- `MY_NUMBER` must not include "+" (e.g., use `919876543210`).
- Ensure venv is active and `pip install -r requirements.txt` ran without errors.
- For Windows paths, prefer absolute paths in `output_path`.

### Repo hygiene

- `.gitignore` excludes bytecode, venvs, `.env`, and IDE files.
- You can safely delete any `__pycache__` folders; they’ll be ignored.
