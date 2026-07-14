# Git Integration

## Overview

Git is a first-class subsystem in Steve v4. It is not an optional add-on. Every task lifecycle follows this pattern:

```
Checkpoint → Work → Verify → Commit (on success)
                            → Repair → Re-verify → Commit (on success)
                            → Rollback / Undo (on failure)
```

## GitManager API

**File:** `utils/git_manager.py` — 22 public methods

### Repository Management

| Method | Description | Git Command |
|--------|-------------|-------------|
| `init()` | Initialize repository, create `.gitignore` | `git init` |
| `is_available()` | Check if Git is installed | `git --version` |
| `is_repo()` | Check if workdir is inside a repo | `git rev-parse --is-inside-work-tree` |

### Status

| Method | Description | Git Command |
|--------|-------------|-------------|
| `full_status()` | Rich `GitStatus` object with all state | `git status --porcelain`, `git log -1`, `git rev-list --count` |
| `branch_name()` | Current branch name | `git branch --show-current` |
| `log(count)` | Recent commit history | `git log -n <count>` |
| `diff(path, staged)` | Working tree diff | `git diff` |
| `diff_summary()` | Diff stat summary | `git diff --stat` |

### Checkpoints (Stash-based)

| Method | Description | Git Command |
|--------|-------------|-------------|
| `checkpoint(message)` | Create lightweight save | `git stash push -m <message> --include-untracked` |
| `restore_checkpoint(ref)` | Restore a specific checkpoint | `git stash pop` |
| `list_checkpoints()` | List all checkpoints | `git stash list` |

### Commits

| Method | Description | Git Command |
|--------|-------------|-------------|
| `commit(message, task_desc)` | Stage all and commit with auto-generated message | `git add . && git commit -m <message>` |
| `suggest_message(status, desc)` | Auto-generate conventional commit message | — |

### Rollback / Undo / Revert

| Method | Description | Git Command |
|--------|-------------|-------------|
| `rollback()` | Soft reset — keep changes, unstage | `git reset --soft HEAD~1 && git restore --staged .` |
| `undo()` | Hard reset — destroy changes | `git reset --hard HEAD~1` |
| `revert(ref)` | Create new commit undoing a previous one | `git revert --no-edit <ref>` |

### Branch Management

| Method | Description | Git Command |
|--------|-------------|-------------|
| `create_branch(name)` | Create a new branch | `git branch <name>` |
| `switch_branch(name)` | Switch to branch (stashes changes) | `git checkout <name>` |
| `list_branches()` | List all branches | `git branch` |

### Stash

| Method | Description | Git Command |
|--------|-------------|-------------|
| `stash()` | Stash working directory changes | `git stash push -m <message>` |
| `stash_pop()` | Restore most recent stash | `git stash pop` |

### Remote

| Method | Description | Git Command |
|--------|-------------|-------------|
| `push(url)` | Push to remote | `git push origin <branch>` |
| `has_origin()` | Check if origin remote exists | `git remote get-url origin` |
| `release(tag, notes)` | Create and push annotated tag | `git tag -a <tag> && git push origin <tag>` |

### Future-ready

| Method | Description |
|--------|-------------|
| `snapshot_tag(name)` | Create lightweight tag snapshot |

## GitIntegration Layer

**File:** `utils/git_integration.py` — Orchestrates Git for the pipeline.

| Method | Description |
|--------|-------------|
| `initialize()` | Auto-init repo on startup |
| `status_report()` | Get `GitStatus` for display |
| `checkpoint_before_task(desc)` | Create checkpoint before work begins |
| `commit_after_verification(passed, desc)` | Auto-commit on verification pass |
| `rollback()` | Soft rollback of last commit |
| `undo()` | Hard undo of last commit |
| `restore_last_checkpoint()` | Pop most recent stash |
| `diff_preview()` | Get diff stat for display |

## Pipeline Integration

In `core/pipeline.py`:

1. **Startup:** `GitIntegration.initialize()` — auto-inits repo + creates `.gitignore`
2. **Before work:** `GitIntegration.checkpoint_before_task()` — stashes current state
3. **After verification pass:** `GitIntegration.commit_after_verification()` — stages all + commits with auto-generated message
4. **After verification fail:** No commit. Repair loop runs. Only commits after successful re-verification.
5. **Git activity:** Every Git operation is logged to `PipelineDisplay.git_activity()` for display in `render_git_block()` and the final report.

## CLI Commands

13 Git commands available in the REPL:

| Command | Maps to |
|---------|---------|
| `/git-status` | `GitManager.full_status()` |
| `/git-init` | `GitManager.init()` |
| `/git-commit <msg>` | `GitManager.commit(message=<msg>)` |
| `/git-undo` | `GitManager.undo()` |
| `/git-rollback` | `GitManager.rollback()` |
| `/git-revert [ref]` | `GitManager.revert(ref)` |
| `/git-restore` | `GitManager.restore_checkpoint()` |
| `/git-log [n]` | `GitManager.log(n)` |
| `/git-diff [file]` | `GitManager.diff(path, staged)` |
| `/git-branch [name]` | `GitManager.list_branches()` / `create_branch()` |
| `/git-switch <name>` | `GitManager.switch_branch(name)` |
| `/git-push [url]` | `GitManager.push(url)` |
| `/git-release <tag>` | `GitManager.release(tag)` |

## Graceful Degradation

If `git --version` fails at startup:
- `GitManager.is_available()` returns `False`
- `GitIntegration.initialize()` returns `(False, "Git is not available...")`
- All Git commands display "Git is not installed or not on PATH."
- Pipeline continues without Git — no checkpoint, no auto-commit
- PipelineDisplay shows Git activity as errors but does not halt

## Future Features

The architecture supports these planned additions:
- **Automatic feature branches** — create `feat/<task-name>` per pipeline run
- **Merge support** — merge feature branches back to `main` after verification
- **Project snapshots** — lightweight tags per milestone
- **AI-generated commit messages** — use the planner's task description to generate messages
- **Change summaries** — generate human-readable summaries from `git diff --stat`
