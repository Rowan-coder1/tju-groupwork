import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from cli_anything.joplin import joplin_cli
from cli_anything.joplin.core import project as project_mod
from cli_anything.joplin.core.session import Session
from cli_anything.joplin.utils import joplin_backend


def test_create_project_schema():
    proj = project_mod.create_project(name="demo", backend_binary="joplin", backend_profile=None)
    assert proj["name"] == "demo"
    assert "backend" in proj
    assert "context" in proj
    assert isinstance(proj["history"], list)


def test_project_save_open_roundtrip(tmp_path):
    proj = project_mod.create_project(name="rt")
    p = tmp_path / "p.json"
    project_mod.save_project(proj, str(p))
    loaded = project_mod.open_project(str(p))
    assert loaded["name"] == "rt"


def test_project_add_history():
    proj = project_mod.create_project(name="h")
    project_mod.add_history(proj, "action", {"k": "v"})
    assert len(proj["history"]) == 1
    assert proj["history"][0]["action"] == "action"


def test_project_save_creates_parent(tmp_path):
    proj = project_mod.create_project(name="nested")
    p = tmp_path / "a" / "b" / "p.json"
    project_mod.save_project(proj, str(p))
    assert p.exists()


def test_session_set_get_has_project():
    sess = Session()
    assert not sess.has_project()
    proj = project_mod.create_project(name="s")
    sess.set_project(proj)
    assert sess.has_project()
    assert sess.get_project()["name"] == "s"


def test_session_snapshot_undo_redo():
    sess = Session()
    proj = project_mod.create_project(name="s")
    sess.set_project(proj)
    sess.snapshot("before")
    sess.get_project()["context"]["current_notebook"] = "A"
    sess.undo()
    assert sess.get_project()["context"]["current_notebook"] is None
    sess.redo()
    assert sess.get_project()["context"]["current_notebook"] == "A"


def test_session_undo_empty_raises():
    sess = Session()
    with pytest.raises(RuntimeError):
        sess.undo()


def test_session_redo_empty_raises():
    sess = Session()
    with pytest.raises(RuntimeError):
        sess.redo()


def test_session_save_without_path_raises():
    sess = Session()
    sess.set_project(project_mod.create_project())
    with pytest.raises(RuntimeError):
        sess.save_session()


def test_session_save_with_path(tmp_path):
    sess = Session()
    sess.set_project(project_mod.create_project(name="save"), str(tmp_path / "x.json"))
    saved = sess.save_session()
    assert os.path.exists(saved)


def test_backend_find_joplin_missing(monkeypatch):
    monkeypatch.setattr(joplin_backend.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError):
        joplin_backend.find_joplin("joplin")


def test_backend_find_joplin_ok(monkeypatch):
    monkeypatch.setattr(joplin_backend.shutil, "which", lambda _: "/usr/bin/joplin")
    assert joplin_backend.find_joplin("joplin") == "/usr/bin/joplin"


def test_backend_run_command_invokes_subprocess(monkeypatch):
    class Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    monkeypatch.setattr(joplin_backend, "find_joplin", lambda _: "joplin")

    captured = {}

    def fake_run(cmd, capture_output, text, timeout, check):
        captured["cmd"] = cmd
        return Proc()

    monkeypatch.setattr(joplin_backend.subprocess, "run", fake_run)
    cfg = joplin_backend.BackendConfig(binary="joplin", profile="/tmp/p")
    out = joplin_backend.run_joplin_command(["ls"], cfg)
    assert out["returncode"] == 0
    assert captured["cmd"][:3] == ["joplin", "--profile", "/tmp/p"]


def test_backend_run_command_error(monkeypatch):
    class Proc:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(joplin_backend, "find_joplin", lambda _: "joplin")
    monkeypatch.setattr(joplin_backend.subprocess, "run", lambda *a, **k: Proc())
    cfg = joplin_backend.BackendConfig(binary="joplin", profile=None)
    with pytest.raises(RuntimeError):
        joplin_backend.run_joplin_command(["ls"], cfg)


