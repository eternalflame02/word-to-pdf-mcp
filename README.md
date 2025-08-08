# MCP Starter for Puch AI

This is a starter template for creating your own Model Context Protocol (MCP) server that works with Puch AI (via WhatsApp). It comes with ready-to-use tools for job searching and image processing, plus two new tools for Puch integration:

- validate – returns your WhatsApp phone number for server verification
- convert_word_to_pdf – converts a .docx file to PDF and returns it as base64

## What is MCP?

MCP (Model Context Protocol) allows AI assistants like Puch to connect to external tools and data sources safely. Think of it like giving your AI extra superpowers without compromising security.

## What's Included in This Starter?

### 🎯 Job Finder Tool

- **Analyze job descriptions** - Paste any job description and get smart insights
- **Fetch job postings from URLs** - Give a job posting link and get the full details
- **Search for jobs** - Use natural language to find relevant job opportunities

### 🖼️ Image Processing Tool

- **Convert images to black & white** - Upload any image and get a monochrome version

### 🔐 Built-in Authentication

- Bearer token authentication (required by Puch AI)
- Validation tool that returns your phone number

## Quick Setup Guide

### Step 1: Install Dependencies

First, make sure you have Python 3.11 or higher installed. Then:

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 2: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

Then edit `.env` and add your details:

```env
AUTH_TOKEN=your_secret_token_here
MY_NUMBER=919876543210
```

**Important Notes:**

- `AUTH_TOKEN`: This is your secret token for authentication. Keep it safe!
- `MY_NUMBER`: Your WhatsApp number in format `{country_code}{number}` (e.g., `919876543210` for +91-9876543210)

### Step 3: Run the Server

You can run either the original script or the ASGI app. Recommended (ASGI):

```powershell
uvicorn main:app --host 0.0.0.0 --port 8086
```

This exposes the MCP endpoint at `http://localhost:8086/mcp/`.

### Step 4: Make It Public (Required by Puch)

Since Puch needs to access your server over HTTPS, you need to expose your local server:

#### Option A: Using ngrok (Recommended)

1. **Install ngrok:**
   Download from https://ngrok.com/download

2. **Get your authtoken:**

   - Go to https://dashboard.ngrok.com/get-started/your-authtoken
   - Copy your authtoken
   - Run: `ngrok config add-authtoken YOUR_AUTHTOKEN`

3. **Start the tunnel:**
   ```powershell
   ngrok http 8086
   ```

#### Option B: Deploy to Cloud

You can also deploy this to services like:

- Railway
- Render
- Heroku
- DigitalOcean App Platform

## How to Connect with Puch AI

1. **[Open Puch AI](https://wa.me/+919998881729)** in your browser
2. **Start a new conversation**
3. **Use the connect command:**
   ```
   /mcp connect https://your-domain.ngrok.app/mcp your_secret_token_here
   ```

### Debug Mode

To get more detailed error messages:

```
/mcp diagnostics-level debug
```

### Troubleshooting

- If PDF conversion fails, install a LaTeX engine (e.g., MiKTeX on Windows) so Pandoc can build PDFs.
- Ensure `.env` is present and `MY_NUMBER` has no plus sign.
- If uvicorn won’t start, confirm the virtual environment is activated and requirements are installed.

### Repo Cleanup

- A `.gitignore` is included to exclude bytecode, virtual envs, and IDE files.
- Compiled `__pycache__` folders can be deleted safely; they’ll be ignored thereafter.

## Customizing the Starter

### Adding New Tools

1. **Create a new tool function:**

   ```python
   @mcp.tool(description="Your tool description")
   async def your_tool_name(
       parameter: Annotated[str, Field(description="Parameter description")]
   ) -> str:
       # Your tool logic here
       return "Tool result"
   ```

2. **Add required imports** if needed

## 📚 **Additional Documentation Resources**

---

**Puch AI WhatsApp Usage**

- Puch MCP requires a `validate` tool that returns your phone number without a plus sign. Example: `919876543210`.
- Use the new conversion tool like this:
  ```
  /mcp call convert_word_to_pdf {"docx_source": "https://example.com/sample.docx", "output_path": "output.pdf"}
  ```

**Happy hacking! 🚀**

### **Technical Specifications**

- **JSON-RPC 2.0 Specification**: https://www.jsonrpc.org/specification (for error handling)
- **MCP Protocol**: Core protocol messages, tool definitions, authentication

### **Supported vs Unsupported Features**

**✓ Supported:**

- Core protocol messages
- Tool definitions and calls
- Authentication (Bearer & OAuth)
- Error handling

**✗ Not Supported:**

- Videos extension
- Resources extension
- Prompts extension

## Getting Help

- **Join Puch AI Discord:** https://discord.gg/VMCnMvYx
- **Check Puch AI MCP docs:** https://puch.ai/mcp
- **Puch WhatsApp Number:** +91 99988 81729

---

**Happy coding! 🚀**

Use the hashtag `#BuildWithPuch` in your posts about your MCP!

This starter makes it super easy to create your own MCP server for Puch AI. Just follow the setup steps and you'll be ready to extend Puch with your custom tools!
