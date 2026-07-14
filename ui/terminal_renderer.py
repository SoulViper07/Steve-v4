import sys
import os
import re
import time
import threading
import itertools
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live
from rich.text import Text
from rich.progress_bar import ProgressBar as RichProgressBar
from rich.columns import Columns
from rich.layout import Layout
from rich.align import Align

from utils.helpers import (
    TERMINAL_ANSI_OK, STEVE_ASCII, NO_COLOR_SET, TERMINAL_UTF8_OK, 
    get_symbol, strip_rich_markup
)
from config.settings import STEVE_NAME, PLAIN_UI, OUTPUT_MODE
from state import get_state_manager

def _build_console() -> Console:
    return Console(
        highlight=False,
        force_terminal=TERMINAL_ANSI_OK and not STEVE_ASCII and not NO_COLOR_SET,
        no_color=NO_COLOR_SET or STEVE_ASCII or not TERMINAL_ANSI_OK,
        safe_box=not TERMINAL_UTF8_OK,
    )

console = _build_console()

def _plain_terminal() -> bool:
    return PLAIN_UI or STEVE_ASCII or not TERMINAL_ANSI_OK

def _rich_terminal() -> bool:
    return not _plain_terminal() and TERMINAL_ANSI_OK and not NO_COLOR_SET

def _clean_mode() -> bool:
    return OUTPUT_MODE == "clean"

def _color_disabled_reason() -> str:
    if STEVE_ASCII:
        return "Color disabled because STEVE_ASCII=1 or --ascii was requested."
    if NO_COLOR_SET:
        return "Color disabled because NO_COLOR is set."
    if not TERMINAL_ANSI_OK:
        return "Color disabled because terminal does not support ANSI."
    if PLAIN_UI:
        return "Color disabled because --plain was requested."
    return ""

def _info(msg: str):
    if _plain_terminal():
        print(f"  {msg}")
    else:
        console.print(f"  [dim]{msg}[/dim]")

def _ok(msg: str):
    if _plain_terminal():
        print(f"  OK: {msg}")
    else:
        symbol = get_symbol("✔", "OK")
        console.print(f"  [green]{symbol}[/green] {msg}")

def _err(msg: str):
    if _plain_terminal():
        print(f"  ERROR: {msg}")
    else:
        symbol = get_symbol("✘", "!")
        console.print(f"  [bold red]{symbol}[/bold red] [red]{msg}[/red]")

def _warn(msg: str):
    if _plain_terminal():
        print(f"  WARN: {msg}")
    else:
        symbol = get_symbol("⚠", "!")
        console.print(f"  [bold yellow]{symbol}[/bold yellow] {msg}")

def _step(msg: str):
    if _plain_terminal():
        print(f"  >> {msg}")
    else:
        symbol = get_symbol("➻", ">>")
        console.print(f"  [bold cyan]{symbol}[/bold cyan] [cyan]{msg}[/cyan]")

def _print_agent_header(show: bool = True):
    if not show: return
    if _plain_terminal():
        print(f"\n{STEVE_NAME}:")
    else:
        console.print(f"\n[bold magenta]{STEVE_NAME}[/bold magenta]:")


# ── Pipeline Display System ───────────────────────────────────

@dataclass
class PipelineEntry:
    timestamp: float = 0.0
    icon: str = ""
    message: str = ""
    status: str = "info"   

@dataclass
class GitActivity:
    action: str = ""
    detail: str = ""
    ref: str = ""
    ok: bool = False

@dataclass
class PipelineState:
    category: str = ""
    models: list = field(default_factory=list)
    stages: list = field(default_factory=list)
    files_created: list = field(default_factory=list)
    files_edited: list = field(default_factory=list)
    files_removed: list = field(default_factory=list)
    folders_created: list = field(default_factory=list)
    verifications: list = field(default_factory=list)
    repairs: list = field(default_factory=list)
    model_switches: list = field(default_factory=list)
    entries: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    git_activities: list = field(default_factory=list)
    start_time: float = 0.0
    running: bool = False


class ProgressBar:
    def __init__(self, total: int = 15, label: str = ""):
        self.total = total
        self.current = 0
        self.label = label
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self.total <= 0 or _plain_terminal():
            return
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def update(self, current: int, label: str = ""):
        self.current = min(current, self.total)
        if label:
            self.label = label

    def _animate(self):
        width = 20
        while not self._stop.is_set():
            filled = int(self.current / self.total * width) if self.total > 0 else 0
            bar = "█" * filled + "░" * (width - filled)
            pct = int(self.current / self.total * 100) if self.total > 0 else 0
            label = self.label[:30].ljust(30) if self.label else " " * 30
            sys.stdout.write(f"\r  {bar} {pct:3d}%  {label}")
            sys.stdout.flush()
            time.sleep(0.15)
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()

    def stop(self):
        if self._thread:
            self._stop.set()
            self._thread.join(timeout=1)


