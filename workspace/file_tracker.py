import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class FileIndexEntry:
    path: str
    absolute_path: str
    file_type: str = ""
    size: int = 0
    last_modified: float = 0.0
    line_count: int = 0
    language: str = ""
    framework: str = ""
    generation_status: str = "unknown"
    verification_status: str = "unknown"
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    checksum: str = ""
    created_at: float = 0.0


LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".json": "json",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".sql": "sql",
    ".sh": "shell",
    ".bat": "batch",
    ".ps1": "powershell",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".dart": "dart",
    ".vue": "vue",
    ".svelte": "svelte",
    ".astro": "astro",
}

FRAMEWORK_DETECTORS = {
    "flask": {"requirements.txt", "app.py"},
    "django": {"manage.py", "django"},
    "fastapi": {"fastapi"},
    "react": {"react", "jsx"},
    "vue": {"vue"},
    "svelte": {"svelte"},
    "express": {"express", "package.json"},
    "nextjs": {"next.config", "next"},
    "tailwind": {"tailwind.config", "tailwindcss"},
    "bootstrap": {"bootstrap", "bootstrap.min.css"},
}


def _detect_language(path: str) -> str:
    return LANGUAGE_MAP.get(Path(path).suffix.lower(), "unknown")


def _detect_framework(files: List[str]) -> str:
    all_text = " ".join(f.lower() for f in files)
    for framework, keywords in FRAMEWORK_DETECTORS.items():
        if any(kw in all_text for kw in keywords):
            return framework
    return ""


def _compute_checksum(content: str) -> str:
    return str(hash(content)) if content else ""


class FileTracker:
    def __init__(self):
        self._index: Dict[str, FileIndexEntry] = {}
        self._modified_files: Set[str] = set()

    @property
    def index(self) -> Dict[str, FileIndexEntry]:
        return dict(self._index)

    @property
    def all_files(self) -> List[str]:
        return list(self._index.keys())

    def get(self, path: str) -> Optional[FileIndexEntry]:
        return self._index.get(path)

    def track(self, path: Path, project_root: Path) -> FileIndexEntry:
        rel = str(path.resolve().relative_to(project_root)).replace("\\", "/") if path.is_absolute() else path.as_posix()
        abs_path = str(path.resolve())
        try:
            stat = path.stat()
            size = stat.st_size
            mtime = stat.st_mtime
        except OSError:
            size = 0
            mtime = 0.0
        content = ""
        if size > 0 and size < 1048576:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
        line_count = content.count("\n") + 1 if content else 0
        language = _detect_language(rel)
        entry = FileIndexEntry(
            path=rel,
            absolute_path=abs_path,
            file_type=Path(rel).suffix.lower(),
            size=size,
            last_modified=mtime,
            line_count=line_count,
            language=language,
            generation_status="tracked",
            verification_status="unknown",
            checksum=_compute_checksum(content),
            created_at=mtime,
        )
        self._index[rel] = entry
        return entry

    def untrack(self, path: str):
        self._index.pop(path, None)
        self._modified_files.discard(path)

    def mark_modified(self, path: str):
        self._modified_files.add(path)
        entry = self._index.get(path)
        if entry:
            entry.last_modified = time.time()
            entry.generation_status = "modified"
            entry.verification_status = "unknown"

    def mark_generated(self, path: str):
        entry = self._index.get(path)
        if entry:
            entry.generation_status = "generated"

    def mark_verified(self, path: str, status: str = "passed"):
        entry = self._index.get(path)
        if entry:
            entry.verification_status = status

    def detect_framework(self) -> str:
        return _detect_framework(list(self._index.keys()))

    def by_language(self, language: str) -> List[FileIndexEntry]:
        return [e for e in self._index.values() if e.language == language]

    def by_type(self, file_type: str) -> List[FileIndexEntry]:
        return [e for e in self._index.values() if e.file_type == file_type]

    def stats(self) -> dict:
        if not self._index:
            return {"total": 0, "languages": {}, "types": {}}
        langs = {}
        types = {}
        for entry in self._index.values():
            langs[entry.language] = langs.get(entry.language, 0) + 1
            types[entry.file_type] = types.get(entry.file_type, 0) + 1
        return {
            "total": len(self._index),
            "languages": dict(sorted(langs.items(), key=lambda x: -x[1])),
            "types": dict(sorted(types.items(), key=lambda x: -x[1])),
            "generated": sum(1 for e in self._index.values() if e.generation_status == "generated"),
            "verified": sum(1 for e in self._index.values() if e.verification_status == "passed"),
            "modified": len(self._modified_files),
        }

    def clear(self):
        self._index.clear()
        self._modified_files.clear()
