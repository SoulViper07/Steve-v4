from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .version_manager import VersionManager, PrereleaseType
from .milestone_manager import MilestoneManager, Milestone
from .changelog_manager import ChangelogManager, ChangelogEntry
from .tag_manager import TagManager


def _err(msg: str):
    print(f"  Error: {msg}", file=sys.stderr)


def _ok(msg: str):
    print(f"  {msg}")


def _warn(msg: str):
    print(f"  Warning: {msg}")


def _step(msg: str):
    print(f"  {msg}")


class ReleaseManager:
    def __init__(self, workdir: Path, git_manager=None):
        self.workdir = Path(workdir).resolve()
        self.state_dir = self.workdir / ".steve" / "state"
        self.settings_path = self.workdir / "config" / "settings.py"
        self.changelog_path = self.workdir / "CHANGELOG.md"
        self.readme_path = self.workdir / "README.md"
        self.git_manager = git_manager

        self.version_manager = VersionManager(self._read_current_version())
        self.milestone_manager = MilestoneManager(self.state_dir)
        self.changelog_manager = ChangelogManager(self.changelog_path)
        self.tag_manager = TagManager(self.workdir)

    def _read_current_version(self) -> str:
        if self.settings_path.exists():
            text = self.settings_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("AGENT_VERSION"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        val = parts[1].strip().strip('"').strip("'")
                        if val:
                            return val
        return "4.0.0"

    def _update_settings_version(self, version_str: str):
        if not self.settings_path.exists():
            return False
        text = self.settings_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        new_lines = []
        updated = False
        for line in lines:
            if line.strip().startswith("AGENT_VERSION"):
                new_lines.append(f'AGENT_VERSION = "{version_str}"')
                updated = True
            else:
                new_lines.append(line)
        if updated:
            self.settings_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return updated

    def _update_readme_latest_milestone(self, name: str, version: str, description: str, modules: list[str]):
        if not self.readme_path.exists():
            return
        text = self.readme_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        new_lines = []
        in_section = False
        section_count = 0
        for line in lines:
            if line.strip().startswith("## Latest Milestone"):
                in_section = True
                section_count += 1
                new_lines.append(line)
                continue
            if in_section:
                if line.strip().startswith("## "):
                    in_section = False
                    new_lines.append(line)
                    continue
                if section_count == 1:
                    if line.strip().startswith("**"):
                        new_lines.append(f"**{version}** — {name}.")
                        continue
                    if line.strip() == "" or line.strip().startswith("Steve now"):
                        continue
                    new_lines.append(line)
                else:
                    new_lines.append(line)
                continue
            new_lines.append(line)

        replacement = [
            f"## Latest Milestone: {name}",
            "",
            f"**{version}** — {description}",
            "",
        ]
        if modules:
            replacement.append("Modules added:")
            for m in modules:
                replacement.append(f"- `{m}`")
            replacement.append("")

        result = "\n".join(new_lines)
        if "## Latest Milestone" in result:
            lines = result.splitlines()
            final_lines = []
            skip_until_next_header = False
            for line in lines:
                if line.strip().startswith("## Latest Milestone"):
                    skip_until_next_header = True
                    continue
                if skip_until_next_header and line.strip().startswith("## "):
                    skip_until_next_header = False
                if skip_until_next_header:
                    continue
                final_lines.append(line)
            result = "\n".join(final_lines)

        first_header = result.find("\n## ")
        if first_header == -1:
            result = result + "\n" + "\n".join(replacement)
        else:
            insert_pos = result.index("\n## ", first_header + 1)
            result = result[:insert_pos] + "\n".join(replacement) + "\n" + result[insert_pos:]

        self.readme_path.write_text(result, encoding="utf-8")

    def _add_to_readme_dev_log(self, name: str, version: str, date: str, description: str, modules: list[str]):
        if not self.readme_path.exists():
            return
        text = self.readme_path.read_text(encoding="utf-8")
        dev_log_marker = "## Development Log"
        if dev_log_marker not in text:
            return
        log_pos = text.index(dev_log_marker)
        next_section = text.find("\n## ", log_pos + len(dev_log_marker))
        after_log = text[log_pos:next_section] if next_section > 0 else text[log_pos:]

        if f"({version})" in after_log:
            return

        entry_lines = [
            f"\n### {date} — {name} ({version})",
            "",
            f"**Purpose:** {description}",
            "",
        ]
        if modules:
            entry_lines.append("**Modules added:**")
            for m in modules:
                entry_lines.append(f"- `{m}`")
            entry_lines.append("")
        entry_lines.append("---\n")

        entry_text = "\n".join(entry_lines)
        if next_section > 0:
            text = text[:next_section] + entry_text + text[next_section:]
        else:
            text = text + entry_text

        self.readme_path.write_text(text, encoding="utf-8")

    def _update_readme_completion_pct(self, pct: int):
        if not self.readme_path.exists():
            return
        text = self.readme_path.read_text(encoding="utf-8")
        import re
        text = re.sub(
            r"\*\*Current completion:\*\* ~\d+%",
            f"**Current completion:** ~{pct}%",
            text,
        )
        self.readme_path.write_text(text, encoding="utf-8")

    def _update_readme_module_table(self, module_name: str):
        if not self.readme_path.exists():
            return
        text = self.readme_path.read_text(encoding="utf-8")
        table_marker = "| `repository/`"
        if table_marker in text:
            insert_pos = text.index(table_marker)
            next_line = text.find("\n", insert_pos)
            before = text[:next_line + 1]
            after = text[next_line + 1:]
            new_row = f"| `release/` | ✓ New | Release & Version Management: version manager, milestone tracker, changelog generator, tag manager |"
            text = before + new_row + "\n" + after
            self.readme_path.write_text(text, encoding="utf-8")

    def _update_readme_project_structure(self):
        if not self.readme_path.exists():
            return
        text = self.readme_path.read_text(encoding="utf-8")
        repo_marker = "├── repository/"
        release_block = """├── release/                  # Release & Version Management
│   ├── __init__.py
│   ├── release_manager.py    # Main orchestrator
│   ├── version_manager.py    # Semantic versioning
│   ├── milestone_manager.py  # Milestone tracking
│   ├── changelog_manager.py  # Changelog generation
│   └── tag_manager.py        # Git tagging
│"""
        if repo_marker in text:
            insert_pos = text.index(repo_marker)
            text = text[:insert_pos] + release_block + "\n" + text[insert_pos:]
            self.readme_path.write_text(text, encoding="utf-8")

    def _infer_prerelease_number(self) -> int:
        latest = self.milestone_manager.get_latest()
        if latest:
            try:
                v = self.version_manager.parse(latest.version)
                return v.prerelease_number + 1
            except (ValueError, AttributeError):
                pass
        changelog_ver = self.changelog_manager.get_latest_version()
        if changelog_ver:
            try:
                v = self.version_manager.parse(changelog_ver)
                return v.prerelease_number + 1
            except (ValueError, AttributeError):
                pass
        return 1

    def prepare(self, release_type: str, name: str = "", description: str = "", modules: Optional[list[str]] = None) -> bool:
        _step("Preparing release...")

        release_type = release_type.lower().strip()
        current = self.version_manager.current

        if release_type == "alpha":
            pnum = self._infer_prerelease_number()
            self.version_manager.current.prerelease = PrereleaseType.ALPHA
            self.version_manager.current.prerelease_number = pnum
        elif release_type == "beta":
            self.version_manager.bump_beta(name)
        elif release_type == "rc":
            self.version_manager.bump_rc(name)
        elif release_type == "stable":
            self.version_manager.bump_stable(name)
        elif release_type == "major":
            self.version_manager.bump_major(name)
        elif release_type == "minor":
            self.version_manager.bump_minor(name)
        elif release_type == "patch":
            self.version_manager.bump_patch(name)
        else:
            _err(f"Unknown release type: {release_type}")
            _ok("Valid types: alpha, beta, rc, stable, major, minor, patch")
            return False

        new_version = self.version_manager.current
        version_str = str(new_version)
        tag_name = new_version.tag()
        today = datetime.now().strftime("%Y-%m-%d")
        milestone_name = name.strip() or f"Release {version_str}"

        _step(f"Version: {version_str}")
        _step(f"Tag: {tag_name}")

        _step("Updating documentation...")
        self._update_settings_version(version_str)
        _ok(f"Updated config/settings.py -> {version_str}")

        entry = self.changelog_manager.generate_entry(
            version=version_str,
            date=today,
            added=modules or [],
            changed=[],
        )
        self.changelog_manager.prepend(entry)
        _ok("Updated CHANGELOG.md")

        self._update_readme_latest_milestone(
            name=milestone_name,
            version=version_str,
            description=description or f"Release {version_str}",
            modules=modules or [],
        )

        self._add_to_readme_dev_log(
            name=milestone_name,
            version=version_str,
            date=today,
            description=description or f"Release {version_str}",
            modules=modules or [],
        )

        if modules:
            for m in modules:
                if m.startswith("release/"):
                    self._update_readme_module_table("release/")
                    self._update_readme_project_structure()
                    break

        _ok("Updated README.md")

        self._update_readme_completion_pct(75)

        milestone = self.milestone_manager.add(Milestone(
            name=milestone_name,
            version=version_str,
            date=today,
            description=description or f"Release {version_str}",
            modules_added=modules or [],
            completion_pct=75,
            architecture_version="4.0",
        ))

        _step("Creating commit...")
        commit_msg = f"feat(release): implement {milestone_name.lower()}"
        try:
            from utils.git_manager import GitManager
            git = GitManager(self.workdir)
            ok, msg, commit_hash = git.commit(message=commit_msg)
            if ok:
                milestone.git_commit = commit_hash
                self.milestone_manager.update_tag(milestone_name, tag_name)
                _ok(f"Commit: [{commit_hash[:8]}] {msg}")
            else:
                commit_hash = self._try_simple_commit(commit_msg)
                if commit_hash:
                    milestone.git_commit = commit_hash
                    _ok(f"Commit: [{commit_hash[:8]}] {commit_msg}")
                else:
                    _ok(f"Commit skipped: {msg}")
        except ImportError:
            commit_hash = self._try_simple_commit(commit_msg)
            if commit_hash:
                milestone.git_commit = commit_hash
                _ok(f"Commit: [{commit_hash[:8]}] {commit_msg}")
            else:
                _ok("Commit skipped (no changes to commit)")

        _step("Creating version tag...")
        if not self.tag_manager.tag_exists(tag_name):
            ok, msg = self.tag_manager.create_tag(tag_name, f"Release {version_str}")
            if ok:
                milestone.release_tag = tag_name
                _ok(msg)
            else:
                _warn(msg)
        else:
            _ok(f"Tag {tag_name} already exists")

        self.milestone_manager.add(milestone)

        _step("Release completed.")
        self._print_summary(milestone, commit_hash if 'commit_hash' in dir() else "")
        return True

    def _try_simple_commit(self, message: str) -> str:
        import subprocess
        try:
            subprocess.run(["git", "add", "."], cwd=str(self.workdir), capture_output=True, timeout=30)
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(self.workdir), capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                hr = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=str(self.workdir), capture_output=True, text=True, timeout=10,
                )
                return hr.stdout.strip()
        except Exception:
            pass
        return ""

    def _print_summary(self, milestone: Milestone, commit_hash: str):
        print()
        print("  Release Summary")
        print("  ===============")
        print(f"  Version:     {milestone.version}")
        print(f"  Tag:         {milestone.release_tag or '(pending)'}")
        print(f"  Name:        {milestone.name}")
        print(f"  Date:        {milestone.date[:10]}")
        if commit_hash:
            print(f"  Commit:      {commit_hash[:8]}")
        if milestone.modules_added:
            print(f"  Modules:     {', '.join(milestone.modules_added)}")
        print(f"  Milestones:  {self.milestone_manager.count()} total")

    def status(self) -> str:
        lines = []
        lines.append(f"  Current version: {self.version_manager.current}")
        lines.append(f"  Next tag:        {self.version_manager.current.tag()}")

        changelog_ver = self.changelog_manager.get_latest_version()
        if changelog_ver:
            lines.append(f"  Latest changelog: {changelog_ver}")

        latest = self.milestone_manager.get_latest()
        if latest:
            lines.append(f"  Last milestone:   {latest.name} ({latest.version})")
            if latest.release_tag:
                lines.append(f"  Last release tag: {latest.release_tag}")
            if latest.git_commit:
                lines.append(f"  Last commit:      {latest.git_commit[:8]}")

        tags = self.tag_manager.list_tags()
        if tags:
            lines.append(f"  Git tags:         {len(tags)} total ({tags[-1]})")
        else:
            lines.append("  Git tags:         none")

        lines.append(f"  Milestones:       {self.milestone_manager.count()} recorded")

        return "\n".join(lines)

    def list_releases(self) -> str:
        milestones = self.milestone_manager.list_all()
        if not milestones:
            return "  No releases recorded."

        lines = ["  Release History"]
        lines.append("  ===============")
        for m in reversed(milestones):
            tag = m.release_tag or "-"
            commit = m.git_commit[:8] if m.git_commit else "-"
            lines.append(f"  v{m.version:<14} {m.date[:10]}  {m.name:<30} tag={tag:<20} commit={commit}")
        return "\n".join(lines)