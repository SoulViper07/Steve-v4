#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    os.environ.setdefault("PYTHONUTF8", "1")

from utils.helpers import IS_WINDOWS, TERMINAL_UTF8_OK, STEVE_ASCII
from utils.git_manager import GitManager
from utils.git_integration import GitIntegration
from ui.terminal_renderer import (
    console, _plain_terminal, _info, _ok, _err, _warn, _step,
    get_symbol,
)
from config.settings import STEVE_NAME, AGENT_VERSION, PLAIN_UI


def print_banner():
    if _plain_terminal():
        print(f"{STEVE_NAME} v{AGENT_VERSION}")
        print("=" * 40)
    else:
        console.print(f"\n[bold cyan]{STEVE_NAME} v{AGENT_VERSION}[/bold cyan]")
        console.print("[dim]Conversational coding assistant[/dim]")
        console.print()


def print_help():
    lines = [
        f"\n{STEVE_NAME} commands:",
        "  /help              Show this help",
        "  /exit, /quit       Exit",
        "",
        "Git commands:",
        "  /git-status        Show repository status",
        "  /git-init          Initialize a Git repository",
        "  /git-commit <msg>  Stage all and commit",
        "  /git-undo          Undo last commit (hard reset)",
        "  /git-rollback      Roll back last commit (soft reset, keep changes)",
        "  /git-revert [ref]  Revert a commit (default: HEAD)",
        "  /git-restore       Restore most recent checkpoint",
        "  /git-log [n]       Show commit log (default: 10)",
        "  /git-diff [file]   Show working tree diff",
        "  /git-branch [name] List or create a branch",
        "  /git-switch <name> Switch to a branch",
        "  /git-push [url]    Push to remote",
        "  /git-release <tag> Create and push a release tag",
        "",
        "Planning:",
        "  /plan <request>    Analyze a request and produce an execution plan",
        "",
        "Other commands:",
        "  /run <cmd>         Run a shell command",
        "  /load <path>       Load files into context",
        "  /ls [path]         List directory contents",
        "  /cd <path>         Change directory",
        "  /reset             Reset conversation",
    ]
    if _plain_terminal():
        print("\n".join(lines))
    else:
        for line in lines:
            console.print(f"  [dim]{line}[/dim]")


def cmd_git_status(git: GitIntegration):
    status = git.status_report()
    if not status.available:
        _err("Git is not installed or not on PATH.")
        return
    if not status.is_repo:
        _warn("Not a Git repository. Run /git-init to create one.")
        return

    lines = status.summary_lines()
    if _plain_terminal():
        print("\n[Repository Status]")
        for line in lines:
            print(f"  {line}")
    else:
        console.print()
        sym = get_symbol("🔀", "[Git]")
        console.print(f"  [bold]{sym} Repository Status[/bold]")
        for line in lines:
            if line.startswith("Branch:"):
                console.print(f"    🌿 [bold]{line}[/bold]")
            elif line.startswith("Modified:") or line.startswith("Untracked:") or line.startswith("Staged:"):
                console.print(f"    [yellow]{line}[/yellow]")
            elif line.startswith("Last commit:"):
                console.print(f"    [dim]{line}[/dim]")
            elif line.startswith("  M "):
                console.print(f"    [red]{line}[/red]")
            elif line.startswith("  ? "):
                console.print(f"    [dim]{line}[/dim]")
            elif line.startswith("  ✓"):
                console.print(f"    [green]{line}[/green]")
            else:
                console.print(f"    {line}")
        console.print()


def cmd_git_init(git: GitIntegration):
    ok, msg = git.initialize(auto_init=True)
    if ok:
        _ok(msg)
    else:
        _err(msg)


def cmd_git_commit(git: GitIntegration, message: str):
    if not git.ready:
        _err("Git not ready. Run /git-init first.")
        return
    ok, msg, commit_hash = git.git.commit(message=message)
    if ok:
        _ok(f"Commit created: [{commit_hash[:8]}] {msg}")
    else:
        _err(msg)


def cmd_git_undo(git: GitIntegration):
    ok, msg = git.undo()
    if ok:
        _warn(msg)
    else:
        _err(msg)


def cmd_git_rollback(git: GitIntegration):
    ok, msg = git.rollback()
    if ok:
        _ok(msg)
    else:
        _err(msg)


def cmd_git_revert(git: GitIntegration, ref: str):
    ok, msg = git.git.revert(ref)
    if ok:
        _ok(msg)
    else:
        _err(msg)


def cmd_git_restore(git: GitIntegration):
    ok, msg = git.restore_last_checkpoint()
    if ok:
        _ok(msg)
    else:
        _err(msg)


def cmd_git_log(git: GitIntegration, count: int = 10):
    entries = git.git.log(count)
    if not entries:
        _info("No commits yet.")
        return
    if _plain_terminal():
        print("\n[Commit Log]")
        for e in entries:
            print(f"  [{e['short']}] {e['message']}  ({e['date'][:10]})")
    else:
        console.print()
        sym = get_symbol("📋", "[Log]")
        console.print(f"  [bold]{sym} Recent Commits[/bold]")
        for e in entries:
            console.print(f"    [green]{e['short']}[/green] [dim]{e['message']}[/dim]")
            console.print(f"           [dim]{e['date'][:10]} by {e['author']}[/dim]")
        console.print()


