from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from .diff_engine import DiffEngine, DiffResult, DiffType


PATCH_CREATE = "create"
PATCH_MODIFY = "modify"
PATCH_RENAME = "rename"
PATCH_DELETE = "delete"
PATCH_MOVE = "move"
PATCH_RESTORE = "restore"
PATCH_ROLLBACK = "rollback"


@dataclass
class PatchResult:
    success: bool
    operation: str
    path: str
    message: str = ""
    diff: Optional[DiffResult] = None
    backup_path: str = ""
    old_size: int = 0
    new_size: int = 0
    line_count: int = 0


class PatchExecutor:
    def __init__(self, workdir: Path):
        self._workdir = workdir.resolve()
        self._diff_engine = DiffEngine()
        self._backup_dir = workdir / ".steve" / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    @property
    def diff_engine(self) -> DiffEngine:
        return self._diff_engine

    def create(self, path: str, content: str) -> PatchResult:
        abs_path = self._workdir / path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        if abs_path.exists():
            existing = abs_path.read_text(encoding="utf-8", errors="replace")
            diff = self._diff_engine.compute(existing, content, f"a/{path}", f"b/{path}")
            if not diff.has_changes:
                return PatchResult(True, PATCH_MODIFY, path, "Already up to date", diff=diff)
            self._backup(abs_path)
        abs_path.write_text(content, encoding="utf-8")
        lines = content.count("\n") + 1
        diff = self._diff_engine.compute("", content, "", path)
        return PatchResult(
            True, PATCH_CREATE, path,
            f"Created {path} ({lines} lines, {len(content)} chars)",
            diff=diff,
            new_size=len(content),
            line_count=lines,
        )

    def modify(self, path: str, content: str) -> PatchResult:
        abs_path = self._workdir / path
        if not abs_path.exists():
            return PatchResult(False, PATCH_MODIFY, path, f"File not found: {path}")
        existing = abs_path.read_text(encoding="utf-8", errors="replace")
        diff = self._diff_engine.compute(existing, content, f"a/{path}", f"b/{path}")
        if not diff.has_changes:
            return PatchResult(True, PATCH_MODIFY, path, "No changes needed", diff=diff)
        self._backup(abs_path)
        abs_path.write_text(content, encoding="utf-8")
        lines = content.count("\n") + 1
        return PatchResult(
            True, PATCH_MODIFY, path,
            f"Modified {path}: {diff.impact_summary}",
            diff=diff,
            old_size=len(existing),
            new_size=len(content),
            line_count=lines,
        )

    def rename(self, old_path: str, new_path: str) -> PatchResult:
        abs_old = self._workdir / old_path
        abs_new = self._workdir / new_path
        if not abs_old.exists():
            return PatchResult(False, PATCH_RENAME, old_path, f"File not found: {old_path}")
        if abs_new.exists():
            return PatchResult(False, PATCH_RENAME, old_path, f"Target already exists: {new_path}")
        abs_new.parent.mkdir(parents=True, exist_ok=True)
        abs_old.rename(abs_new)
        return PatchResult(
            True, PATCH_RENAME, new_path,
            f"Renamed {old_path} -> {new_path}",
        )

    def delete(self, path: str) -> PatchResult:
        abs_path = self._workdir / path
        if not abs_path.exists():
            return PatchResult(True, PATCH_DELETE, path, "Already deleted")
        content = abs_path.read_text(encoding="utf-8", errors="replace") if abs_path.stat().st_size > 0 else ""
        self._backup(abs_path)
        abs_path.unlink()
        return PatchResult(
            True, PATCH_DELETE, path,
            f"Deleted {path}",
            old_size=len(content),
        )

    def move(self, old_path: str, new_path: str) -> PatchResult:
        return self.rename(old_path, new_path)

    def restore(self, path: str) -> PatchResult:
        abs_path = self._workdir / path
        latest = self._find_latest_backup(path)
        if not latest:
            return PatchResult(False, PATCH_RESTORE, path, f"No backup found for {path}")
        content = latest.read_text(encoding="utf-8", errors="replace")
        abs_path.write_text(content, encoding="utf-8")
        return PatchResult(
            True, PATCH_RESTORE, path,
            f"Restored {path} from backup",
            new_size=len(content),
        )

    def rollback(self, path: str) -> PatchResult:
        abs_path = self._workdir / path
        backups = self._list_backups(path)
        if len(backups) < 2:
            return PatchResult(False, PATCH_ROLLBACK, path, f"Not enough backups to rollback {path}")
        last = backups[-1]
        current_content = last.read_text(encoding="utf-8", errors="replace")
        abs_path.write_text(current_content, encoding="utf-8")
        last.unlink()
        return PatchResult(
            True, PATCH_ROLLBACK, path,
            f"Rolled back {path} to previous version",
            new_size=len(current_content),
        )

    def apply_surgical(self, path: str, find: str, replace: str) -> PatchResult:
        abs_path = self._workdir / path
        if not abs_path.exists():
            return PatchResult(False, "edit", path, f"File not found: {path}")
        original = abs_path.read_text(encoding="utf-8", errors="replace")
        strategies = [
            ("exact", lambda: self._exact(original, find, replace)),
            ("ws_normalized", lambda: self._ws_normalized(original, find, replace)),
            ("fuzzy", lambda: self._fuzzy(original, find, replace)),
        ]
        for name, fn in strategies:
            result = fn()
            if result is not None:
                new_content, _ = result
                diff = self._diff_engine.compute(original, new_content, f"a/{path}", f"b/{path}")
                self._backup(abs_path)
                abs_path.write_text(new_content, encoding="utf-8")
                return PatchResult(
                    True, "edit", path,
                    f"Patched {path} via {name}: {diff.impact_summary}",
                    diff=diff, old_size=len(original), new_size=len(new_content),
                )
        return PatchResult(False, "edit", path, f"No match found in {path}")

    def _backup(self, path: Path) -> Path:
        import time
        import shutil
        ns = time.time_ns()
        backup_path = self._backup_dir / f"{path.name}.{ns}.bak"
        shutil.copy2(path, backup_path)
        return backup_path

    def _find_latest_backup(self, path: str) -> Optional[Path]:
        name = Path(path).name
        backups = sorted(self._backup_dir.glob(f"{name}.*.bak"))
        return backups[-1] if backups else None

    def _list_backups(self, path: str) -> List[Path]:
        name = Path(path).name
        return sorted(self._backup_dir.glob(f"{name}.*.bak"))

    def _exact(self, text: str, find: str, replace: str):
        if find in text and text.count(find) == 1:
            return text.replace(find, replace, 1), 1.0
        return None

    def _ws_normalized(self, text: str, find: str, replace: str):
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
        while norm_idx < len(find_norm) and end_char < len(text):
            if text[end_char].isspace():
                while end_char < len(text) and text[end_char].isspace():
                    end_char += 1
                norm_idx += 1
            else:
                end_char += 1
                norm_idx += 1
        return text[:char_idx] + replace + text[end_char:], 0.9

    def _fuzzy(self, text: str, find: str, replace: str):
        import difflib
        find_lines = find.splitlines()
        text_lines = text.splitlines()
        window = len(find_lines)
        best_ratio = 0.0
        best_start = 0
        find_norm = " ".join(part.strip() for part in find_lines if part.strip())
        if not find_norm:
            return None
        for i in range(len(text_lines) - window + 1):
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
            return text[:start_idx] + replace + text[end_idx:], best_ratio
        return None
