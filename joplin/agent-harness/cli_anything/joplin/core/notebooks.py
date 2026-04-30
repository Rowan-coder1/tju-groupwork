from cli_anything.joplin.utils.joplin_backend import BackendConfig, run_joplin_command, run_joplin_json


def list_notebooks(config: BackendConfig) -> dict:
    return run_joplin_json(["ls", "/"], config)


def create_notebook(config: BackendConfig, title: str, parent: str | None = None) -> dict:
    args = ["mkbook", title]
    if parent:
        args += ["-p", parent]
    return run_joplin_command(args, config)


def use_notebook(config: BackendConfig, notebook: str) -> dict:
    return run_joplin_command(["use", notebook], config)
