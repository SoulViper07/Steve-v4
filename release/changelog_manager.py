from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ChangelogEntry:
    version: str
    date: str
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    improved: list[str] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)
    architecture_changes: list[str] = field(default_factory=list)
    performance: list[str] = field(default_factory=list)
    documentation: list[str] = field(default_factory=list)
    breaking_changes: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [f"\n## [{self.version}] — {self.date}\n"]
        sections = [
            ("Added", self.added),
            ("Changed", self.changed),
            ("Improved", self.improved),
            ("Fixed", self.fixed),
            ("Architecture Changes", self.architecture_changes),
            ("Performance", self.performance),
            ("Documentation", self.documentation),
            ("Breaking Changes", self.breaking_changes),
            ("Removed", self.removed),
        ]
        for heading, items in sections:
            if items:
                lines.append(f"### {heading}")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")
        return "\n".join(lines).rstrip("\n") + "\n\n---"


CHANGELOG_HEADER = """# Changelog

All notable changes to Steve v4 are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

"""


class ChangelogManager:
    def __init__(self, changelog_path: Path):
        self.path = Path(changelog_path)
        self.entries: list[ChangelogEntry] = []
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        text = self.path.read_text(encoding="utf-8")
        blocks = re.split(r"\n(?=## \[)", text.strip())
        for block in blocks:
            block = block.strip()
            if not block or block.startswith("# Changelog"):
                continue
            entry = self._parse_entry(block)
            if entry:
                self.entries.append(entry)

    def _parse_entry(self, block: str) -> Optional[ChangelogEntry]:
        header_match = re.match(r"## \[(.+?)\]\s*[—–-]?\s*(\S+)", block)
        if not header_match:
            return None
        version = header_match.group(1)
        date = header_match.group(2)
        entry = ChangelogEntry(version=version, date=date)

        current_section = None
        section_map = {
            "added": "added",
            "changed": "changed",
            "improved": "improved",
            "fixed": "fixed",
            "architecture": "architecture_changes",
            "architecture changes": "architecture_changes",
            "performance": "performance",
            "documentation": "documentation",
            "breaking": "breaking_changes",
            "breaking changes": "breaking_changes",
            "removed": "removed",
        }

        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("### "):
                key = stripped[4:].strip().lower()
                current_section = section_map.get(key)
            elif stripped.startswith("- ") and current_section:
                item_text = stripped[2:].strip()
                getattr(entry, current_section).append(item_text)
        return entry

    def prepend(self, entry: ChangelogEntry):
        self.entries.insert(0, entry)
        self._write()

    def append(self, entry: ChangelogEntry):
        self.entries.append(entry)
        self._write()

    def _write(self):
        lines = [CHANGELOG_HEADER]
        for entry in self.entries:
            lines.append(entry.to_markdown())
        self.path.write_text("".join(lines), encoding="utf-8")

    def generate_entry(
        self,
        version: str,
        date: Optional[str] = None,
        added: Optional[list[str]] = None,
        changed: Optional[list[str]] = None,
        improved: Optional[list[str]] = None,
        fixed: Optional[list[str]] = None,
        architecture_changes: Optional[list[str]] = None,
        performance: Optional[list[str]] = None,
        documentation: Optional[list[str]] = None,
        breaking_changes: Optional[list[str]] = None,
        removed: Optional[list[str]] = None,
    ) -> ChangelogEntry:
        today = date or datetime.now().strftime("%Y-%m-%d")
        return ChangelogEntry(
            version=version,
            date=today,
            added=added or [],
            changed=changed or [],
            improved=improved or [],
            fixed=fixed or [],
            architecture_changes=architecture_changes or [],
            performance=performance or [],
            documentation=documentation or [],
            breaking_changes=breaking_changes or [],
            removed=removed or [],
        )

    def get_latest_version(self) -> Optional[str]:
        return self.entries[0].version if self.entries else None

    def get_entry(self, version: str) -> Optional[ChangelogEntry]:
        for e in self.entries:
            if e.version == version:
                return e
        return None

    def summary(self) -> str:
        if not self.entries:
            return "No changelog entries."
        lines = [f"Changelog entries: {len(self.entries)}"]
        for e in self.entries[:10]:
            added = f" +{len(e.added)}" if e.added else ""
            changed = f" ~{len(e.changed)}" if e.changed else ""
            fixed = f" !{len(e.fixed)}" if e.fixed else ""
            lines.append(f"  [{e.version}] {e.date}{added}{changed}{fixed}")
        return "\n".join(lines)