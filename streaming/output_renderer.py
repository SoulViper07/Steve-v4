import sys
import time
from typing import Optional

from ui.terminal_renderer import (
    console, _plain_terminal, _info, _ok, _err, _warn, _step,
    get_pipeline, get_symbol,
)


class OutputRenderer:
    def __init__(self, echo_tokens: bool = True):
        self._echo_tokens = echo_tokens
        self._current_line = ""
        self._last_file = ""
        self._last_section = ""

    def display_tokens(self, tokens: str):
        if self._echo_tokens and not _plain_terminal():
            sys.stdout.write(tokens)
            sys.stdout.flush()

    def section_start(self, file_path: str, section: str):
        self._last_file = file_path
        self._last_section = section
        pipeline = get_pipeline()
        msg = f"Generating [{file_path}] section: {section}"
        if pipeline:
            pipeline.add("  ➻", msg, "step")
        _step(msg)

    def section_progress(self, token_count: int, char_count: int):
        pass

    def section_complete(self, file_path: str, section: str, token_count: int, char_count: int, elapsed: float):
        pipeline = get_pipeline()
        rate = token_count / elapsed if elapsed > 0 else 0
        msg = f"[{file_path}] {section} — {char_count} chars, {token_count} tokens, {elapsed:.1f}s ({rate:.0f} tok/s)"
        if pipeline:
            pipeline.add("  ✓", msg, "ok")
        _ok(msg)

    def section_failed(self, file_path: str, section: str, error: str = ""):
        pipeline = get_pipeline()
        msg = f"[{file_path}] {section} failed"
        if error:
            msg += f": {error}"
        if pipeline:
            pipeline.add("  ✗", msg, "err")
        _err(msg)

    def file_created(self, file_path: str, char_count: int = 0, section_count: int = 0):
        pipeline = get_pipeline()
        size = f" ({char_count} chars, {section_count} sections)" if char_count else ""
        msg = f"* {file_path} created{size}"
        if pipeline:
            pipeline.file_created(file_path)
        else:
            _ok(msg)

    def file_updated(self, file_path: str, diff_summary: str = ""):
        pipeline = get_pipeline()
        msg = f"~ {file_path} updated"
        if diff_summary:
            msg += f"  ({diff_summary})"
        if pipeline:
            pipeline.file_edited(file_path, diff_summary)
        else:
            _ok(msg)

    def file_patched(self, file_path: str, section_count: int = 0):
        msg = f"* {file_path} patched ({section_count} sections)"
        pipeline = get_pipeline()
        if pipeline:
            pipeline.file_edited(file_path, f"patched {section_count} sections")
        else:
            _ok(msg)

    def diff_added(self, item: str):
        pipeline = get_pipeline()
        msg = f"+ Added {item}"
        if pipeline:
            pipeline.add("  +", msg, "ok")
        else:
            _ok(msg)

    def diff_removed(self, item: str):
        pipeline = get_pipeline()
        msg = f"- Removed {item}"
        if pipeline:
            pipeline.add("  -", msg, "warn")
        else:
            _warn(msg)

    def diff_updated(self, item: str):
        pipeline = get_pipeline()
        msg = f"~ Updated {item}"
        if pipeline:
            pipeline.add("  ~", msg, "step")
        else:
            _step(msg)

    def stage_progress(self, stage_name: str):
        pipeline = get_pipeline()
        label = stage_name.replace("_", " ").title()
        msg = f"{label}..."
        if pipeline:
            pipeline.add("➻", msg, "step")
        _step(msg)

    def analyzing(self):
        self.stage_progress("analyzing request")

    def planning(self):
        self.stage_progress("planning")

    def routing(self):
        self.stage_progress("routing")

    def implementing(self):
        self.stage_progress("implementing")

    def verifying(self):
        self.stage_progress("verifying")

    def repairing(self):
        self.stage_progress("repairing")

    def committing(self):
        self.stage_progress("git commit")

    def newline(self):
        if not _plain_terminal():
            console.print()

    def separator(self):
        if not _plain_terminal():
            from rich.rule import Rule
            console.print(Rule(style="dim"))


class NullRenderer(OutputRenderer):
    def display_tokens(self, tokens: str):
        pass

    def section_start(self, file_path: str, section: str):
        pass

    def section_complete(self, file_path: str, section: str, token_count: int, char_count: int, elapsed: float):
        pass

    def section_failed(self, file_path: str, section: str, error: str = ""):
        pass

    def file_created(self, file_path: str, char_count: int = 0, section_count: int = 0):
        pass

    def file_updated(self, file_path: str, diff_summary: str = ""):
        pass

    def stage_progress(self, stage_name: str):
        pass
