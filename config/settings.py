import os
from pathlib import Path

STEVE_NAME = os.environ.get("CODE_AGENT_NAME", "Steve")
PLAIN_UI = os.environ.get("CODE_AGENT_PLAIN", "").lower() in {"1", "true", "yes", "on"}
OUTPUT_MODE = os.environ.get("STEVE_OUTPUT", "clean").strip().lower()
if OUTPUT_MODE not in {"clean", "verbose", "debug"}:
    OUTPUT_MODE = "clean"

AGENT_VERSION = "4.0.0"

DEFAULT_GITIGNORE = """__pycache__/
*.pyc
.venv/
venv/
.env
logs/
.steve/
cache/
build/
dist/
node_modules/
*.log
*.tmp
*.bak
.pytest_cache/
.mypy_cache/
.ruff_cache/
.idea/
.vscode/
"""

DEFAULT_README = """# Steve v4

Steve is a conversational-first local coding assistant.
"""
