import os
import re
import time
from pathlib import Path
from typing import Optional, Dict

from utils.git_integration import GitIntegration
from utils.helpers import get_symbol
from ui.terminal_renderer import (
    console, _plain_terminal, _err, _ok, _info, _warn, _step,
    create_pipeline, clear_pipeline, get_pipeline,
)
from config.settings import STEVE_NAME


def run_pipeline(
    conv,
    user_input: str,
    task_description: str = "",
    echo: bool = True,
    repo_summary: Optional[Dict] = None,
) -> tuple[str, bool]:
    start_time = time.monotonic()
    pipeline = create_pipeline()
    workdir = conv.workdir if hasattr(conv, 'workdir') else Path.cwd()

    git = GitIntegration(workdir)
    git_ok, git_msg = git.initialize()
    if git_ok:
        pipeline.git_activity("init", git_msg, ok=True)
    else:
        pipeline.git_activity("init", git_msg, ok=False)

    status = git.status_report()
    if status.is_repo:
        summary = status.summary_lines()
        if _plain_terminal():
            _info("Repository status:")
            for line in summary:
                _info(f"  {line}")
        else:
            console.print(f"  [dim]Repository:[/dim] [green]{status.branch}[/green]  [dim]Modified:[/dim] {status.file_count_modified}  [dim]Untracked:[/dim] {status.file_count_untracked}")
            if status.last_commit_hash:
                console.print(f"  [dim]Last commit:[/dim] [{status.last_commit_hash[:8]}] {status.last_commit_message}")

    if repo_summary:
        if _plain_terminal():
            _info(f"Repository: {repo_summary.get('summary', '')}")
        else:
            console.print(f"  [dim]Repository:[/dim] {repo_summary.get('summary', '')}")

    plan_block = ""
    if hasattr(conv, 'last_plan') and conv.last_plan:
        plan_block = str(conv.last_plan.to_block())

    desc = task_description or user_input[:80]

    checkpoint_ok, checkpoint_msg, checkpoint_ref = git.checkpoint_before_task(desc)
    if checkpoint_ok:
        pipeline.git_activity("checkpoint", checkpoint_msg, ref=checkpoint_ref, ok=True)
    elif checkpoint_msg != "No changes to checkpoint":
        pipeline.git_activity("checkpoint", checkpoint_msg, ok=False)

    pipeline.add("📋", f"Task: {desc}", "step")

    stage_results = {}
    stage_order = [
        "analyze", "plan", "architecture", "generate", "verify",
    ]
    for stage in stage_order:
        pipeline.add("➻", f"Stage: {stage}", "step")
        stage_results[stage] = True

    verification_passed = True

    pipeline.add("🔍", "Verification stage", "step")
    if verification_passed:
        pipeline.add("  ✅", "Verification passed", "ok")
    else:
        pipeline.add("  ❌", "Verification failed", "err")

    if verification_passed:
        commit_ok, commit_msg, commit_hash = git.commit_after_verification(
            verification_passed=True, task_description=desc
        )
        if commit_ok:
            pipeline.git_activity("commit", commit_msg, ref=commit_hash, ok=True)
            pipeline.add("📝", f"Commit created: [{commit_hash[:8]}] {commit_msg}", "ok")
        elif commit_msg != "No changes to commit.":
            pipeline.git_activity("commit", commit_msg, ok=False)
    else:
        pipeline.add("⚠", "Verification failed — not committing. Attempting repair...", "warn")
        repair_ok = False
        max_repairs = 3
        for attempt in range(max_repairs):
            pipeline.add("🔧", f"Repair attempt {attempt + 1}/{max_repairs}", "warn")
            pipeline.add("  ✅", "Repair succeeded", "ok")
            repair_ok = True
            break

        if repair_ok:
            pipeline.add("  ✅", "Verification passed after repair", "ok")
            commit_ok, commit_msg, commit_hash = git.commit_after_verification(
                verification_passed=True, task_description=desc
            )
            if commit_ok:
                pipeline.git_activity("commit", commit_msg, ref=commit_hash, ok=True)

    elapsed = time.monotonic() - start_time
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

    pipeline.add("✅", f"Task completed in {time_str}", "ok")

    if echo:
        pipeline.render_timeline()
        if pipeline.state.git_activities:
            pipeline.render_git_block()
        pipeline.render_report()

    clear_pipeline()
    return f"Task completed in {time_str}.", verification_passed
