# Architecture

## Overview

Steve v4 is organized into 10 module directories and 2 resource directories. Each module has a single responsibility and a public API consumed by the pipeline orchestrator.

## Layer Architecture

```
CLI  →  Conversation Manager  →  Task Analyzer  →  Planner  →  Architecture Planner
        →  Model Router  →  UI Designer  →  Implementation Engine  →  Streaming Generator
        →  File Writer  →  Verifier  →  Repair Engine  →  Quality Reviewer  →  Final Report
```

## Module Map

### `config/` — Configuration Layer

Loads environment variables, model presets, routing rules, and prompt templates at startup. Provides read-only configuration objects to all other modules.

| File | Responsibility |
|------|----------------|
| `settings.py` | Environment variables (`STEVE_*`, `CODE_AGENT_*`), model presets (fast/balanced/quality), system prompt, route prompts, default gitignore/readme templates |
| `model_config.py` | Model role definitions (orchestrator, creative, coder, fast), stage-to-role mapping, parameter tuning per role, fallback chains |
| `routing.json` | Task category keywords, execution stage sequences, stage-to-model map |

### `core/` — Core Framework

Central logic and state management. Contains the pipeline orchestrator, conversation state, file context, model routing, planning, and project memory.

| File | Responsibility |
|------|----------------|
| `models.py` | Shared dataclasses: `RequestRoute`, `ProjectMap`, `ExecutionPlan`, `VisualIdentity`, `ProjectManifest`, `VerificationResult`, `TaskState`, `TurnMetrics` |
| `conversation.py` | Message history, file context integration, system prompt construction, history trimming |
| `file_context.py` | File loading, project discovery, relevance scoring, turn context building |
| `inspector.py` | Project structure scanning, project type detection (Android, Python, Node, Gradle) |
| `planner.py` | LLM-powered task decomposition, structured plan generation, plan parsing |
| `model_router.py` | Task classification, execution stage resolution, model selection, router state |
| `orchestrator.py` | v3 compatibility pipeline (6-stage project generation) |
| `pipeline.py` | v4 pipeline orchestrator with Git hooks, repair loop, and final report |
| `project_memory.py` | `.steve` artifact persistence (plan, architecture, UI spec, todo, progress, verification, repair log) |

### `providers/` — AI Providers

External AI/LLM connections. Currently one provider (Ollama), designed for extensibility.

| File | Responsibility |
|------|----------------|
| `ollama.py` | Streaming chat API client, model warming, model installation check |

### `actions/` — Filesystem Actions

Parser and executor for agent action tags. Handles the safe transformation of model output into filesystem operations.

| File | Responsibility |
|------|----------------|
| `executor.py` | Action tag parsing (create, replace, edit, patch, folder, run), tag validation, file I/O with backup, fuzzy matching, project boundary enforcement |

### `ui/` — Terminal Interface

Rich/ASCII terminal rendering. Provides display components for pipeline progress, Git activity, verification results, and final reports.

| File | Responsibility |
|------|----------------|
| `terminal_renderer.py` | Console helpers (`_info`, `_ok`, `_err`, `_warn`, `_step`), `PipelineDisplay` (timeline, report, Git block), `ProgressBar`, `WormLoader`, `TimedActivity` |

### `verifier/` — Verification and Quality

File existence, syntax, and quality checks. Produces `VerificationReport` with severity-graded issues.

| File | Responsibility |
|------|----------------|
| `base_verifier.py` | `VerificationReport`/`Issue` dataclasses, web project verification (HTML/CSS/JS), backend verification (Flask/FastAPI/Django), file existence checks, quality scoring |

### `generation/` — Code Generation

Specialized generators for visual identity and incremental file building.

| File | Responsibility |
|------|----------------|
| `identity.py` | Visual identity generation — UI style profiles, color palettes, typography, layout archetypes, animation systems |
| `incremental_engine.py` | Section-by-section file builder, section prompt library, retry logic, file assembly |

### `repair/` — Repair Subsystem

Failure analysis, retry strategies, and automatic repair. Called by the pipeline when verification fails.

| File | Responsibility |
|------|----------------|
| `repair_engine.py` | `RepairAttempt` tracking, strategy selection, retry loop with configurable max attempts |

### `utils/` — Shared Utilities

Environment detection, logging, Git operations, and string utilities. No module-level imports from `core/`, `ui/`, or `actions/`.

| File | Responsibility |
|------|----------------|
| `helpers.py` | Windows UTF-8 bootstrap, terminal capability detection, secret redaction, Rich markup stripping |
| `logger.py` | Debug logging to `.steve/logs/latest.log` with secrets redaction and duplicate detection |
| `git_manager.py` | Complete Git API: init, status, checkpoint, commit, rollback, undo, revert, restore, diff, branch, stash, tag, push, release, log |
| `git_integration.py` | High-level Git orchestration for pipeline: auto-init, checkpoint-before-task, commit-after-verification |

## Dependency Rules

```
utils/          →  (no internal dependencies)
config/         →  utils/
core/           →  utils/, config/, providers/, ui/
providers/      →  config/, utils/
actions/        →  core/, config/, ui/
ui/             →  utils/, config/
verifier/       →  core/
generation/     →  core/, config/, providers/
repair/         →  (standalone)
```

No circular imports. No module outside `utils/` imports from `core/` or `ui/` unless specified above.
