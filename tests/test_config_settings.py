from pathlib import Path

import pytest

from abc_quant.config.settings import load_settings


def test_load_settings_reads_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project:\n  name: abc_quant\n", encoding="utf-8")

    settings = load_settings(config_path)

    assert settings.require("project") == {"name": "abc_quant"}


def test_load_settings_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a mapping"):
        load_settings(config_path)
