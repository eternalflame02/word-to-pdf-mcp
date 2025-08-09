# Word-to-PDF MCP Server Development Instructions

**CRITICAL**: Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

This repository contains a Python-based MCP (Model Context Protocol) server for Puch AI (WhatsApp) that provides Word document to PDF conversion capabilities. The server exposes two tools: `validate` (phone number verification) and `convert_word_to_pdf` (document conversion).

## Working Effectively

### Bootstrap, Build, and Test the Repository

**NEVER CANCEL ANY OF THESE COMMANDS** - They are time-tested and must complete:

```bash
# 1. Create virtual environment (takes ~3 seconds)
python -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate                    # Linux/Mac
# OR
.venv\Scripts\Activate.ps1                   # Windows PowerShell

# 3. Install Python dependencies (takes ~1 minute - NEVER CANCEL)
pip install -r requirements.txt             # TIMEOUT: Set 3+ minutes

# 4. Install LaTeX for PDF generation (takes 10-15 minutes - NEVER CANCEL)
sudo apt-get update
sudo apt-get install -y texlive-latex-base texlive-fonts-recommended texlive-latex-extra texlive-xetex
# TIMEOUT: Set 20+ minutes. This is ESSENTIAL for PDF conversion.

# 5. Configure environment
cp .env.example .env
# Edit .env with your AUTH_TOKEN and MY_NUMBER (no plus sign)
```

### Run the MCP Server

```bash
# ALWAYS run the bootstrapping steps first
# Start server (immediate startup - less than 1 second)
uvicorn main:app --host 0.0.0.0 --port 8086

# Server will be available at: http://localhost:8086/mcp/
# For Puch AI integration, expose with ngrok:
ngrok http 8086
```

### Environment Configuration

**CRITICAL**: The server requires a `.env` file with proper configuration:

```env
AUTH_TOKEN=your_secret_token_here
MY_NUMBER=919876543210
```

**IMPORTANT**: 
- `MY_NUMBER` must be in `{country_code}{number}` format WITHOUT the "+" prefix
- `AUTH_TOKEN` is used as a Bearer token for authentication
- Keep `AUTH_TOKEN` secret and secure

## Validation

### Manual Validation Requirements

**ALWAYS manually validate any new code** by testing both tools:

```bash
# Test 1: Server import and configuration
python -c "import main; print('Server loads:', main.MY_NUMBER)"

# Test 2: Validate tool functionality
# (Requires server to be running and proper authentication)

# Test 3: PDF conversion functionality
python -c "
from tools.convert import _convert_docx_to_pdf, _read_pdf_base64
import os

# Test with sample document (create test.docx first)
if os.path.exists('test.docx'):
    _convert_docx_to_pdf('test.docx', 'output.pdf')
    b64 = _read_pdf_base64('output.pdf')
    print(f'Conversion successful: {len(b64)} chars base64')
else:
    print('Create test.docx first')
"
```

### Critical Validation Scenarios

**ALWAYS test these scenarios after making changes:**

1. **Server Startup Test**: Verify server starts without errors and loads environment variables
2. **Authentication Test**: Confirm Bearer token authentication works with configured AUTH_TOKEN
3. **Validate Tool Test**: Ensure tool returns configured MY_NUMBER correctly
4. **PDF Conversion Test**: Test both local file and URL conversion (if internet available)
5. **End-to-End Test**: Complete workflow from DOCX input to base64 PDF output

### Timing Expectations and Timeouts

**CRITICAL TIMEOUT VALUES** - Always use these minimums:

- `pip install -r requirements.txt`: **3 minutes timeout** (actual: ~1 minute)
- `apt-get install texlive-*`: **20 minutes timeout** (actual: 10-15 minutes)
- Server startup: **30 seconds timeout** (actual: <1 second)
- PDF conversion: **2 minutes timeout** (actual: ~1.3 seconds per document)
- Virtual environment creation: **1 minute timeout** (actual: ~3 seconds)

**NEVER CANCEL** these operations even if they seem to hang - builds and installations can take significant time.

## Common Tasks and File Locations

### Key Project Structure

```
├── main.py                 # ASGI server entry point
├── tools/                  # MCP tools directory
│   ├── __init__.py
│   ├── validate.py         # Phone number validation tool
│   └── convert.py          # Word to PDF conversion tool
├── requirements.txt        # Python dependencies
├── pyproject.toml         # Project metadata
├── .env.example           # Environment template
├── .env                   # Environment configuration (create this)
└── README.md              # Basic setup instructions
```

### Important Files to Know