def test_backend_run_json_parse(monkeypatch):
    monkeypatch.setattr(
        joplin_backend,
        "run_joplin_command",
        lambda args, config, timeout=120: {"stdout": json.dumps({"a": 1}), "returncode": 0, "stderr": "", "command": args},
    )
    cfg = joplin_backend.BackendConfig()
    data = joplin_backend.run_joplin_json(["ls"], cfg)
    assert data["data"]["a"] == 1


def test_backend_run_json_fallback_text(monkeypatch):
    monkeypatch.setattr(
        joplin_backend,
        "run_joplin_command",
        lambda args, config, timeout=120: {"stdout": "plain text", "returncode": 0, "stderr": "", "command": args},
    )
    cfg = joplin_backend.BackendConfig()
    data = joplin_backend.run_joplin_json(["ls"], cfg)
    assert data["data"]["text"] == "plain text"


def test_json_envelope_shape():
    ok_payload = joplin_cli._json_envelope(True, "notes.list", data={"k": 1})
    assert ok_payload["ok"] is True
    assert ok_payload["command"] == "notes.list"
    assert ok_payload["data"]["k"] == 1
    assert ok_payload["error"] is None

    err = RuntimeError("boom")
    bad_payload = joplin_cli._json_envelope(False, "notes.create", data=None, error=err)
    assert bad_payload["ok"] is False
    assert bad_payload["command"] == "notes.create"
    assert bad_payload["data"] is None
    assert bad_payload["error"]["type"] == "RuntimeError"
    assert bad_payload["error"]["message"] == "boom"


@pytest.fixture(autouse=True)
def reset_global_session():
    joplin_cli._session = None
    joplin_cli._json_output = False
    joplin_cli._repl_mode = False
    yield
    joplin_cli._session = None
    joplin_cli._json_output = False
    joplin_cli._repl_mode = False


def _mock_ok(monkeypatch):
    monkeypatch.setattr(joplin_cli, "_backend_config", lambda *a, **k: object())
    monkeypatch.setattr(joplin_cli.notebook_mod, "list_notebooks", lambda cfg: {"data": [{"title": "N1"}]})
    monkeypatch.setattr(joplin_cli.notebook_mod, "create_notebook", lambda cfg, title, parent=None: {"created": title})
    monkeypatch.setattr(joplin_cli.notebook_mod, "use_notebook", lambda cfg, notebook: {"used": notebook})
    monkeypatch.setattr(joplin_cli.note_mod, "list_notes", lambda cfg, pattern=None, limit=None: {"data": [{"title": "A"}]})
    monkeypatch.setattr(joplin_cli.note_mod, "create_note", lambda cfg, title: {"created": title})
    monkeypatch.setattr(joplin_cli.note_mod, "set_note_field", lambda cfg, note_ref, field, value: {"updated": note_ref})
    monkeypatch.setattr(joplin_cli.note_mod, "get_note", lambda cfg, note_ref: {"body": "x", "id": note_ref})
    monkeypatch.setattr(joplin_cli.note_mod, "remove_note", lambda cfg, note_ref, force=True: {"removed": note_ref})
    monkeypatch.setattr(joplin_cli.tag_mod, "list_tags", lambda cfg: {"tags": ["t1"]})
    monkeypatch.setattr(joplin_cli.tag_mod, "add_tag", lambda cfg, tag, note: {"added": tag})
    monkeypatch.setattr(joplin_cli.tag_mod, "remove_tag", lambda cfg, tag, note: {"removed": tag})
    monkeypatch.setattr(joplin_cli.tag_mod, "note_tags", lambda cfg, note: {"tags": ["t1"]})
    monkeypatch.setattr(joplin_cli.search_mod, "search", lambda cfg, pattern, notebook=None: {"hits": [pattern]})
    monkeypatch.setattr(joplin_cli.sync_mod, "run_sync", lambda cfg, target=None: {"synced": True})
    monkeypatch.setattr(joplin_cli.interop_mod, "import_data", lambda cfg, path, notebook=None, fmt=None: {"imported": path})
    monkeypatch.setattr(joplin_cli.interop_mod, "export_data", lambda cfg, path, fmt="jex", note=None, notebook=None: {"exported": path})
    monkeypatch.setattr(joplin_cli.config_mod, "config_get", lambda cfg, key: {key: "v"})
    monkeypatch.setattr(joplin_cli.config_mod, "config_set", lambda cfg, key, value: {key: value})
    monkeypatch.setattr(joplin_cli.config_mod, "config_list", lambda cfg: {"k": "v"})


