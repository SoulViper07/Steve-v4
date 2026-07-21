import json
import time
import os
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from .execution_state import ExecutionState
from .task_state import TaskState
from .project_state import ProjectState
from .model_state import ModelState
from .git_state import GitState
from .verification_state import VerificationState
from .repository_state import RepositoryState


_STATE_DIR = ".steve" / Path("state")

_STATE_FILES = {
    "execution": "execution.json",
    "task": "task.json",
    "project": "project.json",
    "model": "model.json",
    "git": "git.json",
    "verification": "verification.json",
    "repository": "repository.json",
}


class StateManager:
    _instance: Optional["StateManager"] = None
    _lock = threading.Lock()

    def __new__(cls, workdir: Optional[Path] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, workdir: Optional[Path] = None):
        if self._initialized:
            return
        self._initialized = True
        self._workdir = (workdir or Path.cwd()).resolve()
        self._state_dir = self._workdir / _STATE_DIR
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self.execution = ExecutionState()
        self.task = TaskState()
        self.project = ProjectState()
        self.model = ModelState()
        self.git = GitState()
        self.verification = VerificationState()
        self.repository = RepositoryState()

        self._recover()

    # ── Persistence ──────────────────────────────────────────

    def _recover(self):
        for attr, filename in _STATE_FILES.items():
            path = self._state_dir / filename
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    substate = getattr(self, attr, None)
                    if substate:
                        for key, value in data.items():
                            if hasattr(substate, key):
                                setattr(substate, key, value)
                except Exception:
                    pass

    def save(self):
        for attr, filename in _STATE_FILES.items():
            substate = getattr(self, attr, None)
            if substate is None:
                continue
            path = self._state_dir / filename
            tmp = path.with_suffix(".tmp")
            try:
                tmp.write_text(
                    json.dumps(asdict(substate), indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8",
                )
                tmp.replace(path)
            except Exception:
                pass

    def save_sync(self):
        self.save()

    def clear(self):
        self.execution = ExecutionState()
        self.task = TaskState()
        self.project = ProjectState()
        self.model = ModelState()
        self.git = GitState()
        self.verification = VerificationState()
        self.repository = RepositoryState()
        self.save()

    # ── Public API ───────────────────────────────────────────

    def initialize_task(self, request: str, task_id: str = "", category: str = ""):
        self.clear()
        self.execution.task_id = task_id
        self.execution.start_time = time.time()
        self.task.request = request
        self.task.task_id = task_id
        self.task.category = category
        self.execution.current_activity = "initializing"
        self.save()

    def start_stage(self, name: str):
        self.execution.current_stage = name
        self.execution.current_activity = f"stage:{name}"
        self.save()

    def finish_stage(self, name: str):
        if name not in self.execution.stages_completed:
            self.execution.stages_completed.append(name)
        self.execution.current_activity = f"completed:{name}"
        self.save()

    def set_model(self, model: str, stage: str = "", reason: str = ""):
        self.model.push_model(model, stage, reason)
        self.save()

    def set_project(self, project_root: str, tree: Optional[List[str]] = None):
        self.project.project_root = project_root
        if tree:
            self.project.project_tree = tree
        self.save()

    def set_file(self, filename: str):
        self.project.current_file = filename
        self.save()

    def set_component(self, component: str):
        self.project.current_component = component
        self.save()

    def mark_generated(self, filepath: str):
        if filepath not in self.project.generated_files:
            self.project.generated_files.append(filepath)
        self.project.current_file = filepath
        self.save()

    def mark_modified(self, filepath: str):
        if filepath not in self.project.modified_files:
            self.project.modified_files.append(filepath)
        self.save()

    def mark_verified(self, status: str = "passed", score: float = 1.0):
        self.verification.status = status
        self.verification.score = score
        self.save()

    def mark_repaired(self, attempt: int = 1, success: bool = True):
        self.verification.repair_attempts = attempt
        self.verification.repair_success = success
        if success:
            self.verification.status = "repaired"
        self.save()

    def mark_committed(self, commit_hash: str = "", message: str = ""):
        self.git.commit_status = "committed"
        if commit_hash:
            self.git.last_commit_hash = commit_hash
        if message:
            self.git.last_commit_message = message
        self.save()

    def add_warning(self, msg: str):
        self.execution.warnings.append(msg)
        self.execution.logs.append(f"[WARN] {msg}")
        self.save()

    def add_error(self, msg: str):
        self.execution.errors.append(msg)
        self.execution.logs.append(f"[ERROR] {msg}")
        self.save()

    def add_log(self, msg: str):
        self.execution.logs.append(msg)
        self.save()

    def finish_task(self):
        self.execution.current_stage = "completed"
        self.execution.elapsed_time = time.time() - self.execution.start_time
        self.execution.current_activity = "finished"
        self.save()

    def update_git_status(self, branch: str = "", modified: int = 0, untracked: int = 0, status: str = ""):
        if branch:
            self.git.branch = branch
        if modified:
            self.git.modified_count = modified
        if untracked:
            self.git.untracked_count = untracked
        if status:
            self.git.status = status
        self.save()

    def update_task_classification(self, project_type: str = "", complexity: str = "",
                                    languages: Optional[List[str]] = None,
                                    frameworks: Optional[List[str]] = None,
                                    category: str = ""):
        if project_type:
            self.task.project_type = project_type
        if complexity:
            self.task.complexity = complexity
        if category:
            self.task.category = category
        if languages:
            self.task.languages = languages
        if frameworks:
            self.task.frameworks = frameworks
        self.save()

    def update_architecture(self, components: Optional[List[str]] = None,
                            folder_structure: Optional[List[str]] = None,
                            summary: str = ""):
        if components:
            self.project.components = components
        if folder_structure:
            self.project.folder_structure = folder_structure
        if summary:
            self.task.architecture_summary = summary
        self.save()

    def update_verification(self, critical: int = 0, major: int = 0, minor: int = 0,
                            issues: Optional[List[Dict]] = None, quality: float = 0.0):
        self.verification.critical_count = critical
        self.verification.major_count = major
        self.verification.minor_count = minor
        if issues:
            self.verification.issues = issues
        if quality:
            self.verification.quality_score = quality
        self.save()

    def update_repository(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.repository, key):
                setattr(self.repository, key, value)
        self.save()

    # ── Report ───────────────────────────────────────────────

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "task": {
                "id": self.task.task_id,
                "request": self.task.request[:100],
                "category": self.task.category,
                "project_type": self.task.project_type,
                "complexity": self.task.complexity,
            },
            "execution": {
                "stage": self.execution.current_stage,
                "completed": self.execution.stages_completed,
                "elapsed": round(self.execution.elapsed_time, 1),
                "errors": len(self.execution.errors),
                "warnings": len(self.execution.warnings),
            },
            "project": {
                "root": self.project.project_root,
                "generated": len(self.project.generated_files),
                "modified": len(self.project.modified_files),
                "components": len(self.project.components),
            },
            "model": {
                "current": self.model.current_model,
                "switches": len(self.model.model_history),
            },
            "git": {
                "branch": self.git.branch,
                "committed": self.git.commit_status == "committed",
                "hash": self.git.last_commit_hash[:8] if self.git.last_commit_hash else "",
            },
            "verification": {
                "status": self.verification.status,
                "score": self.verification.score,
                "critical": self.verification.critical_count,
            },
            "repository": {
                "indexed": self.repository.is_indexed,
                "files": self.repository.total_files,
                "symbols": self.repository.total_symbols,
                "languages": list(self.repository.languages.keys()),
                "frameworks": list(self.repository.frameworks.keys()),
                "architecture": self.repository.architecture_type,
                "summary": self.repository.summary[:100] if self.repository.summary else "",
            },
        }


def get_state_manager(workdir: Optional[Path] = None) -> StateManager:
    return StateManager(workdir)


def reset_state_manager():
    StateManager._instance = None
