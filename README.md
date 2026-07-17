# Steve v4

**Next-generation autonomous coding assistant — locally-powered, privacy-first, pipeline-driven.**

Steve v4 is a conversational-first AI coding agent that inspects, plans, generates, verifies, and repairs software projects through a multi-model pipeline. Every stage is routed to the optimal model via intelligent capability-based selection. Git is a first-class subsystem — auto-initialized, checkpointed before every task, and automatically committed after successful verification.

---

## Vision

A locally-run, privacy-preserving, autonomous pair programmer that does not just chat about code, but understands your project, plans changes, writes files, verifies correctness, repairs failures, and commits results — all while keeping you in the loop through a clean terminal UI with live streaming output.

Steve v4 delivers on that vision by making every subsystem a first-class citizen with a clear API and single responsibility.

---

## Latest Milestone: Execution Engine

**v4.0.0-alpha.4** — Autonomous execution engine with atomic stage decomposition, dependency graph, and per-stage failure recovery.

The Execution Engine is the runtime that decides HOW to build what the Planner decides WHAT to build. It breaks execution plans into atomic stages, resolves dependencies via a directed acyclic graph, executes each stage through a dedicated stage executor, and retries only failed stages instead of regenerating the entire project.

---

## Features

- **Conversational-first** — chat, explain, debug, plan, and brainstorm in natural language. No action tags needed for discussion.
- **Autonomous action** — build, create, fix, refactor, and generate projects via action tags. Infer operational intent automatically.
- **Execution Engine** — receives plans from Planner, decomposes work into atomic stages, resolves dependencies via directed acyclic graph, executes each stage independently, retries only failed stages.
- **Git as backbone** — auto-initialize repo, checkpoint before every task, auto-commit on verification pass, rollback, undo, branch management. 13 Git commands available.
- **Intelligent model routing** — capability-based model selection across 6 models. Three routing modes (quality, performance, balanced). Configurable overrides. Performance tracking and feedback.
- **Live streaming generation** — real-time token display during file generation. Per-section progress with timing. Never appears frozen.
- **Multi-model pipeline** — routes each pipeline stage to the optimal model via capability matching (Qwen3:14b, Qwen2.5-Coder, Mistral-Small, Llama3, Deepseek-Coder).
- **Planned architecture** — modular pipeline with conversation manager, task analyzer, planner, architecture planner, model router, UI designer, execution engine, streaming generator, file writer, verifier, repair engine, quality reviewer, and final report.
- **Incremental file generation** — section-by-section code building with retry logic and memory persistence.
- **Visual identity generation** — design systems with palettes, typography, layout archetypes, and animation systems.
- **Project verification** — file existence, syntax checks, quality scoring, and refinement triggers.
- **Repair engine** — failure analysis, retry strategies, automatic re-verification loop.
- **Graceful degradation** — if any model is unavailable, Steve falls back gracefully instead of crashing.
- **Rich terminal UI** — real-time pipeline display, activity feed, Git activity block, and final reports. ASCII fallback for non-UTF-8 terminals.

