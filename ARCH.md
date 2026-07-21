# Steve Architecture

Steve has evolved from a monolithic script into a modular autonomous agent framework.

## Directory Structure

- `repository/`: Repository Intelligence Engine.
  - `repository_manager.py`: Main orchestrator for scanning, indexing, search, and analysis.
  - `repository_scanner.py`: Recursive file scanner with exclusion rules and classification.
  - `project_graph.py`: Internal graph of folders, files, and dependency relationships.
  - `symbol_index.py`: Indexes functions, classes, methods, variables, constants, interfaces, types.
  - `dependency_analyzer.py`: Import/export/asset dependency analysis across languages.
  - `language_detector.py`: 60+ language detection by extension and filename.
  - `framework_detector.py`: 25+ framework detection via files, patterns, and extensions.
  - `architecture_analyzer.py`: Architecture pattern recognition (MVC, SPA, API, CLI, etc.).
- `core/`: Central logic and state management.
  - `models.py`: Data structures (RequestRoute, ExecutionPlan, etc.).
  - `conversation.py`: History and context management.
  - `orchestrator.py`: Main loops and builder pipelines.
  - `file_context.py`: Filesystem awareness and context building.
  - `inspector.py`: Project structure analysis.
  - `planner.py`: Task decomposition and planning.
  - `pipeline.py`: v4 pipeline orchestrator with Git hooks and repo context.
- `state/`: Persistent state management.
  - `state_manager.py`: Singleton with 7 sub-states (execution, task, project, model, git, verification, repository).
  - `repository_state.py`: Repository intelligence persistence.
- `workspace/`: Centralized workspace and file system manager.
  - `workspace_manager.py`: File CRUD, project index, change detection.
  - `project_tree.py`: Directory tree scanner with exclusions.
  - `file_manager.py`: Smart writes, surgical edits, backup/restore.
  - `file_tracker.py`: In-memory project index (40+ languages, framework detection).
  - `dependency_graph.py`: File-level import analysis.
  - `change_detector.py`: Added/modified/deleted/moved file detection.
  - `path_resolver.py`: Absolute/relative path resolution, exclusion rules.
- `planner/`: Modular planning subsystem.
  - `planner.py`: PlanningEngine orchestrator with repository-aware routing.
  - `execution_plan.py`: Data classes (CompletePlan, TaskClassification, etc.).
  - `task_classifier.py`, `architecture_planner.py`, `ui_planner.py`, `feature_planner.py`.
- `router/`: Intelligent model router.
  - `model_router.py`: IntelligentRouter, pipeline builder, repository-aware routing.
  - `routing_rules.py`: Rule engine with priority chain and overrides.
  - `model_profiles.py`: 6 model profiles with capability registries.
  - `capabilities.py`: 19 capabilities, 29 stage mappings.
- `execution/`: Autonomous execution engine.
  - `execution_engine.py`: Receives plans, executes atomic stages, repository-aware.
  - `execution_context.py`, `dependency_manager.py`, `task_scheduler.py`, `stage_executor.py`.
- `ui/`: Terminal rendering and user interaction.
  - `terminal_renderer.py`: Rich-powered CLI components.
- `providers/`: External AI/LLM connections.
  - `ollama.py`: Local LLM integration.
- `actions/`: Parser and executor for agent operations.
  - `executor.py`: Safe filesystem operations and command execution.
- `verifier/`: Quality gates and verification logic.
  - `base_verifier.py`: Syntax and project integrity checks.
- `generation/`: Specialized generators.
  - `identity.py`: Visual identity and design system generation.
  - `incremental_engine.py`: Section-by-section file builder.
- `streaming/`: Live streaming generation.
  - `stream_manager.py`, `token_stream.py`, `progress_tracker.py`, `output_renderer.py`.
- `repair/`: Repair subsystem.
  - `repair_engine.py`: Failure analysis, retry strategies.
- `utils/`: Common helpers and logging.
  - `logger.py`: Debug logging and redaction.
  - `git_manager.py`: Git integration (22 methods).
  - `git_integration.py`: High-level Git orchestration.
  - `helpers.py`: Environment and string utilities.
- `config/`: Global settings and model presets.
  - `settings.py`: Environment variables, presets, prompts.
  - `model_config.py`: Model roles, stage-to-role mapping.
  - `routing.json`: Task categories, execution stages.
- `tests/`: Test suite.
  - `test_repository.py`: Repository Intelligence tests (40+ tests).
  - `test_workspace.py`, `test_verifier.py`, `test_patcher.py`.

## Key Design Principles

1. **Safety First**: All filesystem operations are validated and backed up before execution. Edits to core framework files are blocked.
2. **Repository Awareness**: Before any edit, Steve builds a complete internal model of the project — files, languages, frameworks, symbols, dependencies, and architecture pattern.
3. **Modularity**: Components are decoupled and can be tested or replaced independently.
4. **Stateless Logic**: Generators and verifiers are designed to be as stateless as possible, relying on state and context for continuity.
5. **Rich Feedback**: The UI provides detailed, real-time feedback on agent actions and reasoning.
6. **Self-Healing**: Automated startup checks ensure system integrity.

## Startup Lifecycle

1. `agent.py` performs environment bootstrap (UTF-8, Git initialization).
2. Repository Intelligence runs automatically: scan → graph → symbol index → dependency analysis → architecture detection.
3. CLI displays: "Scanning repository..." → "Indexed N files" → "Detected languages" → "Detected frameworks" → "Repository ready".
4. The user enters the main interaction loop with repository-aware routing and execution.
