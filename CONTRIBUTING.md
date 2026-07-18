# Contributing to CreativeOS

Thank you for helping improve CreativeOS.

## Development setup

```bash
git clone https://github.com/kelvinrenkhoe/CreativeOS.git
cd CreativeOS
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Quality checks

Run these commands before opening a pull request:

```bash
ruff check .
ruff format --check .
pytest -q
```

To automatically format the code:

```bash
ruff format .
ruff check . --fix
```

## Branches and commits

Use a focused branch such as:

```text
feature/configuration-engine
fix/workspace-discovery
chore/project-polish
```

Prefer clear commit messages:

```text
feat(core): add configuration loader
fix(cli): handle missing workspace configuration
chore: update development dependencies
```

## Pull requests

A pull request should:

- explain the problem and proposed solution;
- include tests for new behaviour;
- update documentation when commands or configuration change;
- pass linting, formatting, and automated tests.

Keep changes small enough to review confidently.
