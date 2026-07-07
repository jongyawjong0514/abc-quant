import importlib
import json
import tomllib
from pathlib import Path
from typing import Callable

from abc_quant.cli import lightgbm_dependency_smoke
from abc_quant.cli.lightgbm_dependency_smoke import main as lightgbm_dependency_main

LIGHTGBM_DEPENDENCY_SCRIPT_NAME = "abc-quant-lightgbm-dependency-smoke"
LIGHTGBM_DEPENDENCY_SCRIPT_TARGET = "abc_quant.cli.lightgbm_dependency_smoke:main"
EXPECTED_SUMMARY_KEYS = {
    "package_name",
    "installed",
    "message",
    "default_params",
    "default_model_name",
    "default_method",
    "fitting_enabled",
}


def test_pyproject_declares_lightgbm_dependency_smoke_console_script() -> None:
    pyproject = _load_pyproject()

    assert (
        pyproject["project"]["scripts"][LIGHTGBM_DEPENDENCY_SCRIPT_NAME]
        == LIGHTGBM_DEPENDENCY_SCRIPT_TARGET
    )


def test_lightgbm_dependency_smoke_console_script_target_resolves_to_main() -> None:
    resolved = _resolve_script_target(LIGHTGBM_DEPENDENCY_SCRIPT_TARGET)

    assert resolved is lightgbm_dependency_main
    assert callable(resolved)


def test_lightgbm_dependency_smoke_console_script_function_outputs_json(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        lightgbm_dependency_smoke,
        "run_lightgbm_dependency_smoke",
        lambda: _fake_summary(installed=False),
    )
    pyproject = _load_pyproject()
    resolved = _resolve_script_target(
        pyproject["project"]["scripts"][LIGHTGBM_DEPENDENCY_SCRIPT_NAME]
    )

    exit_code = resolved([])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload == _fake_summary(installed=False)
    assert set(payload) == EXPECTED_SUMMARY_KEYS
    assert payload["package_name"] == "lightgbm"
    assert isinstance(payload["installed"], bool)
    assert isinstance(payload["message"], str)
    assert set(payload["default_params"]) == {
        "objective",
        "n_estimators",
        "learning_rate",
        "num_leaves",
        "min_data_in_leaf",
        "feature_fraction",
        "bagging_fraction",
        "bagging_freq",
        "random_state",
        "verbosity",
    }
    assert payload["default_model_name"] == "lightgbm_regressor"
    assert payload["default_method"] == "lightgbm_regressor"
    assert payload["fitting_enabled"] is False


def test_lightgbm_dependency_smoke_console_script_indent_preserves_content(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        lightgbm_dependency_smoke,
        "run_lightgbm_dependency_smoke",
        lambda: _fake_summary(installed=True),
    )
    resolved = _resolve_script_target(LIGHTGBM_DEPENDENCY_SCRIPT_TARGET)

    default_exit_code = resolved([])
    default_output = capsys.readouterr().out
    indented_exit_code = resolved(["--indent", "2"])
    indented_output = capsys.readouterr().out

    assert default_exit_code == 0
    assert indented_exit_code == 0
    assert default_output.startswith("{")
    assert not default_output.startswith("{\n")
    assert indented_output.startswith("{\n")
    assert json.loads(default_output) == json.loads(indented_output)


def test_lightgbm_dependency_smoke_console_script_has_no_forbidden_keys(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        lightgbm_dependency_smoke,
        "run_lightgbm_dependency_smoke",
        lambda: _fake_summary(installed=False),
    )
    resolved = _resolve_script_target(LIGHTGBM_DEPENDENCY_SCRIPT_TARGET)
    forbidden_keys = {
        "winner",
        "rank",
        "ranking",
        "decision",
        "selected_model",
        "selected-model",
        "model_selection",
        "strategy",
        "signal",
        "signals",
        "trading_signals",
        "allocation",
        "allocations",
        "performance_curve",
        "performance-curve",
        "equity_curve",
        "order",
        "orders",
        "position",
        "positions",
        "simulation",
        "simulation_results",
    }

    exit_code = resolved([])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert forbidden_keys.isdisjoint(_all_dict_keys(payload))


def _load_pyproject() -> dict[str, object]:
    return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))


def _resolve_script_target(target: str) -> Callable[[list[str]], int]:
    module_name, function_name = target.split(":", maxsplit=1)
    module = importlib.import_module(module_name)
    resolved = getattr(module, function_name)
    if not callable(resolved):
        raise TypeError(f"script target is not callable: {target}")
    return resolved


def _fake_summary(*, installed: bool) -> dict[str, object]:
    return {
        "package_name": "lightgbm",
        "installed": installed,
        "message": "fake lightgbm dependency status",
        "default_params": {
            "objective": "regression",
            "n_estimators": 100,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_data_in_leaf": 20,
            "feature_fraction": 1.0,
            "bagging_fraction": 1.0,
            "bagging_freq": 0,
            "random_state": 42,
            "verbosity": -1,
        },
        "default_model_name": "lightgbm_regressor",
        "default_method": "lightgbm_regressor",
        "fitting_enabled": False,
    }


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
