# Joplin Agent Harness

`cli-anything-joplin` is a stateful CLI harness for the Joplin terminal application.
It uses the real `joplin` binary for backend operations and is designed for agent-driven workflows, command validation, and end-to-end demonstrations.

## What it does

- wraps Joplin project/session state
- supports notebook, note, tag, search, sync, import/export, and config commands
- emits JSON for machine parsing
- provides undo/redo session snapshots
- supports one-shot mode and REPL mode

## Requirements

- Python 3.10+
- Joplin terminal CLI installed and available in `PATH` as `joplin`

## Usage

```bash
# REPL mode
cli-anything-joplin

# One-shot command mode
cli-anything-joplin --json notebooks list

# Use a saved project file
cli-anything-joplin --project ./demo.joplin-harness.json notes create "hello"
```

## Command groups

- `project`
- `notebooks`
- `notes`
- `tags`
- `search`
- `sync`
- `interop`
- `config`
- `session`

## Test structure

- command-level subprocess checks
- backend command coverage
- short workflow tests
- one full end-to-end integration flow

See `cli_anything/joplin/tests/TEST.md` for the current test plan.