def test_json_contract_notebooks_group(monkeypatch):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    r1 = runner.invoke(joplin_cli.cli, ["--json", "notebooks", "list"])
    p1 = json.loads(r1.output)
    assert p1["ok"] is True and p1["command"] == "notebooks.list"

    r2 = runner.invoke(joplin_cli.cli, ["--json", "notebooks", "create", "BookA"])
    p2 = json.loads(r2.output)
    assert p2["ok"] is True and p2["command"] == "notebooks.create"

    r3 = runner.invoke(joplin_cli.cli, ["--json", "notebooks", "use", "BookA"])
    p3 = json.loads(r3.output)
    assert p3["ok"] is True and p3["command"] == "notebooks.use"


def test_json_contract_project_status(monkeypatch, tmp_path):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    project_path = tmp_path / "status.json"
    project_mod.save_project(project_mod.create_project(name="status"), str(project_path))

    result = runner.invoke(joplin_cli.cli, ["--json", "--project", str(project_path), "project", "status"])
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "project.status"
    assert "project" in payload["data"]
    assert "project_path" in payload["data"]
    assert "session" in payload["data"]
    assert payload["data"]["project"]["name"] == "status"
    assert payload["data"]["project_path"] == str(project_path)


def test_json_contract_notes_group(monkeypatch):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    p1 = json.loads(runner.invoke(joplin_cli.cli, ["--json", "notes", "list"]).output)
    assert p1["ok"] is True and p1["command"] == "notes.list"

    p2 = json.loads(runner.invoke(joplin_cli.cli, ["--json", "notes", "create", "A"]).output)
    assert p2["ok"] is True and p2["command"] == "notes.create"

    p3 = json.loads(runner.invoke(joplin_cli.cli, ["--json", "notes", "set", "A", "title", "B"]).output)
    assert p3["ok"] is True and p3["command"] == "notes.set"

    p4 = json.loads(runner.invoke(joplin_cli.cli, ["--json", "notes", "get", "A"]).output)
    assert p4["ok"] is True and p4["command"] == "notes.get"

    p5 = json.loads(runner.invoke(joplin_cli.cli, ["--json", "notes", "remove", "A"]).output)
    assert p5["ok"] is True and p5["command"] == "notes.remove"


def test_json_contract_notebooks_notes_tags_workflow(monkeypatch):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    nb_create = json.loads(runner.invoke(joplin_cli.cli, ["--json", "notebooks", "create", "BookA"]).output)
    assert nb_create["ok"] is True
    assert nb_create["command"] == "notebooks.create"

    nb_use = json.loads(runner.invoke(joplin_cli.cli, ["--json", "notebooks", "use", "BookA"]).output)
    assert nb_use["ok"] is True
    assert nb_use["command"] == "notebooks.use"

    note_create = json.loads(runner.invoke(joplin_cli.cli, ["--json", "notes", "create", "NoteA"]).output)
    assert note_create["ok"] is True
    assert note_create["command"] == "notes.create"

    note_set = json.loads(runner.invoke(joplin_cli.cli, ["--json", "notes", "set", "NoteA", "title", "NoteB"]).output)
    assert note_set["ok"] is True
    assert note_set["command"] == "notes.set"

    tag_add = json.loads(runner.invoke(joplin_cli.cli, ["--json", "tags", "add", "TagA", "NoteB"]).output)
    assert tag_add["ok"] is True
    assert tag_add["command"] == "tags.add"

    tag_remove = json.loads(runner.invoke(joplin_cli.cli, ["--json", "tags", "remove", "TagA", "NoteB"]).output)
    assert tag_remove["ok"] is True
    assert tag_remove["command"] == "tags.remove"

    note_tags = json.loads(runner.invoke(joplin_cli.cli, ["--json", "tags", "notetags", "NoteB"]).output)
    assert note_tags["ok"] is True
    assert note_tags["command"] == "tags.notetags"


