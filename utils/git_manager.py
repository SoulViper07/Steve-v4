import subprocess
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .helpers import redact_secret_text

STEVE_GITIGNORE = """__pycache__/
*.pyc
.venv/
venv/
.env
logs/
.steve/
cache/
build/
dist/
node_modules/
*.log
*.tmp
*.bak
.pytest_cache/
.mypy_cache/
.ruff_cache/
.idea/
.vscode/
"""

GIT_COMMIT_TYPES = ("feat", "fix", "refactor", "chore", "docs", "test", "style", "perf", "build", "ci")


@dataclass
class GitCommandResult:
    ok: bool
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    error: str = ""


@dataclass
class GitStatus:
    available: bool = False
    is_repo: bool = False
    branch: str = ""
    modified: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    last_commit_hash: str = ""
    last_commit_message: str = ""
    last_commit_date: str = ""
    file_count_modified: int = 0
    file_count_untracked: int = 0
    file_count_staged: int = 0

    def has_changes(self) -> bool:
        return bool(self.modified or self.untracked or self.staged)

    def summary_lines(self) -> list[str]:
        lines = []
        if not self.available:
            lines.append("Git not available")
            return lines
        if not self.is_repo:
            lines.append("Not a Git repository")
            return lines
        lines.append(f"Branch: {self.branch}")
        if self.ahead or self.behind:
            parts = []
            if self.ahead:
                parts.append(f"{self.ahead} ahead")
            if self.behind:
                parts.append(f"{self.behind} behind")
            lines.append(f"  ({', '.join(parts)} of origin)")
        if self.last_commit_hash:
            lines.append(f"Last commit: {self.last_commit_hash[:8]} {self.last_commit_message}")
            lines.append(f"  ({self.last_commit_date})")
        if self.modified:
            lines.append(f"Modified: {self.file_count_modified}")
            for f in self.modified[:10]:
                lines.append(f"  M  {f}")
            if len(self.modified) > 10:
                lines.append(f"  ... +{len(self.modified) - 10} more")
        if self.untracked:
            lines.append(f"Untracked: {self.file_count_untracked}")
            for f in self.untracked[:10]:
                lines.append(f"  ?  {f}")
            if len(self.untracked) > 10:
                lines.append(f"  ... +{len(self.untracked) - 10} more")
        if self.staged:
            lines.append(f"Staged: {self.file_count_staged}")
            for f in self.staged[:5]:
                lines.append(f"  ✓  {f}")
        return lines


@dataclass
class CheckpointInfo:
    ref: str
    message: str
    created_at: str
    files_count: int


