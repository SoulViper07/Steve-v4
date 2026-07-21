# Steve v4 Roadmap

## Overview

Steve v4 is built in 11 phases. Each phase produces a working, testable increment.

**Current phase:** 9 — Verifier

**Progress:** 75% — Foundation ✓, Planner ✓, State Manager ✓, Model Router ✓, Streaming ✓, Execution Engine ✓, Workspace Manager ✓, Repository Intelligence ✓

---

## Phase 1 — Foundation ✓

*Establish the repository, project structure, Git subsystem, and documentation.*

- [x] Clean workspace creation and module migration from v3
- [x] Git as a first-class subsystem
- [x] `GitManager` with 22 methods (init, status, checkpoint, commit, rollback, undo, revert, restore, diff, branch, stash, tag, push, release, log)
- [x] Auto-checkpoint before every task
- [x] Auto-commit after successful verification
- [x] No-commit policy on verification failure
- [x] Rollback, undo, revert, restore commands
- [x] Branch creation and switching
- [x] 13 Git CLI commands in agent.py
- [x] Git activity display in pipeline (`git_activity()`, `render_git_block()`)
- [x] Professional project documentation (README, CHANGELOG, ROADMAP, CONTRIBUTING, docs/)
- [x] Graceful degradation when Git is unavailable

**Deliverable:** Working terminal agent with full Git lifecycle management.

---

## Phase 2 — Planner ✓

*Implement the structured plan generator using Qwen3:14b.*

- [x] `PlanningEngine` with 4 sub-planners (task classifier, architecture, UI, features)
- [x] Structured `CompletePlan` with `ExecutionRoadmap`
- [x] Task classification — project type, complexity, category, languages, frameworks
- [x] Architecture planning — component tree, file map, data flow
- [x] UI planning — design language, color scheme, typography, layout archetype
- [x] Feature planning — features, verification strategy, dependencies, model recommendations
- [x] Plan persistence to `.steve/plans/{task_id}/`
- [x] Fallback plan generation when LLM unavailable
- [x] StateManager integration — task classification, architecture, feature updates

**Deliverable:** Steve can analyze a request and produce a structured, queryable plan.

---

## Phase 3 — State Manager ✓

*Implement persistent session state across all subsystems.*

- [x] `StateManager` singleton with 6 sub-states (execution, task, project, model, git, verification)
- [x] JSON persistence to `.steve/state/` with atomic writes
- [x] Full public API: `initialize_task`, `start_stage`, `finish_stage`, `set_model`, `mark_generated`, `mark_modified`, `mark_verified`, `mark_committed`
- [x] Auto-save on every mutation
- [x] Task lifecycle management — initialization, stage transitions, completion tracking
- [x] Model history — every model switch recorded with stage and reason
- [x] Project tracking — generated files, modified files, components, folder structure
- [x] Verification tracking — status, score, issues, repair attempts
- [x] Git tracking — branch, commit status, checkpoint history
- [x] `summary_dict()` — nested report for pipeline display

**Deliverable:** Every subsystem tracks its state in a unified, persistent singleton.

---

## Phase 4 — Model Router ✓

*Build the intelligent capability-based model selection system.*

- [x] `IntelligentRouter` — task classification, pipeline building, model selection
- [x] 6 model profiles with capability registries (Qwen3, Qwen2.5-Coder:14b, Mistral Small, Qwen2.5-Coder:7b, Llama3, Deepseek Coder)
- [x] 19 capability definitions (planning, reasoning, architecture, code generation, UI design, etc.)
- [x] 29 stage-to-capability mappings, 32 stage-to-role mappings
- [x] Capability matching — score models by capability overlap, priority, speed, quality
- [x] Three routing modes: `quality`, `performance`, `balanced`
- [x] Rule engine with priority chain: `always_use` → `prefer` → `planner_recommendation` → `capability_match` → `first_available`
- [x] Config override system — environment variables and runtime CLI commands
- [x] Routing rules — `register_rule()` for custom rule extension
- [x] `PerformanceTracker` — model response times, success rates, quality scores per stage/category
- [x] Performance data persistence to `.steve/router/performance.json`
- [x] `FeaturePlan.model_recommendations` mapped to stage-specific recommendations
- [x] Planner integration — `_build_execution_roadmap` delegates to router
- [x] StateManager integration — every model switch tracked with stage and reason
- [x] CLI routing display — `/route`, `/router-mode`, `/router-always`, `/router-prefer`, `/router-disable`

**Deliverable:** Pipeline routes each stage to the optimal model with capability-based matching, configurable overrides, and performance feedback.

---

## Phase 5 — Streaming Generation ✓

*Implement token-streaming file generation with live progress display.*