def test_json_contract_tags_search_sync_interop_config_session(monkeypatch):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "tags", "list"]).output)["command"] == "tags.list"
    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "tags", "add", "t1", "n1"]).output)["command"] == "tags.add"
    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "tags", "remove", "t1", "n1"]).output)["command"] == "tags.remove"
    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "tags", "notetags", "n1"]).output)["command"] == "tags.notetags"

    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "search", "run", "abc"]).output)["command"] == "search.run"
    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "sync", "run"]).output)["command"] == "sync.run"

    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "interop", "import", "a.enex"]).output)["command"] == "interop.import"
    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "interop", "export", "a.jex"]).output)["command"] == "interop.export"

    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "config", "get", "locale"]).output)["command"] == "config.get"
    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "config", "set", "locale", "en_US"]).output)["command"] == "config.set"
    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "config", "list"]).output)["command"] == "config.list"

    assert json.loads(runner.invoke(joplin_cli.cli, ["--json", "session", "status"]).output)["command"] == "session.status"


def test_json_contract_search_sync_interop_workflow(monkeypatch):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    search_payload = json.loads(runner.invoke(joplin_cli.cli, ["--json", "search", "run", "abc"]).output)
    assert search_payload["ok"] is True
    assert search_payload["command"] == "search.run"

    sync_payload = json.loads(runner.invoke(joplin_cli.cli, ["--json", "sync", "run"]).output)
    assert sync_payload["ok"] is True
    assert sync_payload["command"] == "sync.run"

    import_payload = json.loads(runner.invoke(joplin_cli.cli, ["--json", "interop", "import", "a.enex"]).output)
    assert import_payload["ok"] is True
    assert import_payload["command"] == "interop.import"

    export_payload = json.loads(runner.invoke(joplin_cli.cli, ["--json", "interop", "export", "a.jex"]).output)
    assert export_payload["ok"] is True
    assert export_payload["command"] == "interop.export"


def test_json_contract_search_sync_interop_workflow(monkeypatch):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    search_payload = json.loads(runner.invoke(joplin_cli.cli, ["--json", "search", "run", "keyword"]).output)
    assert search_payload["ok"] is True
    assert search_payload["command"] == "search.run"
    assert search_payload["data"]["hits"] == ["keyword"]

    sync_payload = json.loads(runner.invoke(joplin_cli.cli, ["--json", "sync", "run"]).output)
    assert sync_payload["ok"] is True
    assert sync_payload["command"] == "sync.run"
    assert sync_payload["data"]["synced"] is True

    import_payload = json.loads(runner.invoke(joplin_cli.cli, ["--json", "interop", "import", "notes.enex"]).output)
    assert import_payload["ok"] is True
    assert import_payload["command"] == "interop.import"
    assert import_payload["data"]["imported"] == "notes.enex"

    export_payload = json.loads(runner.invoke(joplin_cli.cli, ["--json", "interop", "export", "notes.jex"]).output)
    assert export_payload["ok"] is True
    assert export_payload["command"] == "interop.export"
    assert export_payload["data"]["exported"] == "notes.jex"


def test_json_error_contract(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(joplin_cli, "_backend_config", lambda *a, **k: object())
    monkeypatch.setattr(joplin_cli.search_mod, "search", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("search failed")))

    result = runner.invoke(joplin_cli.cli, ["--json", "search", "run", "abc"])
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "RuntimeError"
    assert payload["error"]["message"] == "search failed"


