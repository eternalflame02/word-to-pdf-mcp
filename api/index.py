import os
import sys

# Ensure project root is on sys.path
sys.path.append(os.getcwd())

# Expose ASGI app for Vercel Python runtime
from main import app  # noqa: F401