- [x] `StreamManager` — orchestrates section-by-section file generation with streaming
- [x] `TokenStream` — wraps Ollama streaming with timing, abort, and progress callbacks
- [x] `ProgressTracker` — per-file and per-section progress with timing and statistics
- [x] `OutputRenderer` — real-time terminal display of tokens, file ops, and diff-style indicators
- [x] Live progress: analyzing → planning → routing → generating → writing → verifying → committing
- [x] Per-file operation display: `* index.html created`, `* styles.css updated`
- [x] Diff-style indicators: `+ Added component`, `- Removed legacy`, `~ Updated interface`
- [x] Section-level progress with token count and timing
- [x] StateManager updates during streaming
- [x] Integration with `IncrementalFileBuilder` and pipeline

**Deliverable:** Steve generates files with live streaming output, real-time progress, and continuous state tracking.

---

## Phase 6 — Execution Engine ✓

*Implement the autonomous execution runtime that receives plans from Planner and breaks them into atomic stages.*

- [x] `ExecutionEngine` — receives `CompletePlan` from Planner, orchestrates full execution lifecycle
- [x] `ExecutionContext` — tracks current stage, completed stages, remaining stages, progress percentage, elapsed time
- [x] `DependencyManager` — builds and validates directed acyclic dependency graphs, topological sort, parallel level detection
- [x] `TaskScheduler` — decomposes plans into independently executable atomic stages (folder, html, css, js, verify, repair, finalize)
- [x] `StageExecutor` — dispatches to type-specific handlers (folder creation, file generation via `IncrementalFileBuilder`, verification via `base_verifier`, repair via `RepairEngine`)
- [x] Dependency graph ensures stages execute only after their dependencies complete
- [x] Per-stage failure recovery — only the failed stage is retried, never the entire project
- [x] Progress bar with percentage and stage label displayed during execution
- [x] Continuous StateManager updates through every stage transition
- [x] Integration with existing Planner, Router, Streaming, Verifier, and Repair modules
- [x] Abort support — clean shutdown on user interrupt

**Deliverable:** Steve autonomously executes multi-stage plans with dependency resolution, per-stage retry, and real-time progress display.

---

## Phase 7 — Workspace Manager ✓

*Implement the centralized workspace and file system manager responsible for all filesystem operations.*

- [x] `WorkspaceManager` — single authority for all filesystem operations, integrates with StateManager
- [x] `PathResolver` — absolute/relative path resolution, exclusion rules, glob support, directory creation
- [x] `ProjectScanner` — recursive directory tree scanning with configurable excluded dirs and extensions
- [x] `FileTracker` — in-memory project index: 40+ language detection, framework detection, generation/verification status per file
- [x] `FileManager` — full CRUD: create, read, update, rename, move, delete. Backup/restore to `.steve/backups/`
- [x] Smart writes — compare existing content before overwriting; skip if identical; use surgical edits when possible
- [x] Surgical edits — three strategies: exact match, whitespace-normalized match, fuzzy match (threshold 0.72)
- [x] `ChangeDetector` — snapshot-based change detection: added, modified, deleted, and moved files
- [x] `FileDependencyGraph` — file-level import analysis for Python (`import`/`from`), JS/TS (`require`/`import`), HTML (`link`/`script`/`img`), CSS (`@import`/`url()`)
- [x] Framework detection — Flask, Django, FastAPI, React, Vue, Svelte, Express, Next.js, Tailwind, Bootstrap
- [x] Config file detection — package.json, requirements.txt, Dockerfile, tsconfig, etc.
- [x] Continuous StateManager updates — project tree, current file, generated/modified files
- [x] CLI display — scanning, indexing, file operations, change summary

**Deliverable:** WorkspaceManager becomes the only component allowed to perform filesystem operations. No other module writes directly to disk.

---

## Phase 8 — Repository Intelligence ✓

*Build a complete internal representation of the project before editing anything.*

