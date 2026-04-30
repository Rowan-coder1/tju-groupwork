import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class BackendConfig:
    binary: str = "joplin"
    profile: Optional[str] = None


def find_joplin(binary: str = "joplin") -> str:
    path = shutil.which(binary)
    if path:
        return path
    raise RuntimeError(
        "Joplin terminal binary not found in PATH. Install Joplin CLI and ensure `joplin` is executable."
    )


def _is_benign_node_warning(stderr: str, stdout: str = "") -> bool:
    text = f"{stderr}\n{stdout}".strip().lower()
    return bool(text) and "dep0040" in text and "punycode" in text


def run_joplin_command(args: list[str], config: BackendConfig, timeout: int = 120) -> dict:
    binary = find_joplin(config.binary)
    cmd = [binary]
    if config.profile:
        cmd += ["--profile", config.profile]
    cmd += args

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Joplin command timed out after {timeout}s") from e

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    result = {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }

    if proc.returncode != 0 and not _is_benign_node_warning(stderr, stdout):
        raise RuntimeError(stderr or stdout or "Joplin command failed")

    return result


def run_joplin_json(args: list[str], config: BackendConfig, timeout: int = 120) -> dict:
    raw = run_joplin_command(args + ["--format", "json"], config, timeout=timeout)
    text = raw["stdout"]
    if not text:
        return {"raw": raw, "data": None}

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"text": text}

    return {"raw": raw, "data": data}
