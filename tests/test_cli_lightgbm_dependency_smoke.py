import json
import os
import subprocess
import sys
from pathlib import Path

from abc_quant.cli import lightgbm_dependency_smoke
from abc_quant.cli.lightgbm_dependency_smoke import main
from abc_quant.pipeline.lightgbm_diagnostics import run_lightgbm_dependency_smoke

EXPECTED_SUMMARY_KEYS = {
    "package_name",
    "installed",
    "message",
    "default_params",
    "default_model_name",
    "default_method",
    "fitting_enabled",
}


def test_lightgbm_dependency_smoke_cli_module_prints_sorted_json() -> None:
    result = _run_module()

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload == _json_round_trip(run_lightgbm_dependency_smoke())
    assert list(payload) == sorted(EXPECTED_SUMMARY_KEYS)


def test_lightgbm_dependency_smoke_cli_main_prints_expected_shape(capsys) -> None:
    exit_code = main([])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
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


def test_lightgbm_dependency_smoke_cli_indent_preserves_decoded_content(capsys) -> None:
    default_exit_code = main([])
    default_output = capsys.readouterr().out

    indented_exit_code = main(["--indent", "2"])
    indented_output = capsys.readouterr().out

    assert default_exit_code == 0
    assert indented_exit_code == 0
    assert default_output.startswith("{")
    assert not default_output.startswith("{\n")
    assert indented_output.startswith("{\n")
    assert json.loads(default_output) == json.loads(indented_output)


def test_lightgbm_dependency_smoke_cli_calls_pipeline_once_per_invocation(
    monkeypatch,
    capsys,
) -> None:
    calls = 0

    def fake_smoke() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return _fake_summary(installed=False)

    monkeypatch.setattr(
        lightgbm_dependency_smoke,
        "run_lightgbm_dependency_smoke",
        fake_smoke,
    )

    exit_code = main(["--indent", "2"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert calls == 1
    assert json.loads(captured.out) == _fake_summary(installed=False)
    assert captured.err == ""


def test_lightgbm_dependency_smoke_cli_monkeypatched_summary_needs_no_real_package(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        lightgbm_dependency_smoke,
        "run_lightgbm_dependency_smoke",
        lambda: _fake_summary(installed=True),
    )

    exit_code = main([])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload == _fake_summary(installed=True)
    assert payload["fitting_enabled"] is False
    assert captured.err == ""


def test_lightgbm_dependency_smoke_cli_output_has_no_decision_or_simulation_keys(
    capsys,
) -> None:
    exit_code = main([])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
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

    assert exit_code == 0
    assert forbidden_keys.isdisjoint(_all_dict_keys(payload))


def _run_module(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(Path.cwd() / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else src_path + os.pathsep + env["PYTHONPATH"]
    )
    return subprocess.run(
        [sys.executable, "-m", "abc_quant.cli.lightgbm_dependency_smoke", *args],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )


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


def _json_round_trip(value: object) -> object:
    return json.loads(json.dumps(value, sort_keys=True))


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
