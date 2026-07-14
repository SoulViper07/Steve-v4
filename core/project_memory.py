import json
import os
import time
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field, asdict


STEVE_DIR = ".steve"


@dataclass
class Artifact:
    plan: str = ""
    architecture: dict = field(default_factory=dict)
    ui_spec: dict = field(default_factory=dict)
    todo: dict = field(default_factory=dict)
    progress: dict = field(default_factory=dict)
    verification: dict = field(default_factory=dict)
    repair_log: list = field(default_factory=list)
    generation_state: dict = field(default_factory=dict)
    section_states: dict = field(default_factory=dict)


class ProjectMemory:
    def __init__(self, workdir: Path):
        self.root = workdir.resolve()
        self.steve_dir = self.root / STEVE_DIR
        self.steve_dir.mkdir(parents=True, exist_ok=True)
        self._artifacts = Artifact()
        self._dirty = set()
        self._load_all()

    def _path(self, name: str) -> Path:
        return self.steve_dir / name

    def _load_all(self):
        mapping = {
            "plan.md": "plan",
            "architecture.json": "architecture",
            "ui_spec.json": "ui_spec",
            "todo.json": "todo",
            "progress.json": "progress",
            "verification.json": "verification",
            "repair_log.json": "repair_log",
            "generation_state.json": "generation_state",
        }
        for filename, attr in mapping.items():
            p = self._path(filename)
            if p.exists():
                try:
                    if filename.endswith(".json"):
                        setattr(self._artifacts, attr, json.loads(p.read_text(encoding="utf-8")))
                    else:
                        setattr(self._artifacts, attr, p.read_text(encoding="utf-8"))
                except Exception:
                    pass

    def save_all(self):
        mapping = {
            "plan.md": ("plan", False),
            "architecture.json": ("architecture", True),
            "ui_spec.json": ("ui_spec", True),
            "todo.json": ("todo", True),
            "progress.json": ("progress", True),
            "verification.json": ("verification", True),
            "repair_log.json": ("repair_log", True),
            "generation_state.json": ("generation_state", True),
        }
        for filename, (attr, is_json) in mapping.items():
            if attr in self._dirty or filename not in [p.name for p in self.steve_dir.iterdir()]:
                p = self._path(filename)
                val = getattr(self._artifacts, attr)
                try:
                    if is_json:
                        p.write_text(json.dumps(val, indent=2, default=str), encoding="utf-8")
                    else:
                        p.write_text(str(val), encoding="utf-8")
                except Exception:
                    pass
        self._dirty.clear()

    def _mark_dirty(self, attr: str):
        self._dirty.add(attr)

    def plan_text(self) -> str:
        return self._artifacts.plan

    def set_plan(self, text: str):
        self._artifacts.plan = text
        self._mark_dirty("plan")

    def architecture(self) -> dict:
        return self._artifacts.architecture

    def set_architecture(self, data: dict):
        self._artifacts.architecture = data
        self._mark_dirty("architecture")

    def ui_spec(self) -> dict:
        return self._artifacts.ui_spec

    def set_ui_spec(self, data: dict):
        self._artifacts.ui_spec = data
        self._mark_dirty("ui_spec")

    def todo_list(self) -> dict:
        return self._artifacts.todo

    def set_todo(self, data: dict):
        self._artifacts.todo = data
        self._mark_dirty("todo")

    def mark_component_done(self, component: str):
        todos = self._artifacts.todo
        if isinstance(todos, dict):
            todos[component] = {"done": True, "completed_at": time.time()}
            self._mark_dirty("todo")

    def progress_data(self) -> dict:
        return self._artifacts.progress

    def set_progress(self, data: dict):
        self._artifacts.progress = data
        self._mark_dirty("progress")

    def verification_data(self) -> dict:
        return self._artifacts.verification

    def set_verification(self, data: dict):
        self._artifacts.verification = data
        self._mark_dirty("verification")

    def add_repair(self, entry: dict):
        self._artifacts.repair_log.append(entry)
        self._mark_dirty("repair_log")

    def repair_log(self) -> list:
        return self._artifacts.repair_log

    def generation_state(self) -> dict:
        return self._artifacts.generation_state

    def set_generation_state(self, data: dict):
        self._artifacts.generation_state.update(data)
        self._mark_dirty("generation_state")

    def set_section_state(self, file_path: str, section: str, status: str):
        if file_path not in self._artifacts.section_states:
            self._artifacts.section_states[file_path] = {}
        self._artifacts.section_states[file_path][section] = {
            "status": status,
            "updated_at": time.time(),
        }
        self._mark_dirty("generation_state")

    def section_state(self, file_path: str, section: str) -> Optional[str]:
        return self._artifacts.section_states.get(file_path, {}).get(section, {}).get("status")

    def clear(self):
        self._artifacts = Artifact()
        self._dirty = set()
        for p in self.steve_dir.iterdir():
            if p.is_file():
                p.unlink()
