import json
import os
import subprocess
import sys
from pathlib import Path

from abc_quant.cli.model_comparison_smoke import main
from abc_quant.pipeline.contracts import MODEL_COMPARISON_SMOKE_SUMMARY_KEYS
from abc_quant.pipeline.model_comparison import run_model_comparison_smoke


def test_model_comparison_smoke_cli_module_prints_deterministic_json() -> None:
    first = _run_module()
    second = _run_module()

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stderr == ""
    assert second.stderr == ""
    assert first.stdout == second.stdout
    assert json.loads(first.stdout) == _json_round_trip(run_model_comparison_smoke())


def test_model_comparison_smoke_cli_main_supports_indent_and_summary_contract(
    capsys,
) -> None:
    exit_code = main(["--indent", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.startswith("{\n")
    assert list(payload) == sorted(MODEL_COMPARISON_SMOKE_SUMMARY_KEYS)
    assert set(payload) == MODEL_COMPARISON_SMOKE_SUMMARY_KEYS
    assert payload == _json_round_trip(run_model_comparison_smoke())


def test_model_comparison_smoke_cli_custom_split_arguments_change_split_counts(
    capsys,
) -> None:
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
    expected = _json_round_trip(
        run_model_comparison_smoke(
            train_end="2026-01-08",
            validation_end="2026-01-13",
        )
    )
    assert exit_code == 0
    assert captured.err == ""
    assert payload == expected
    assert payload["split_counts"] == {"train": 4, "validation": 6, "test": 2}


def test_model_comparison_smoke_cli_baseline_method_median_passes_through(
    capsys,
) -> None:
    exit_code = main(["--baseline-method", "median"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    expected = _json_round_trip(run_model_comparison_smoke(baseline_method="median"))
    assert exit_code == 0
    assert captured.err == ""
    assert payload == expected
    assert payload["reference_model"] == {
        "model_name": "constant_baseline",
        "method": "median",
    }


def test_model_comparison_smoke_cli_invalid_boundaries_return_error(capsys) -> None:
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


def test_model_comparison_smoke_cli_output_contains_only_diagnostic_summary_keys(
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
        "model_selection",
        "strategy",
        "signal",
        "signals",
        "trading_signals",
        "allocation",
        "allocations",
        "performance_curve",
        "equity_curve",
        "order",
        "orders",
        "position",
        "positions",
        "simulation",
        "simulation_results",
    }

    assert exit_code == 0
    assert set(payload) == MODEL_COMPARISON_SMOKE_SUMMARY_KEYS
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
        [sys.executable, "-m", "abc_quant.cli.model_comparison_smoke", *args],
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
