"""E2E coverage for the Joplin backend CLI.

Test layout:
- `TestCLISubprocess`: lightweight command checks
- `TestBackendCommands`: isolated command-level backend tests
- `TestBackendWorkflows`: short workflow tests for common user flows
- `TestBackendIntegration`: one full end-to-end demonstration flow

The integration test is the one most suitable for a live agent demo.
"""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

import pytest


def _resolve_cli(name: str) -> list[str]:
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_anything.joplin.joplin_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


@dataclass
class WorkflowStep:
    title: str
    args: list[str]


class BackendTestBase:
    CLI_BASE = _resolve_cli("cli-anything-joplin")

    def _run(self, args: list[str], check: bool = True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def _run_json(self, args: list[str], check: bool = True) -> dict:
        result = self._run(["--json", *args], check=check)
        return json.loads(result.stdout)

    def _print_workflow_start(self, name: str, total_steps: int):
        print(f"\n=== Workflow: {name} ===")
        print(f"Steps: {total_steps}")

    def _print_step(self, index: int, total_steps: int, title: str, args: list[str]):
        print(f"[{index}/{total_steps}] {title}")
        print(f"Command: {' '.join(args)}")

    def _print_result(self, payload: dict):
        if payload.get("ok"):
            print(f"Result: ok=true, command={payload.get('command')}")
            data = payload.get("data")
            if isinstance(data, dict) and data:
                preview_keys = list(data.keys())[:3]
                preview = {k: data[k] for k in preview_keys}
                print(f"Data: {json.dumps(preview, ensure_ascii=False, default=str)}")
            elif data is not None:
                print(f"Data: {data}")
        else:
            err = payload.get("error") or {}
            print(f"Result: ok=false, command={payload.get('command')}, error={err.get('message')}")

    def _print_workflow_end(self, name: str, success: bool = True):
        if success:
            print(f"[PASS] Workflow passed: {name}")
        else:
            print(f"[FAIL] Workflow failed: {name}")

    def _run_workflow_step(self, step: WorkflowStep, check: bool = True) -> dict:
        result = self._run(["--json", *step.args], check=check)
        payload = json.loads(result.stdout)
        self._print_result(payload)
        return payload

    def _create_project(self, tmp_path, name: str):
        project_file = tmp_path / f"{name}.json"
        payload = self._run_json(["project", "new", "--name", name, "-o", str(project_file)])
        assert payload["ok"] is True
        assert payload["command"] == "project.new"
        assert project_file.exists()
        return project_file

    def _prepare_workspace(self, tmp_path, project_name: str):
        project_file = self._create_project(tmp_path, project_name)
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        return project_file, profile_dir


class TestCLISubprocess(BackendTestBase):
    def test_help_shows_usage(self):
        r = self._run(["--help"])
        assert r.returncode == 0
        assert "cli-anything-joplin" in r.stdout or "Usage" in r.stdout

    def test_project_new_returns_json_payload(self, tmp_path):
        out = tmp_path / "p.json"
        r = self._run(["--json", "project", "new", "--name", "demo", "-o", str(out)])
        payload = json.loads(r.stdout)
        assert r.returncode == 0
        assert payload["ok"] is True
        assert payload["command"] == "project.new"
        assert payload["data"]["name"] == "demo"
        assert out.exists()

    def test_project_info_works_on_new_project(self, tmp_path):
        out = tmp_path / "p.json"
        self._run(["project", "new", "--name", "demo", "-o", str(out)])
        r = self._run(["--json", "--project", str(out), "project", "info"])
        payload = json.loads(r.stdout)
        assert r.returncode == 0
        assert payload["ok"] is True
        assert payload["command"] == "project.info"
        assert payload["data"]["name"] == "demo"

    def test_session_status_without_project(self):
        r = self._run(["--json", "session", "status"])
        payload = json.loads(r.stdout)
        assert r.returncode == 0
        assert payload["ok"] is True
        assert payload["command"] == "session.status"
        assert payload["data"]["has_project"] is False

    def test_project_save_roundtrip(self, tmp_path):
        out = tmp_path / "p.json"
        self._run(["project", "new", "--name", "demo", "-o", str(out)])
        r = self._run(["--json", "--project", str(out), "project", "save"])
        payload = json.loads(r.stdout)
        assert r.returncode == 0
        assert payload["ok"] is True
        assert payload["command"] == "project.save"
        assert "saved" in payload["data"]

    def test_project_status_reports_loaded_project(self, tmp_path):
        out = tmp_path / "status.json"
        self._run(["project", "new", "--name", "status-demo", "-o", str(out)])
        r = self._run(["--json", "--project", str(out), "project", "status"])
        payload = json.loads(r.stdout)
        assert r.returncode == 0
        assert payload["ok"] is True
        assert payload["command"] == "project.status"
        assert payload["data"]["project"]["name"] == "status-demo"
        assert payload["data"]["project_path"] == str(out)
        assert payload["data"]["session"]["has_project"] is True


@pytest.mark.skipif(shutil.which("joplin") is None, reason="joplin binary not installed")
class TestBackendCommands(BackendTestBase):
    def test_project_status_and_info(self, tmp_path):
        project_file = self._create_project(tmp_path, "commands-project")

        status = self._run_json(["--project", str(project_file), "project", "status"])
        assert status["ok"] is True
        assert status["command"] == "project.status"
        assert status["data"]["project"]["name"] == "commands-project"
        assert status["data"]["session"]["has_project"] is True

        info = self._run_json(["--project", str(project_file), "project", "info"])
        assert info["ok"] is True
        assert info["command"] == "project.info"
        assert info["data"]["name"] == "commands-project"

    def test_notebooks_and_notes_list(self, tmp_path):
        project_file, profile_dir = self._prepare_workspace(tmp_path, "commands-lists")

        notebooks = self._run_json(["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "list"])
        assert notebooks["ok"] is True
        assert notebooks["command"] == "notebooks.list"

        notes = self._run_json(["--project", str(project_file), "--profile", str(profile_dir), "notes", "list"])
        assert notes["ok"] is True
        assert notes["command"] == "notes.list"

    def test_config_get_and_list(self, tmp_path):
        project_file = self._create_project(tmp_path, "commands-config")

        config_get = self._run_json(["--project", str(project_file), "config", "get", "sync.target"])
        assert config_get["ok"] is True
        assert config_get["command"] == "config.get"

        config_list = self._run_json(["--project", str(project_file), "config", "list"])
        assert config_list["ok"] is True
        assert config_list["command"] == "config.list"
        assert config_list["data"] is not None

    def test_session_undo_redo(self, tmp_path):
        project_file = self._create_project(tmp_path, "commands-session")

        undo = self._run_json(["--project", str(project_file), "session", "undo"], check=False)
        assert undo["ok"] is False
        assert undo["command"] == "session.undo"
        assert undo["error"]["message"] == "Nothing to undo"

        redo = self._run_json(["--project", str(project_file), "session", "redo"], check=False)
        assert redo["ok"] is False
        assert redo["command"] == "session.redo"
        assert redo["error"]["message"] == "Nothing to redo"


@pytest.mark.skipif(shutil.which("joplin") is None, reason="joplin binary not installed")
class TestBackendWorkflows(BackendTestBase):
    def test_note_lifecycle_workflow(self, tmp_path):
        project_file, profile_dir = self._prepare_workspace(tmp_path, "workflow-notes")
        steps = [
            WorkflowStep("Create notebook", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "create", "WorkflowBook"]),
            WorkflowStep("Use notebook", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "use", "WorkflowBook"]),
            WorkflowStep("Create note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "create", "WorkflowNote"]),
            WorkflowStep("Rename note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "set", "WorkflowNote", "title", "WorkflowNoteRenamed"]),
            WorkflowStep("Get note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "get", "WorkflowNoteRenamed"]),
            WorkflowStep("Remove note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "remove", "WorkflowNoteRenamed"]),
        ]
        self._print_workflow_start("Note lifecycle", len(steps))
        for index, step in enumerate(steps, start=1):
            self._print_step(index, len(steps), step.title, step.args)
            payload = self._run_workflow_step(step)
            assert payload["ok"] is True
        self._print_workflow_end("Note lifecycle")

    def test_tagging_workflow(self, tmp_path):
        project_file, profile_dir = self._prepare_workspace(tmp_path, "workflow-tags")
        steps = [
            WorkflowStep("Create notebook", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "create", "WorkflowBook"]),
            WorkflowStep("Use notebook", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "use", "WorkflowBook"]),
            WorkflowStep("Create note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "create", "WorkflowNote"]),
            WorkflowStep("Rename note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "set", "WorkflowNote", "title", "WorkflowNoteRenamed"]),
            WorkflowStep("Add tag", ["--project", str(project_file), "--profile", str(profile_dir), "tags", "add", "wf-tag", "WorkflowNoteRenamed"]),
            WorkflowStep("List note tags", ["--project", str(project_file), "--profile", str(profile_dir), "tags", "notetags", "WorkflowNoteRenamed"]),
            WorkflowStep("Remove tag", ["--project", str(project_file), "--profile", str(profile_dir), "tags", "remove", "wf-tag", "WorkflowNoteRenamed"]),
        ]
        self._print_workflow_start("Tagging", len(steps))
        for index, step in enumerate(steps, start=1):
            self._print_step(index, len(steps), step.title, step.args)
            payload = self._run_workflow_step(step)
            assert payload["ok"] is True
        self._print_workflow_end("Tagging")

    def test_search_workflow(self, tmp_path):
        project_file, profile_dir = self._prepare_workspace(tmp_path, "workflow-search")
        steps = [
            WorkflowStep("Create notebook", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "create", "WorkflowBook"]),
            WorkflowStep("Use notebook", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "use", "WorkflowBook"]),
            WorkflowStep("Create note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "create", "WorkflowNote"]),
            WorkflowStep("Rename note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "set", "WorkflowNote", "title", "WorkflowNoteRenamed"]),
            WorkflowStep("Search note", ["--project", str(project_file), "--profile", str(profile_dir), "search", "run", "WorkflowNoteRenamed"]),
        ]
        self._print_workflow_start("Search", len(steps))
        for index, step in enumerate(steps, start=1):
            self._print_step(index, len(steps), step.title, step.args)
            payload = self._run_workflow_step(step)
            assert payload["ok"] is True
        self._print_workflow_end("Search")

    def test_sync_workflow(self, tmp_path):
        project_file, profile_dir = self._prepare_workspace(tmp_path, "workflow-sync")
        step = WorkflowStep("Run sync", ["--project", str(project_file), "--profile", str(profile_dir), "sync", "run"])
        self._print_workflow_start("Sync", 1)
        self._print_step(1, 1, step.title, step.args)
        payload = self._run_workflow_step(step)
        assert payload["ok"] is True
        self._print_workflow_end("Sync")

    def test_export_workflow(self, tmp_path):
        project_file, profile_dir = self._prepare_workspace(tmp_path, "workflow-export")
        export_jex_path = tmp_path / "workflow-export.jex"
        export_md_path = tmp_path / "workflow-export.md"
        steps = [
            WorkflowStep("Create notebook", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "create", "WorkflowBook"]),
            WorkflowStep("Use notebook", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "use", "WorkflowBook"]),
            WorkflowStep("Create note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "create", "WorkflowNote"]),
            WorkflowStep("Export JEX", ["--project", str(project_file), "--profile", str(profile_dir), "interop", "export", str(export_jex_path), "--format", "jex"]),
            WorkflowStep("Export MD", ["--project", str(project_file), "--profile", str(profile_dir), "interop", "export", str(export_md_path), "--format", "md"]),
        ]
        self._print_workflow_start("Export", len(steps))
        for index, step in enumerate(steps, start=1):
            self._print_step(index, len(steps), step.title, step.args)
            payload = self._run_workflow_step(step)
            assert payload["ok"] is True
        assert export_jex_path.exists()
        assert export_jex_path.stat().st_size > 0
        assert export_md_path.exists()
        self._print_workflow_end("Export")

    def test_project_save_workflow(self, tmp_path):
        project_file = self._create_project(tmp_path, "workflow-save")
        steps = [
            WorkflowStep("Inspect project status", ["--project", str(project_file), "project", "status"]),
            WorkflowStep("Save project", ["--project", str(project_file), "project", "save"]),
            WorkflowStep("Inspect saved project", ["--project", str(project_file), "project", "status"]),
        ]
        self._print_workflow_start("Project save", len(steps))
        for index, step in enumerate(steps, start=1):
            self._print_step(index, len(steps), step.title, step.args)
            payload = self._run_workflow_step(step)
            assert payload["ok"] is True
        self._print_workflow_end("Project save")


@pytest.mark.skipif(shutil.which("joplin") is None, reason="joplin binary not installed")
class TestBackendIntegration(BackendTestBase):
    def test_full_backend_roundtrip(self, tmp_path):
        project_file, profile_dir = self._prepare_workspace(tmp_path, "integration-full")
        export_jex_path = tmp_path / "integration-full.jex"
        export_md_path = tmp_path / "integration-full.md"

        phases = [
            ("Inspect project", [
                WorkflowStep("Project status", ["--project", str(project_file), "project", "status"]),
                WorkflowStep("Project info", ["--project", str(project_file), "project", "info"]),
            ]),
            ("Notebook setup", [
                WorkflowStep("List notebooks", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "list"]),
                WorkflowStep("Create notebook", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "create", "IntegrationBook"]),
                WorkflowStep("Use notebook", ["--project", str(project_file), "--profile", str(profile_dir), "notebooks", "use", "IntegrationBook"]),
            ]),
            ("Note lifecycle", [
                WorkflowStep("List notes", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "list"]),
                WorkflowStep("Create note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "create", "IntegrationNote"]),
                WorkflowStep("Rename note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "set", "IntegrationNote", "title", "IntegrationNoteRenamed"]),
                WorkflowStep("Get note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "get", "IntegrationNoteRenamed"]),
            ]),
            ("Config and session", [
                WorkflowStep("Get config", ["--project", str(project_file), "config", "get", "sync.target"]),
                WorkflowStep("List config", ["--project", str(project_file), "config", "list"]),
                WorkflowStep("Undo", ["--project", str(project_file), "session", "undo"],),
                WorkflowStep("Redo", ["--project", str(project_file), "session", "redo"],),
            ]),
            ("Tags", [
                WorkflowStep("Add tag", ["--project", str(project_file), "--profile", str(profile_dir), "tags", "add", "integration-tag", "IntegrationNoteRenamed"]),
                WorkflowStep("List note tags", ["--project", str(project_file), "--profile", str(profile_dir), "tags", "notetags", "IntegrationNoteRenamed"]),
                WorkflowStep("List tags", ["--project", str(project_file), "--profile", str(profile_dir), "tags", "list"]),
                WorkflowStep("Remove tag", ["--project", str(project_file), "--profile", str(profile_dir), "tags", "remove", "integration-tag", "IntegrationNoteRenamed"]),
            ]),
            ("Search and sync", [
                WorkflowStep("Search note", ["--project", str(project_file), "--profile", str(profile_dir), "search", "run", "IntegrationNoteRenamed"]),
                WorkflowStep("Run sync", ["--project", str(project_file), "--profile", str(profile_dir), "sync", "run"]),
            ]),
            ("Export and import", [
                WorkflowStep("Export JEX", ["--project", str(project_file), "--profile", str(profile_dir), "interop", "export", str(export_jex_path), "--format", "jex"]),
                WorkflowStep("Export MD", ["--project", str(project_file), "--profile", str(profile_dir), "interop", "export", str(export_md_path), "--format", "md"]),
            ]),
            ("Cleanup", [
                WorkflowStep("Remove note", ["--project", str(project_file), "--profile", str(profile_dir), "notes", "remove", "IntegrationNoteRenamed"]),
                WorkflowStep("Save project", ["--project", str(project_file), "project", "save"]),
                WorkflowStep("Final project status", ["--project", str(project_file), "project", "status"]),
            ]),
        ]

        print("\n=== Workflow: Full backend roundtrip ===")
        for phase_name, steps in phases:
            print(f"\n--- Phase: {phase_name} ---")
            for index, step in enumerate(steps, start=1):
                self._print_step(index, len(steps), step.title, step.args)
                check = not (step.title in {"Undo", "Redo"})
                payload = self._run_workflow_step(step, check=check)
                if step.title == "Undo":
                    assert payload["ok"] is False
                    assert payload["error"]["message"] == "Nothing to undo"
                elif step.title == "Redo":
                    assert payload["ok"] is False
                    assert payload["error"]["message"] == "Nothing to redo"
                else:
                    assert payload["ok"] is True
        assert export_jex_path.exists()
        assert export_jex_path.stat().st_size > 0
        assert export_md_path.exists()
        print("[PASS] Workflow passed: Full backend roundtrip")