class GitManager:
    def __init__(self, workdir: Path):
        self.workdir = Path(workdir).resolve()
        self._available: Optional[bool] = None

    def _run(self, args: list[str], timeout: int = 60) -> GitCommandResult:
        command = ["git"] + args
        try:
            proc = subprocess.run(
                command,
                cwd=str(self.workdir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            return GitCommandResult(False, command, returncode=127, error="Git is not installed or not on PATH.")
        except subprocess.TimeoutExpired:
            return GitCommandResult(False, command, returncode=124, error="Git command timed out.")
        except Exception as exc:
            return GitCommandResult(False, command, returncode=1, error=str(exc))
        return GitCommandResult(
            proc.returncode == 0,
            command,
            redact_secret_text(proc.stdout or ""),
            redact_secret_text(proc.stderr or ""),
            proc.returncode,
        )

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        result = self._run(["--version"], timeout=10)
        self._available = result.ok
        return self._available

    def is_repo(self) -> bool:
        result = self._run(["rev-parse", "--is-inside-work-tree"])
        return result.ok and result.stdout.strip().lower() == "true"

    def init(self) -> tuple[bool, str]:
        if not self.is_available():
            return False, "Git is not available on this system."
        if self.is_repo():
            return True, "Repository already initialized."
        result = self._run(["init"])
        if not result.ok:
            return False, f"Failed to initialize repository: {result.error or result.stderr.strip()}"
        self._ensure_gitignore()
        return True, "Repository initialized"

    def _ensure_gitignore(self) -> bool:
        path = self.workdir / ".gitignore"
        existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        additions = []
        for line in STEVE_GITIGNORE.splitlines():
            if line and line not in existing.splitlines():
                additions.append(line)
        if not path.exists():
            path.write_text(STEVE_GITIGNORE, encoding="utf-8")
            return True
        if additions:
            sep = "" if existing.endswith("\n") or not existing else "\n"
            path.write_text(existing + sep + "\n".join(additions) + "\n", encoding="utf-8")
            return True
        return False

    def full_status(self) -> GitStatus:
        status = GitStatus()
        status.available = self.is_available()
        if not status.available:
            return status
        status.is_repo = self.is_repo()
        if not status.is_repo:
            return status

        status.branch = self._get_branch()
        self._populate_changes(status)
        self._populate_last_commit(status)
        self._populate_ahead_behind(status)
        status.file_count_modified = len(status.modified)
        status.file_count_untracked = len(status.untracked)
        status.file_count_staged = len(status.staged)
        return status

    def _get_branch(self) -> str:
        result = self._run(["branch", "--show-current"])
        return result.stdout.strip() if result.ok else ""

    def _populate_changes(self, status: GitStatus):
        result = self._run(["status", "--porcelain"])
        if not result.ok:
            return
        for line in result.stdout.splitlines():
            line = line.rstrip()
            if not line:
                continue
            prefix = line[:2]
            path = line[3:]
            if prefix == "??":
                status.untracked.append(path)
            elif prefix in (" M", "MM"):
                status.modified.append(path)
            elif prefix in ("A ", "M ", "AM", "RM", "??"):
                status.staged.append(path)
            elif "M" in prefix:
                status.modified.append(path)

    def _populate_last_commit(self, status: GitStatus):
        result = self._run(["log", "-1", "--format=%H%n%s%n%ai", "--no-color"])
        if result.ok and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 1:
                status.last_commit_hash = lines[0].strip()
            if len(lines) >= 2:
                status.last_commit_message = lines[1].strip()
            if len(lines) >= 3:
                status.last_commit_date = lines[2].strip()

    def _populate_ahead_behind(self, status: GitStatus):
        result = self._run(["rev-list", "--left-right", "--count", "HEAD...@{u}"], timeout=10)
        if result.ok and result.stdout.strip():
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                try:
                    status.ahead = int(parts[0])
                    status.behind = int(parts[1])
                except ValueError:
                    pass

    def checkpoint(self, message: str = "") -> tuple[bool, str, str]:
        if not self.is_available():
            return False, "Git not available", ""
        if not self.is_repo():
            return False, "Not a Git repository", ""
        status = self.full_status()
        if not status.has_changes():
            return True, "No changes to checkpoint", ""

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_message = re.sub(r'[^\w\s-]', '', message)[:60] if message else f"checkpoint-{timestamp}"
        ref = f"steve-checkpoint-{timestamp}"

        result = self._run(["stash", "push", "-m", f"{ref}: {safe_message}", "--include-untracked"])
        if not result.ok:
            error = result.stderr.strip() or result.error or "stash failed"
            return False, error, ""

        return True, f"Checkpoint saved: {safe_message}", ref

    def restore_checkpoint(self, ref: str = "") -> tuple[bool, str]:
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"

        if ref:
            stash_result = self._run(["stash", "list"])
            if stash_result.ok:
                for line in stash_result.stdout.splitlines():
                    if ref in line:
                        stash_id = line.split(":")[0].strip()
                        pop = self._run(["stash", "pop", stash_id])
                        if pop.ok:
                            return True, f"Restored checkpoint: {ref}"
                        return False, f"Failed to restore: {pop.stderr.strip()}"
            return False, f"Checkpoint not found: {ref}"

        result = self._run(["stash", "pop"])
        if result.ok:
            return True, "Restored most recent checkpoint"
        if "No stash entries" in result.stderr:
            return False, "No checkpoints to restore"
        return False, f"Failed to restore checkpoint: {result.stderr.strip()}"

    def list_checkpoints(self) -> list[CheckpointInfo]:
        result = self._run(["stash", "list"])
        if not result.ok or not result.stdout.strip():
            return []
        checkpoints = []
        for line in result.stdout.splitlines():
            parts = line.split(": ", 2)
            if len(parts) >= 2:
                stash_ref = parts[0].strip()
                rest = parts[-1]
                message = rest
                ref_match = re.match(r"steve-checkpoint-\d{8}-\d{6}", rest)
                ref = ref_match.group(0) if ref_match else stash_ref
                checkpoints.append(CheckpointInfo(
                    ref=ref,
                    message=message,
                    created_at=stash_ref,
                    files_count=0,
                ))
        return checkpoints

    def commit(self, message: str = "", task_description: str = "") -> tuple[bool, str, str]:
        if not self.is_available():
            return False, "Git not available", ""
        if not self.is_repo():
            return False, "Not a Git repository", ""
        if self._detached_head():
            return False, "Detached HEAD. Check out a branch before committing.", ""

        status = self.full_status()
        if not status.has_changes():
            return False, "No changes to commit.", ""

        add_result = self._run(["add", "."])
        if not add_result.ok:
            return False, f"Failed to stage changes: {add_result.stderr.strip()}", ""

        if not message:
            message = self._suggest_message(status, task_description)
        else:
            message = self._normalize_message(message)

        commit_result = self._run(["commit", "-m", message])
        if not commit_result.ok:
            if "nothing to commit" in (commit_result.stdout + commit_result.stderr).lower():
                return False, "No changes to commit.", ""
            return False, f"Commit failed: {commit_result.stderr.strip()}", ""

        commit_hash = self._get_head_hash()
        return True, message, commit_hash

    def _detached_head(self) -> bool:
        result = self._run(["symbolic-ref", "--quiet", "HEAD"])
        return not result.ok

    def _get_head_hash(self) -> str:
        result = self._run(["rev-parse", "--short", "HEAD"])
        return result.stdout.strip() if result.ok else ""

    def _suggest_message(self, status: GitStatus, task_description: str = "") -> str:
        if task_description:
            lowered = task_description.lower()
            if any(t in lowered for t in ("fix", "bug", "error", "broken", "issue", "repair")):
                prefix = "fix"
            elif any(t in lowered for t in ("refactor", "rewrite", "redesign", "restructure", "clean")):
                prefix = "refactor"
            elif any(t in lowered for t in ("style", "ui", "theme", "visual", "css")):
                prefix = "style"
            elif any(t in lowered for t in ("doc", "readme", "comment", "help")):
                prefix = "docs"
            elif any(t in lowered for t in ("test", "verify", "check")):
                prefix = "test"
            elif any(t in lowered for t in ("build", "ci", "deploy", "config", "setup")):
                prefix = "perf" if "perf" in lowered else "build"
            else:
                prefix = "feat"
            short_desc = task_description.strip().split(".")[0][:60].lower()
            return f"{prefix}: {short_desc}"

        paths = []
        for f in status.modified + status.staged + status.untracked:
            paths.append(Path(f).stem.lower())

        path_text = " ".join(paths)
        if any(t in path_text for t in ("test", "verification", "spec")):
            return "test: add verification coverage"
        if any(t in path_text for t in ("ui", "style", "css", "theme", "design", "layout")):
            return "style: improve terminal ui"
        if any(t in path_text for t in ("readme", "gitignore", "doc", "license")):
            return "docs: update project metadata"
        if any(t in path_text for t in ("config", "setting", "routing", "model")):
            return "refactor: reconfigure project"
        if any(t in path_text for t in ("builder", "template", "generator", "engine")):
            return "refactor: simplify module"
        if any(t in path_text for t in ("fix", "repair", "patch")):
            return "fix: resolve issue"
        return "chore: update project"

    def _normalize_message(self, message: str) -> str:
        cleaned = " ".join(redact_secret_text(message).strip().split())
        if not cleaned:
            return "chore: update project"
        if re.match(rf"^({'|'.join(GIT_COMMIT_TYPES)})(\([^)]+\))?: .+", cleaned):
            return cleaned
        return "chore: " + cleaned[0].lower() + cleaned[1:]

    def rollback(self) -> tuple[bool, str]:
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"
        head_before = self._get_head_hash()
        if not head_before:
            return False, "No commits to roll back"

        result = self._run(["reset", "--soft", "HEAD~1"])
        if result.ok:
            self._run(["restore", "--staged", "."])
            return True, f"Rolled back commit {head_before}"

        first_commit = self._run(["rev-list", "--max-parents=0", "HEAD"])
        if first_commit.ok and first_commit.stdout.strip() == head_before:
            return False, "Only one commit exists. Use /git-undo to remove it."

        return False, f"Rollback failed: {result.stderr.strip()}"

    def undo(self) -> tuple[bool, str]:
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"
        head_before = self._get_head_hash()
        if not head_before:
            return False, "No commits to undo"

        status = self.full_status()
        if status.has_changes():
            self._run(["stash", "push", "-m", f"auto-stash-before-undo-{head_before}"])

        result = self._run(["reset", "--hard", "HEAD~1"])
        if result.ok:
            return True, f"Undo complete. Removed commit {head_before}. Changes are gone."
        return False, f"Undo failed: {result.stderr.strip()}"

    def revert(self, ref: str = "") -> tuple[bool, str]:
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"
        target = ref if ref else self._get_head_hash()
        if not target:
            return False, "No commits to revert"

        result = self._run(["revert", "--no-edit", target])
        if result.ok:
            new_hash = self._get_head_hash()
            return True, f"Reverted {target[:8]}. New commit: {new_hash}"
        return False, f"Revert failed: {result.stderr.strip()}"

    def diff(self, path: str = "", staged: bool = False) -> list[str]:
        if not self.is_available() or not self.is_repo():
            return []
        args = ["diff"]
        if staged:
            args.append("--cached")
        if path:
            args.append("--")
            args.append(path)
        result = self._run(args)
        if result.ok and result.stdout.strip():
            return result.stdout.splitlines()
        return []

    def diff_summary(self) -> str:
        if not self.is_available() or not self.is_repo():
            return ""
        result = self._run(["diff", "--stat"])
        if result.ok:
            return result.stdout.strip()
        return ""

    def create_branch(self, name: str) -> tuple[bool, str]:
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"
        if not name.strip():
            return False, "Branch name is required"
        check = self._run(["branch", "--list", name.strip()])
        if check.ok and name.strip() in check.stdout:
            return False, f"Branch '{name}' already exists"
        result = self._run(["branch", name.strip()])
        if result.ok:
            return True, f"Branch created: {name.strip()}"
        return False, f"Failed to create branch: {result.stderr.strip()}"

    def switch_branch(self, name: str) -> tuple[bool, str]:
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"
        status = self.full_status()
        if status.has_changes():
            self._run(["stash", "push", "-m", f"auto-stash-before-switch-{name}"])
        result = self._run(["checkout", name.strip()])
        if result.ok:
            return True, f"Switched to branch: {name.strip()}"
        return False, f"Failed to switch branch: {result.stderr.strip()}"

    def list_branches(self) -> list[str]:
        result = self._run(["branch"])
        if result.ok:
            return [b.strip() for b in result.stdout.splitlines() if b.strip()]
        return []

    def stash(self) -> tuple[bool, str]:
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"
        result = self._run(["stash", "push", "-m", f"auto-stash-{datetime.now().strftime('%H%M%S')}", "--include-untracked"])
        if result.ok:
            return True, "Changes stashed"
        return False, f"Stash failed: {result.stderr.strip()}"

    def stash_pop(self) -> tuple[bool, str]:
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"
        result = self._run(["stash", "pop"])
        if result.ok:
            return True, "Stash restored"
        if "No stash entries" in result.stderr:
            return False, "No stashed changes"
        return False, f"Stash pop failed: {result.stderr.strip()}"

    def snapshot_tag(self, name: str) -> tuple[bool, str]:
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"
        if not name.strip():
            name = f"snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        result = self._run(["tag", name.strip()])
        if result.ok:
            return True, f"Snapshot tagged: {name.strip()}"
        return False, f"Tag failed: {result.stderr.strip()}"

    def has_origin(self) -> bool:
        return self._run(["remote", "get-url", "origin"]).ok

    def push(self, remote_url: str = "", branch: str = "main") -> tuple[bool, str]:
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"
        if self._detached_head():
            return False, "Detached HEAD. Check out a branch before pushing."
        if remote_url.strip():
            if self.has_origin():
                self._run(["remote", "set-url", "origin", remote_url.strip()])
            else:
                rm = self._run(["remote", "add", "origin", remote_url.strip()])
                if not rm.ok:
                    return False, f"Failed to add remote: {rm.stderr.strip()}"
        if not self.has_origin():
            return False, "No remote configured. Provide a URL: /git-push <url>"
        branch_name = self._get_branch() or branch
        result = self._run(["push", "origin", branch_name], timeout=180)
        if result.ok:
            return True, f"Pushed to origin/{branch_name}"
        error = result.stderr.strip() or result.error or ""
        if "authentication failed" in error.lower():
            return False, "Authentication failed. Configure a credential helper or SSH key."
        return False, f"Push failed: {error}"

    def release(self, tag: str, notes: str = "") -> tuple[bool, str]:
        if not tag.strip():
            return False, "Tag name is required"
        if not self.is_available() or not self.is_repo():
            return False, "Git not available or not a repository"
        message = notes.strip() or f"Release {tag.strip()}"
        tag_result = self._run(["tag", "-a", tag.strip(), "-m", message])
        if not tag_result.ok:
            return False, f"Tag failed: {tag_result.stderr.strip()}"
        push_result = self._run(["push", "origin", tag.strip()], timeout=180)
        if not push_result.ok:
            return False, f"Tag push failed: {push_result.stderr.strip()}"
        return True, f"Release tag pushed: {tag.strip()}"

    def log(self, count: int = 10) -> list[dict]:
        if not self.is_available() or not self.is_repo():
            return []
        fmt = "--format=%H|%h|%s|%ai|%an"
        result = self._run(["log", f"-{count}", fmt, "--no-color"])
        if not result.ok or not result.stdout.strip():
            return []
        entries = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|", 4)
            if len(parts) >= 4:
                entries.append({
                    "hash": parts[0].strip(),
                    "short": parts[1].strip(),
                    "message": parts[2].strip(),
                    "date": parts[3].strip(),
                    "author": parts[4].strip() if len(parts) > 4 else "",
                })
        return entries
