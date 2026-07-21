# Changelog

All notable changes to Steve v4 are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [4.0.0-alpha.6] — 2026-07-21

### Added
- **Repository Intelligence Engine** — `repository/` module with 9 sub-modules for complete internal project representation
- `RepositoryManager` — orchestrates scanning, indexing, semantic search, API route detection, unused code detection
- `RepositoryScanner` — recursive file scanner with exclusion rules, entry point/config/asset/test/environment/build/package manager file classification
- `ProjectGraph` — internal graph representation of folders, files, imports, dependencies, relationships, connected components
- `SymbolIndex` — indexes functions, classes, methods, variables, constants, interfaces, types, modules, exports, imports across Python, JavaScript, TypeScript, HTML, CSS
- `DependencyAnalyzer` — import/require/export/static asset dependency analysis for Python, JS/TS, HTML, CSS, Vue
- `LanguageDetector` — 60+ language detection by file extension and well-known filenames
- `FrameworkDetector` — 25+ framework detection (React, Vue, Svelte, Angular, Next.js, Django, Flask, FastAPI, Tailwind, Bootstrap, Spring Boot, Rails, Laravel, Express, and more)
- `ArchitectureAnalyzer` — architecture pattern recognition: MVC, SPA, API, CLI, Microservice, Library, Package, Plugin, Monolith
- `RepositoryState` — 7th sub-state in StateManager with JSON persistence to `.steve/state/repository.json`
- Auto-scan on startup — "Scanning repository..." → "Indexed N files" → "Detected X" → "Repository ready"
- CLI commands: `/repo-status`, `/repo-search <query>`, `/repo-routes`, `/repo-reindex`
- Repository-aware Model Router — router accepts repo context for informed model selection
- Repository-aware Execution Engine — accepts repo summary for indexed execution
- Semantic search — find symbols, files, functions, classes by name query
- API route finder — detects routes from Python decorators and JS/TS route registrations
- Duplicate function detection across the entire codebase
- Architecture recognition with primary type, secondary types, confidence scoring, and evidence list
- Comprehensive test suite: 40+ tests covering scanner, graph, symbol index, dependency analyzer, language detector, framework detector, architecture analyzer

### Changed
- New `repository/` top-level module added to the architecture between CLI and Conversation Manager
- StateManager now manages 7 sub-states (added `repository_state.py`)
- Router includes repository context for better routing decisions
- Pipeline displays repository summary during task execution
- Architecture diagram updated to include Repository Intelligence layer
- Roadmap updated: Phase 8 shifted to Repository Intelligence, subsequent phases renumbered
- Module status table includes `repository/` as a new module with stable status
- Project completion percentage updated from 65% to 75%

---

## [4.0.0-alpha.5] — 2026-07-17

### Added
- **Workspace & File System Manager** — `workspace/` module with 8 sub-modules for centralized filesystem authority
- `WorkspaceManager` — orchestrates all filesystem operations, integrates with StateManager, single entry point for disk I/O
- `PathResolver` — absolute/relative path resolution, exclusion rules (`.git`, `__pycache__`, `node_modules`, etc.), glob support
- `ProjectScanner` — recursive directory tree scanning with configurable excluded directories and file extensions
- `FileTracker` — in-memory project index: 40+ language detection, framework detection (Flask, Django, FastAPI, React, Vue, Svelte, Express, Next.js, Tailwind, Bootstrap), generation/verification status per file
- `FileManager` — full file CRUD (create, read, update, rename, move, delete), backup/restore to `.steve/backups/`
- Smart writes — compare existing content before overwriting; skip if identical; apply surgical edits when possible
- Surgical edit strategies — exact match, whitespace-normalized match, fuzzy match (sequences with ratio >= 0.72)
- `ChangeDetector` — snapshot-based change detection across four change types: added, modified, deleted, moved
- `FileDependencyGraph` — file-level import analysis: Python (`import`/`from`), JS/TS (`require`/`import` `from`), HTML (`link`/`script`/`img` `src`), CSS (`@import`/`url()`)
- Config file detection — package.json, requirements.txt, pyproject.toml, Dockerfile, tsconfig.json, .gitignore, and more
- Continuous StateManager updates for project tree, current file, generated and modified files
- CLI display: workspace scanning, indexing statistics, file operation results, change summaries

### Changed
- New `workspace/` top-level module added to the architecture between Streaming Generator and File Writer
- WorkspaceManager becomes the only component allowed to perform filesystem operations
- Module status table includes `workspace/` as a new module
- Project completion percentage updated from 55% to 65%

---

## [4.0.0-alpha.4] — 2026-07-17

### Added
- **Execution Engine** — `execution/` module with 6 sub-modules for autonomous execution orchestration
- `ExecutionEngine` — receives `CompletePlan` from Planner, coordinates full execution lifecycle, manages stage ordering via dependency graph
- `ExecutionContext` — tracks current stage, completed/remaining stages, progress percentage, elapsed time, retry counts
- `DependencyManager` — builds directed acyclic dependency graphs with topological sort, parallel level detection, cycle validation
- `TaskScheduler` — decomposes execution plans into independently executable atomic stages (folder, html, css, js, verify, repair, finalize)
- `StageExecutor` — dispatches stages to type-specific handlers: folder creation, file generation, verification, repair, finalization
- Per-stage failure recovery — only the failed stage is retried (up to 2 retries), never the entire project
- Dependency graph execution — each stage waits only for its required dependencies before executing
- Live progress bar with percentage and current stage label during execution
- Full abort support — clean shutdown on interrupt at any point during execution
- Continuous StateManager integration — every stage transition updates execution state