---

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│                        CLI (agent.py)                      │
│     argparse, REPL loop, 13 Git commands, UTF-8 bootstrap  │
├───────────────────────────────────────────────────────────┤
│                   Conversation Manager                     │
│         Message history, file context, session state       │
├───────────────────────────────────────────────────────────┤
│                      Task Analyzer                         │
│         Intent classification, operational detection       │
├───────────────────────────────────────────────────────────┤
│                    Planner (Qwen3:14b)                      │
│     4 sub-planners: task, architecture, UI, features       │
├───────────────────────────────────────────────────────────┤
│                   Architecture Planner                     │
│         Component tree, file map, dependency analysis      │
├───────────────────────────────────────────────────────────┤
│                      Model Router                          │
│    Capability-based routing, 6 profiles, 3 modes, overrides│
├───────────────────────────────────────────────────────────┤
│               UI Designer (Mistral-Small)                   │
│      Visual identity, layout archetypes, design tokens     │
├───────────────────────────────────────────────────────────┤
│                     Execution Engine                        │
│  Atomic stage decomposition, dependency graph, scheduling  │
├───────────────────────────────────────────────────────────┤
│          Implementation Engine (Qwen2.5-Coder:14b)          │
│          Code generation, patching, file creation          │
├───────────────────────────────────────────────────────────┤
│                   Streaming Generator                      │
│     Token stream → chunked output, live progress display   │
├───────────────────────────────────────────────────────────┤
│                      File Writer                           │
│       Action tag parser, file I/O, backup, boundaries      │
├───────────────────────────────────────────────────────────┤
│                       Verifier                             │
│     File existence, syntax checks, quality scoring         │
├─────────────────── REPAIR LOOP ───────────────────────────│
│                     Repair Engine                          │
│      Failure analysis, retry strategies, re-verification   │
├───────────────────────────────────────────────────────────┤
│                    Quality Reviewer                        │
│     Multi-dimensional scoring, refinement triggers         │
├───────────────────────────────────────────────────────────┤
│                     Final Report                           │
│    Summary, file list, timing, model usage, Git activity   │
└───────────────────────────────────────────────────────────┘
```

---

## Module Status

| Module | Status | Description |
|--------|--------|-------------|
| `config/` | ✓ Stable | Settings, model config, routing rules |
| `core/` | ✓ Stable | Pipeline, planner, conversation, file context |
| `state/` | ✓ Stable | StateManager — 6 sub-states, JSON persistence |
| `planner/` | ✓ Stable | 4 sub-planners, structured CompletePlan |
| `router/` | ✓ Stable | IntelligentRouter, 6 profiles, capability matching |
| `execution/` | ✓ New | ExecutionEngine, atomic stage decomposition, dependency graph, per-stage retry |
| `streaming/` | ✓ Stable | Live token streaming, progress tracking, real-time display |
| `providers/` | ✓ Stable | Ollama API client (streaming, warming) |
| `actions/` | ✓ Stable | Action tag parser/executor |
| `ui/` | ✓ Stable | Terminal renderer (Rich/ASCII) |
| `verifier/` | ✓ Stable | File checks, quality scoring |
| `generation/` | ✓ Stable | Incremental file builder, section generation |
| `repair/` | ✓ Stable | RepairEngine with retry strategies |
| `utils/` | ✓ Stable | Git, helpers, logging |

---

## Installation

### Requirements

- **Python 3.11 or newer**
- **Ollama** (for local LLM inference) — [ollama.ai](https://ollama.ai)
- **Git** (optional but recommended for full feature set)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/SoulViper07/Steve-v4.git
cd Steve-v4

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install and run Ollama
curl -fsSL https://ollama.ai/install.sh | sh   # Linux/macOS
# or download from https://ollama.ai/download   # Windows

# 4. Pull the required models
ollama pull qwen3:14b
ollama pull qwen2.5-coder:14b
ollama pull mistral-small:latest
```

### Models Supported

| Model | Capabilities | Size | Required |
|-------|-------------|------|----------|
| `qwen3:14b` | Planning, Reasoning, Architecture, Task Analysis, Project Decomposition | ~14B | Yes |
| `qwen2.5-coder:14b` | Code Generation, Refactoring, Bug Fixing, File Implementation | ~14B | Yes |
| `mistral-small:latest` | UI Design, UX Design, Visual Refinement, Design Language | ~7B | Recommended |
| `qwen2.5-coder:7b` | Fast Edits, Small Repairs, Lightweight Coding | ~7B | Optional |
| `llama3:latest` | Documentation, Explanations, General Chat | ~8B | Optional |
| `deepseek-coder:latest` | Fast Edits, Small Repairs, Lightweight Coding | ~7B | Optional |

### Quick Start

```bash
# Start Steve in the current directory
steve

# Or explicitly
python agent.py

# With a specific working directory
python agent.py --workdir /path/to/project

# Minimal UI (plain text, no Rich)
python agent.py --plain
```

---

## CLI Commands

### Router Commands
```
/route <request>           Analyze and display model routing decisions
/router-mode <mode>        Set routing mode (performance|quality|balanced)
/router-always <model>     Always use a specific model for all stages
/router-prefer <model>     Prefer a specific model when capabilities match
/router-disable <model>    Disable a specific model from routing
```

### Git Commands
```
/git-status                Show repository status
/git-commit <msg>          Stage all and commit
/git-undo                  Undo last commit (hard reset)
/git-rollback              Roll back last commit (soft reset, keep changes)
/git-revert [ref]          Revert a commit (default: HEAD)
/git-restore               Restore most recent checkpoint
/git-log [n]               Show commit log (default: 10)
/git-diff [file]           Show working tree diff
/git-branch [name]         List or create a branch
/git-switch <name>         Switch to a branch
/git-push [url]            Push to remote
/git-release <tag>         Create and push a release tag
```

### Planning
```
/plan <request>            Analyze a request and produce an execution plan
```

---

## Roadmap Summary