def cmd_git_diff(git: GitIntegration, path: str = ""):
    lines = git.git.diff(path=path)
    if not lines:
        lines = git.git.diff(staged=True, path=path)
    if not lines:
        _info("No changes to show.")
        return
    if _plain_terminal():
        for line in lines:
            print(line)
    else:
        for line in lines:
            if line.startswith("+") and not line.startswith("+++"):
                console.print(f"  [green]{line}[/green]")
            elif line.startswith("-") and not line.startswith("---"):
                console.print(f"  [red]{line}[/red]")
            elif line.startswith("@@"):
                console.print(f"  [cyan]{line}[/cyan]")
            elif line.startswith("diff --git"):
                console.print(f"  [bold]{line}[/bold]")
            else:
                console.print(f"  {line}")


def cmd_git_branch(git: GitIntegration, name: str = ""):
    if not name:
        branches = git.git.list_branches()
        if _plain_terminal():
            print("\n[Branches]")
            for b in branches:
                print(f"  {b}")
        else:
            console.print()
            sym = get_symbol("🌿", "[Branch]")
            console.print(f"  [bold]{sym} Branches[/bold]")
            for b in branches:
                if b.startswith("*"):
                    console.print(f"    [green]{b}[/green]")
                else:
                    console.print(f"    {b}")
            console.print()
        return
    ok, msg = git.git.create_branch(name)
    if ok:
        _ok(msg)
    else:
        _err(msg)


def cmd_git_switch(git: GitIntegration, name: str):
    ok, msg = git.git.switch_branch(name)
    if ok:
        _ok(msg)
    else:
        _err(msg)


def cmd_git_push(git: GitIntegration, url: str = ""):
    ok, msg = git.git.push(remote_url=url)
    if ok:
        _ok(msg)
    else:
        _err(msg)


def cmd_git_release(git: GitIntegration, tag: str):
    ok, msg = git.git.release(tag)
    if ok:
        _ok(msg)
    else:
        _err(msg)


def cmd_run(command: str):
    import subprocess
    try:
        proc = subprocess.run(command, shell=True, capture_output=False, timeout=30)
        if proc.returncode != 0:
            _err(f"Command exited with code {proc.returncode}")
    except subprocess.TimeoutExpired:
        _err("Command timed out after 30s")
    except Exception as e:
        _err(str(e))


def cmd_plan(request: str):
    from pathlib import Path
    from state import get_state_manager
    workdir = Path.cwd().resolve()
    sm = get_state_manager(workdir)
    sm.initialize_task(request)
    engine = PlanningEngine(workdir, state_manager=sm)
    plan = engine.plan(request)
    if plan:
        _ok(f"Plan [{plan.task_id}] saved to .steve/plans/{plan.task_id}/")
    else:
        _err("Planning failed.")


def main():
    workdir = Path.cwd().resolve()
    p = argparse.ArgumentParser(description=f"{STEVE_NAME} v{AGENT_VERSION}")
    p.add_argument("path", nargs="?", default=".", help="Working directory")
    p.add_argument("--workdir", default=None, help="Working directory (compatibility)")
    p.add_argument("--plain", action="store_true", help="Minimal UI")
    args = p.parse_args()

    requested = args.path if args.path != "." else (args.workdir or ".")
    workdir = Path(requested).resolve()
    os.chdir(workdir)

    git = GitIntegration(workdir)
    git_ok, git_msg = git.initialize(auto_init=True)

    print_banner()

    if git_ok:
        _ok(git_msg)
    else:
        _warn(git_msg)

    if _plain_terminal():
        print(f"\nTalk to {STEVE_NAME} or type /help for commands.\n")
    else:
        console.print(f"\n  [dim]Type [cyan]/help[/cyan] for commands. Talk to {STEVE_NAME} naturally.[/dim]\n")

    while True:
        try:
            raw = input()
        except (KeyboardInterrupt, EOFError):
            if _plain_terminal():
                print("\nGoodbye!")
            else:
                console.print("\n  [dim]Goodbye![/dim]")
            break

        if not raw:
            continue

        if raw.startswith("/"):
            parts = raw[1:].split(" ", 1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in ("exit", "quit", "q"):
                break
            elif cmd == "help":
                print_help()
            elif cmd == "git-status":
                cmd_git_status(git)
            elif cmd == "git-init":
                cmd_git_init(git)
            elif cmd == "git-commit":
                cmd_git_commit(git, arg)
            elif cmd == "git-undo":
                cmd_git_undo(git)
            elif cmd == "git-rollback":
                cmd_git_rollback(git)
            elif cmd == "git-revert":
                cmd_git_revert(git, arg)
            elif cmd == "git-restore":
                cmd_git_restore(git)
            elif cmd == "git-log":
                count = int(arg) if arg.strip().isdigit() else 10
                cmd_git_log(git, count)
            elif cmd == "git-diff":
                cmd_git_diff(git, arg)
            elif cmd == "git-branch":
                cmd_git_branch(git, arg)
            elif cmd == "git-switch":
                cmd_git_switch(git, arg)
            elif cmd == "git-push":
                cmd_git_push(git, arg)
            elif cmd == "git-release":
                cmd_git_release(git, arg)
            elif cmd == "run":
                cmd_run(arg)
            elif cmd == "reset":
                _ok("Conversation reset.")
            elif cmd == "plan":
                cmd_plan(arg)
            elif cmd in ("ls",):
                try:
                    target = Path(arg).resolve() if arg else workdir
                    items = list(target.iterdir())
                    for item in sorted(items, key=lambda x: (not x.is_dir(), x.name.lower())):
                        suffix = "/" if item.is_dir() else ""
                        print(f"  {item.name}{suffix}")
                except Exception as e:
                    _err(str(e))
            else:
                _err(f"Unknown command: /{cmd}  Use /help")
        else:
            from core.pipeline import run_pipeline
            run_pipeline(None, raw, task_description=raw, echo=True)


if __name__ == "__main__":
    main()
