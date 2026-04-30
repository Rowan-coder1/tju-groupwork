from cli_anything.joplin.utils.joplin_backend import BackendConfig, run_joplin_command, run_joplin_json


def list_notes(config: BackendConfig, pattern: str | None = None, limit: int | None = None) -> dict:
    args = ["ls"]
    if pattern:
        args.append(pattern)
    if limit:
        args += ["-n", str(limit)]
    return run_joplin_json(args, config)


def create_note(config: BackendConfig, title: str) -> dict:
    return run_joplin_command(["mknote", title], config)


def set_note_field(config: BackendConfig, note_ref: str, field: str, value: str) -> dict:
    return run_joplin_command(["set", note_ref, field, value], config)


def get_note(config: BackendConfig, note_ref: str) -> dict:
    return run_joplin_command(["cat", note_ref], config)


def remove_note(config: BackendConfig, note_ref: str, force: bool = True) -> dict:
    args = ["rmnote", note_ref]
    if force:
        args.append("-f")
    return run_joplin_command(args, config)
