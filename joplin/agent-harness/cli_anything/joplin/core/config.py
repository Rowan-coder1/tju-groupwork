from cli_anything.joplin.utils.joplin_backend import BackendConfig, run_joplin_command


def config_get(config: BackendConfig, key: str) -> dict:
    return run_joplin_command(["config", key], config)


def config_set(config: BackendConfig, key: str, value: str) -> dict:
    return run_joplin_command(["config", key, value], config)


def config_list(config: BackendConfig) -> dict:
    return run_joplin_command(["config"], config)
