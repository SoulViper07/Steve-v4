import re
from datetime import datetime
from pathlib import Path

from .helpers import redact_secret_text

class SteveDebugLog:
    def __init__(self, workdir: Path):
        self.workdir = Path(workdir).resolve()
        self.path = self.workdir / ".steve" / "logs" / "latest.log"
        self.repeated: dict[str, int] = {}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(f"Steve debug log started {datetime.now().isoformat(timespec='seconds')}\n", encoding="utf-8")
        except Exception:
            pass

    def log(self, message: str):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(message.rstrip() + "\n")
        except Exception:
            pass

    def section(self, title: str, body: str = ""):
        self.log(f"\n=== {title} ===")
        if body:
            self.log(body)

    def repeated_error(self, message: str):
        key = re.sub(r"\s+", " ", message.strip())
        self.repeated[key] = self.repeated.get(key, 0) + 1
        if self.repeated[key] == 1:
            self.log("ERROR: " + message)
        else:
            self.log(f"ERROR repeated {self.repeated[key]}x: {message}")

    def display_path(self) -> str:
        try:
            return self.path.relative_to(self.workdir).as_posix()
        except ValueError:
            return str(self.path)
