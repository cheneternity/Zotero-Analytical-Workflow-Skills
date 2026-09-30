"""Shared, dependency-free configuration for the ResearchVault tools."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_KEYS = {
    "vault_root": "RESEARCHVAULT_ROOT",
    "zotero_data_dir": "ZOTERO_DATA_DIR",
    "mineru_executable": "MINERU_EXECUTABLE",
    "archive_root": "RESEARCHVAULT_ARCHIVE_ROOT",
}


def load_config(config_path: Path | None = None) -> dict[str, str]:
    path = config_path or Path(os.environ.get("RESEARCHVAULT_CONFIG", REPO_ROOT / "config.toml"))
    values: dict[str, str] = {}
    if path.is_file():
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
        values.update({key: str(value) for key, value in raw.get("paths", {}).items() if value})
    for key, env_name in ENV_KEYS.items():
        if os.environ.get(env_name):
            values[key] = os.environ[env_name]
    return values


def configured_path(key: str, config: dict[str, str]) -> Path | None:
    value = config.get(key)
    if not value:
        return None
    return Path(value).expanduser().resolve()
