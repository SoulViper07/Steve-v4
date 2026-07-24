from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
import difflib


class DiffType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class DiffLine:
    content: str
    diff_type: DiffType
    old_line_no: int = 0
    new_line_no: int = 0


@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[DiffLine] = field(default_factory=list)

    @property
    def added_count(self) -> int:
        return sum(1 for l in self.lines if l.diff_type == DiffType.ADDED)

    @property
    def removed_count(self) -> int:
        return sum(1 for l in self.lines if l.diff_type == DiffType.REMOVED)

    @property
    def impact(self) -> str:
        parts = []
        if self.removed_count:
            parts.append(f"-{self.removed_count}")
        if self.added_count:
            parts.append(f"+{self.added_count}")
        return " ".join(parts) if parts else "0"


@dataclass
class DiffResult:
    hunks: List[DiffHunk] = field(default_factory=list)
    old_path: str = ""
    new_path: str = ""
    old_size: int = 0
    new_size: int = 0

    @property
    def total_added(self) -> int:
        return sum(h.added_count for h in self.hunks)

    @property
    def total_removed(self) -> int:
        return sum(h.removed_count for h in self.hunks)

    @property
    def total_changed(self) -> int:
        return self.total_added + self.total_removed

    @property
    def has_changes(self) -> bool:
        return self.total_changed > 0

    @property
    def impact_summary(self) -> str:
        parts = []
        if self.total_added:
            parts.append(f"+{self.total_added} added")
        if self.total_removed:
            parts.append(f"-{self.total_removed} removed")
        if not parts:
            return "No changes"
        return f"{len(self.hunks)} hunk(s), " + ", ".join(parts)

    def to_unified_diff(self) -> str:
        lines = [f"--- {self.old_path}", f"+++ {self.new_path}"]
        for hunk in self.hunks:
            header = f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@"
            lines.append(header)
            for line in hunk.lines:
                prefix = {"added": "+", "removed": "-", "modified": "~", "unchanged": " "}.get(
                    line.diff_type.value, " "
                )
                lines.append(f"{prefix}{line.content}")
        return "\n".join(lines)


class DiffEngine:
    def compute(self, old_text: str, new_text: str, old_path: str = "a/file", new_path: str = "b/file") -> DiffResult:
        result = DiffResult(old_path=old_path, new_path=new_path)
        result.old_size = len(old_text)
        result.new_size = len(new_text)

        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        old_line_no = 0
        new_line_no = 0

        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "equal":
                for idx in range(i1, i2):
                    old_line_no += 1
                    new_line_no += 1
                continue

            old_count = i2 - i1
            new_count = j2 - j1
            hunk = DiffHunk(
                old_start=old_line_no + 1,
                old_count=old_count,
                new_start=new_line_no + 1,
                new_count=new_count,
            )

            for idx in range(i1, i2):
                old_line_no += 1
                hunk.lines.append(DiffLine(
                    content=old_lines[idx].rstrip("\n").rstrip("\r"),
                    diff_type=DiffType.REMOVED,
                    old_line_no=old_line_no,
                ))

            for idx in range(j1, j2):
                new_line_no += 1
                hunk.lines.append(DiffLine(
                    content=new_lines[idx].rstrip("\n").rstrip("\r"),
                    diff_type=DiffType.ADDED,
                    new_line_no=new_line_no,
                ))

            result.hunks.append(hunk)

        return result

    def compute_minimal_edits(self, old_text: str, new_text: str) -> List[Tuple[str, str, str]]:
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        edits: List[Tuple[str, str, str]] = []

        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            old_block = "".join(old_lines[i1:i2])
            new_block = "".join(new_lines[j1:j2])
            if op == "replace":
                edits.append(("replace", old_block, new_block))
            elif op == "delete":
                edits.append(("delete", old_block, ""))
            elif op == "insert":
                edits.append(("insert", "", new_block))

        return edits
