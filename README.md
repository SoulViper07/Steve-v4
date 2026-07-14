# Steve v4

**Next-generation autonomous coding assistant — locally-powered, privacy-first, pipeline-driven.**

Steve v4 is a conversational-first AI coding agent that inspects, plans, generates, verifies, and repairs software projects through a multi-model pipeline. Every stage is routed to the optimal model for the task. Git is a first-class subsystem — auto-initialized, checkpointed before every task, and automatically committed after successful verification.

---

## Vision

A locally-run, privacy-preserving, autonomous pair programmer that does not just chat about code, but understands your project, plans changes, writes files, verifies correctness, repairs failures, and commits results — all while keeping you in the loop through a clean terminal UI.

Steve v4 delivers on that vision by making every subsystem a first-class citizen with a clear API and single responsibility.

---

## Steve v3 → Steve v4 Evolution

| Aspect | Steve v3 | Steve v4 |
|--------|----------|----------|
| **Architecture** | Monolithic → modular (refactored) | Clean 14-layer pipeline designed from scratch |
| **Git** | Optional slash commands | First-class subsystem: auto-init, checkpoint, auto-commit, rollback, undo, branches |
| **Pipeline** | 6-stage project generation pipeline | 14-layer model-routed pipeline with explicit stage transitions |
| **Repair** | Implicit section retries | Dedicated `RepairEngine` with strategy selection and retry logic |
| **File Generation** | Hardcoded HTML/CSS/JS sections | Generic section-based generation supporting any file type |
| **Model Routing** | Keyword-based task classification | Stage-aware model router with fallback chains |
| **Conversation** | Tightly coupled to planner and inspector | Pure message store with separated concerns |
| **Codebase** | 8K-line legacy + 4K-line modular | Clean-slate modular (~5K lines, 45 files) |

---

## Features

- **Conversational-first** — chat, explain, debug, plan, and brainstorm in natural language. No action tags needed for discussion.
- **Autonomous action** — build, create, fix, refactor, and generate projects via action tags. Infer operational intent automatically.
- **Git as backbone** — auto-initialize repo, checkpoint before every task, auto-commit on verification pass, rollback, undo, branch management. 13 Git commands available.
- **Multi-model pipeline** — routes each pipeline stage to the optimal model (Qwen3:14b, Mistral-Small, Qwen2.5-Coder:14b, Qwen2.5-Coder:7b).
- **Planned architecture** — 14-layer pipeline with conversation manager, task analyzer, planner, architecture planner, model router, UI designer, implementation engine, streaming generator, file writer, verifier, repair engine, quality reviewer, and final report.
- **Incremental file generation** — section-by-section code building with retry logic and memory persistence.
- **Visual identity generation** — design systems with palettes, typography, layout archetypes, and animation systems.
- **Project verification** — file existence, syntax checks, quality scoring, and refinement triggers.
- **Repair engine** — failure analysis, retry strategies, automatic re-verification loop.
- **Graceful degradation** — if any model is unavailable, Steve falls back gracefully instead of crashing.
- **Rich terminal UI** — real-time pipeline display, activity feed, Git activity block, and final reports. ASCII fallback for non-UTF-8 terminals.

---

## Planned Architecture

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
│         Structured plan generation, quality profiles       │
├───────────────────────────────────────────────────────────┤
│                   Architecture Planner                     │
│         Component tree, file map, dependency analysis      │
├───────────────────────────────────────────────────────────┤
│                      Model Router                          │
│         Stage-to-model mapping, fallback chains, warm-up   │
├───────────────────────────────────────────────────────────┤
│               UI Designer (Mistral-Small)                   │
│      Visual identity, layout archetypes, design tokens     │
├───────────────────────────────────────────────────────────┤
│          Implementation Engine (Qwen2.5-Coder:14b)          │
│          Code generation, patching, file creation          │
├───────────────────────────────────────────────────────────┤
│                   Streaming Generator                      │
│        Token stream → chunked output, progress events      │
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

| Model | Role | Size | Required |
|-------|------|------|----------|
| `qwen3:14b` | Planner, architecture, analysis | ~14B | Yes |
| `qwen2.5-coder:14b` | Code generation, patching, repair | ~14B | Yes |
| `mistral-small:latest` | UI design, visual identity, creative | ~7B | Recommended |
| `qwen2.5-coder:7b` | Fast edits, small fixes | ~7B | Optional |

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

## Roadmap Summary

| Phase | Milestone | Status |
|-------|-----------|--------|
| 1 | Foundation — Git, workspace, project structure | ✓ Complete |
| 2 | Planner — structured JSON plan from Qwen3 | ⏳ Next |
| 3 | Model Router — stage-aware routing with fallbacks | Planned |
| 4 | Streaming Generator — token stream, progress events | Planned |
| 5 | Live Terminal — real-time pipeline display | Planned |
| 6 | Verifier — syntax checks, quality scoring | Planned |
| 7 | Repair Engine — failure analysis, retry strategies | Planned |
| 8 | Project Memory — .steve artifact persistence | Planned |
| 9 | Plugins — custom generators, integrations | Future |
| 10 | Stable Release — v4.0.0 stable | Future |

See [ROADMAP.md](./ROADMAP.md) for full details.

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
│   ├── planner.py            # Task decomposition and LLM planning
│   ├── model_router.py       # Task classification, stage routing, model selection
│   ├── orchestrator.py       # v3 compatibility pipeline
│   ├── pipeline.py           # v4 pipeline orchestrator with Git hooks
│   └── project_memory.py     # .steve artifact persistence
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
│   ├── git_manager.py        # 22-method Git API (init, status, checkpoint, commit, rollback, etc.)
│   └── git_integration.py    # High-level Git orchestration for pipeline
│
├── docs/                     # Documentation
│   ├── README.md             # Docs index
│   ├── architecture.md       # Detailed architecture reference
│   ├── git-integration.md    # Git subsystem reference
│   └── development.md        # Development guide
│
├── resources/                # Non-code resources
├── assets/                   # Static assets (images, templates)
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
