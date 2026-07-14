import glob
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from .models import ProjectMap
from config.settings import (
    AUTOLOAD_PROJECT_EXTS, AUTOLOAD_EXCLUDED_DIRS, 
    AUTOLOAD_PROJECT_MAX_FILES, AUTOLOAD_PROJECT_MAX_BYTES,
    MAX_FILE_SNIPPET_CHARS, MAX_CONTEXT_CHARS, MAX_CONTEXT_FILES_PER_TURN,
    PLAIN_UI
)
from ui.terminal_renderer import console, _plain_terminal, get_symbol

def _is_excluded_path_part(part: str) -> bool:
    lowered = part.lower()
    return lowered in AUTOLOAD_EXCLUDED_DIRS or bool(re.fullmatch(r"tmp[a-z0-9_]{6,}", lowered))

def _extract_terms(text: str) -> List[str]:
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text.lower())

class FileContext:
    def __init__(self, workdir: Optional[Path] = None):
        self.workdir = Path(workdir).resolve() if workdir else Path.cwd().resolve()
        self.files: Dict[str, str] = {}
        self._context_cache = ""
        self._dirty = True
        self.pending: List[str] = []
        self._manifest_cache = ""
        self.project_map: Optional[ProjectMap] = None
        self.recently_modified: List[str] = []

    def set_workdir(self, workdir: Path):
        self.workdir = Path(workdir).resolve()
        self.project_map = None
        self.recently_modified.clear()

    def _mark_pending(self, key: str):
        if key not in self.pending:
            self.pending.append(key)

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str).expanduser()
        return p.resolve() if p.is_absolute() else (self.workdir / p).resolve()

    def load(self, pattern: str) -> List[str]:
        loaded = []
        p = Path(pattern).expanduser()
        search = str(p if p.is_absolute() else self.workdir / p)
        paths = glob.glob(search, recursive=True)
        if not paths:
            p = self._resolve(pattern)
            if p.exists() and p.is_file(): paths = [str(p)]
        for path in paths:
            try:
                resolved = Path(path).resolve()
                key = str(resolved)
                self.files[key] = resolved.read_text(encoding="utf-8", errors="replace")
                loaded.append(key)
                self._dirty = True
                self._mark_pending(key)
            except Exception as e:
                console.print(f"[red]Cannot read {path}: {e}[/red]")
        return loaded

    def load_paths(self, paths: List[Path]) -> List[str]:
        loaded = []
        for path in paths:
            try:
                resolved = Path(path).resolve()
                key = str(resolved)
                self.files[key] = resolved.read_text(encoding="utf-8", errors="replace")
                loaded.append(key)
                self._dirty = True
                self._mark_pending(key)
            except Exception as e:
                console.print(f"[red]Cannot read {path}: {e}[/red]")
        return loaded

    def _autoload_score(self, path: Path):
        try:
            rel = path.resolve().relative_to(self.workdir)
            parts = rel.parts
        except Exception:
            rel = path
            parts = path.parts
        name = path.name.lower()
        stem = path.stem.lower()
        ext_order = {".html": 0, ".css": 1, ".js": 2}.get(path.suffix.lower(), 9)
        important = 0 if stem in {"index", "app", "main", "style", "styles", "script", "scripts"} else 1
        return (len(parts), ext_order, important, str(rel).lower())

    def discover_project_files(self) -> List[Path]:
        candidates = []
        for ext in AUTOLOAD_PROJECT_EXTS:
            try:
                iterator = self.workdir.rglob(f"*{ext}")
                for path in iterator:
                    if not path.is_file():
                        continue
                    rel_parts = [part.lower() for part in path.relative_to(self.workdir).parts[:-1]]
                    if any(_is_excluded_path_part(part) for part in rel_parts):
                        continue
                    name = path.name.lower()
                    if name.endswith(".min.js") or name.endswith(".min.css"):
                        continue
                    try:
                        if path.stat().st_size > AUTOLOAD_PROJECT_MAX_BYTES:
                            continue
                    except OSError:
                        continue
                    key = str(path.resolve())
                    if key not in self.files:
                        candidates.append(path)
            except Exception:
                continue
        candidates.sort(key=self._autoload_score)
        return candidates[:AUTOLOAD_PROJECT_MAX_FILES]

    def autoload_project_files(self) -> List[str]:
        return self.load_paths(self.discover_project_files())

    def unload(self, pat: str) -> List[str]:
        r = [k for k in list(self.files) if pat in k]
        for k in r: del self.files[k]
        if r:
            self._dirty = True
            self.pending = [p for p in self.pending if p not in r]
        return r

    def clear(self):
        self.files.clear()
        self._dirty = True
        self.pending.clear()
        self.project_map = None
        self.recently_modified.clear()

    def set_project_map(self, project_map: Optional[ProjectMap]):
        self.project_map = project_map

    def note_modified(self, paths: List[str]):
        for path in paths:
            resolved = str(self._resolve(path))
            if resolved in self.recently_modified:
                self.recently_modified.remove(resolved)
            self.recently_modified.insert(0, resolved)
        self.recently_modified = self.recently_modified[:8]

    def _path_score(self, path: str, terms: List[str]) -> int:
        path_l = path.lower()
        name_l = Path(path).name.lower()
        score = 0
        for term in terms:
            if term == name_l or term == path_l:
                score += 8
            elif term in name_l:
                score += 5
            elif term in path_l:
                score += 3
        return score

    def _line_score(self, line: str, terms: List[str]) -> int:
        line_l = line.lower()
        score = 0
        for term in terms:
            if term in line_l:
                score += 2
                if re.search(rf"\b{re.escape(term)}\b", line_l):
                    score += 1
        if re.match(r"\s*(def|class|function|const|let|var|interface|type)\b", line_l):
            score += 1
        return score

    def _relevance_windows(self, path: str, content: str, user_text: str) -> str:
        if len(content) <= MAX_FILE_SNIPPET_CHARS:
            return content

        terms = _extract_terms(user_text)
        lines = content.splitlines()
        if not lines:
            return ""

        scored = []
        path_bonus = self._path_score(path, terms)
        for idx, line in enumerate(lines):
            score = self._line_score(line, terms) + path_bonus
            if score > 0:
                scored.append((score, idx))

        if not scored:
            head = content[: max(240, MAX_FILE_SNIPPET_CHARS // 2)]
            tail = content[-max(120, MAX_FILE_SNIPPET_CHARS // 3):]
            return head + "\n...[middle truncated]...\n" + tail

        scored.sort(key=lambda item: (-item[0], item[1]))
        windows = []
        window_radius = 6
        for _, idx in scored[:8]:
            start = max(0, idx - window_radius)
            end = min(len(lines), idx + window_radius + 1)
            windows.append((start, end))

        merged = []
        for start, end in sorted(windows):
            if not merged or start > merged[-1][1] + 2:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        sections = []
        used = 0
        for start, end in merged:
            block_lines = lines[start:end]
            label = f"... lines {start + 1}-{end} ..."
            block = label + "\n" + "\n".join(block_lines)
            if sections:
                block = "\n...\n" + block
            if used + len(block) > MAX_FILE_SNIPPET_CHARS:
                remaining = MAX_FILE_SNIPPET_CHARS - used
                if remaining <= 0:
                    break
                block = block[:remaining].rstrip() + "\n...[truncated]"
            sections.append(block)
            used += len(block)
            if used >= MAX_FILE_SNIPPET_CHARS:
                break
        return "".join(sections)

    def _rebuild_caches(self):
        if not self.files:
            self._context_cache = ""
            self._manifest_cache = ""
            self._dirty = False
            return
        parts = ["Loaded files index:"]
        for path, content in self.files.items():
            parts.append(f"- {path} ({len(content):,} chars)")
        self._manifest_cache = "\n".join(parts)
        self._context_cache = self._manifest_cache
        self._dirty = False

    def build_context_block(self) -> str:
        if not self.files:
            self._context_cache = ""
            return ""
        if self._dirty:
            self._rebuild_caches()
        return self._context_cache

    def manifest(self) -> str:
        if self._dirty:
            self._rebuild_caches()
        return self._manifest_cache

    def _match_referenced(self, user_text: str) -> List[str]:
        if not user_text or not self.files:
            return []
        lowered = user_text.lower()
        matches = []
        for path in self.files:
            p = Path(path)
            path_l = path.lower()
            base = p.name.lower()
            stem = p.stem.lower()
            if path_l in lowered or base in lowered:
                matches.append(path)
                continue
            if len(stem) >= 3 and re.search(rf"\b{re.escape(stem)}\b", lowered):
                matches.append(path)
        return matches

    def build_turn_context(self, user_text: str, active_files=None) -> Tuple[str, List[str]]:
        if not self.files and not self.project_map:
            return "", []
        if self._dirty:
            self._rebuild_caches()

        active_files = list(active_files or [])
        selected = []
        selection_limit = min(6, MAX_CONTEXT_FILES_PER_TURN + 2)
        selection_pool = list(self.pending) + self._match_referenced(user_text) + active_files + self.recently_modified
        if self.project_map:
            # Note: project_map attributes like important_files would be defined in models.py or ProjectInspector
            pass 
        for path in selection_pool:
            if path in self.files and path not in selected:
                selected.append(path)
            if len(selected) >= selection_limit:
                break

        parts = []
        if self.project_map:
            parts.append("Project map:")
            # parts.append(self.project_map.to_block()) # Need to implement to_block
        if self._manifest_cache:
            parts.append(self._manifest_cache)
        if selected:
            parts.append("\nRelevant loaded file snippets:")
            total = 0
            for path in selected:
                content = self.files[path]
                snippet = self._relevance_windows(path, content, user_text)
                if total + len(snippet) > MAX_CONTEXT_CHARS:
                    rem = MAX_CONTEXT_CHARS - total
                    if rem <= 0:
                        parts.append("\n[...truncated - context limit reached...]")
                        break
                    snippet = snippet[:rem] + "\n...[truncated]"
                lang = self._lang(path)
                parts.append(f"\n### File: `{path}`\n```{lang}\n{snippet}\n```")
                total += len(snippet)
        if selected:
            self.pending = [p for p in self.pending if p not in selected]
        return "\n".join(parts), selected

    def _lang(self, path: str) -> str:
        m = {".py":"python",".js":"javascript",".ts":"typescript",".jsx":"jsx",
             ".tsx":"tsx",".java":"java",".c":"c",".cpp":"cpp",".cs":"csharp",
             ".go":"go",".rs":"rust",".rb":"ruby",".php":"php",".sh":"bash",
             ".md":"markdown",".json":"json",".yaml":"yaml",".yml":"yaml",
             ".toml":"toml",".html":"html",".css":"css",".sql":"sql",".dart":"dart"}
        return m.get(Path(path).suffix.lower(), "")

    def summary(self) -> str:
        if not self.files:
            return "  No files loaded." if PLAIN_UI else "  [dim]No files loaded.[/dim]"
        if _plain_terminal():
            return "\n".join(f"  - {p} ({len(c):,} chars)" for p, c in self.files.items())
        sym = get_symbol("*", "*")
        return "\n".join(
            f"  [green]{sym}[/green] [cyan]{p}[/cyan] [dim]({len(c):,} chars)[/dim]"
            for p,c in self.files.items()
        )

    def reload(self, path: str):
        """Reload a file after it's been modified."""
        try:
            resolved = self._resolve(path)
            key = str(resolved)
            if key in self.files:
                self.files[key] = resolved.read_text(encoding="utf-8", errors="replace")
                self._dirty = True
        except Exception:
            pass
