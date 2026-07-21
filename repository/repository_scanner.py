import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime


EXCLUDED_DIRS: Set[str] = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    ".env", ".steve", "build", "dist", ".next", ".nuxt",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".idea", ".vscode", ".vs", "coverage", ".tox",
    "eggs", "target", "bin", "obj", "lib", "include",
    ".yardoc", "doc", ".dart_tool", ".packages", ".pub-cache",
    ".gradle", ".svn", "CVS", ".hg",
}

EXCLUDED_EXTENSIONS: Set[str] = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib",
    ".exe", ".msi", ".bin", ".o", ".a", ".lib",
    ".class", ".jar", ".war",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".mp3", ".mp4", ".avi", ".mov", ".wav",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".db", ".sqlite", ".sqlite3",
    ".log", ".tmp", ".bak", ".swp",
    ".DS_Store", ".gitkeep",
}


@dataclass
class ScanResult:
    total_files: int = 0
    total_dirs: int = 0
    total_lines: int = 0
    total_size: int = 0
    file_paths: List[str] = field(default_factory=list)
    dir_paths: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    asset_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    environment_files: List[str] = field(default_factory=list)
    build_files: List[str] = field(default_factory=list)
    package_manager_files: List[str] = field(default_factory=list)
    binary_files: List[str] = field(default_factory=list)
    scanned_at: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: float = 0.0

    @property
    def summary(self) -> Dict:
        return {
            "total_files": self.total_files,
            "total_dirs": self.total_dirs,
            "total_lines": self.total_lines,
            "total_size_kb": round(self.total_size / 1024, 1),
            "config_files": len(self.config_files),
            "entry_points": len(self.entry_points),
            "assets": len(self.asset_files),
            "tests": len(self.test_files),
            "environment_files": len(self.environment_files),
            "scanned_at": self.scanned_at,
        }


ENTRY_POINT_PATTERNS: List[str] = [
    "main.py", "app.py", "application.py", "wsgi.py", "manage.py",
    "index.js", "index.ts", "index.jsx", "index.tsx",
    "server.js", "server.ts", "app.js", "app.ts",
    "main.js", "main.ts", "cli.js", "cli.ts",
    "agent.py", "cli.py",
    "package.json", "Dockerfile",
]

CONFIG_FILE_PATTERNS: Set[str] = {
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "requirements.txt", "Pipfile", "Pipfile.lock",
    "pyproject.toml", "setup.py", "setup.cfg",
    "Cargo.toml", "Cargo.lock",
    "go.mod", "go.sum",
    "Gemfile", "Gemfile.lock",
    "composer.json", "composer.lock",
    "build.gradle", "build.gradle.kts", "pom.xml",
    "Makefile", "CMakeLists.txt",
    "tsconfig.json", "tsconfig.build.json",
    "webpack.config.js", "vite.config.js", "vite.config.ts",
    "next.config.js", "nuxt.config.js",
    "tailwind.config.js", "postcss.config.js",
    ".gitignore", ".dockerignore", ".npmignore",
    "docker-compose.yml", "docker-compose.yaml",
    "Dockerfile",
    ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".prettierrc",
    ".babelrc", "babel.config.js",
}

ENVIRONMENT_FILE_PATTERNS: Set[str] = {
    ".env", ".env.example", ".env.local", ".env.production",
    ".env.development", ".env.test",
    ".env.sample", "env.example",
}

ASSET_EXTENSIONS: Set[str] = {
    ".html", ".css", ".scss", ".sass", ".less",
    ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".json", ".xml", ".yaml", ".yml", ".toml",
    ".md", ".rst", ".txt",
}


class RepositoryScanner:
    def __init__(self, excluded_dirs: Optional[Set[str]] = None, excluded_extensions: Optional[Set[str]] = None):
        self._excluded_dirs = excluded_dirs or EXCLUDED_DIRS
        self._excluded_extensions = excluded_extensions or EXCLUDED_EXTENSIONS

    def scan(self, root_path: str) -> ScanResult:
        import time
        start = time.time()
        root = Path(root_path).resolve()
        result = ScanResult()

        if not root.exists():
            return result

        for dirpath, dirnames, filenames in os.walk(str(root)):
            rel_dir = Path(dirpath).relative_to(root)
            parts = set(rel_dir.parts) if str(rel_dir) != "." else set()

            dirnames[:] = [d for d in dirnames if d not in self._excluded_dirs]
            dirnames.sort()

            if str(rel_dir) != ".":
                result.dir_paths.append(str(rel_dir))
                result.total_dirs += 1

            for fname in sorted(filenames):
                ext = Path(fname).suffix.lower()
                if ext in self._excluded_extensions:
                    continue

                rel_path = str(rel_dir / fname) if str(rel_dir) != "." else fname
                result.file_paths.append(rel_path)
                result.total_files += 1

                try:
                    fp = Path(dirpath) / fname
                    stat = fp.stat()
                    result.total_size += stat.st_size
                    if stat.st_size > 0 and ext not in self._excluded_extensions:
                        try:
                            lines = fp.read_text(encoding="utf-8", errors="replace").count("\n") + 1
                            result.total_lines += lines
                        except Exception:
                            pass
                except Exception:
                    pass

                self._classify_file(rel_path, fname, result)

        result.duration_ms = round((time.time() - start) * 1000, 2)
        return result

    def _classify_file(self, rel_path: str, fname: str, result: ScanResult):
        if fname in ENTRY_POINT_PATTERNS:
            result.entry_points.append(rel_path)
        if fname in CONFIG_FILE_PATTERNS:
            result.config_files.append(rel_path)
        if fname in ENVIRONMENT_FILE_PATTERNS:
            result.environment_files.append(rel_path)
        if "test" in fname.lower() or "spec" in fname.lower() or "test_" in fname or "_test" in fname:
            result.test_files.append(rel_path)
        if any(pkg in fname for pkg in ("package", "yarn", "pnpm", "requirements", "Pipfile", "Gemfile", "Cargo", "go.mod", "composer")):
            result.package_manager_files.append(rel_path)
        if any(build in fname.lower() for build in ("Makefile", "CMake", "build.gradle", "pom.xml", "Dockerfile")):
            result.build_files.append(rel_path)
        ext = Path(fname).suffix.lower()
        if ext in ASSET_EXTENSIONS and fname not in CONFIG_FILE_PATTERNS:
            result.asset_files.append(rel_path)

    def scan_file_list(self, file_paths: List[str]) -> Dict:
        return {
            "total": len(file_paths),
            "entry_points": [f for f in file_paths if Path(f).name in ENTRY_POINT_PATTERNS],
            "config_files": [f for f in file_paths if Path(f).name in CONFIG_FILE_PATTERNS],
            "test_files": [f for f in file_paths if "test" in Path(f).stem.lower() or "spec" in Path(f).stem.lower()],
        }
