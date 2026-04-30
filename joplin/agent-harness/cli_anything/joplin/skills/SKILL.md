---
name: "cli-anything-joplin"
description: "Command-line interface for Joplin workflows using the real joplin terminal backend"
---

# cli-anything-joplin

Use this skill to automate Joplin notebook and note workflows through a stateful harness.

## Requirements

- Python 3.10+
- Joplin terminal binary available as `joplin`
- Optional: pass `--profile` to target a specific Joplin profile

## Install

```bash
cd joplin/agent-harness
pip install -e .
```

## Usage

```bash
# REPL mode (default)
cli-anything-joplin

# Machine-readable one-shot command
cli-anything-joplin --json notebooks list

# Stateful project
cli-anything-joplin project new --name demo -o ./demo.joplin-harness.json
cli-anything-joplin --project ./demo.joplin-harness.json notes create "Meeting note"
```

## JSON output contract

When `--json` is enabled, commands return:

- `ok`: boolean
- `command`: command identifier (for example `notes.list`)
- `data`: command payload
- `error`: null on success, or `{ type, message }` on failure

## Command groups

- `project`: Manage harness project file (`new`, `open`, `save`, `info`, `json`)
- `notebooks`: List/create/select notebooks
- `notes`: List/create/read/update/remove notes
- `tags`: List/add/remove/note tags
- `search`: Run note search
- `sync`: Trigger synchronization
- `interop`: Import/export data
- `config`: Get/set/list Joplin config values
- `session`: Inspect and control harness undo/redo state

## Agent guidance

- Prefer `--json` for parseable output.
- Use `--project` when running multi-step workflows.
- One-shot mutating commands auto-save project unless `--dry-run` is set.
- REPL mode does not auto-save; run `project save` explicitly.

## Test workflow

```bash
# Quick feedback loop
python -m pytest -q cli_anything/joplin/tests/test_core.py
python -m pytest -q cli_anything/joplin/tests/test_full_e2e.py::TestCLISubprocess

# Full suite
python -m pytest -v --tb=no cli_anything/joplin/tests

# Installed-command verification
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest -v -s cli_anything/joplin/tests/test_full_e2e.py
```
