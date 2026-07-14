from pathlib import Path
from typing import Optional

from .git_manager import GitManager, GitStatus


class GitIntegration:
    def __init__(self, workdir: Path):
        self.workdir = Path(workdir).resolve()
        self.git = GitManager(self.workdir)
        self._initialized = False

    def initialize(self, auto_init: bool = True) -> tuple[bool, str]:
        if not self.git.is_available():
            return False, "Git is not available on this system. Continuing without version control."
        if self.git.is_repo():
            self._initialized = True
            return True, "Git repository detected"
        if auto_init:
            ok, msg = self.git.init()
            if ok:
                self._initialized = True
                return True, "Repository initialized and .gitignore created"
            return False, msg
        return False, "No Git repository. Run /git-init to create one."

    @property
    def available(self) -> bool:
        return self.git.is_available()

    @property
    def ready(self) -> bool:
        return self._initialized and self.git.is_repo()

    def status_report(self) -> GitStatus:
        return self.git.full_status()

    def checkpoint_before_task(self, task_description: str) -> tuple[bool, str, str]:
        if not self.ready:
            return False, "Git not ready", ""
        ok, msg, ref = self.git.checkpoint(task_description)
        if ok and ref:
            return True, msg, ref
        return False, msg, ""

    def commit_after_verification(
        self, verification_passed: bool, task_description: str = "", force: bool = False
    ) -> tuple[bool, str, str]:
        if not self.ready:
            return False, "Git not ready", ""
        if not verification_passed and not force:
            return False, "Verification failed — not committing", ""

        ok, msg, commit_hash = self.git.commit(task_description=task_description)
        if ok:
            return True, msg, commit_hash
        return False, msg, ""

    def rollback(self) -> tuple[bool, str]:
        if not self.ready:
            return False, "Git not ready"
        return self.git.rollback()

    def undo(self) -> tuple[bool, str]:
        if not self.ready:
            return False, "Git not ready"
        return self.git.undo()

    def restore_last_checkpoint(self) -> tuple[bool, str]:
        if not self.ready:
            return False, "Git not ready"
        return self.git.restore_checkpoint()

    def diff_preview(self) -> str:
        if not self.ready:
            return ""
        return self.git.diff_summary()
