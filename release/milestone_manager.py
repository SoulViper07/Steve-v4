from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Milestone:
    name: str
    version: str
    date: str
    description: str = ""
    modules_added: list[str] = field(default_factory=list)
    tests_added: list[str] = field(default_factory=list)
    docs_updated: list[str] = field(default_factory=list)
    git_commit: str = ""
    release_tag: str = ""
    completion_pct: int = 0
    architecture_version: str = "4.0"

    @property
    def is_tagged(self) -> bool:
        return bool(self.release_tag)

    @property
    def is_committed(self) -> bool:
        return bool(self.git_commit)


class MilestoneManager:
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.milestones_file = self.state_dir / "milestones.json"
        self._milestones: list[Milestone] = []
        self._load()

    def _load(self):
        if self.milestones_file.exists():
            try:
                data = json.loads(self.milestones_file.read_text(encoding="utf-8"))
                self._milestones = [Milestone(**m) for m in data]
            except (json.JSONDecodeError, KeyError, TypeError):
                self._milestones = []
        else:
            self._milestones = []

    def _save(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        data = [asdict(m) for m in self._milestones]
        self.milestones_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def add(self, milestone: Milestone) -> Milestone:
        self._milestones.append(milestone)
        self._save()
        return milestone

    def get_latest(self) -> Optional[Milestone]:
        return self._milestones[-1] if self._milestones else None

    def get_by_version(self, version: str) -> Optional[Milestone]:
        for m in self._milestones:
            if m.version == version:
                return m
        return None

    def get_by_name(self, name: str) -> Optional[Milestone]:
        for m in self._milestones:
            if m.name.lower() == name.lower():
                return m
        return None

    def list_all(self) -> list[Milestone]:
        return list(self._milestones)

    def count(self) -> int:
        return len(self._milestones)

    def update_commit(self, name: str, commit_hash: str) -> Optional[Milestone]:
        for m in self._milestones:
            if m.name == name:
                m.git_commit = commit_hash
                self._save()
                return m
        return None

    def update_tag(self, name: str, tag: str) -> Optional[Milestone]:
        for m in self._milestones:
            if m.name == name:
                m.release_tag = tag
                self._save()
                return m
        return None

    def remove(self, name: str) -> bool:
        before = len(self._milestones)
        self._milestones = [m for m in self._milestones if m.name != name]
        if len(self._milestones) < before:
            self._save()
            return True
        return False

    def summary(self) -> str:
        if not self._milestones:
            return "No milestones recorded."
        lines = [f"Milestones: {len(self._milestones)}"]
        for m in self._milestones:
            tag = m.release_tag or "(untagged)"
            commit = m.git_commit[:8] if m.git_commit else ""
            lines.append(f"  v{m.version}  {tag}  {m.date[:10]}  {m.name}  [{commit}]")
        return "\n".join(lines)