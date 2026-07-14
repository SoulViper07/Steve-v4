import os
import sys
import re
import requests
from typing import Any

# -- Windows UTF-8 bootstrap (runs before any terminal output) ---------
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    os.environ.setdefault("PYTHONUTF8", "1")

# -- Environment Detection ---------------------------------------------
IS_WINDOWS = sys.platform == "win32"
_stdout_encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
_env_ascii = os.environ.get("STEVE_ASCII", "").lower()
EXPLICIT_ASCII = _env_ascii in {"1", "true", "yes", "on"} or "--ascii" in sys.argv
STEVE_ASCII = EXPLICIT_ASCII
TERMINAL_UTF8_OK = "utf" in _stdout_encoding
NO_COLOR_SET = "NO_COLOR" in os.environ

def _windows_ansi_supported() -> bool:
    if not IS_WINDOWS:
        return True
    if any(os.environ.get(name) for name in ("WT_SESSION", "ANSICON", "TERM_PROGRAM", "ConEmuANSI", "VSCODE_PID")):
        return True
    term = os.environ.get("TERM", "").lower()
    return "xterm" in term or "ansi" in term or TERMINAL_UTF8_OK

TERMINAL_ANSI_OK = (not NO_COLOR_SET) and _windows_ansi_supported()

def get_symbol(u: str, a: str) -> str:
    return a if STEVE_ASCII or not TERMINAL_UTF8_OK else u

def redact_secret_text(value: str) -> str:
    text = str(value)
    text = re.sub(r"github_pat_[A-Za-z0-9_]+", "github_pat_[REDACTED]", text)
    text = re.sub(r"gh[pousr]_[A-Za-z0-9_]+", "gh_[REDACTED]", text)
    text = re.sub(r"(https?://)([^/\s:@]+):([^@\s/]+)@", r"\1[REDACTED]@", text)
    text = re.sub(r"([?&](?:token|access_token|pat)=)[^&\s]+", r"\1[REDACTED]", text, flags=re.I)
    return text

def strip_rich_markup(value: Any) -> str:
    from rich.text import Text
    text = str(value)
    try:
        return Text.from_markup(text).plain
    except Exception:
        return re.sub(r"\[/?[a-zA-Z][a-zA-Z0-9_ #=-]*(?: [a-zA-Z0-9_ #=-]+)*\]", "", text)

HTTP = requests.Session()
