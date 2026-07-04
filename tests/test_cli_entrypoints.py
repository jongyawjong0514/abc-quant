import importlib
import json
import tomllib
from pathlib import Path
from typing import Callable

from abc_quant.cli.modeling_smoke import main as modeling_main
from abc_quant.cli.preprocessing_smoke import main as preprocessing_main


MODELING_SCRIPT_NAME = "abc-quant-modeling-smoke"
MODELING_SCRIPT_TARGET = "abc_quant.cli.modeling_smoke:main"
PREPROCESSING_SCRIPT_NAME = "abc-quant-preprocessing-smoke"
PREPROCESSING_SCRIPT_TARGET = "abc_quant.cli.preprocessing_smoke:main"


def test_pyproject_declares_modeling_smoke_console_script() -> None:
    pyproject = _load_pyproject()

    assert pyproject["project"]["scripts"][MODELING_SCRIPT_NAME] == MODELING_SCRIPT_TARGET


def test_pyproject_declares_preprocessing_smoke_console_script() -> None:
    pyproject = _load_pyproject()

    assert (
        pyproject["project"]["scripts"][PREPROCESSING_SCRIPT_NAME]
        == PREPROCESSING_SCRIPT_TARGET
    )


def test_modeling_smoke_console_script_target_resolves_to_main() -> None:
    resolved = _resolve_script_target(MODELING_SCRIPT_TARGET)

    assert resolved is modeling_main


def test_preprocessing_smoke_console_script_target_resolves_to_main() -> None:
    resolved = _resolve_script_target(PREPROCESSING_SCRIPT_TARGET)

    assert resolved is preprocessing_main


def test_modeling_smoke_console_script_function_outputs_json(capsys) -> None:
    pyproject = _load_pyproject()
    resolved = _resolve_script_target(
        pyproject["project"]["scripts"][MODELING_SCRIPT_NAME]
    )

    exit_code = resolved(["--method", "median"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["baseline_method"] == "median"
    assert payload["split_counts"] == {"train": 8, "validation": 6, "test": 10}


def test_preprocessing_smoke_console_script_function_outputs_json(capsys) -> None:
    pyproject = _load_pyproject()
    resolved = _resolve_script_target(
        pyproject["project"]["scripts"][PREPROCESSING_SCRIPT_NAME]
    )

    exit_code = resolved(["--indent", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.startswith("{\n")
    assert payload["split_counts"] == {"train": 2, "validation": 6, "test": 10}
    assert payload["split_shape"]["train"] == {"columns": 4, "rows": 2}


def _load_pyproject() -> dict[str, object]:
    return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))


def _resolve_script_target(target: str) -> Callable[[list[str]], int]:
    module_name, function_name = target.split(":", maxsplit=1)
    module = importlib.import_module(module_name)
    resolved = getattr(module, function_name)
    if not callable(resolved):
        raise TypeError(f"script target is not callable: {target}")
    return resolved