def test_json_error_contract_no_profile_path(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(joplin_cli, "_backend_config", lambda *a, **k: object())
    monkeypatch.setattr(
        joplin_cli.note_mod,
        "get_note",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Cannot find note")),
    )

    result = runner.invoke(joplin_cli.cli, ["--json", "notes", "get", "missing-note"])
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "notes.get"
    assert payload["error"]["message"] == "Cannot find note"


def test_json_error_contract_backend_missing(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(joplin_cli, "_backend_config", lambda *a, **k: object())
    monkeypatch.setattr(
        joplin_cli.tag_mod,
        "add_tag",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Joplin terminal binary not found in PATH")),
    )

    result = runner.invoke(joplin_cli.cli, ["--json", "tags", "add", "t1", "n1"])
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "tags.add"
    assert "not found" in payload["error"]["message"]


def test_json_error_contract_remove_missing_note(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(joplin_cli, "_backend_config", lambda *a, **k: object())
    monkeypatch.setattr(
        joplin_cli.note_mod,
        "remove_note",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("No such note")),
    )

    result = runner.invoke(joplin_cli.cli, ["--json", "notes", "remove", "missing-note"])
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "notes.remove"
    assert payload["error"]["message"] == "No such note"


def test_json_error_contract_remove_missing_tag(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(joplin_cli, "_backend_config", lambda *a, **k: object())
    monkeypatch.setattr(
        joplin_cli.tag_mod,
        "remove_tag",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("No such tag")),
    )

    result = runner.invoke(joplin_cli.cli, ["--json", "tags", "remove", "missing-tag", "n1"])
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "tags.remove"
    assert payload["error"]["message"] == "No such tag"


def test_one_shot_mutation_auto_saves_project(monkeypatch, tmp_path):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    project_path = tmp_path / "autosave.json"
    project_mod.save_project(project_mod.create_project(name="auto"), str(project_path))
    before = project_mod.open_project(str(project_path))
    before_hist = len(before["history"])

    result = runner.invoke(
        joplin_cli.cli,
        ["--json", "--project", str(project_path), "notebooks", "create", "AutoBook"],
    )
    assert result.exit_code == 0

    after = project_mod.open_project(str(project_path))
    assert len(after["history"]) >= before_hist + 2
    actions = [h.get("action") for h in after["history"]]
    assert "snapshot" in actions
    assert "notebook.create" in actions


def test_dry_run_suppresses_auto_save(monkeypatch, tmp_path):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    project_path = tmp_path / "dryrun.json"
    project_mod.save_project(project_mod.create_project(name="dry"), str(project_path))
    before = project_mod.open_project(str(project_path))

    result = runner.invoke(
        joplin_cli.cli,
        ["--json", "--dry-run", "--project", str(project_path), "notebooks", "create", "DryBook"],
    )
    assert result.exit_code == 0

    after = project_mod.open_project(str(project_path))
    assert len(after["history"]) == len(before["history"])


def test_session_save_keeps_undo_redo_consistent(tmp_path):
    sess = Session()
    project_path = tmp_path / "session.json"

    proj = project_mod.create_project(name="persist")
    sess.set_project(proj, str(project_path))
    sess.snapshot("set notebook")
    sess.get_project()["context"]["current_notebook"] = "NB1"

    saved = sess.save_session()
    assert os.path.exists(saved)
    assert sess.status()["modified"] is False
    assert sess.status()["undo_depth"] == 1

    sess.undo()
    assert sess.get_project()["context"]["current_notebook"] is None
    assert sess.status()["redo_depth"] == 1

    sess.redo()
    assert sess.get_project()["context"]["current_notebook"] == "NB1"

    saved2 = sess.save_session()
    assert os.path.exists(saved2)


def test_project_status_requires_project(monkeypatch):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    result = runner.invoke(joplin_cli.cli, ["--json", "project", "status"])
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "project.status"
    assert payload["error"]["message"] == "No project loaded"


def test_project_save_requires_path(monkeypatch):
    _mock_ok(monkeypatch)
    runner = CliRunner()

    result = runner.invoke(joplin_cli.cli, ["--json", "project", "save"])
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "project.save"
    assert payload["error"]["message"] == "No project loaded"


