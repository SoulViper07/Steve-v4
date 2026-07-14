# Changelog

All notable changes to Steve v4 are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [4.0.0-alpha] — 2026-07-14

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
