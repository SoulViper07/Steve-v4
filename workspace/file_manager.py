import difflib
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from .path_resolver import PathResolver
from .file_tracker import FileTracker


class FileManager:
    def __init__(self, resolver: PathResolver, tracker: FileTracker):
        self._resolver = resolver
        self._tracker = tracker
        self._backup_dir: Optional[Path] = None

    @property
    def resolver(self) -> PathResolver:
        return self._resolver

    def create(self, path: str, content: str) -> Tuple[bool, str]:
        abs_path = self._resolver.absolute(path)
        existed = abs_path.exists()
        if existed:
            existing = abs_path.read_text(encoding="utf-8", errors="replace") if abs_path.stat().st_size > 0 else ""
            if existing == content:
                return True, f"Already up to date: {path}"
            self._backup(abs_path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        self._tracker.track(abs_path, self._resolver.root)
        self._tracker.mark_generated(path)
        action = "Updated" if existed else "Created"
        lines = content.count("\n") + 1
        return True, f"{action} {path} ({lines} lines, {len(content)} chars)"

    def read(self, path: str) -> Optional[str]:
        abs_path = self._resolver.absolute(path)
        if not abs_path.exists():
            return None
        try:
            return abs_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    def update(self, path: str, content: str) -> Tuple[bool, str]:
        return self.create(path, content)

    def rename(self, old_path: str, new_path: str) -> Tuple[bool, str]:
        abs_old = self._resolver.absolute(old_path)
        abs_new = self._resolver.absolute(new_path)
        if not abs_old.exists():
            return False, f"File not found: {old_path}"
        if abs_new.exists():
            return False, f"Target already exists: {new_path}"
        abs_new.parent.mkdir(parents=True, exist_ok=True)
        abs_old.rename(abs_new)
        self._tracker.untrack(old_path)
        self._tracker.track(abs_new, self._resolver.root)
        self._tracker.track(abs_new, self._resolver.root)
        return True, f"Renamed {old_path} -> {new_path}"

    def move(self, old_path: str, new_path: str) -> Tuple[bool, str]:
        return self.rename(old_path, new_path)

    def delete(self, path: str) -> Tuple[bool, str]:
        abs_path = self._resolver.absolute(path)
        if not abs_path.exists():
            self._tracker.untrack(path)
            return True, f"Already deleted: {path}"
        self._backup(abs_path)
        abs_path.unlink()
        self._tracker.untrack(path)
        return True, f"Deleted {path}"

    def apply_surgical_edit(
        self,
        path: str,
        find_text: str,
        replace_text: str,
    ) -> Tuple[bool, str, str]:
        abs_path = self._resolver.absolute(path)
        if not abs_path.exists():
            return False, "File not found", ""
        original = abs_path.read_text(encoding="utf-8")
        strategies = [
            ("exact", lambda: self._exact_replace(original, find_text, replace_text)),
            ("ws_normalized", lambda: self._ws_normalized_replace(original, find_text, replace_text)),
            ("fuzzy", lambda: self._fuzzy_replace(original, find_text, replace_text)),
        ]
        for strategy_name, strategy_fn in strategies:
            result = strategy_fn()
            if result is not None:
                new_content, confidence = result
                self._backup(abs_path)
                abs_path.write_text(new_content, encoding="utf-8")
                self._tracker.mark_modified(path)
                self._tracker.track(abs_path, self._resolver.root)
                return True, f"Patched {path} via {strategy_name}", strategy_name
        return False, f"No match found in {path}", ""

    def smart_write(self, path: str, content: str) -> Tuple[bool, str]:
        abs_path = self._resolver.absolute(path)
        if not abs_path.exists():
            return self.create(path, content)
        existing = abs_path.read_text(encoding="utf-8", errors="replace") if abs_path.stat().st_size > 0 else ""
        if existing == content:
            return True, "No changes needed — already identical"
        if abs_path.stat().st_size < 102400:
            diff = list(difflib.unified_diff(
                existing.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{path}", tofile=f"b/{path}",
            ))
            if len(diff) <= 20:
                return self.create(path, content)
        return self.create(path, content)

    def backup(self, path: str) -> Optional[str]:
        abs_path = self._resolver.absolute(path)
        if not abs_path.exists():
            return None
        backup_path = self._backup(abs_path)
        return str(backup_path)

    def restore(self, backup_path: str) -> Tuple[bool, str]:
        bp = Path(backup_path)
        if not bp.exists():
            return False, f"Backup not found: {backup_path}"
        original_path = bp.with_suffix("") if bp.suffix == ".bak" else bp
        shutil.copy2(bp, original_path)
        return True, f"Restored {original_path.name} from backup"

    def list_backups(self) -> List[str]:
        if not self._backup_dir or not self._backup_dir.exists():
            return []
        return sorted(
            str(p) for p in self._backup_dir.iterdir()
            if p.suffix == ".bak"
        )

    def _backup(self, path: Path) -> Path:
        if self._backup_dir is None:
            self._backup_dir = self._resolver.root / ".steve" / "backups"
            self._backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_name = f"{path.name}.{timestamp}.bak"
        backup_path = self._backup_dir / backup_name
        shutil.copy2(path, backup_path)
        return backup_path

    def _exact_replace(self, text: str, find: str, replace: str) -> Optional[Tuple[str, float]]:
        if find in text:
            count = text.count(find)
            if count == 1:
                return text.replace(find, replace, 1), 1.0
        return None

    def _ws_normalized_replace(self, text: str, find: str, replace: str) -> Optional[Tuple[str, float]]:
        import re
        find_norm = re.sub(r"\s+", " ", find.strip())
        text_norm = re.sub(r"\s+", " ", text)
        idx = text_norm.find(find_norm)
        if idx == -1:
            return None
        char_idx = 0
        norm_idx = 0
        while norm_idx < idx:
            if text[char_idx].isspace():
                while char_idx < len(text) and text[char_idx].isspace():
                    char_idx += 1
                norm_idx += 1
            else:
                char_idx += 1
                norm_idx += 1
        end_char = char_idx
        text_end = text[char_idx:]
        find_end_norm = 0
        while find_end_norm < len(find_norm) and end_char < len(text):
            if text[end_char].isspace():
                while end_char < len(text) and text[end_char].isspace():
                    end_char += 1
                find_end_norm += 1
            else:
                end_char += 1
                find_end_norm += 1
        new_content = text[:char_idx] + replace + text[end_char:]
        return new_content, 0.9

    def _fuzzy_replace(self, text: str, find: str, replace: str) -> Optional[Tuple[str, float]]:
        find_lines = find.splitlines()
        text_lines = text.splitlines()
        window = len(find_lines)
        best_ratio = 0.0
        best_start = 0
        find_norm = " ".join(part.strip() for part in find_lines if part.strip())
        if not find_norm:
            return None
        for i in range(len(text_lines) - window + 1):
            block = "\n".join(text_lines[i:i + window])
            block_norm = " ".join(part.strip() for part in text_lines[i:i + window] if part.strip())
            if not block_norm:
                continue
            ratio = difflib.SequenceMatcher(None, find_norm, block_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i
        if best_ratio >= 0.72:
            start_idx = len("\n".join(text_lines[:best_start]))
            if best_start > 0:
                start_idx += 1
            end_idx = len("\n".join(text_lines[:best_start + window]))
            new_content = text[:start_idx] + replace + text[end_idx:]
            return new_content, best_ratio
        return None