- **main.py**: Server configuration, authentication setup, tool registration
- **tools/validate.py**: Returns configured phone number for Puch AI verification
- **tools/convert.py**: Handles DOCX to PDF conversion with URL download support
- **.env**: Environment configuration - MUST be created from .env.example

### Dependencies and External Requirements

**Python Dependencies** (installed via pip):
- `fastmcp>=2.11.2` - MCP server framework (has deprecation warning for Bearer auth)
- `pypandoc>=1.14` - Document conversion (auto-downloads pandoc if needed)
- `python-dotenv>=1.1.1` - Environment variable loading
- `requests>=2.31.0` - HTTP client for URL downloads
- `uvicorn>=0.35.0` - ASGI server

**System Dependencies** (REQUIRED for PDF generation):
- **pandoc** - Automatically downloaded by pypandoc on first use
- **LaTeX distribution** - MUST be installed manually:
  - Linux: `texlive-latex-base texlive-fonts-recommended texlive-latex-extra texlive-xetex`
  - Windows: MiKTeX or similar
  - macOS: MacTeX or BasicTeX

### Known Issues and Workarounds

1. **FastMCP Deprecation Warning**: Bearer auth provider is deprecated but functional
   - Warning message is harmless and can be ignored
   - Future versions should migrate to JWT authentication

2. **LaTeX Installation Required**: PDF conversion fails without LaTeX
   - Error: "pdflatex not found. Please select a different --pdf-engine"
   - Solution: Install full LaTeX distribution as shown in bootstrap steps

3. **Phone Number Format**: MY_NUMBER must exclude "+" prefix
   - Correct: `919876543210`
   - Incorrect: `+919876543210`

4. **MCP Session Management**: Direct HTTP testing requires proper session handling
   - Use Puch AI client or compatible MCP client for testing
   - Direct curl testing requires session ID and proper headers

## Tools and Functionality

### Validate Tool
- **Purpose**: Returns configured phone number for Puch AI server verification
- **Input**: None
- **Output**: Phone number string (e.g., "919876543210")
- **Use case**: `/mcp call validate` in Puch AI

### Convert Word to PDF Tool
- **Purpose**: Converts .docx files to PDF and returns as base64
- **Inputs**:
  - `docx_source` (str): Local file path or URL to .docx file
  - `output_path` (str): Path where PDF will be saved
- **Output**: JSON with success status, PDF path, and base64 encoded PDF
- **Performance**: ~1.3 seconds per conversion
- **Use case**: `/mcp call convert_word_to_pdf {"docx_source": "file.docx", "output_path": "output.pdf"}`

### Testing Both Tools

```bash
# Start server in background
uvicorn main:app --host 0.0.0.0 --port 8086 &

# Test via Puch AI (requires ngrok and Puch setup):
# /mcp connect https://your-ngrok-url/mcp your_bearer_token
# /mcp call validate
# /mcp call convert_word_to_pdf {"docx_source": "https://example.com/doc.docx", "output_path": "result.pdf"}
```

## Development Best Practices

### Before Making Changes
1. **Always** activate the virtual environment first
2. **Always** verify the server imports without errors: `python -c "import main"`
3. **Never** commit `.env` file (it's in .gitignore)
4. **Always** test both tools after making changes

### After Making Changes
1. **Always** test server startup
2. **Always** verify both tools still work
3. **Always** test with both local files and URLs (if applicable)
4. **Always** check that environment variables load correctly

### No Existing Test Infrastructure
- **No unit tests** exist in this repository
- **No CI/CD workflows** are configured
- **No automated testing** - all validation must be manual
- **No linting configuration** - code style is informal

### Quick Reference Commands

```bash
# Repository status check
git status
ls -la                                   # View files
source .venv/bin/activate               # Activate environment
python -c "import main; print('OK')"    # Test imports

# Environment check
cat .env                                # View configuration
echo $AUTH_TOKEN                        # Check token (when activated)

# Server operations
uvicorn main:app --reload              # Development mode with auto-reload
uvicorn main:app --host 0.0.0.0 --port 8086  # Production mode

# Dependency management
pip list                               # Show installed packages
pip install -r requirements.txt       # Reinstall dependencies
```

## Critical Reminders

- **NEVER CANCEL** long-running installation commands
- **ALWAYS** install LaTeX before attempting PDF conversion
- **ALWAYS** create and configure .env file before running server
- **ALWAYS** activate virtual environment before any Python operations
- **ALWAYS** test both tools after making any changes
- **REMEMBER** that MY_NUMBER must not include the "+" prefix
- **SET APPROPRIATE TIMEOUTS** for all build and installation commands (see timing section above)