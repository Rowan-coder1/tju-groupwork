# Test Plan — cli-anything-joplin

## Unit / Command Tests (`test_full_e2e.py`)

Run without requiring a live Joplin backend workflow:

```bash
python -m pytest cli_anything/joplin/tests/test_full_e2e.py::TestCLISubprocess -v
python -m pytest cli_anything/joplin/tests/test_full_e2e.py::TestBackendCommands -v
```

Covers:
- CLI help and command entrypoint behavior
- `project new`, `project info`, `project save`, `project status`
- `session status` without a loaded project
- Isolated backend command coverage for:
  - `notebooks list`
  - `notes list`
  - `config get`
  - `config list`
  - `session undo`
  - `session redo`

## Workflow Tests (`test_full_e2e.py`)

Run short real-backend workflows when `joplin` is installed and available in `PATH`:

```bash
python -m pytest cli_anything/joplin/tests/test_full_e2e.py::TestBackendWorkflows -v
```

Covers:
- Note lifecycle workflow
- Tagging workflow
- Search workflow
- Sync workflow
- Export workflow (`jex` and `md`)
- Project save workflow

## E2E Integration Tests (`test_full_e2e.py`)

Requires the real `joplin` terminal binary:

```bash
python -m pytest cli_anything/joplin/tests/test_full_e2e.py::TestBackendIntegration -v
```

Covers:
- Full project creation and inspection
- Notebook discovery and selection
- Note creation and editing
- Config access
- Session undo/redo commands
- Tag operations
- Search and sync
- Export operations
- Cleanup and final project save

## Notes

- Real backend tests are skipped automatically when `joplin` is unavailable.
- The JSON output contract is validated across all layers with `ok`, `command`, `data`, and `error` fields.
- The full integration flow is the recommended demo path for agent-driven end-to-end runs.
