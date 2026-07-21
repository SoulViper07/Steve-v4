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
from rich.table import Table
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
        "Repository:",
        "  /repo-status       Show repository intelligence summary",
        "  /repo-search <q>   Semantic search across indexed symbols",
        "  /repo-routes       Find all API routes",
        "  /repo-reindex      Force re-index the repository",
        "",
        "Router:",
        "  /route <request>   Analyze and display model routing decisions",
        "  /router-mode <m>   Set routing mode (performance|quality|balanced)",
        "  /router-always <m>  Always use a specific model for all stages",
        "  /router-prefer <m>  Prefer a specific model when capabilities match",
        "  /router-disable <m> Disable a specific model from routing",
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
        "Planning & Routing:",
        "  /plan <request>    Analyze a request and produce an execution plan",
        "  /route <request>   Show routing decisions for a request",
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


def cmd_plan(request: str, repo_manager=None):
    from pathlib import Path
    from state import get_state_manager
    from planner import PlanningEngine
    workdir = Path.cwd().resolve()
    sm = get_state_manager(workdir)
    sm.initialize_task(request)
    engine = PlanningEngine(workdir, state_manager=sm)
    if repo_manager and repo_manager.is_indexed:
        engine.set_repository_context(repo_manager.summary_dict())
    plan = engine.plan(request)
    if plan:
        _ok(f"Plan [{plan.task_id}] saved to .steve/plans/{plan.task_id}/")
    else:
        _err("Planning failed.")


def cmd_route(request: str, repo_manager=None):
    from router import get_router, route_task
    router = get_router()
    if repo_manager and repo_manager.is_indexed:
        router.set_repository_context(repo_manager.summary_dict())
    pipeline = router.get_pipeline_for_task(request)
    if pipeline and pipeline.steps:
        _ok(f"Routing completed: {pipeline.total_steps} stage(s)")
    else:
        _err("Routing failed.")
    _info("Override with: always_use=<model>, prefer=<model>, disabled=<model>, mode=performance|quality|balanced")


def cmd_repo_status(repo_manager):
    if not repo_manager or not repo_manager.is_indexed:
        _warn("Repository not indexed. Run /repo-reindex first.")
        return
    ctx = repo_manager.context
    if _plain_terminal():
        print(f"\n[Repository Intelligence]")
        print(f"  Files: {ctx.total_files} | Dirs: {ctx.total_dirs} | Symbols: {ctx.total_symbols}")
        print(f"  Languages: {', '.join(ctx.languages.keys())}")
        print(f"  Frameworks: {', '.join(ctx.frameworks.keys())}")
        if ctx.architecture:
            print(f"  Architecture: {ctx.architecture.primary_type.value} ({round(ctx.architecture.confidence * 100)}%)")
        print(f"  Entry points: {len(ctx.entry_points)} | Configs: {len(ctx.config_files)} | Tests: {len(ctx.test_files)}")
        print(f"  Dependencies: {ctx.dependency_count}")
        if ctx.duplicate_functions:
            print(f"  Duplicate functions: {ctx.duplicate_functions}")
        print(f"  Duration: {ctx.duration_ms}ms")
        print(f"  Summary: {ctx.summary}")
    else:
        sym = get_symbol("📊", "[Repo]")
        console.print(f"\n  [bold]{sym} Repository Intelligence[/bold]")
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="dim")
        table.add_column("Value", style="green")
        table.add_row("Files", f"{ctx.total_files}")
        table.add_row("Directories", f"{ctx.total_dirs}")
        table.add_row("Symbols Indexed", f"{ctx.total_symbols}")
        table.add_row("Languages", ", ".join(ctx.languages.keys()))
        table.add_row("Frameworks", ", ".join(ctx.frameworks.keys()))
        if ctx.architecture:
            table.add_row("Architecture", f"{ctx.architecture.primary_type.value} ({round(ctx.architecture.confidence * 100)}%)")
        table.add_row("Entry Points", f"{len(ctx.entry_points)}")
        table.add_row("Config Files", f"{len(ctx.config_files)}")
        table.add_row("Test Files", f"{len(ctx.test_files)}")
        table.add_row("Dependencies", f"{ctx.dependency_count}")
        if ctx.duplicate_functions:
            table.add_row("Duplicates", f"{ctx.duplicate_functions}")
        table.add_row("Scan Duration", f"{ctx.duration_ms}ms")
        console.print(table)
        if ctx.summary:
            console.print(f"  [dim]{ctx.summary}[/dim]")
        console.print()

def cmd_repo_search(repo_manager, query):
    if not repo_manager or not repo_manager.is_indexed:
        _warn("Repository not indexed. Run /repo-reindex first.")
        return
    results = repo_manager.search(query)
    total = len(results["symbols"]) + len(results["files"])
    if total == 0:
        _info(f"No results for '{query}'")
        return
    _ok(f"Found {len(results['symbols'])} symbol(s), {len(results['files'])} file(s) for '{query}'")
    for sym in results["symbols"][:15]:
        if _plain_terminal():
            print(f"  [{sym['kind']}] {sym['name']}  ({sym['file']}:{sym['line']})")
        else:
            console.print(f"    [cyan]{sym['kind']:>10}[/cyan] [green]{sym['name']}[/green] [dim]{sym['file']}:{sym['line']}[/dim]")
    for f in results["files"][:10]:
        if _plain_terminal():
            print(f"  [file] {f}")
        else:
            console.print(f"    [yellow]file[/yellow] [dim]{f}[/dim]")
    if total > 25:
        _info(f"... and {total - 25} more results")

