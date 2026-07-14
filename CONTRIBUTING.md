# Contributing to Steve v4

Thank you for your interest in contributing. This document defines the standards for contributing to Steve v4.

---

## Code of Conduct

Be respectful, constructive, and professional. This project is open to contributors of all skill levels. Personal attacks, harassment, or unprofessional behavior will not be tolerated.

---

## Getting Started

1. Fork the repository.
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Steve-v4.git
   cd Steve-v4
   ```
3. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # macOS/Linux
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Create a branch for your work (see branch naming below).

---

## Coding Standards

### Python

- **Target:** Python 3.11+
- **Style:** Follow [PEP 8](https://peps.python.org/pep-0008/) with the following conventions:
  - Line length: 120 characters max
  - Indentation: 4 spaces (no tabs)
  - Quotes: double quotes (`"`) for strings unless single quotes (`'`) reduce escaping
- **Typing:** Use type hints on all function signatures and dataclass fields
- **Imports:** Group in order: standard library → third-party → local. One import per line. No `from x import *`.
- **Naming:**
  - `snake_case` for functions, methods, variables
  - `PascalCase` for classes, dataclasses, exceptions
  - `UPPER_CASE` for constants
  - Prefix private methods with `_`
- **Docstrings:** Use triple double-quotes (`"""`). One-line docstrings for simple methods, full docstrings for public APIs.

### Architecture Rules

- Every module in `core/`, `utils/`, `providers/`, `actions/`, `ui/`, `verifier/`, `generation/`, `repair/` must have exactly one clear responsibility.
- No circular imports. Dependency direction: `utils/` → all others; `core/` → no other modules; `ui/` → `utils/` only.
- Git logic (`utils/git_manager.py`) must not import anything outside `utils/`.
- Pipeline (`core/pipeline.py`) must call `GitIntegration` and `RepairEngine` through their public APIs — never directly invoke `subprocess`.

### Error Handling

- Never crash on user-facing errors. Wrap external calls (LLM, filesystem, Git) in try/except.
- Log all unexpected errors via `SteveDebugLog` (or Python `logging` in v4).
- Use specific exception types (`FileNotFoundError`, `PermissionError`, etc.) rather than bare `except:`.

---

## Branch Naming

All branches must follow this convention:

```
<type>/<short-description>
```

### Types

| Type | Use |
|------|-----|
| `feat/` | New feature (e.g., `feat/streaming-generator`) |
| `fix/` | Bug fix (e.g., `fix/git-checkpoint-encoding`) |
| `refactor/` | Code restructuring (e.g., `refactor/pipeline-stages`) |
| `docs/` | Documentation (e.g., `docs/api-reference`) |
| `chore/` | Maintenance (e.g., `chore/update-dependencies`) |
| `test/` | Test additions (e.g., `test/git-manager-coverage`) |

### Examples

```
feat/planner-json-output
fix/empty-commit-on-verify-fail
refactor/extract-action-parser
docs/architecture-diagrams
```

---

## Commit Style

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `docs` | Documentation only |
| `style` | Formatting, missing semicolons, etc. (no code change) |
| `test` | Adding or fixing tests |
| `chore` | Build process, dependencies, etc. |
| `perf` | Performance improvement |
| `ci` | CI/CD configuration |

### Scopes

Use the module directory name as the scope:

```
feat(core): implement planner json output
fix(utils): handle empty git stash list
docs(readme): update architecture diagram
refactor(pipeline): extract repair loop to separate method
```

### Rules

- First line: max 72 characters
- No period at end of subject line
- Use imperative mood ("add" not "added" or "adds")
- Body (optional): wrap at 72 characters, separate from subject with blank line

---

## Pull Request Process

1. **Before opening a PR**, ensure your branch is rebased on the latest `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout your-branch
   git rebase main
   ```

2. **PR title** must follow conventional commit format (same as commit style).

3. **PR description** must include:
   - What this PR does (one paragraph)
   - Why this change is needed
   - How it was tested
   - Any breaking changes or migration notes
   - Related issues (closes #123, refs #456)

4. **Checklist** in PR description:
   - [ ] Code follows project coding standards
   - [ ] Type hints added to all new functions
   - [ ] No new circular imports introduced
   - [ ] Changes tested locally
   - [ ] Documentation updated (if applicable)
   - [ ] Changelog entry added (if applicable)

5. **Review requirements:**
   - At least one maintainer review required
   - All CI checks must pass
   - No merge commits — rebase only

6. **Merge strategy:** Squash merge with conventional commit message.

---

## Testing

- Tests live in a `tests/` directory mirroring the source structure:
  ```
  tests/
  ├── test_git_manager.py
  ├── test_repair_engine.py
  ├── test_pipeline.py
  └── ...
  ```
- Run tests with:
  ```bash
  python -m pytest
  ```
- Minimum target: 80% coverage on new code.

---

## Documentation

- All public APIs must have docstrings.
- Module-level docstrings explaining the module's responsibility.
- Significant changes must update the relevant file in `docs/`.
- Keep `CHANGELOG.md` up to date with each significant change.
- Keep `ROADMAP.md` checkboxes updated as phases progress.

---

## Questions

Open a [discussion](https://github.com/SoulViper07/Steve-v4/discussions) or an issue for any questions about contributing.
