"""Configuration loading utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Settings:
    """Thin wrapper around project settings."""

    values: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Return a top-level setting value."""
        return self.values.get(key, default)

    def require(self, key: str) -> Any:
        """Return a required top-level setting value.

        Raises
        ------
        KeyError
            If the key is absent from the YAML root mapping.
        """
        if key not in self.values:
            raise KeyError(f"Required config key is missing: {key}")
        return self.values[key]


def load_settings(path: str | Path) -> Settings:
    """Load YAML settings from a path.

    Parameters
    ----------
    path:
        Path to a YAML configuration file.
    """
    config_path = Path(path)
    if config_path.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError(f"Config file must be YAML (.yaml or .yml): {config_path}")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    if not config_path.is_file():
        raise ValueError(f"Config path is not a file: {config_path}")
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML config file {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping/dictionary: {config_path}")
    return Settings(values=data)
