# Steve Architecture

Steve has evolved from a monolithic script into a modular autonomous agent framework.

## Directory Structure

- `core/`: Central logic and state management.
  - `models.py`: Data structures (RequestRoute, ExecutionPlan, etc.).
  - `conversation.py`: History and context management.
  - `orchestrator.py`: Main loops and builder pipelines.
  - `file_context.py`: Filesystem awareness and context building.
  - `inspector.py`: Project structure analysis.
  - `planner.py`: Task decomposition and planning.
- `ui/`: Terminal rendering and user interaction.
  - `terminal_renderer.py`: Rich-powered CLI components.
- `providers/`: External AI/LLM connections.
  - `ollama.py`: Local LLM integration.
- `actions/`: Parser and executor for agent operations.
  - `executor.py`: Safe filesystem operations and command execution.
- `verifier/`: Quality gates and verification logic.
  - `base_verifier.py`: Syntax and project integrity checks.
- `generation/`: specialized generators.
  - `identity.py`: Visual identity and design system generation.
- `templates/`: Base scaffold templates for project types.
- `utils/`: Common helpers and logging.
  - `logger.py`: Debug logging and redaction.
  - `git_manager.py`: Git integration.
  - `helpers.py`: Environment and string utilities.
- `config/`: Global settings and model presets.

## Key Design Principles

1. **Safety First**: All filesystem operations are validated and backed up before execution. Edits to core framework files are blocked.
2. **Modularity**: Components are decoupled and can be tested or replaced independently.
3. **Stateless Logic**: Generators and verifiers are designed to be as stateless as possible, relying on the `Conversation` and `ExecutionPlan` for context.
4. **Rich Feedback**: The UI provides detailed, real-time feedback on agent actions and reasoning.
5. **Self-Healing**: Automated startup checks ensure system integrity.

## Startup Lifecycle

1. `agent.py` performs a `self_check()` to verify module availability.
2. `Conversation` is initialized with the current working directory.
3. `ProjectInspector` scans the project to build a `ProjectMap`.
4. The user enters the main interaction loop.
