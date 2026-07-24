import os
from pathlib import Path

STEVE_NAME = os.environ.get("CODE_AGENT_NAME", "Steve")
PLAIN_UI = os.environ.get("CODE_AGENT_PLAIN", "").lower() in {"1", "true", "yes", "on"}
OUTPUT_MODE = os.environ.get("STEVE_OUTPUT", "clean").strip().lower()
if OUTPUT_MODE not in {"clean", "verbose", "debug"}:
    OUTPUT_MODE = "clean"

AGENT_VERSION = "4.0.0-alpha.7"

OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

MODEL_TEMPERATURE = float(os.environ.get("STEVE_MODEL_TEMPERATURE", "0.3"))
MODEL_NUM_CTX = int(os.environ.get("STEVE_MODEL_NUM_CTX", "8192"))
MODEL_NUM_PREDICT = int(os.environ.get("STEVE_MODEL_NUM_PREDICT", "2048"))
MODEL_REPEAT_PENALTY = float(os.environ.get("STEVE_MODEL_REPEAT_PENALTY", "1.08"))
MODEL_TOP_P = float(os.environ.get("STEVE_MODEL_TOP_P", "0.9"))
MODEL_TOP_K = int(os.environ.get("STEVE_MODEL_TOP_K", "40"))
WARM_KEEP_ALIVE = os.environ.get("STEVE_WARM_KEEP_ALIVE", "5m")
STEVE_WARM_TIMEOUT_MS = int(os.environ.get("STEVE_WARM_TIMEOUT_MS", "60000"))
PREFERRED_MODEL = os.environ.get("STEVE_PREFERRED_MODEL", "")
ACTIVE_MODEL_PRESET = os.environ.get("STEVE_MODEL_PRESET", "default")

# Execution settings
RUN_TIMEOUT = int(os.environ.get("STEVE_RUN_TIMEOUT", "60"))

# Conversation settings
SYSTEM_PROMPT = os.environ.get("STEVE_SYSTEM_PROMPT", "You are Steve, a conversational coding assistant.")
DEFAULT_MODEL = os.environ.get("STEVE_DEFAULT_MODEL", "qwen3:14b")
MAX_HISTORY_MESSAGES = int(os.environ.get("STEVE_MAX_HISTORY", "50"))
ROUTE_PROMPTS = {}
DEFAULT_ROUTE_PROMPT = "{request}"

# File context settings
AUTOLOAD_PROJECT_EXTS = os.environ.get("STEVE_AUTOLOAD_EXTS", ".py,.js,.ts,.jsx,.tsx,.html,.css,.json,.md,.yaml,.yml,.toml,.ini,.cfg,.conf,.sh,.bat,.ps1,.sql,.rs,.go,.java,.rb,.php,.c,.h,.cpp,.hpp,.swift,.kt,.dart,.vue,.svelte,.astro,.mjs,.cjs,.mts,.cts").split(",")
AUTOLOAD_EXCLUDED_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "env", ".tox", "dist", "build", ".next", ".nuxt", "target", "bin", "obj", "vendor", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".steve", "logs", "cache", ".opencode"}
AUTOLOAD_PROJECT_MAX_FILES = int(os.environ.get("STEVE_MAX_FILES", "50"))
AUTOLOAD_PROJECT_MAX_BYTES = int(os.environ.get("STEVE_MAX_FILE_BYTES", "65536"))
MAX_FILE_SNIPPET_CHARS = int(os.environ.get("STEVE_SNIPPET_CHARS", "4000"))
MAX_CONTEXT_CHARS = int(os.environ.get("STEVE_CONTEXT_CHARS", "32000"))
MAX_CONTEXT_FILES_PER_TURN = int(os.environ.get("STEVE_CONTEXT_FILES", "8"))

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
