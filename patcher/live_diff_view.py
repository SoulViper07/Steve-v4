from typing import List, Optional

from .diff_engine import DiffResult, DiffLine, DiffType
from ui.terminal_renderer import console, _plain_terminal, get_symbol


def _color(diff_type: DiffType) -> str:
    return {
        DiffType.ADDED: "green",
        DiffType.REMOVED: "red",
        DiffType.MODIFIED: "yellow",
        DiffType.UNCHANGED: "dim",
    }.get(diff_type, "dim")


def _symbol(diff_type: DiffType) -> str:
    return {
        DiffType.ADDED: "+",
        DiffType.REMOVED: "-",
        DiffType.MODIFIED: "~",
        DiffType.UNCHANGED: " ",
    }.get(diff_type, " ")


class LiveDiffView:
    def __init__(self, max_context_lines: int = 5):
        self._max_context = max_context_lines

    def display_diff(self, diff: DiffResult, path: str = ""):
        if not diff.has_changes:
            if _plain_terminal():
                print(f"  No changes: {path}")
            else:
                console.print(f"  [dim]No changes: {path}[/dim]")
            return

        label = path or f"{diff.old_path} -> {diff.new_path}"
        if _plain_terminal():
            print(f"\n  [{label}] {diff.impact_summary}")
            for hunk in diff.hunks:
                print(f"    @@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@")
                for line in hunk.lines:
                    sym = _symbol(line.diff_type)
                    print(f"    {sym} {line.content}")
        else:
            from rich.table import Table
            from rich.text import Text
            from rich.panel import Panel
            from rich.rule import Rule

            table = Table.grid(expand=True, padding=(0, 1))
            table.add_column(justify="left", ratio=1)

            sym = get_symbol("📝", "[Patch]")
            table.add_row(Text.from_markup(f"  [bold]{sym} {label}[/bold]  [dim]{diff.impact_summary}[/dim]"))
            table.add_row(Rule(style="dim"))

            for hunk in diff.hunks:
                hdr = f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@"
                table.add_row(Text.from_markup(f"    [cyan]{hdr}[/cyan]"))

                context_before = []
                context_after = []
                changes = []
                for line in hunk.lines:
                    if line.diff_type == DiffType.UNCHANGED:
                        if changes:
                            context_after.append(line)
                        else:
                            context_before.append(line)
                    else:
                        changes.append(line)

                if len(context_before) > self._max_context:
                    table.add_row(Text.from_markup(f"      [dim]... {len(context_before) - self._max_context} unchanged lines ...[/dim]"))
                    context_before = context_before[-self._max_context:]
                for line in context_before:
                    table.add_row(Text.from_markup(f"      [dim] {line.content}[/dim]"))

                for line in changes:
                    sym = _symbol(line.diff_type)
                    color = _color(line.diff_type)
                    table.add_row(Text.from_markup(f"      [{color}]{sym} {line.content}[/{color}]"))

                if context_after:
                    if len(context_after) > self._max_context:
                        context_after = context_after[:self._max_context]
                        table.add_row(Text.from_markup(f"      [dim]... truncated ...[/dim]"))
                    for line in context_after:
                        table.add_row(Text.from_markup(f"      [dim] {line.content}[/dim]"))

            console.print()
            console.print(Panel(table, border_style="cyan", padding=(1, 2)))
            console.print()

    def display_summary(self, diff: DiffResult, path: str = ""):
        label = path or f"{diff.old_path}"
        if _plain_terminal():
            print(f"  {label}: {diff.impact_summary} ({diff.total_changed} lines affected)")
        else:
            sym = get_symbol("📝", "[Patch]")
            console.print(f"  {sym} [bold]{label}[/bold] [dim]{diff.impact_summary}[/dim]")

    def display_batch(self, diffs: List[DiffResult]):
        for diff in diffs:
            if diff.has_changes:
                path = diff.new_path if diff.new_path != "b/file" else diff.old_path
                self.display_summary(diff, path)
