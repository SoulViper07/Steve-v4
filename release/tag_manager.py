from __future__ import annotations

from pathlib import Path
from typing import Optional, Callable


class TagManager:
    def __init__(self, workdir: Path):
        self.workdir = Path(workdir).resolve()
        self._git_run: Optional[Callable] = None

    def set_git_runner(self, runner: Callable):
        self._git_run = runner

    def _run(self, args: list[str]) -> tuple[bool, str]:
        import subprocess
        command = ["git"] + args
        try:
            proc = subprocess.run(
                command,
                cwd=str(self.workdir),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0:
                return True, (proc.stdout or "").strip()
            return False, (proc.stderr or "").strip()
        except FileNotFoundError:
            return False, "Git is not installed or not on PATH."
        except subprocess.TimeoutExpired:
            return False, "Git command timed out."
        except Exception as exc:
            return False, str(exc)

    def tag_exists(self, tag: str) -> bool:
        ok, out = self._run(["tag", "-l", tag.strip()])
        return ok and out.strip() == tag.strip()

    def create_tag(self, tag: str, message: str = "") -> tuple[bool, str]:
        tag = tag.strip()
        if not tag:
            return False, "Tag name is required."
        if self.tag_exists(tag):
            return False, f"Tag '{tag}' already exists."
        msg = message.strip() or f"Release {tag}"
        ok, out = self._run(["tag", "-a", tag, "-m", msg])
        if ok:
            return True, f"Tag created: {tag}"
        return False, out or "Tag creation failed."

    def push_tag(self, tag: str, remote: str = "origin") -> tuple[bool, str]:
        tag = tag.strip()
        if not tag:
            return False, "Tag name is required."
        if not self.tag_exists(tag):
            return False, f"Tag '{tag}' does not exist locally."
        ok, out = self._run(["push", remote, tag])
        if ok:
            return True, f"Tag pushed: {tag}"
        error = out or ""
        if "authentication failed" in error.lower():
            return False, "Authentication failed. Configure a credential helper or SSH key."
        if "remote origin not found" in error.lower() or "no such remote" in error.lower():
            return False, "No remote configured. Use /git-push <url> first."
        return False, f"Tag push failed: {error}"

    def delete_tag(self, tag: str, remote: bool = False) -> tuple[bool, str]:
        tag = tag.strip()
        ok_local, out_local = self._run(["tag", "-d", tag])
        result = ""
        if ok_local:
            result += f"Local tag '{tag}' deleted. "
        else:
            result += f"Local delete: {out_local}. "
        if remote:
            ok_remote, out_remote = self._run(["push", "origin", f":refs/tags/{tag}"])
            if ok_remote:
                result += f"Remote tag '{tag}' deleted."
            else:
                result += f"Remote delete: {out_remote}."
        return True, result.strip()

    def list_tags(self, pattern: str = "") -> list[str]:
        args = ["tag"]
        if pattern:
            args.extend(["-l", pattern])
        ok, out = self._run(args)
        if ok and out.strip():
            return [t.strip() for t in out.splitlines() if t.strip()]
        return []

    def get_tag_commit(self, tag: str) -> Optional[str]:
        ok, out = self._run(["rev-list", "-n", "1", tag.strip()])
        return out.strip() if ok and out.strip() else None

    def verify_commit(self, commit_hash: str) -> bool:
        ok, _ = self._run(["cat-file", "-e", commit_hash.strip()])
        return ok

    def latest_tag(self) -> Optional[str]:
        ok, out = self._run(["describe", "--tags", "--abbrev=0"])
        if ok and out.strip():
            return out.strip()
        return None

    def commit_and_tag(
        self, commit_message: str, tag: str, tag_message: str = "", push: bool = False
    ) -> tuple[bool, str, str]:
        import subprocess
        commands = [
            ["add", "."],
            ["commit", "-m", commit_message],
        ]
        for args in commands:
            ok, out = self._run(args)
            if not ok:
                return False, out or f"Failed: git {' '.join(args)}", ""

        ok, out = self._run(["rev-parse", "--short", "HEAD"])
        commit_hash = out.strip() if ok else ""

        ok, out = self.create_tag(tag, tag_message or commit_message)
        if not ok:
            return False, out or "Tag creation failed.", commit_hash

        if push:
            ok, out = self._run(["push", "origin", "HEAD"])
            if not ok:
                return False, f"Commit push failed: {out}", commit_hash
            ok, out = self.push_tag(tag)
            if not ok:
                return False, f"Tag push failed: {out}", commit_hash

        return True, f"Released {tag}", commit_hash