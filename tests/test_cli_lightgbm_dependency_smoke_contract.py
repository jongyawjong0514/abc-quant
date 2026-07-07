import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from abc_quant import pipeline

LIGHTGBM_DEPENDENCY_COMMAND = "abc-quant-lightgbm-dependency-smoke"


def test_lightgbm_dependency_smoke_module_cli_output_matches_public_contract() -> None:
    payload = _decode_successful_json(_run_module_cli())

    validated = pipeline.validate_lightgbm_dependency_smoke_summary(payload)

    assert validated is payload
    assert set(payload) == set(pipeline.LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS)
    assert list(payload) == sorted(pipeline.LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS)
    assert set(payload["default_params"]) == set(
        pipeline.LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS
    )
    assert list(payload["default_params"]) == sorted(
        pipeline.LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS
    )
    assert payload["fitting_enabled"] is False
    assert set(pipeline.LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS).isdisjoint(
        _all_dict_keys(payload)
    )


def test_lightgbm_dependency_smoke_packaged_command_output_matches_module_when_available() -> None:
    module_payload = _decode_successful_json(_run_module_cli())
    command_payload = _decode_successful_json(_run_packaged_command_or_skip())

    validated = pipeline.validate_lightgbm_dependency_smoke_summary(command_payload)

    assert validated is command_payload
    assert command_payload == module_payload
    assert command_payload["fitting_enabled"] is False
    assert set(pipeline.LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS).isdisjoint(
        _all_dict_keys(command_payload)
    )


def _run_module_cli() -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(Path.cwd() / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else src_path + os.pathsep + env["PYTHONPATH"]
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "abc_quant.cli.lightgbm_dependency_smoke",
            "--indent",
            "2",
        ],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )


def _run_packaged_command_or_skip() -> subprocess.CompletedProcess[str]:
    command_path = shutil.which(LIGHTGBM_DEPENDENCY_COMMAND)
    if command_path is None:
        pytest.skip(
            f"{LIGHTGBM_DEPENDENCY_COMMAND} is not installed on PATH in this environment"
        )
    return subprocess.run(
        [command_path, "--indent", "2"],
        check=False,
        capture_output=True,
        text=True,
    )


def _decode_successful_json(
    result: subprocess.CompletedProcess[str],
) -> dict[str, object]:
    assert result.returncode == 0
    assert result.stderr == ""
    decoded = json.loads(result.stdout)
    assert isinstance(decoded, dict)
    return decoded


def _all_dict_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_all_dict_keys(nested))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_dict_keys(item))
        return keys
    return set()
