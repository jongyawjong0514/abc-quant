import json
import os
import subprocess
import sys
from pathlib import Path

import abc_quant.cli.lightgbm_dependency_smoke as cli
from abc_quant.cli.lightgbm_dependency_smoke import main
from abc_quant.pipeline import run_lightgbm_dependency_smoke


EXPECTED_TOP_LEVEL_KEYS = {
    "package_name",
    "installed",
    "message",
    "default_params",
    "default_model_name",
    "default_method",
    "fitting_enabled",
}

FORBIDDEN_OUTPUT_KEYS = {
    "winner",
    "rank",
    "ranking",
    "decision",
    "selected_model",
    "selected-model",
    "model_selection",
    "selected_model_name",
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


def test_lightgbm_dependency_smoke_cli_module_prints_sorted_json() -> None:
    result = _run_module()

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert result.stderr == ""
    assert list(payload) == sorted(EXPECTED_TOP_LEVEL_KEYS)
    assert set(payload) == EXPECTED_TOP_LEVEL_KEYS
    assert payload == _json_round_trip(run_lightgbm_dependency_smoke())


def test_lightgbm_dependency_smoke_cli_main_supports_indent_without_changing_content(
    capsys,
) -> None:
    compact_exit = main([])
    compact = capsys.readouterr()
    indented_exit = main(["--indent", "2"])
    indented = capsys.readouterr()

    assert compact_exit == 0
    assert indented_exit == 0
    assert compact.err == ""
    assert indented.err == ""
    assert not compact.out.startswith("{\n")
    assert indented.out.startswith("{\n")
    assert json.loads(compact.out) == json.loads(indented.out)


def test_lightgbm_dependency_smoke_cli_calls_smoke_helper_once_per_invocation(
    monkeypatch,
    capsys,
) -> None:
    calls = {"count": 0}

    def fake_smoke() -> dict[str, object]:
        calls["count"] += 1
        return {
            "package_name": "lightgbm",
            "installed": False,
            "message": "fake missing LightGBM for CLI test",
            "default_params": {"n_estimators": 7},
            "default_model_name": "lightgbm_regressor",
            "default_method": "lightgbm_regressor",
            "fitting_enabled": False,
        }

    monkeypatch.setattr(cli, "run_lightgbm_dependency_smoke", fake_smoke)

    exit_code = main(["--indent", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert calls == {"count": 1}
    assert payload["message"] == "fake missing LightGBM for CLI test"
    assert payload["fitting_enabled"] is False


def test_lightgbm_dependency_smoke_cli_output_excludes_forbidden_keys(capsys) -> None:
    exit_code = main([])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert FORBIDDEN_OUTPUT_KEYS.isdisjoint(_all_dict_keys(payload))


def test_lightgbm_dependency_smoke_cli_does_not_need_real_lightgbm(monkeypatch, capsys) -> None:
    def fake_smoke() -> dict[str, object]:
        return {
            "package_name": "lightgbm",
            "installed": False,
            "message": "optional package not installed",
            "default_params": {},
            "default_model_name": "lightgbm_regressor",
            "default_method": "lightgbm_regressor",
            "fitting_enabled": False,
        }

    monkeypatch.setattr(cli, "run_lightgbm_dependency_smoke", fake_smoke)

    exit_code = main([])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["installed"] is False
    assert payload["fitting_enabled"] is False
    assert FORBIDDEN_OUTPUT_KEYS.isdisjoint(_all_dict_keys(payload))


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