| Phase | Milestone | Status |
|-------|-----------|--------|
| 1 | Foundation — Git, workspace, project structure | ✓ Complete |
| 2 | Planner — structured JSON plan from Qwen3 | ✓ Complete |
| 3 | State Manager — persistent session state | ✓ Complete |
| 4 | Model Router — capability-based routing, 6 profiles | ✓ Complete |
| 5 | Streaming Generator — live token display, progress tracking | ✓ Complete |
| 6 | Execution Engine — atomic stage decomposition, dependency graph, per-stage retry | ✓ Complete |
| 7 | Verifier — syntax checks, quality scoring | ⏳ Next |
| 8 | Repair Engine — failure analysis, retry strategies | ⏳ Next |
| 9 | Project Memory — .steve artifact persistence | ⏳ Next |
| 10 | Plugins — custom generators, integrations | Future |
| 11 | Live Terminal — enhanced real-time pipeline UI | Future |
| 12 | Stable Release — v4.0.0 stable | Future |

See [ROADMAP.md](./ROADMAP.md) for full details.

---

## Development Log

### 2026-07-17 — Execution Engine (v4.0.0-alpha.4)

**Purpose:** Decide HOW to build what the Planner decides WHAT to build. Break execution plans into atomic stages, resolve dependencies, execute independently, and retry only failed stages.

**Modules added:**
- `execution/__init__.py` — package exports
- `execution/execution_engine.py` — main orchestrator receiving plans from Planner
- `execution/execution_context.py` — tracks current stage, completed stages, progress, elapsed time
- `execution/dependency_manager.py` — builds and resolves directed acyclic dependency graphs
- `execution/task_scheduler.py` — breaks execution plans into independently executable atomic stages
- `execution/stage_executor.py` — dispatches to handlers for folder, file_gen, verify, repair, finalize stages

**Architecture changes:**
- New `execution/` top-level module with 6 sub-modules
- Planner now delegates execution to ExecutionEngine instead of running a linear pipeline
- Dependency graph ensures stages execute only after their dependencies complete
- Per-stage failure recovery — only the failed stage is retried, never the entire project
- Integration with StateManager for continuous stage tracking
- Progress bar with percentage and stage label displayed during execution

**Current completion:** ~55%

### 2026-07-15 — Model Router (v4.0.0-alpha.2)

**Purpose:** Replace hardcoded single-model routing with intelligent capability-based model selection.

**Modules added:**
- `router/__init__.py` — package exports (40+ symbols)
- `router/capabilities.py` — 19 capabilities, 29 stage mappings, 32 role mappings
- `router/model_profiles.py` — 6 model profiles with capability registries
- `router/routing_rules.py` — rule engine with priority chain and config overrides
- `router/performance.py` — model performance tracking and persistence
- `router/model_router.py` — IntelligentRouter with pipeline building and CLI display

**Architecture changes:**
- New `router/` top-level module with 6 sub-modules
- Planner now delegates model selection to IntelligentRouter
- StateManager tracks every model switch with stage and reason
- CLI: `/route`, `/router-mode`, `/router-always`, `/router-prefer`, `/router-disable`

**Commit:** `f0b0799`

**Current completion:** ~30%

### 2026-07-14 — Foundation & Core Pipeline (v4.0.0-alpha.1)

**Purpose:** Establish the repository, Git subsystem, project structure, and core pipeline.

**Modules added:** `config/`, `core/`, `providers/`, `actions/`, `ui/`, `verifier/`, `generation/`, `repair/`, `utils/`, `docs/`

**Architecture changes:** Clean-slate rewrite from Steve v3. 14-layer pipeline design. Git as first-class subsystem.

**Commit:** `72b233f`

**Current completion:** ~15%

---

## Project Structure

