# Steve v4 Roadmap

## Overview

Steve v4 is built in 10 phases. Each phase produces a working, testable increment. Phases 1–3 establish the foundation, phases 4–7 build the AI pipeline, phases 8–9 add advanced features, and phase 10 stabilizes for release.

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

## Phase 2 — Planner ⏳

*Implement the structured plan generator using Qwen3:14b.*

- [ ] `TaskAnalyzer` — intent classification and operational detection
- [ ] `Planner` rewrite — structured JSON plan output from Qwen3
- [ ] Quality profile system (quick, standard, premium, cinematic)
- [ ] Plan parsing — regex-free, schema-validated extraction
- [ ] Component auto-detection from plan
- [ ] Plan persistence in `ProjectMemory`
- [ ] Fallback plan generation when LLM unavailable

**Deliverable:** Steve can analyze a request and produce a structured, queryable plan.

---

## Phase 3 — Model Router

*Build the stage-aware model routing and fallback system.*

- [ ] `ModelRouter` rewrite — 14-layer stage-to-model mapping
- [ ] Fallback chain (primary → secondary → fallback → graceful error)
- [ ] Model warm-up manager (pre-load models on startup)
- [ ] Per-stage parameter tuning (temperature, context, predict)
- [ ] Manual model override from CLI
- [ ] Model health checks and availability detection
- [ ] Model switching notifications in UI

**Deliverable:** Pipeline routes each stage to the optimal model with automatic fallback.

---

## Phase 4 — Streaming Generation

*Implement token-streaming file generation with progress events.*

- [ ] `StreamingGenerator` — token stream → chunked output
- [ ] Section-based file generation (generic, not HTML-only)
- [ ] Section prompt library (reusable prompts for common file types)
- [ ] Progress events (section started, token received, section complete)
- [ ] Abort/cancel support during generation
- [ ] Retry logic per section with exponential backoff
- [ ] File assembly (concatenate sections into complete files)

**Deliverable:** Steve generates multi-section files with real-time streaming and progress.

---

## Phase 5 — Live Terminal

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

## Phase 6 — Verifier

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

## Phase 7 — Repair Engine

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

## Phase 8 — Project Memory

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

## Phase 9 — Plugins

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

## Phase 10 — Stable Release

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
