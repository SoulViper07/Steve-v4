import os
from pathlib import Path
from typing import List, Optional, Set


EXCLUDED_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env", "node_modules",
    ".tox", "dist", "build", ".next", ".nuxt", "target", "bin", "obj",
    "vendor", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".steve",
    "logs", "cache", ".opencode", ".idea", ".vscode",
}

EXCLUDED_EXTS = {".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib", ".bin", ".obj"}


class PathResolver:
    def __init__(self, root: Path):
        self._root = root.resolve()

    @property
    def root(self) -> Path:
        return self._root

    def absolute(self, path: str) -> Path:
        p = Path(path)
        return (self._root / p).resolve() if not p.is_absolute() else p.resolve()

    def relative(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self._root)).replace("\\", "/")
        except ValueError:
            return str(path)

    def exists(self, path: str) -> bool:
        return self.absolute(path).exists()

    def is_inside(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self._root)
            return True
        except ValueError:
            return False

    def is_excluded(self, path: Path) -> bool:
        try:
            rel = path.resolve().relative_to(self._root)
        except ValueError:
            return True
        parts = rel.parts
        for part in parts:
            if part in EXCLUDED_DIRS:
                return True
        return path.suffix.lower() in EXCLUDED_EXTS

    def list_dir(self, path: str, recursive: bool = False) -> List[Path]:
        target = self.absolute(path)
        if not target.is_dir():
            return []
        if recursive:
            return sorted([
                p for p in target.rglob("*")
                if p.is_file() and not self.is_excluded(p)
            ])
        return sorted([p for p in target.iterdir() if p.is_file()])

    def resolve_glob(self, pattern: str) -> List[str]:
        matches = list(self._root.glob(pattern))
        return [self.relative(m) for m in matches]

    def ensure_dir(self, path: str) -> Path:
        p = self.absolute(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def parent(self, path: str) -> str:
        return self.relative(self.absolute(path).parent)

    def join(self, *parts: str) -> str:
        return str(Path(*parts)).replace("\\", "/")

    def normalize(self, path: str) -> str:
        return Path(path).as_posix()
