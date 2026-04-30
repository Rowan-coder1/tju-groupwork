from cli_anything.joplin.utils.joplin_backend import BackendConfig, run_joplin_command


def run_sync(config: BackendConfig, target: str | None = None) -> dict:
    args = ["sync"]
    if target:
        args += ["--target", target]
    return run_joplin_command(args, config, timeout=600)