### Changed
- New `execution/` top-level module added to the architecture pipeline between Planner and Implementation Engine
- README architecture diagram updated to include Execution Engine layer
- Module status table includes `execution/` as a new module
- Project completion percentage updated from 45% to 55%

---

## [4.0.0-alpha.3] — 2026-07-15

### Added
- **Streaming Generation Engine** — `streaming/` module with live token display, per-file progress tracking, section-level timing, real-time terminal rendering, and continuous StateManager updates
- `StreamManager` — orchestrates section-by-section file generation with live streaming output
- `TokenStream` — wraps Ollama streaming with timing, abort support, and progress callbacks
- `ProgressTracker` — tracks section/file-level generation progress with timing and statistics
- `OutputRenderer` — real-time terminal display of tokens, file operations, and diff-style change indicators
- Live progress display for every stage: analyzing, planning, routing, generating, writing, patching, verifying, committing
- `IncrementalFileBuilder` now streams tokens to terminal in real-time during section generation
- `/route`, `/router-mode`, `/router-always`, `/router-prefer`, `/router-disable` CLI commands
- `PerformanceTracker` persists model performance data to `.steve/router/performance.json`

### Changed
- `router/` — new top-level module replaces hardcoded model selection with capability-based intelligent routing
- `IntelligentRouter` — task classification, pipeline building, multi-model routing, config overrides, StateManager integration
- Model selection is now dynamic: each stage is matched against model capability profiles (quality/performance/balanced modes)
- Planner's `_build_execution_roadmap` now delegates model selection to `IntelligentRouter`
- Documentation updated to include Model Router and Streaming Engine as completed milestones

---

## [4.0.0-alpha.2] — 2026-07-14

### Added
- `state/` module — `StateManager` singleton with 6 sub-states (execution, task, project, model, git, verification), JSON persistence to `.steve/state/`, full public API
- `planner/` module — `PlanningEngine` with 4 sub-planners (task classifier, architecture, UI, features), structured `CompletePlan` with `ExecutionRoadmap`, `.steve/plans/` persistence
- `router/` module — `IntelligentRouter` with capability-based model selection, 6 model profiles, routing rules engine, config overrides, performance tracking
- `ModelProfile` dataclass — 6 supported models with capability registries, speed/quality ratings, priority-based fallback
- Capability taxonomy — 19 capability definitions, 29 stage-to-capability mappings, 32 stage-to-role mappings
- Config override system — `always_use`, `prefer`, `disabled_models`, `mode` (performance/quality/balanced)
- Performance tracking — model response times, success rates, quality scores per stage/category, persistence to JSON

---

## [4.0.0-alpha.1] — 2026-07-14

### Added
- Complete architecture rewrite from Steve v3 with a clean 14-layer pipeline
- New repository initialized at `github.com/SoulViper07/Steve-v4`
- First-class Git integration with 22-method `GitManager` API
- `GitIntegration` orchestration layer for pipeline Git hooks
- `RepairEngine` with strategy selection and retry logic
- `PipelineDisplay` Git activity tracking (`git_activity()`, `render_git_block()`)
- Pipeline orchestrator with checkpoint-before-task and auto-commit-after-verification
- 13 Git CLI commands: `/git-status`, `/git-init`, `/git-commit`, `/git-undo`, `/git-rollback`, `/git-revert`, `/git-restore`, `/git-log`, `/git-diff`, `/git-branch`, `/git-switch`, `/git-push`, `/git-release`
- Professional project documentation (README, CHANGELOG, ROADMAP, CONTRIBUTING, docs/)
- Comprehensive `.gitignore` covering Python, venvs, logs, caches, builds, IDE, Ollama, OS files

### Changed
- Reorganized repository into clean module hierarchy: `config/`, `core/`, `providers/`, `actions/`, `ui/`, `verifier/`, `generation/`, `repair/`, `utils/`, `docs/`, `resources/`, `assets/`

### Removed
- Removed `templates/manager.py` (delegated to legacy monolithic)
- Removed `agent_legacy.py` (8K-line monolithic replaced by modular architecture)
- Removed `app.py` (placeholder stub)
- Removed `test_agent_verification.py` (v3-specific tests — will be replaced)
- Removed stray `.git` from home directory

---

## [3.2.0] — Steve v3 (legacy, pre-fork)

The last release of Steve v3. See `C:\Users\areet\Tools` for the v3 codebase.

Key characteristics of v3 (retained for reference):
- Monolithic → modular refactoring path
- 6-stage project generation pipeline
- Keyword-based task classification
- Hardcoded HTML/CSS/JS section generation
- Optional Git commands via slash commands
