import json
import os
import subprocess
import sys
from pathlib import Path

from abc_quant.cli.modeling_smoke import main
from abc_quant.pipeline.contracts import MODELING_SMOKE_SUMMARY_KEYS
from abc_quant.pipeline.modeling import run_baseline_modeling_smoke


def test_modeling_smoke_cli_module_prints_deterministic_json() -> None:
    first = _run_module()
    second = _run_module()

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stderr == ""
    assert second.stderr == ""
    assert first.stdout == second.stdout
    assert json.loads(first.stdout) == _json_round_trip(run_baseline_modeling_smoke())


def test_modeling_smoke_cli_main_supports_indent_and_summary_contract(capsys) -> None:
    exit_code = main(["--indent", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.startswith("{\n")
    assert set(payload) == MODELING_SMOKE_SUMMARY_KEYS
    assert payload["split_counts"] == {"train": 8, "validation": 6, "test": 10}
    assert payload["baseline_method"] == "mean"
    assert set(payload["evaluation"]) == {"train", "validation", "test"}


def test_modeling_smoke_cli_custom_split_arguments_change_split_counts(capsys) -> None:
    exit_code = main(
        [
            "--train-end",
            "2026-01-08",
            "--validation-end",
            "2026-01-13",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["split_counts"] == {"train": 10, "validation": 6, "test": 8}
    assert payload["training_label_count"] == 10


def test_modeling_smoke_cli_method_argument_selects_median(capsys) -> None:
    exit_code = main(["--method", "median"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    expected = _json_round_trip(run_baseline_modeling_smoke(method="median"))
    assert exit_code == 0
    assert captured.err == ""
    assert payload == expected
    assert payload["baseline_method"] == "median"


def test_modeling_smoke_cli_invalid_method_is_rejected(capsys) -> None:
    exit_code = main(["--method", "mode"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "invalid choice" in captured.err
    assert "mode" in captured.err


def test_modeling_smoke_cli_invalid_boundaries_return_error(capsys) -> None:
    exit_code = main(
        [
            "--train-end",
            "2026-01-12",
            "--validation-end",
            "2026-01-07",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "error:" in captured.err
    assert "boundaries must be increasing" in captured.err


def test_modeling_smoke_cli_output_contains_only_diagnostic_summary_keys(capsys) -> None:
    exit_code = main([])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    forbidden_keys = {
        "signals",
        "trading_signals",
        "positions",
        "portfolio",
        "portfolio_values",
        "allocations",
        "equity_curve",
        "performance_curve",
        "backtest",
        "backtest_results",
        "simulation",
        "simulation_results",
    }

    assert exit_code == 0
    assert set(payload) == MODELING_SMOKE_SUMMARY_KEYS
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
        [sys.executable, "-m", "abc_quant.cli.modeling_smoke", *args],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )


def _json_round_trip(value: object) -> object:
    return json.loads(json.dumps(value, sort_keys=True))


def _all_dict_keys(value: object) -> set[str]:
    if not isinstance(value, dict):
        return set()

    keys = {str(key) for key in value}
    nested_keys: set[str] = set()
    for nested in value.values():
        nested_keys.update(_all_dict_keys(nested))
    return keys | nested_keys
