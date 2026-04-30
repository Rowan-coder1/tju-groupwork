# cli-anything-joplin

Stateful CLI harness for Joplin automation using the real `joplin` terminal binary.

## Overview

`cli-anything-joplin` provides a stateful, agent-friendly CLI wrapper around the Joplin terminal application. It is designed to support iterative workflow automation through:

- project lifecycle management
- notebook / note / tag operations
- search, sync, import/export, and config commands
- JSON output for machine parsing
- session undo/redo and snapshot support
- layered test coverage from command tests to a real backend integration flow

## Requirements

- Python 3.10+
- Joplin terminal app installed and available in PATH as `joplin`

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

# One-shot with JSON output
cli-anything-joplin --json notebooks list

# With project file
cli-anything-joplin --project ./demo.joplin-harness.json notes create "hello"
```

## Core workflows

### Project lifecycle

- `project new`
- `project open`
- `project save`
- `project info`
- `project json`
- `project status`

### Content workflows

- `notebooks list/create/use`
- `notes list/create/set/get/remove`
- `tags list/add/remove/notetags`
- `search run`

### Integration workflows

- `sync run`
- `interop import/export`
- `config get/set/list`
- `session status/undo/redo`

## JSON output contract

When `--json` is enabled, commands return:

- `ok`: boolean
- `command`: command identifier, for example `notes.list`
- `data`: command payload
- `error`: null on success, or `{ type, message }` on failure

## Save behavior

- One-shot mutating commands auto-save if a project is loaded.
- `--dry-run` suppresses auto-save.
- REPL mode never auto-saves.

## Test workflow

```bash
# Quick feedback loop
python -m pytest -q cli_anything/joplin/tests/test_core.py
python -m pytest -q cli_anything/joplin/tests/test_full_e2e.py::TestCLISubprocess

# Full suite
python -m pytest -v --tb=no cli_anything/joplin/tests

# Installed command verification / real backend integration
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest -v -s cli_anything/joplin/tests/test_full_e2e.py
```

## Test layers

### 1. Command-level tests
Focus on isolated command behavior and backend argument construction.

### 2. CLI subprocess tests
Validate the installed command or Python module entrypoint.

### 3. Workflow tests
Validate short task flows such as notebook, note, tag, search, sync, export, and config operations.

### 4. Real backend integration
Run only when the `joplin` terminal CLI is installed and available in PATH. These tests exercise a real Joplin backend and are skipped automatically otherwise.

## Development guidance

- Expand workflows before adding isolated edge commands.
- Keep the JSON envelope stable across all command groups.
- Preserve the distinction between audit history and undo/redo snapshots.
- Add tests alongside every new workflow.