class PipelineDisplay:
    def __init__(self):
        self.state = PipelineState(start_time=time.monotonic())
        self.progress: Optional[ProgressBar] = None
        self._header_rendered = False
        self._sm = get_state_manager()

    def add(self, icon: str, message: str, status: str = "info"):
        entry = PipelineEntry(timestamp=time.monotonic(), icon=icon, message=message, status=status)
        self.state.entries.append(entry)
        self._sm.add_log(message)

    def add_decision(self, decision: str):
        self.state.decisions.append(decision)

    def stage(self, name: str, model: str = ""):
        self.state.stages.append((name, model))

    def model_switch(self, model: str, reason: str = "", stage: str = ""):
        self.state.models.append(model)
        self.state.model_switches.append((model, reason, stage))
        self._sm.set_model(model, stage, reason)
        self.add("🤖", f"Using {model}" + (f" for {stage}" if stage else ""), "step")

    def file_created(self, path: str):
        self.state.files_created.append(path)
        self._sm.mark_generated(path)
        self.add("📄", f"Created {path}", "ok")

    def file_edited(self, path: str, summary: str = ""):
        self.state.files_edited.append((path, summary))
        self._sm.mark_modified(path)
        msg = f"Edited {path}"
        if summary:
            msg += f"  # {summary}"
        self.add("✏", msg, "ok")

    def file_removed(self, path: str):
        self.state.files_removed.append(path)
        self.add("🗑", f"Removed {path}", "warn")

    def folder_created(self, path: str):
        self.state.folders_created.append(path)
        self.add("📁", f"Created folder {path}", "ok")

    def verify(self, check: str, status: str, detail: str = ""):
        self.state.verifications.append((check, status, detail))
        ico = "✓" if status == "ok" else "⚠" if status == "warn" else "✗"
        self.add(f"  {ico}", f"{check}: {detail}", status)

    def repair(self, msg: str):
        self.state.repairs.append(msg)
        self.add("🔧", msg, "warn")

    def git_activity(self, action: str, detail: str, ref: str = "", ok: bool = True):
        activity = GitActivity(action=action, detail=detail, ref=ref, ok=ok)
        self.state.git_activities.append(activity)
        if action == "commit" and ok and ref:
            self._sm.mark_committed(ref, detail)
        if action == "checkpoint":
            self._sm.git.checkpoints.append(ref) if ref else None
        icons = {
            "init": "🔧",
            "checkpoint": "💾",
            "commit": "📝",
            "restore": "⏪",
            "rollback": "↩",
            "branch": "🌿",
        }
        icon = icons.get(action, "🔀")
        status = "ok" if ok else "err"
        msg = f"{detail}"
        if ref:
            msg += f" [{ref[:8]}]"
        self.add(icon, msg, status)

    def render_header(self, category: str, models: dict):
        if _plain_terminal() or self._header_rendered:
            return
        self._header_rendered = True
        self.state.category = category

        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(justify="left", ratio=1)

        table.add_row(Text.from_markup("[bold cyan]🧠 Execution Pipeline[/bold cyan]"))
        table.add_row(Rule(style="dim"))

        icon_cat = get_symbol("📋", ">")
        table.add_row(Text.from_markup(f"  {icon_cat} [bold]Category:[/bold] [cyan]{category}[/cyan]"))

        if models:
            table.add_row(Text.from_markup(f"  🤖 [bold]Models Selected:[/bold]"))
            for role, model in models.items():
                friendly = model.split(":")[0].split("/")[-1]
                tag = model.split(":")[1] if ":" in model else ""
                label = f"{friendly}:{tag}" if tag else friendly
                table.add_row(Text.from_markup(f"    [dim]{role.capitalize():>12}[/dim] → [green]{label}[/green]"))

        console.print()
        console.print(Panel(table, border_style="cyan", padding=(1, 2)))
        console.print()

    def render_stage(self, name: str, current: int, total: int):
        if _plain_terminal():
            return
        icon = get_symbol("➻", ">>")
        label = name.replace("_", " ").title()
        console.print(f"  [bold cyan]{icon}[/bold cyan] [bold]{label}[/bold]  [dim]({current}/{total})[/dim]")

    def render_verification_block(self, results):
        if _plain_terminal() or not results:
            return
        table = Table.grid(expand=True, padding=(0, 1))
        has_ok = any(r[1] == "ok" for r in results)
        has_warn = any(r[1] == "warn" for r in results)
        has_err = any(r[1] == "err" for r in results)
        border = "green" if not has_err else "yellow" if has_warn else "red"
        
        title_icon = get_symbol("🔍", "[Verify]")
        table.add_row(Text.from_markup(f"  [bold]{title_icon} Verification Results[/bold]"))
        
        for check, status, detail in results:
            if status == "ok":
                ico = get_symbol("✓", "OK")
                table.add_row(Text.from_markup(f"    [green]{ico}[/green] [dim]{check}[/dim]"))
            elif status == "warn":
                ico = get_symbol("⚠", "!")
                table.add_row(Text.from_markup(f"    [yellow]{ico}[/yellow] [dim]{check}[/dim]: {detail}"))
            else:
                ico = get_symbol("✗", "ERR")
                table.add_row(Text.from_markup(f"    [red]{ico}[/red] [dim]{check}[/dim]: {detail}"))
        
        console.print()
        console.print(Panel(table, border_style=border, padding=(1, 2)))
        console.print()

    def render_activity_feed(self):
        if _plain_terminal() or not self.state.entries:
            return
        
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(justify="left", ratio=1)
        table.add_row(Text.from_markup("  [bold]📋 Activity Feed[/bold]"))
        table.add_row(Rule(style="dim"))

        for entry in self.state.entries[-12:]:
            elapsed = entry.timestamp - self.state.start_time
            time_str = f"[{int(elapsed//60):02d}:{int(elapsed%60):02d}]"
            color = {"ok": "green", "warn": "yellow", "err": "red", "step": "cyan", "info": "dim"}.get(entry.status, "dim")
            ico = entry.icon if not _plain_terminal() else ""
            table.add_row(Text.from_markup(f"  [dim]{time_str}[/dim] {ico} [{color}]{entry.message}[/{color}]"))

        console.print()
        console.print(Panel(table, border_style="dim", padding=(1, 2)))
        console.print()

    def render_timeline(self):
        if _plain_terminal() or not self.state.entries:
            return
        
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(justify="left", ratio=1)
        table.add_row(Text.from_markup("  [bold]⏱ Execution Timeline[/bold]"))
        table.add_row(Rule(style="dim"))

        for entry in self.state.entries:
            elapsed = entry.timestamp - self.state.start_time
            time_str = f"[{int(elapsed//60):02d}:{int(elapsed%60):02d}]"
            ico = entry.icon if not _plain_terminal() else ""
            color = {"ok": "green", "warn": "yellow", "err": "red", "step": "cyan", "info": "dim"}.get(entry.status, "dim")
            table.add_row(Text.from_markup(f"  [bold]{time_str}[/bold] {ico} [{color}]{entry.message}[/{color}]"))

        console.print()
        console.print(Panel(table, border_style="cyan", padding=(1, 2)))

    def render_git_block(self):
        if _plain_terminal() or not self.state.git_activities:
            return
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(justify="left", ratio=1)
        title_icon = get_symbol("🔀", "[Git]")
        table.add_row(Text.from_markup(f"  [bold]{title_icon} Git Activity[/bold]"))
        table.add_row(Rule(style="dim"))
        for act in self.state.git_activities:
            icon = get_symbol("✓", "OK") if act.ok else get_symbol("✗", "ERR")
            color = "green" if act.ok else "red"
            ref_part = f"  [dim]{act.ref[:8]}[/dim]" if act.ref else ""
            table.add_row(Text.from_markup(f"    [{color}]{icon}[/{color}] [dim]{act.action}[/dim] {act.detail}{ref_part}"))
        console.print()
        console.print(Panel(table, border_style="cyan", padding=(1, 2)))
        console.print()

    def render_report(self):
        if _plain_terminal():
            return
        
        elapsed = time.monotonic() - self.state.start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(justify="left", ratio=1)
        table.add_column(justify="right")

        table.add_row(Text.from_markup("  [bold]📊 Final Report[/bold]"))
        table.add_row(Rule(style="dim"))

        icon_cat = get_symbol("📋", ">")
        table.add_row(
            Text.from_markup(f"  {icon_cat} [bold]Category:[/bold] [cyan]{self.state.category or 'N/A'}[/cyan]"),
            Text.from_markup(f"[dim]{time_str}[/dim]")
        )

        if self.state.models:
            models_str = ", ".join(
                m.split(":")[0].split("/")[-1] + (":" + m.split(":")[1] if ":" in m else "")
                for m in dict.fromkeys(self.state.models)
            )
            table.add_row(Text.from_markup(f"  🤖 [bold]Models:[/bold] [green]{models_str}[/green]"))

        if self.state.files_created:
            file_list = ", ".join(self.state.files_created[:8])
            if len(self.state.files_created) > 8:
                file_list += f" ... (+{len(self.state.files_created) - 8} more)"
            table.add_row(Text.from_markup(f"  📄 [bold]Created:[/bold] [dim]{file_list}[/dim]"))

        if self.state.files_edited:
            edit_list = ", ".join(p for p, _ in self.state.files_edited[:8])
            if len(self.state.files_edited) > 8:
                edit_list += f" ... (+{len(self.state.files_edited) - 8} more)"
            table.add_row(Text.from_markup(f"  ✏ [bold]Edited:[/bold] [dim]{edit_list}[/dim]"))

        if self.state.folders_created:
            folder_list = ", ".join(self.state.folders_created[:4])
            table.add_row(Text.from_markup(f"  📁 [bold]Folders:[/bold] [dim]{folder_list}[/dim]"))

        if self.state.repairs:
            table.add_row(Text.from_markup(f"  🔧 [bold]Repairs:[/bold] [yellow]{len(self.state.repairs)}[/yellow]"))

        if self.state.git_activities:
            commits = [a for a in self.state.git_activities if a.action == "commit"]
            checkpoints = [a for a in self.state.git_activities if a.action == "checkpoint"]
            parts = []
            if commits:
                parts.append(f"{len(commits)} commit(s)")
            if checkpoints:
                parts.append(f"{len(checkpoints)} checkpoint(s)")
            if parts:
                table.add_row(Text.from_markup(f"  🔀 [bold]Git:[/bold] [dim]{', '.join(parts)}[/dim]"))

        ver_ok = sum(1 for _, s, _ in self.state.verifications if s == "ok")
        ver_total = len(self.state.verifications)
        ver_status = "✓ Passed" if ver_total > 0 and ver_ok == ver_total else "⚠ Partial" if ver_total > 0 else "N/A"
        ver_color = "green" if ver_total > 0 and ver_ok == ver_total else "yellow"
        table.add_row(Text.from_markup(f"  🔍 [bold]Verification:[/bold] [{ver_color}]{ver_status}[/{ver_color}] [{ver_ok}/{ver_total}]"))

        if self.state.decisions:
            table.add_row(Rule(style="dim"))
            table.add_row(Text.from_markup("  💡 [bold]Key Decisions:[/bold]"))
            for d in self.state.decisions[-5:]:
                table.add_row(Text.from_markup(f"    [dim]• {d}[/dim]"))

        table.add_row(Rule(style="dim"))
        final_icon = get_symbol("✅", "[OK]")
        table.add_row(Text.from_markup(f"  {final_icon} [bold green]Completed[/bold green]"))

        console.print()
        console.print(Panel(table, border_style="green", padding=(1, 2)))
        console.print()

    def start_progress(self, total: int = 15, label: str = ""):
        self.progress = ProgressBar(total, label)
        self.progress.start()

    def update_progress(self, current: int, label: str = ""):
        if self.progress:
            self.progress.update(current, label)

    def stop_progress(self):
        if self.progress:
            self.progress.stop()
            self.progress = None


