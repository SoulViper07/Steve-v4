# Steve v4

**Next-generation autonomous coding assistant — a complete modular rewrite of the Steve CLI framework.**

Steve v4 is a conversational-first, locally-powered coding agent that inspects, plans, generates, verifies, and repairs software projects through a multi-model AI pipeline. Built from the ground up with a clean 14-layer architecture, Steve v4 replaces the monolithic v3 design with strict separation of concerns, first-class Git integration, and a streaming pipeline that routes every stage to the optimal model for the job.

---

## Vision

Steve exists to be a locally-run, privacy-preserving, autonomous pair programmer — one that does not just chat about code, but **understands your project**, **plans changes**, **writes files**, **verifies correctness**, **repairs failures**, and **commits results** via Git, all while keeping you in the loop through a clean terminal UI.

v4 delivers on that vision by making every subsystem a first-class citizen: Git, verification, repair, streaming, and the model router are all independent modules with clear APIs.

---

## Architecture

```
CLI                         agent.py
  ↓
Conversation Manager        Manages message history and file context
  ↓
Task Analyzer               Classifies intent, detects operational requests
  ↓
Planner (Qwen3:14b)         Generates structured plans with quality profiles
  ↓
Architecture Planner        Builds component trees and file dependency graphs
  ↓
Model Router                Routes each stage to the optimal LLM
  ↓
UI Designer (Mistral-Small) Generates visual identity, palettes, layouts
  ↓
Implementation Engine       Writes code using Qwen2.5-Coder:14b
  ↓
Streaming Generator         Handles token stream, progress events, abort
  ↓
File Writer                 Action tag parser, file I/O, backup, boundaries
  ↓
Verifier                    File existence, syntax checks, quality scoring
  ↓
Repair Engine               Failure analysis, retry, alternative strategies
  ↓
Quality Reviewer            Multi-dimensional scoring, refinement triggers
  ↓
Final Report                Summary, file list, timing, verification status
```

### Model Pipeline

| Layer | Model | Role |
|-------|-------|------|
| Planner | Qwen3:14b | Structured plan generation |
| Architecture Planner | Qwen3:14b | Component tree, dependency graph |
| UI Designer | Mistral-Small | Visual identity, layout, animations |
| Implementation Engine | Qwen2.5-Coder:14b | Code generation, patching |
| Fast Edits | Qwen2.5-Coder:7b | Small edits, fast fixes |

---

## Features

- **Conversational-first** — chat, explain, debug, plan, and brainstorm in natural language
- **Autonomous action** — build, create, fix, refactor, and generate projects via action tags
- **Git as a first-class subsystem** — auto-init, checkpoints before every task, auto-commit on verification pass, rollback, undo, branch management
- **Multi-model pipeline** — routes each stage to the optimal model (Qwen3, Mistral, Qwen2.5-Coder)
- **Incremental file generation** — section-by-section code building with retry logic
- **Visual identity generation** — palette, typography, layout, animation system
- **Project verification** — file existence, syntax checks, quality scoring, refinement triggers
- **Repair engine** — failure analysis, retry strategies, automatic re-verification
- **Graceful degradation** — if any model is unavailable, Steve falls back gracefully
- **Rich terminal UI** — real-time pipeline display, activity feed, final reports (with ASCII fallback)

---

## What's New in v4

| Aspect | Steve v3 | Steve v4 |
|--------|----------|----------|
| Architecture | Monolithic → modular (refactored) | Clean 14-layer pipeline |
| Git | Optional commands | First-class subsystem with checkpoint, auto-commit, rollback |
| Pipeline | 6-stage project generation | 14-layer model-routed pipeline |
| Repair | Implicit (retry sections) | Dedicated RepairEngine with strategy selection |
| File generation | Hardcoded HTML/CSS/JS sections | Generic section-based generation |
| Model routing | Keyword-based task classification | Stage-aware model router with fallback chains |
| Conversation | Coupled to planner/inspector | Pure message store, separated concerns |
| Codebase | 8K-line legacy + 4K-line modular | Clean-slate modular architecture |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/SoulViper07/Steve-v4.git
cd Steve-v4

# 2. Install dependencies
pip install requests rich

# 3. Install and run Ollama (https://ollama.ai)
# 4. Pull the required models
ollama pull qwen3:14b
ollama pull qwen2.5-coder:14b
ollama pull mistral-small:latest

# 5. Start Steve
python agent.py
```

---

## Quick Start

```bash
# Start Steve in the current directory
steve

# Or use the batch launcher
steve.bat

# Start with a specific working directory
steve --workdir /path/to/project
```

### Git Commands

| Command | Description |
|---------|-------------|
| `/git-status` | Show repository status |
| `/git-init` | Initialize a Git repository |
| `/git-commit <msg>` | Stage all and commit |
| `/git-undo` | Hard undo of last commit |
| `/git-rollback` | Soft rollback of last commit |
| `/git-revert [ref]` | Revert a specific commit |
| `/git-restore` | Restore most recent checkpoint |
| `/git-log [n]` | Show commit log |
| `/git-diff [file]` | Show working tree diff |
| `/git-branch [name]` | List or create branches |
| `/git-switch <name>` | Switch to a branch |
| `/git-push [url]` | Push to remote |
| `/git-release <tag>` | Create and push a release tag |

---

## Philosophy

1. **Safety First** — all filesystem operations are validated and backed up before execution
2. **Modularity** — every component has one clear responsibility and a public API
3. **Privacy** — all models run locally via Ollama; no data leaves your machine
4. **Graceful Degradation** — if any component fails, Steve continues with reduced capability
5. **Git-native** — Git is not an add-on; it is the backbone of every task lifecycle

---

## Roadmap

See [ROADMAP.md](./ROADMAP.md) for the full development roadmap.

---

## License

MIT — see [LICENSE](./LICENSE).