- [x] `RepositoryManager` — orchestrates scanning, indexing, search, API route and unused code detection
- [x] `RepositoryScanner` — recursive file scanner with exclusion rules, entry point/config/asset/test classification
- [x] `ProjectGraph` — internal graph of folders, files, and dependency relationships with connected components
- [x] `SymbolIndex` — indexes functions, classes, methods, variables, constants, interfaces, types, imports across Python, JS/TS, HTML, CSS
- [x] `DependencyAnalyzer` — import/require/export/asset analysis for Python, JS/TS, HTML, CSS, Vue
- [x] `LanguageDetector` — 60+ language detection by extension and filename
- [x] `FrameworkDetector` — 25+ framework detection via files, patterns, and extensions (React, Vue, Svelte, Angular, Django, Flask, FastAPI, Tailwind, Bootstrap, etc.)
- [x] `ArchitectureAnalyzer` — pattern recognition: MVC, SPA, API, CLI, Microservice, Library, Package, Plugin, Monolith
- [x] `RepositoryState` — 7th StateManager sub-state with JSON persistence
- [x] Auto-scan on startup with CLI display: "Scanning repository..." → "Indexed N files" → "Detected X" → "Repository ready"
- [x] CLI commands: `/repo-status`, `/repo-search <query>`, `/repo-routes`, `/repo-reindex`
- [x] Repository-aware Model Router and Execution Engine
- [x] Semantic search across all indexed symbols
- [x] API route finder (Python decorators, JS/TS routes)
- [x] Duplicate function detection
- [x] Architecture summary with confidence scoring

**Deliverable:** Steve builds a complete internal model of every repository before any edit, enabling informed decisions based on indexed knowledge.

---

## Phase 9 — Verifier ⏳

*Implement multi-dimensional verification and quality scoring.*

- [ ] File existence and size verification
- [ ] Syntax checking (HTML, CSS, JS, Python)
- [ ] Structural verification (DOCTYPE, tags, imports, exports)
- [ ] Quality scoring (0–1 scale across multiple dimensions)
- [ ] Refinement triggers (auto-refine when score < threshold)
- [ ] Verification report generation
- [ ] Integration with pipeline verification stage
- [ ] Graceful handling of partial verification failures

**Deliverable:** Steve automatically verifies generated files and scores quality before committing.

---

## Phase 10 — Repair Engine ⏳

*Implement failure analysis, retry strategies, and automatic repair.*

- [ ] `RepairEngine` — full implementation with strategy selection
- [ ] Failure classification (missing file, syntax error, incomplete content, unbalanced syntax)
- [ ] Strategy catalog (regenerate, append, fix syntax, restructure)
- [ ] Retry loop with configurable max attempts
- [ ] Repair log persistence in `ProjectMemory`
- [ ] Pipeline integration — repair on verification failure, re-verify, commit on success
- [ ] Escalation — if all strategies fail, report to user with diagnostics

**Deliverable:** Steve automatically repairs failed generations with intelligent strategy selection.

---

## Phase 11 — Project Memory ⏳

*Implement persistent project state across sessions.*

- [ ] `ProjectMemory` — full implementation with `.steve` artifact storage
- [ ] Plan persistence (plan.md)
- [ ] Architecture persistence (architecture.json)
- [ ] UI spec persistence (ui_spec.json)
- [ ] Todo tracking (todo.json)
- [ ] Progress tracking (progress.json)
- [ ] Verification history (verification.json)
- [ ] Repair log (repair_log.json)
- [ ] Section generation state (generation_state.json)
- [ ] Session resume — restore state from `.steve/` on restart

**Deliverable:** Steve remembers project state across sessions and can resume interrupted work.

---

## Phase 12 — Plugins ⏳

*Create a plugin system for custom generators, verifiers, and integrations.*

- [ ] Plugin discovery (scan `plugins/` directory)
- [ ] Plugin API (hooks for generation, verification, repair, reporting)
- [ ] Custom generator plugins (React, Vue, Flask, FastAPI, etc.)
- [ ] Custom verifier plugins (framework-specific checks)
- [ ] Plugin documentation and examples
- [ ] Integration with pipeline (plugins register at specific stages)
- [ ] Plugin isolation (safe execution, error boundaries)

**Deliverable:** Steve can be extended with community plugins for any framework or workflow.

---

## Phase 13 — Live Terminal ⏳

*Enhance the terminal UI with real-time pipeline visualization.*

- [ ] Real-time pipeline stage indicator
- [ ] Live token streaming display in terminal
- [ ] Progress bar per file/section
- [ ] Timeline view with stage durations
- [ ] Git activity block (checkpoints, commits, rollbacks)
- [ ] Collapsible sections for verbose output
- [ ] Clean summary mode for production use
- [ ] ANSI/ASCII fallback for all display components

**Deliverable:** Rich, real-time terminal UI that shows pipeline progress, Git activity, and streamed output.

---

## Phase 14 — Stable Release ⏳

*Polish, test, document, and release Steve v4.0.0 stable.*

- [ ] Comprehensive test suite (unit + integration for every module)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Cross-platform testing (Windows, macOS, Linux)
- [ ] Performance benchmarks and optimization
- [ ] Full documentation review
- [ ] Security audit
- [ ] v4.0.0 stable release tag
- [ ] Migration guide for v3 users
- [ ] Package distribution (PyPI or standalone)

**Deliverable:** Steve v4.0.0 stable — tested, documented, and distributed.