```
Steve-v4/
├── agent.py                  # CLI entry point — REPL, commands, bootstrap
├── steve.bat / steve.cmd     # Windows launcher scripts
│
├── config/                   # Configuration layer
│   ├── settings.py           # Environment variables, presets, prompts
│   ├── model_config.py       # Model roles, stage-to-role mapping
│   └── routing.json          # Task categories, execution stages
│
├── core/                     # Core framework
│   ├── models.py             # Shared dataclasses (RequestRoute, ExecutionPlan, etc.)
│   ├── conversation.py       # Message history and context management
│   ├── file_context.py       # File loading, relevance scoring, context building
│   ├── inspector.py          # Project structure analysis (ProjectMap)
│   ├── planner.py            # Legacy task decomposition planner
│   ├── model_router.py       # Legacy task classification and routing
│   ├── orchestrator.py       # v3 compatibility pipeline
│   ├── pipeline.py           # v4 pipeline orchestrator with Git hooks
│   └── project_memory.py     # .steve artifact persistence
│
├── state/                    # State management subsystem
│   ├── __init__.py
│   ├── state_manager.py      # StateManager singleton with 6 sub-states
│   ├── execution_state.py    # Task execution tracking
│   ├── task_state.py         # Task classification and metadata
│   ├── project_state.py      # Project file and component tracking
│   ├── model_state.py        # Model history and current model
│   ├── git_state.py          # Git status and commit tracking
│   └── verification_state.py # Verification results and repair tracking
│
├── planner/                  # Modular planning subsystem
│   ├── __init__.py
│   ├── planner.py            # PlanningEngine orchestrator
│   ├── execution_plan.py     # Data classes (CompletePlan, TaskClassification, etc.)
│   ├── task_classifier.py    # Task classification agent
│   ├── architecture_planner.py  # Architecture planning agent
│   ├── ui_planner.py         # UI/UX design planning agent
│   ├── feature_planner.py    # Feature and verification planning agent
│   └── _llm.py               # Low-level qwen3:14b caller
│
├── router/                   # Intelligent model router
│   ├── __init__.py
│   ├── model_router.py       # IntelligentRouter, pipeline builder, CLI display
│   ├── routing_rules.py      # Rule engine with priority chain and overrides
│   ├── model_profiles.py     # 6 model profiles with capability registries
│   ├── capabilities.py       # Capability taxonomy and stage mappings
│   └── performance.py        # Model performance tracking and persistence
│
├── execution/                # Autonomous execution engine
│   ├── __init__.py
│   ├── execution_engine.py   # Main orchestrator — receives plans, executes stages
│   ├── execution_context.py  # Stage tracking, progress, elapsed time
│   ├── dependency_manager.py # Directed acyclic dependency graph
│   ├── task_scheduler.py     # Atomic stage decomposition
│   └── stage_executor.py     # Stage dispatcher (folder, file gen, verify, repair)
│
├── streaming/                # Streaming generation engine
│   ├── __init__.py
│   ├── stream_manager.py     # Section-by-section streaming orchestrator
│   ├── token_stream.py       # Real-time token streaming from Ollama
│   ├── progress_tracker.py   # Section/file-level progress with timing
│   └── output_renderer.py    # Terminal rendering of streaming output
│
├── providers/                # AI provider integrations
│   └── ollama.py             # Ollama API client (streaming, warming, install)
│
├── actions/                  # Filesystem action system
│   └── executor.py           # Action tag parser, validator, executor
│
├── ui/                       # Terminal interface
│   └── terminal_renderer.py  # Rich/ASCII display (pipeline, Git, reports)
│
├── verifier/                 # Verification and quality
│   └── base_verifier.py      # File checks, web project verification, quality scoring
│
├── generation/               # Code generation modules
│   ├── identity.py           # Visual identity, palettes, layout archetypes
│   └── incremental_engine.py # Section-by-section file builder
│
├── repair/                   # Repair subsystem
│   ├── __init__.py
│   └── repair_engine.py      # Failure analysis, retry strategies
│
├── utils/                    # Shared utilities
│   ├── helpers.py            # Environment detection, redaction
│   ├── logger.py             # Debug logging to .steve/logs/
│   ├── git_manager.py        # 22-method Git API
│   └── git_integration.py    # High-level Git orchestration for pipeline
│
├── docs/                     # Documentation
│   ├── README.md             # Docs index
│   ├── architecture.md       # Detailed architecture reference
│   ├── git-integration.md    # Git subsystem reference
│   └── development.md        # Development guide
│
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── CHANGELOG.md              # Version history
├── ROADMAP.md                # Development roadmap
├── CONTRIBUTING.md           # Contribution guidelines
├── AGENTS.md                 # Agent behavior rules (for Steve itself)
├── ARCH.md                   # Archived v3 architecture reference
├── LICENSE                   # MIT License
└── .gitignore                # Repository ignore rules
```

---

## Philosophy

1. **Safety First** — every filesystem operation is validated, backed up, and boundary-enforced before execution. Edits to core framework files are blocked.
2. **Modularity** — every component has one clear responsibility and a public API. No circular dependencies. Testable in isolation.
3. **Privacy** — all models run locally via Ollama. No code, no prompts, no data ever leaves your machine.
4. **Git-native** — Git is not an add-on or an afterthought. It is the backbone of every task lifecycle: checkpoint → work → verify → commit.
5. **Graceful Degradation** — if any model is unavailable or any component fails, Steve logs the error and continues with reduced capability. Never crash.
6. **Conversational-first** — chat and discussion stay in plain language. Action tags are inferred from operational intent, not manually toggled.

---

## License

MIT — see [LICENSE](./LICENSE).

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on coding standards, branch naming, commit style, and the pull request process.
