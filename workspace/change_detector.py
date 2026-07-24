from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .file_tracker import FileTracker


CHANGE_ADDED = "added"
CHANGE_MODIFIED = "modified"
CHANGE_DELETED = "deleted"
CHANGE_MOVED = "moved"
CHANGE_UNCHANGED = "unchanged"


@dataclass
class FileChange:
    path: str
    change_type: str
    old_path: str = ""
    old_size: int = 0
    new_size: int = 0
    old_checksum: str = ""
    new_checksum: str = ""


class ChangeDetector:
    def __init__(self, tracker: FileTracker):
        self._tracker = tracker
        self._previous_snapshot: Dict[str, Tuple[int, str]] = {}

    def snapshot(self):
        self._previous_snapshot = {}
        for path, entry in self._tracker.index.items():
            self._previous_snapshot[path] = (entry.size, entry.checksum)

    def detect(self, current_files: Set[str]) -> List[FileChange]:
        changes: List[FileChange] = []
        snapshot_paths = set(self._previous_snapshot.keys())

        added = current_files - snapshot_paths
        deleted = snapshot_paths - current_files

        tracked_set = set(self._tracker.all_files)

        for path in sorted(added):
            entry = self._tracker.get(path)
            changes.append(FileChange(
                path=path,
                change_type=CHANGE_ADDED,
                new_size=entry.size if entry else 0,
                new_checksum=entry.checksum if entry else "",
            ))

        for path in sorted(deleted):
            prev = self._previous_snapshot.get(path)
            changes.append(FileChange(
                path=path,
                change_type=CHANGE_DELETED,
                old_size=prev[0] if prev else 0,
                old_checksum=prev[1] if prev else "",
            ))

        for path in sorted(tracked_set & current_files):
            entry = self._tracker.get(path)
            prev = self._previous_snapshot.get(path)
            if entry and prev:
                if entry.checksum != prev[1]:
                    changes.append(FileChange(
                        path=path,
                        change_type=CHANGE_MODIFIED,
                        old_size=prev[0],
                        new_size=entry.size,
                        old_checksum=prev[1],
                        new_checksum=entry.checksum,
                    ))

        moved = self._detect_moves(changes)
        for move in moved:
            changes = [c for c in changes if c.path != move.path and c.path != move.old_path]
            changes.append(move)

        return changes

    def _detect_moves(self, changes: List[FileChange]) -> List[FileChange]:
        added = {c.path: c for c in changes if c.change_type == CHANGE_ADDED}
        deleted = {c.path: c for c in changes if c.change_type == CHANGE_DELETED}
        moves: List[FileChange] = []
        matched: Set[str] = set()
        for del_path, del_change in deleted.items():
            if del_path in matched:
                continue
            del_prev = self._previous_snapshot.get(del_path)
            if not del_prev:
                continue
            del_size = del_prev[0]
            for add_path, add_change in added.items():
                if add_path in matched:
                    continue
                if add_change.new_size == del_size:
                    moves.append(FileChange(
                        path=add_path,
                        change_type=CHANGE_MOVED,
                        old_path=del_path,
                        old_size=del_size,
                        new_size=add_change.new_size,
                    ))
                    matched.add(del_path)
                    matched.add(add_path)
                    break
        return moves

    def has_changes(self) -> bool:
        current_files = set(self._tracker.all_files)
        changes = self.detect(current_files)
        return bool(changes)

    def summary(self) -> str:
        current_files = set(self._tracker.all_files)
        changes = self.detect(current_files)
        if not changes:
            return "No changes detected"
        parts = []
        counts = {}
        for c in changes:
            counts[c.change_type] = counts.get(c.change_type, 0) + 1
        for change_type in (CHANGE_ADDED, CHANGE_MODIFIED, CHANGE_DELETED, CHANGE_MOVED):
            count = counts.get(change_type, 0)
            if count > 0:
                parts.append(f"{count} {change_type}")
        return ", ".join(parts)