def cmd_repo_routes(repo_manager):
    if not repo_manager or not repo_manager.is_indexed:
        _warn("Repository not indexed. Run /repo-reindex first.")
        return
    routes = repo_manager.find_api_routes()
    if not routes:
        _info("No API routes found")
        return
    _ok(f"Found {len(routes)} API route(s)")
    for r in routes[:30]:
        if _plain_terminal():
            print(f"  {r['method']:6} {r['path']:40} ({r['file']}:{r['line']})")
        else:
            method_colors = {"GET": "green", "POST": "yellow", "PUT": "blue", "DELETE": "red", "PATCH": "magenta"}
            color = method_colors.get(r["method"], "white")
            console.print(f"    [{color}]{r['method']:6}[/{color}] [bold]{r['path']}[/bold] [dim]{r['file']}:{r['line']}[/dim]")
    if len(routes) > 30:
        _info(f"... and {len(routes) - 30} more routes")

def cmd_repo_reindex(repo_manager):
    _step("Re-indexing repository...")
    ctx = repo_manager.reindex()
    _ok(f"Re-indexed {ctx.total_files} files, {ctx.total_symbols} symbols in {ctx.duration_ms}ms")
    if _plain_terminal():
        print(f"  {ctx.summary}")
    else:
        console.print(f"  [dim]{ctx.summary}[/dim]")

def run_repository_scan(repo_manager, state_manager):
    _step("Scanning repository...")
    ctx = repo_manager.index()
    state_manager.update_repository(
        is_indexed=True,
        total_files=ctx.total_files,
        total_dirs=ctx.total_dirs,
        total_symbols=ctx.total_symbols,
        languages=ctx.languages,
        frameworks=ctx.frameworks,
        architecture_type=ctx.architecture.primary_type.value if ctx.architecture else "",
        architecture_confidence=ctx.architecture.confidence if ctx.architecture else 0.0,
        architecture_description=ctx.architecture.description if ctx.architecture else "",
        entry_points=ctx.entry_points,
        config_files=ctx.config_files,
        test_files=ctx.test_files,
        assets=ctx.assets,
        dependency_count=ctx.dependency_count,
        duplicate_functions=ctx.duplicate_functions,
        summary=ctx.summary,
        scanned_at=ctx.scanned_at,
    )
    _ok(f"Indexed {ctx.total_files} files")
    if ctx.languages:
        top_langs = sorted(ctx.languages.items(), key=lambda x: -x[1].get("percentage", 0))[:3]
        for lang, info in top_langs:
            _info(f"Detected {lang}")
    if ctx.frameworks:
        for fw, info in ctx.frameworks.items():
            if info.get("confidence", 0) >= 0.5:
                _info(f"Detected {fw}")
    _info(f"Found {ctx.total_symbols} symbols")
    if ctx.architecture and ctx.architecture.primary_type.value != "unknown":
        _info(f"Architecture: {ctx.architecture.primary_type.value}")
    _ok("Repository ready")
    return ctx


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

    from state import get_state_manager
    sm = get_state_manager(workdir)
    from repository import RepositoryManager
    repo_manager = RepositoryManager(str(workdir))

    print_banner()

    if git_ok:
        _ok(git_msg)
    else:
        _warn(git_msg)

    run_repository_scan(repo_manager, sm)

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
            elif cmd == "repo-status":
                cmd_repo_status(repo_manager)
            elif cmd == "repo-search":
                cmd_repo_search(repo_manager, arg) if arg else _err("Query required. Usage: /repo-search <query>")
            elif cmd == "repo-routes":
                cmd_repo_routes(repo_manager)
            elif cmd == "repo-reindex":
                cmd_repo_reindex(repo_manager)
            elif cmd == "run":
                cmd_run(arg)
            elif cmd == "reset":
                _ok("Conversation reset.")
            elif cmd == "plan":
                cmd_plan(arg, repo_manager)
            elif cmd == "router-mode":
                from router import set_mode
                set_mode(arg) if arg else _err("Mode required (performance|quality|balanced)")
                _ok(f"Router mode set to: {arg}")
            elif cmd == "router-always":
                from router import set_always_use
                set_always_use(arg) if arg else _err("Model name required")
                _ok(f"Always using model: {arg}")
            elif cmd == "router-prefer":
                from router import set_prefer
                set_prefer(arg) if arg else _err("Model name required")
                _ok(f"Preferring model: {arg}")
            elif cmd == "router-disable":
                from router import disable_model
                disable_model(arg) if arg else _err("Model name required")
                _ok(f"Disabled model: {arg}")
            elif cmd in ("route", "router"):
                cmd_route(arg, repo_manager)
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
            run_pipeline(None, raw, task_description=raw, echo=True,
                         repo_summary=repo_manager.summary_dict() if repo_manager and repo_manager.is_indexed else None)


if __name__ == "__main__":
    main()
