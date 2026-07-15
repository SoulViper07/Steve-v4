# Changelog

All notable changes to Steve v4 are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
