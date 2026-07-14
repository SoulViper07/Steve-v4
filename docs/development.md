# Development Guide

## Prerequisites

- Python 3.11 or newer
- Git
- Ollama (for LLM integration testing)
- Visual Studio Code or any Python IDE

## Setup

```bash
# Clone the repository
git clone https://github.com/SoulViper07/Steve-v4.git
cd Steve-v4

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running

```bash
# Start the interactive REPL
python agent.py

# With a specific working directory
python agent.py --workdir /path/to/project

# Minimal UI (no Rich)
python agent.py --plain
```

## Project Structure

```
Steve-v4/
├── agent.py              # Entry point
├── config/               # Configuration
├── core/                 # Core framework
├── providers/            # LLM providers
├── actions/              # Filesystem actions
├── ui/                   # Terminal UI
├── verifier/             # Verification
├── generation/           # Code generation
├── repair/               # Repair subsystem
├── utils/                # Utilities (Git, logging, helpers)
├── docs/                 # Documentation
├── resources/            # Resources
└── assets/               # Static assets
```

See [architecture.md](./architecture.md) for a detailed module map.

## Coding Standards

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full coding standards.

Key points:
- Python 3.11+, PEP 8 with 120-char lines
- Type hints on all function signatures
- No circular imports
- `utils/` has no dependencies on `core/` or `ui/`
- `snake_case` for functions, `PascalCase` for classes

## Testing

Tests use `pytest`.

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=term-missing
```

## Common Tasks

### Adding a new Git command

1. Add method to `GitManager` in `utils/git_manager.py`
2. Add orchestration method to `GitIntegration` in `utils/git_integration.py` (if needed for pipeline)
3. Add handler function in `agent.py`
4. Add command routing in the REPL loop in `agent.py`
5. Add display support in `ui/terminal_renderer.py` (if needed)
6. Update `docs/git-integration.md`

### Adding a new pipeline stage

1. Add the stage name to `config/routing.json` execution stages
2. Create the module in the appropriate directory
3. Register the stage in `core/pipeline.py` stage order
4. Add model mapping in `config/model_config.py`
5. Add display support in `ui/terminal_renderer.py`
6. Update `docs/architecture.md`

### Adding a new configuration option

1. Add the environment variable to `config/settings.py`
2. Update `config/model_config.py` if model-specific
3. Document in the default prompt or route prompts if needed
4. Update `docs/*` if user-facing
