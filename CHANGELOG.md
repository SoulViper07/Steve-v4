# Changelog

## [4.0.0] — Initial Release

### Architecture
- Complete rewrite from Steve v3 with a clean 14-layer pipeline
- Layered architecture: CLI → Conversation Manager → Task Analyzer → Planner → Architecture Planner → Model Router → UI Designer → Implementation Engine → Streaming Generator → File Writer → Verifier → Repair Engine → Quality Reviewer → Final Report
- Git as a first-class subsystem with checkpoint, auto-commit, rollback, and 13 Git commands
- Dedicated RepairEngine with strategy selection and retry logic

### New Modules
- `utils/git_manager.py` — 22-method Git API (init, status, checkpoint, commit, rollback, undo, revert, diff, branch, stash, tag, push, release, log)
- `utils/git_integration.py` — High-level Git orchestration for pipeline integration
- `core/pipeline.py` — 14-layer pipeline orchestrator with Git hooks
- `repair/repair_engine.py` — Failure analysis and retry engine
- `config/settings.py` — v4 configuration with environment variable support

### Improvements over v3
- First-class Git integration vs. optional commands
- Clean 14-layer separation vs. refactored monolithic
- Generic section-based generation vs. hardcoded HTML/CSS/JS
- Stage-aware model router with fallback chains
- Pure message store conversation manager
- Dedicated repair system with strategy selection
