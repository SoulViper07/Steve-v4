from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set


@dataclass
class FileEntry:
    path: str
    absolute_path: str
    file_name: str
    extension: str
    size: int
    is_dir: bool = False
    children: List["FileEntry"] = field(default_factory=list)


@dataclass
class ProjectTree:
    root: str
    total_files: int = 0
    total_dirs: int = 0
    total_size: int = 0
    entries: List[FileEntry] = field(default_factory=list)
    flat_list: List[str] = field(default_factory=list)


DEFAULT_EXCLUDED_DIRS: Set[str] = {
    ".git", "__pycache__", ".venv", "venv", "env", "node_modules",
    ".tox", "dist", "build", ".next", ".nuxt", "target", "bin", "obj",
    "vendor", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".steve",
    "logs", "cache", ".opencode", ".idea", ".vscode",
}

DEFAULT_EXCLUDED_EXTS: Set[str] = {
    ".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib", ".bin", ".obj",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2",
    ".ttf", ".eot", ".mp3", ".mp4", ".pdf", ".zip", ".tar", ".gz",
}


def _build_entry(path: Path, root: Path) -> FileEntry:
    rel = str(path.relative_to(root)).replace("\\", "/") if path != root else "."
    return FileEntry(
        path=rel,
        absolute_path=str(path.resolve()),
        file_name=path.name,
        extension=path.suffix.lower(),
        size=path.stat().st_size if path.is_file() else 0,
        is_dir=path.is_dir(),
    )


class ProjectScanner:
    def __init__(
        self,
        excluded_dirs: Optional[Set[str]] = None,
        excluded_exts: Optional[Set[str]] = None,
    ):
        self._excluded_dirs = excluded_dirs or DEFAULT_EXCLUDED_DIRS
        self._excluded_exts = excluded_exts or DEFAULT_EXCLUDED_EXTS

    def scan(self, root: Path, recursive: bool = True) -> ProjectTree:
        root = root.resolve()
        if not root.is_dir():
            return ProjectTree(root=str(root))
        tree = ProjectTree(root=str(root))
        tree.entries = self._scan_dir(root, root, recursive)
        tree.flat_list = self._flatten(tree.entries)
        tree.total_dirs = sum(1 for e, _ in self._walk(tree.entries) if e.is_dir)
        tree.total_files = sum(1 for e, _ in self._walk(tree.entries) if not e.is_dir)
        tree.total_size = sum(e.size for e, _ in self._walk(tree.entries))
        return tree

    def _walk(self, entries: List[FileEntry]):
        for entry in entries:
            yield entry, entry.path
            if entry.children:
                yield from self._walk(entry.children)

    def _scan_dir(self, dir_path: Path, root: Path, recursive: bool) -> List[FileEntry]:
        entries: List[FileEntry] = []
        try:
            children = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return entries
        for child in children:
            if self._is_excluded(child):
                continue
            entry = _build_entry(child, root)
            if child.is_dir() and recursive:
                entry.children = self._scan_dir(child, root, recursive)
            entries.append(entry)
        return entries

    def _is_excluded(self, path: Path) -> bool:
        if path.name in self._excluded_dirs:
            return True
        if path.is_file() and path.suffix.lower() in self._excluded_exts:
            return True
        return False

    def _flatten(self, entries: List[FileEntry]) -> List[str]:
        result: List[str] = []
        for entry in entries:
            result.append(entry.path)
            if entry.children:
                result.extend(self._flatten(entry.children))
        return result

    def scan_flat(self, root: Path) -> List[str]:
        tree = self.scan(root)
        return tree.flat_list