_current_pipeline: Optional[PipelineDisplay] = None

def get_pipeline() -> Optional[PipelineDisplay]:
    global _current_pipeline
    return _current_pipeline

def set_pipeline(pipeline: Optional[PipelineDisplay]):
    global _current_pipeline
    _current_pipeline = pipeline

def create_pipeline() -> PipelineDisplay:
    pipeline = PipelineDisplay()
    set_pipeline(pipeline)
    return pipeline

def clear_pipeline():
    set_pipeline(None)


class TimedActivity:
    def __init__(self, message: str, echo: bool = True):
        self.message = message
        self.echo = echo and not PLAIN_UI and TERMINAL_ANSI_OK
        self.start_time = 0.0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def __enter__(self):
        self.start_time = time.time()
        if self.echo:
            self._thread = threading.Thread(target=self._animate)
            self._thread.start()
        elif not PLAIN_UI:
            _step(self.message)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if self.echo and self._thread:
            self._stop_event.set()
            self._thread.join()
        return False

    def _animate(self):
        pass


class WormLoader(TimedActivity):
    def _animate(self):
        chars = itertools.cycle(["▱", "▰", "▱", "▲"]) if not STEVE_ASCII else itertools.cycle(["-", "\\", "|", "/"])
        while not self._stop_event.is_set():
            char = next(chars)
            sys.stdout.write(f"\r  [cyan]{char}[/cyan] [dim]{self.message}...[/dim]   ")
            sys.stdout.flush()
            time.sleep(0.12)
        sys.stdout.write("\r" + " " * (len(self.message) + 20) + "\r")
        sys.stdout.flush()


def _progress(message: str) -> WormLoader:
    """Backward-compatible progress spinner. Delegates to WormLoader."""
    return WormLoader(message)
