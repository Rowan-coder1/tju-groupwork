# JOPLIN Harness SOP

## Overview

`cli-anything-joplin` is a stateful CLI harness for Joplin automation backed by the real `joplin` terminal binary.
It is intended for command-driven workflows, real backend validation, and agent-style demo runs.

## Requirements

- Python 3.10+
- Joplin terminal CLI installed and available in `PATH` as `joplin`
- The harness package installed in editable mode for local development

Verify the backend with:

```bash
where joplin
joplin help
```

## Install

```bash
cd joplin/agent-harness
pip install -e .
```

## Usage

```bash
# REPL mode (default)
cli-anything-joplin

# One-shot command mode with JSON output
cli-anything-joplin --json notebooks list

# Use a project file
cli-anything-joplin --project ./demo.joplin-harness.json notes create "hello"
```

## Command groups

- `project`: `new`, `open`, `save`, `info`, `json`, `status`
- `notebooks`: `list`, `create`, `use`
- `notes`: `list`, `create`, `set`, `get`, `remove`
- `tags`: `list`, `add`, `remove`, `notetags`
- `search`: `run`
- `sync`: `run`
- `interop`: `import`, `export`
- `config`: `get`, `set`, `list`
- `session`: `status`, `undo`, `redo`

## State model

The harness project is JSON-based and stores:

- `name`
- `created_at`, `updated_at`
- backend settings such as `binary` and `profile`
- user context such as `current_notebook`
- `history` as an operations log

The session keeps in-memory project state plus undo/redo snapshots.

## Save behavior

- One-shot mutating commands auto-save when a project is loaded.
- `--dry-run` disables auto-save.
- REPL mode does not auto-save; the user saves explicitly.

## JSON output contract

When `--json` is enabled, commands return a stable envelope:

- `ok`: boolean
- `command`: command identifier such as `notes.list`
- `data`: command payload
- `error`: `null` on success, or `{ type, message }` on failure

## Testing strategy

### 1. Command-level tests
Validate isolated command behavior and subprocess invocation.

### 2. Workflow tests
Validate short task flows such as notebook, note, tag, search, sync, export, and config operations.

### 3. End-to-end integration test
Validate a full real backend roundtrip from project creation to final save/reopen consistency.

### Test commands

```bash
python -m pytest -q cli_anything/joplin/tests/test_core.py
python -m pytest -q cli_anything/joplin/tests/test_full_e2e.py::TestCLISubprocess
python -m pytest -v cli_anything/joplin/tests/test_full_e2e.py
```

For real backend runs, ensure `joplin` is installed and available in `PATH`.

## Development notes

- Prefer adding new coverage as a small command test first.
- Promote longer user journeys into workflow tests.
- Keep exactly one full integration flow for demonstration and regression.
- Preserve the JSON envelope and backend command naming conventions.
