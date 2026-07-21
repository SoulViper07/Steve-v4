from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field


LANGUAGE_EXTENSIONS: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React JSX)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React TSX)",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SASS",
    ".less": "Less",
    ".json": "JSON",
    ".xml": "XML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin Script",
    ".rs": "Rust",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".h": "C Header",
    ".cpp": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".swift": "Swift",
    ".r": "R",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".dart": "Dart",
    ".lua": "Lua",
    ".ex": "Elixir",
    ".exs": "Elixir Script",
    ".erl": "Erlang",
    ".hrl": "Erlang Header",
    ".clj": "Clojure",
    ".scala": "Scala",
    ".hs": "Haskell",
    ".svelte": "Svelte",
    ".vue": "Vue",
    ".astro": "Astro",
    ".sqlite": "SQLite",
    ".graphql": "GraphQL",
    ".gql": "GraphQL",
    ".proto": "Protocol Buffers",
    ".zig": "Zig",
    ".nim": "Nim",
    ".crystal": "Crystal",
    ".fs": "F#",
    ".fsx": "F# Script",
    ".prisma": "Prisma",
    ".tf": "Terraform",
    ".tfvars": "Terraform Variables",
    ".dockerfile": "Dockerfile",
    ".sol": "Solidity",
    ".pyx": "Cython",
    ".pxd": "Cython Definition",
}


@dataclass
class LanguageInfo:
    name: str
    extensions: List[str] = field(default_factory=list)
    file_count: int = 0
    line_count: int = 0
    percentage: float = 0.0


class LanguageDetector:
    def __init__(self):
        self._extension_map = LANGUAGE_EXTENSIONS.copy()

    def detect(self, file_path: str) -> Optional[str]:
        ext = Path(file_path).suffix.lower()
        if ext == ".dockerfile":
            return "Dockerfile"
        if Path(file_path).name.lower() == "dockerfile":
            return "Dockerfile"
        return self._extension_map.get(ext)

    def detect_from_path(self, file_path: str) -> Optional[str]:
        path = Path(file_path)
        name_lower = path.name.lower()
        if name_lower == "dockerfile":
            return "Dockerfile"
        if name_lower == "makefile":
            return "Makefile"
        if name_lower in ("gemfile", "gemfile.lock"):
            return "Ruby"
        if name_lower == "cmakelists.txt":
            return "CMake"
        return self.detect(file_path)

    def analyze_directory(self, files: List[str]) -> Dict[str, LanguageInfo]:
        lang_counts: Dict[str, int] = {}
        lang_lines: Dict[str, int] = {}
        lang_exts: Dict[str, set] = {}
        total = len(files)

        for f in files:
            lang = self.detect_from_path(f)
            if not lang:
                ext = Path(f).suffix.lower()
                if ext:
                    lang = f"Unknown ({ext})"
                else:
                    lang = "Unknown"
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
            lang_lines.setdefault(lang, 0)
            lang_exts.setdefault(lang, set()).add(Path(f).suffix.lower())

        result: Dict[str, LanguageInfo] = {}
        for name, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
            pct = round(count / total * 100, 1) if total else 0.0
            result[name] = LanguageInfo(
                name=name,
                extensions=sorted(lang_exts.get(name, set())),
                file_count=count,
                line_count=lang_lines.get(name, 0),
                percentage=pct,
            )
        return result

    @property
    def supported_languages(self) -> List[str]:
        return sorted(set(self._extension_map.values()))
