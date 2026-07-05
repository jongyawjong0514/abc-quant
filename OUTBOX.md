# OUTBOX

## 2026-07-05 Closed-Loop Task 044 - Optional LightGBM Dependency Guard

## 修改檔案
- `src/abc_quant/models/lightgbm.py`: added optional LightGBM dependency status, required import helper, and deterministic regressor parameter contract.
- `src/abc_quant/models/__init__.py`: exported the new LightGBM dataclasses and helper functions.
- `tests/test_models_lightgbm.py`: added dependency-detection, optional import, defaults, invalid-parameter, and frozen-dataclass tests without requiring the real package.
- `docs/modeling.md`: documented the optional LightGBM guard and parameter boundary.
- `README.md`: documented the LightGBM optional dependency contract.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 044 progress and completion evidence.
- `INBOX.md`: reset the active Task 044 block to the commented empty template before PR handoff.

## 實作摘要
- Added frozen `LightGBMDependencyStatus`.
- Added frozen `LightGBMRegressorParams` with deterministic conservative defaults.
- Added `check_lightgbm_dependency()` using standard-library `importlib.util.find_spec(...)` without importing `lightgbm`.
- Added `require_lightgbm()` to return the imported optional module when available or raise a clear `ImportError`.
- Added `make_default_lightgbm_regressor_params()`.
- Validated objective text, estimator count, learning rate, leaf count, min data in leaf, feature/bagging fractions, bagging frequency, random state, and verbosity.
- Kept `lightgbm` out of mandatory project dependencies.
- Did not fit a model, search parameters, select models, change pipeline/CLI outputs, create strategy signals, define allocation logic, build performance curves, or run simulation engines.

## 測試方式
- `python -m pytest tests\test_models_lightgbm.py`
- `python -m pytest tests\test_models_lightgbm.py tests\test_models_linear.py tests\test_models_baseline.py tests\test_models_predictions.py tests\test_models_comparison.py tests\test_models_evaluation.py tests\test_models_dataset.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI.

## 測試結果
- Focused LightGBM tests: 23 passed in 1.06s.
- Related model tests: 77 passed in 1.63s.
- `pytest`: 335 passed in 25.97s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only prepares optional dependency detection and parameter validation. It does not add a LightGBM estimator, fit any model, add mandatory dependencies, run parameter search, or change diagnostics outputs.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 043 - Model Comparison Smoke Console Script

## 修改檔案
- `pyproject.toml`: added the `abc-quant-model-comparison-smoke` console script.
- `tests/test_cli_entrypoints.py`: added pyproject parsing, target import, resolved-function JSON, and median baseline tests for the model-comparison script.
- `docs/modeling.md`: documented the packaged model-comparison smoke console script.
- `README.md`: documented the installed console-script command.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 043 progress and completion evidence.
- `INBOX.md`: reset the active Task 043 block to the commented empty template before PR handoff.

## 實作摘要
- Added `abc-quant-model-comparison-smoke = "abc_quant.cli.model_comparison_smoke:main"`.
- Kept `python -m abc_quant.cli.model_comparison_smoke` unchanged.
- Extended `tests/test_cli_entrypoints.py` to parse `pyproject.toml` with `tomllib` and verify all existing script entries plus the new model-comparison entry.
- Verified the configured target imports and resolves to `abc_quant.cli.model_comparison_smoke.main`.
- Verified the resolved function emits valid JSON with `--indent 2`.
- Verified the resolved function supports `--baseline-method median`.
- No model-comparison calculation, summary key, split default, baseline-method choice, CLI argument semantic, model selection, ranking, strategy signal, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_cli_entrypoints.py tests\test_cli_model_comparison_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` should be attempted for local parity with CI.

## 測試結果
- Focused entrypoint/model-comparison CLI tests: 22 passed in 4.33s.
- `pytest`: 312 passed in 25.67s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds a packaged console-script alias for the existing CLI. It does not add new diagnostics, model selection, ranking, or strategy/backtest behavior.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 042 - Model Comparison Smoke CLI

## 修改檔案
- `src/abc_quant/cli/model_comparison_smoke.py`: added a module-executable CLI wrapper around `run_model_comparison_smoke(...)`.
- `tests/test_cli_model_comparison_smoke.py`: added module invocation, deterministic output, custom split, median baseline method, invalid-boundary, and key-contract tests.
- `docs/modeling.md`: documented the model-comparison smoke CLI.
- `README.md`: documented the module command and supported arguments.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 042 progress and completion evidence.
- `INBOX.md`: reset the active Task 042 block to the commented empty template before PR handoff.

## 實作摘要
- Added `python -m abc_quant.cli.model_comparison_smoke`.
- Added `main(argv=None) -> int` with the same stdout/stderr wrapper pattern as existing smoke CLIs.
- Supported `--train-end`, `--validation-end`, `--baseline-method mean|median`, and `--indent`.
- Successful runs write sorted deterministic JSON to stdout and return exit code 0.
- Invalid temporal boundaries return exit code 1 and write a concise `error:` message to stderr.
- `--baseline-method median` passes through to the existing constant-baseline reference method.
- The CLI remains a thin wrapper and does not change model-comparison calculations, summary keys, split defaults, existing smoke outputs, model selection, ranking, strategy signals, allocation logic, performance curves, or simulation engines.

## 測試方式
- `python -m abc_quant.cli.model_comparison_smoke --baseline-method median --indent 2`
- `python -m pytest tests\test_cli_model_comparison_smoke.py tests\test_pipeline_model_comparison.py tests\test_pipeline_contracts.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Module smoke execution: passed and printed sorted deterministic JSON.
- Focused CLI/model-comparison/contract tests: 109 passed in 10.59s.
- `pytest`: 308 passed in 25.05s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds the module CLI. It does not add a packaged console-script alias, choose a model, rank models, or add strategy/backtest behavior.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 041 - Model Comparison Smoke Summary Validator

## 修改檔案
- `src/abc_quant/pipeline/contracts.py`: added model comparison smoke summary constants and `validate_model_comparison_smoke_summary(...)`.
- `src/abc_quant/pipeline/model_comparison.py`: validates the model-comparison summary before returning it.
- `src/abc_quant/pipeline/__init__.py`: exported the new constants and validator.
- `tests/test_pipeline_contracts.py`: added valid and invalid model-comparison summary shape tests.
- `tests/test_pipeline_model_comparison.py`: switched model-comparison smoke tests to shared constants and validator.
- `docs/modeling.md`: documented the model-comparison smoke summary contract validator.
- `README.md`: documented the return-time validation boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 041 progress and completion evidence.
- `INBOX.md`: reset the active Task 041 block to the commented empty template before PR handoff.

## 實作摘要
- Added `MODEL_COMPARISON_SMOKE_SUMMARY_KEYS`.
- Added `MODEL_COMPARISON_SMOKE_SPLITS`.
- Added `MODEL_COMPARISON_SMOKE_MODEL_KEYS`.
- Added `MODEL_COMPARISON_SMOKE_COMPARISON_KEYS`.
- Added `MODEL_COMPARISON_SMOKE_SPLIT_COMPARISON_KEYS`.
- Added `validate_model_comparison_smoke_summary(summary)`.
- The validator returns the original summary object unchanged when valid.
- The validator rejects non-dict summaries, missing/unknown top-level keys, malformed reference/candidate model metadata, malformed split count mappings, malformed dropped label counts, malformed reference/candidate evaluations, malformed comparison blocks, and missing/unknown per-split comparison keys.
- The validator checks reference/candidate evaluation split metrics against existing `EVALUATION_METRIC_KEYS`.
- `run_model_comparison_smoke(...)` now validates the summary before returning.
- Default model-comparison smoke output values remain unchanged.
- No winner, ranking, decision, model selection, strategy signal, allocation logic, performance curve, order, position, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_model_comparison.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused contract/model-comparison tests: 103 passed in 7.69s.
- `pytest`: 302 passed in 21.57s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only hardens the model-comparison smoke summary shape. It does not add a CLI, choose a model, or add strategy/backtest behavior.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 040 - Baseline Versus OLS Comparison Smoke

## 修改檔案
- `src/abc_quant/pipeline/model_comparison.py`: added `run_model_comparison_smoke(...)` and local helpers for aligned baseline-vs-OLS diagnostics.
- `src/abc_quant/pipeline/__init__.py`: exported `run_model_comparison_smoke`.
- `tests/test_pipeline_model_comparison.py`: added deterministic JSON, metadata, split-count alignment, direct comparison parity, and forbidden-key tests.
- `docs/modeling.md`: documented the model comparison smoke diagnostic and safety boundary.
- `README.md`: documented the model comparison smoke diagnostic.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 040 progress and completion evidence.
- `INBOX.md`: reset the active Task 040 block to the commented empty template before PR handoff.

## 實作摘要
- Built deterministic comparison diagnostics from the existing smoke fixture.
- Wired `FeatureMatrix`, `TemporalSplit`, train-only scaler fit/transform, and `SupervisedSplitDataset`.
- Fit the constant baseline from training labels only.
- Fit OLS from the supervised training split only.
- Restricted baseline predictions to the same supervised split indices used by OLS after missing-label rows are dropped.
- Evaluated reference and candidate predictions with `evaluate_prediction_bundle(...)`.
- Compared the resulting evaluations with `compare_prediction_evaluations(...)`.
- Returned JSON-friendly `row_count`, `feature_columns`, `label_column`, model metadata, split counts, dropped label counts, reference evaluation, candidate evaluation, and raw comparison deltas.
- No winner, ranking, decision, selected model, model selection, strategy signal, allocation logic, performance curve, order, position, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_model_comparison.py tests\test_models_comparison.py tests\test_pipeline_linear_modeling.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused model-comparison/comparison/OLS-smoke tests: 22 passed in 2.02s.
- `pytest`: 268 passed in 19.62s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds in-memory smoke diagnostics for already-defined contracts. It does not choose a model, change existing smoke outputs, add CLI behavior, or add strategy/backtest behavior.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 039 - Prediction Evaluation Comparison Contract

## 修改檔案
- `src/abc_quant/models/comparison.py`: added frozen comparison dataclasses and `compare_prediction_evaluations(...)`.
- `src/abc_quant/models/__init__.py`: exported the comparison contract.
- `tests/test_models_comparison.py`: added deterministic delta, error-contract, no-decision, and frozen-dataclass tests.
- `docs/modeling.md`: documented the prediction evaluation comparison contract and safety boundary.
- `README.md`: documented the comparison helper in the model-output diagnostics section.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 039 progress and completion evidence.
- `INBOX.md`: reset the active Task 039 block to the commented empty template before PR handoff.

## 實作摘要
- Added `SplitEvaluationComparison` and `PredictionEvaluationComparison` as frozen dataclasses.
- Added `compare_prediction_evaluations(reference, candidate, reference_name="reference", candidate_name="candidate")`.
- The helper accepts only `SplitPredictionBundleEvaluationResult` inputs.
- Reference and candidate names are normalized as non-empty strings.
- Train, validation, and test splits must match on `row_count`, `non_missing_count`, and `missing_actual_count`.
- Each split records candidate-minus-reference deltas for `mae`, `rmse`, `mean_error`, and `prediction_mean`.
- Negative deltas remain raw numeric differences and are not converted into rankings, winners, or decisions.
- No model refit, prediction recomputation, model selection, parameter search, allocation logic, strategy signal output, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_models_comparison.py tests\test_models_evaluation.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused comparison/evaluation tests: 21 passed in 1.06s.
- `pytest`: 263 passed in 18.74s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task compares already-computed diagnostic evaluation objects only. It does not choose a model or modify any smoke summary output.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 038 - OLS Smoke Console Script Alias

## 修改檔案
- `pyproject.toml`: added the `abc-quant-linear-regression-smoke` project script pointing to `abc_quant.cli.linear_regression_smoke:main`.
- `tests/test_cli_entrypoints.py`: added linear-regression console-script metadata, import resolution, and callable JSON-output tests while preserving modeling/preprocessing/supervised script coverage.
- `docs/modeling.md`: documented the installed OLS smoke console-script command alongside `python -m`.
- `README.md`: documented the packaged OLS smoke console command.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 038 progress and completion evidence.
- `INBOX.md`: reset the active Task 038 block to the commented empty template before PR handoff.

## 實作摘要
- Added a package metadata console-script alias: `abc-quant-linear-regression-smoke`.
- Kept the script target exactly `abc_quant.cli.linear_regression_smoke:main`.
- Added `tomllib`-based tests for the linear-regression script entry in `pyproject.toml`.
- Verified the configured target imports and resolves to the existing linear-regression smoke `main` function.
- Verified the resolved function accepts `--indent 2`, returns `0`, and emits valid JSON.
- Existing linear-regression CLI tests and modeling/preprocessing/supervised console-script tests remain covered.
- No OLS calculation, summary key, split default, CLI argument semantic, estimator implementation, parameter search, model selection, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was changed.

## 測試方式
- `python -m pytest tests\test_cli_entrypoints.py tests\test_cli_linear_regression_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused entrypoint/OLS CLI tests: 17 passed in 3.99s.
- `pytest`: 251 passed in 18.58s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only exposes the existing OLS smoke CLI as an installed console script. It does not alter OLS diagnostics behavior or add strategy/backtest behavior.

## PR 狀態
- Branch pushed: `codex/task-038-ols-smoke-console-script`.
- Draft PR creation is blocked in this environment because the GitHub connector returned `token_revoked` and local `gh auth status` reports no logged-in GitHub hosts.
- PR creation URL from git push: `https://github.com/jongyawjong0514/abc-quant/pull/new/codex/task-038-ols-smoke-console-script`.

## 建議下一步
- Restore GitHub connector or run `gh auth login`, then open a draft PR from `codex/task-038-ols-smoke-console-script` to `main`.
- After the draft PR exists, have ChatGPT Pro review the pyproject script entry, entrypoint tests, and documentation wording.

## 2026-07-05 Closed-Loop Task 037 - OLS Smoke CLI

## 修改檔案
- `src/abc_quant/cli/linear_regression_smoke.py`: added the module-executable OLS smoke diagnostics CLI.
- `tests/test_cli_linear_regression_smoke.py`: added module execution, deterministic stdout JSON, indent, custom split, invalid boundary, summary-key, and forbidden-key tests.
- `docs/modeling.md`: documented `python -m abc_quant.cli.linear_regression_smoke`.
- `README.md`: documented the OLS smoke CLI.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 037 progress and completion evidence.
- `INBOX.md`: reset the active Task 037 block to the commented empty template before PR handoff.

## 實作摘要
- Added `main(argv=None) -> int` in `src/abc_quant/cli/linear_regression_smoke.py`.
- The CLI is a thin wrapper around `run_linear_regression_smoke(...)`.
- Supports `--train-end`, `--validation-end`, and `--indent`.
- Valid invocations write sorted deterministic JSON to stdout and return `0`.
- Invalid temporal boundaries return non-zero and write a concise `error:` message to stderr.
- Tests verify stdout JSON equals `run_linear_regression_smoke(...)`.
- Tests verify repeated module calls are deterministic.
- Tests verify custom split arguments alter `split_counts_after_label_drop` deterministically.
- Tests verify output contains only `LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS`.
- Existing modeling, preprocessing, and supervised CLI behavior remains unchanged.
- No OLS calculation change, summary key change, split default change, package script change, new estimator implementation, parameter search, model selection, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_cli_linear_regression_smoke.py tests\test_cli_modeling_smoke.py tests\test_cli_preprocessing_smoke.py tests\test_cli_supervised_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused OLS/modeling/preprocessing/supervised CLI tests: 22 passed in 11.55s.
- `pytest`: 248 passed in 21.97s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds a module-executable OLS smoke CLI. It does not add a packaged console-script alias, change OLS diagnostics, or add strategy/backtest behavior.

## 建議下一步
- Wait for GitHub Actions on the draft PR, then have ChatGPT Pro review the CLI wrapper, stdout/stderr behavior, custom split pass-through, and unchanged summary contract boundary.

## 2026-07-05 Closed-Loop Task 036 - OLS Smoke Summary Validator

## 修改檔案
- `src/abc_quant/pipeline/contracts.py`: added OLS smoke summary constants and `validate_linear_regression_smoke_summary(...)`.
- `src/abc_quant/pipeline/linear_modeling.py`: validates the OLS smoke summary before returning it.
- `src/abc_quant/pipeline/__init__.py`: exported the new OLS smoke constants and validator.
- `tests/test_pipeline_contracts.py`: added valid and invalid OLS smoke summary shape tests.
- `tests/test_pipeline_linear_modeling.py`: switched OLS smoke tests to shared constants and validator.
- `docs/modeling.md`: documented the OLS smoke summary contract validator.
- `README.md`: documented the centralized OLS smoke summary shape.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 036 progress and completion evidence.
- `INBOX.md`: reset the active Task 036 block to the commented empty template before PR handoff.

## 實作摘要
- Added `LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS`.
- Added `LINEAR_REGRESSION_SMOKE_SPLITS`.
- Added `LINEAR_REGRESSION_SMOKE_EVALUATION_KEYS` using the shared evaluation metric keys.
- Added `validate_linear_regression_smoke_summary(summary)`.
- The validator returns the original summary object unchanged when valid.
- The validator rejects non-dict summaries, missing/unknown top-level keys, non-dict split mappings, missing/unknown split mappings, non-dict evaluation blocks, missing/unknown evaluation splits, non-dict split metrics, and missing/unknown metric keys.
- The validator checks `split_counts_after_label_drop`, `dropped_label_counts`, `prediction_counts`, and `evaluation` against the train/validation/test split names.
- The validator checks `feature_columns` is a list and `coefficients` is a dict.
- `run_linear_regression_smoke(...)` now validates the summary before returning.
- Default OLS smoke output values remain unchanged.
- Existing modeling, preprocessing, and supervised smoke summary contracts remain unchanged.
- No new estimator implementation, parameter search, model selection, allocation logic, strategy signal output, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_linear_modeling.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused contract/OLS smoke tests: 69 passed in 5.15s.
- `pytest`: 243 passed in 16.37s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only hardens the OLS smoke diagnostics summary shape. It does not add an OLS smoke CLI, package script, model selection, or any strategy/backtest behavior.

## 建議下一步
- Wait for GitHub Actions on the draft PR, then have ChatGPT Pro review the shared constants, validator failure cases, OLS smoke return path, and unchanged output-value boundary.

## 2026-07-05 Closed-Loop Task 035 - Train-Only OLS Smoke Diagnostics

## 修改檔案
- `src/abc_quant/pipeline/linear_modeling.py`: added `run_linear_regression_smoke(...)`.
- `src/abc_quant/pipeline/__init__.py`: exported the new OLS smoke diagnostic helper.
- `tests/test_pipeline_linear_modeling.py`: added deterministic, JSON-serializable, direct OLS-result parity, direct evaluation parity, metadata preservation, and forbidden-key tests.
- `docs/modeling.md`: documented the OLS smoke diagnostics pipeline and safety boundaries.
- `README.md`: documented the deterministic OLS smoke diagnostics helper.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 035 progress and completion evidence.
- `INBOX.md`: reset the active Task 035 block to the commented empty template before PR handoff.

## 實作摘要
- Added `run_linear_regression_smoke(...)` using the existing deterministic smoke frame and feature-complete rows.
- Wired `FeatureMatrix`, `TemporalSplit`, train-only scaler fit/transform, `SupervisedSplitDataset`, `fit_linear_regression(...)`, and `evaluate_prediction_bundle(...)`.
- Returned a JSON-friendly summary with row count, feature columns, label column, model name, method, intercept, ordered coefficients, training row count, split counts after label drop, dropped label counts, prediction counts, and train/validation/test evaluation metrics.
- Kept OLS fitting behind the existing train-only estimator contract.
- Did not change existing smoke outputs, CLI behavior, package scripts, preprocessing, dataset, or linear model contracts.
- No new estimator implementation, parameter search, model selection, strategy signal output, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_linear_modeling.py`
- `python -m pytest tests\test_pipeline_linear_modeling.py tests\test_models_linear.py tests\test_pipeline_supervised.py tests\test_models_evaluation.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused OLS smoke tests: 5 passed in 4.21s.
- Related pipeline/model tests: 28 passed in 2.28s.
- `pytest`: 222 passed in 14.91s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds an in-memory diagnostics pipeline. It does not add a CLI for OLS smoke diagnostics, a summary contract validator, model selection, or any strategy/backtest behavior.

## 建議下一步
- Wait for GitHub Actions on the draft PR, then have ChatGPT Pro review summary shape, direct evaluator parity, train-only fitting path, and forbidden-output-key coverage.

## 2026-07-05 Closed-Loop Task 034 - Train-Only OLS Regression Contract

## 修改檔案
- `src/abc_quant/models/linear.py`: added `LinearRegressionResult` and `fit_linear_regression(...)`.
- `src/abc_quant/models/__init__.py`: exported the OLS result dataclass and fit function.
- `tests/test_models_linear.py`: added train-only fit, deterministic coefficient/prediction, holdout-label non-leakage, split-index, invalid-input, invalid-train-data, and copy-isolation tests.
- `docs/modeling.md`: documented the ordinary least-squares regression contract and safety boundaries.
- `README.md`: documented the train-only OLS model contract.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 034 progress and completion evidence.
- `INBOX.md`: reset the active Task 034 block to the commented empty template before PR handoff.

## 實作摘要
- Added a frozen `LinearRegressionResult` with `model_name`, `method`, `feature_columns`, `coefficients`, `intercept`, `training_row_count`, and `prediction_bundle`.
- Added `fit_linear_regression(dataset, fit_intercept=True, model_name="ordinary_least_squares")`.
- The fit path only uses `SupervisedSplitDataset.train_X` and `train_y`.
- Validation/test feature frames are used only for prediction; validation/test labels are not read.
- OLS coefficients are fit with `numpy.linalg.lstsq`; no sklearn or new dependency was added.
- Returned train/validation/test predictions are produced through `build_split_prediction_bundle(...)`.
- Invalid input type, empty train data, missing/non-finite training data, nonnumeric feature columns, index mismatch, and split column mismatch fail loudly.
- No parameter search, model selection, allocation logic, strategy signal output, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_models_linear.py`
- `python -m pytest tests\test_models_linear.py tests\test_models_dataset.py tests\test_models_predictions.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused OLS tests: 7 passed in 1.09s.
- Related model contract tests: 28 passed in 1.27s.
- `pytest`: 217 passed in 14.60s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task introduces only a minimal in-memory OLS estimator contract. It does not wire OLS into smoke CLIs, model selection, evaluation summaries, or training pipelines.

## 建議下一步
- Wait for GitHub Actions on the draft PR, then have ChatGPT Pro review train-only fitting, holdout-label non-leakage, prediction bundle metadata, and invalid-data behavior.

## 2026-07-05 Closed-Loop Task 033 - Supervised Smoke Console Script Alias

## 修改檔案
- `pyproject.toml`: added the `abc-quant-supervised-smoke` project script pointing to `abc_quant.cli.supervised_smoke:main`.
- `tests/test_cli_entrypoints.py`: added supervised console-script metadata, import resolution, and callable JSON-output tests while preserving modeling/preprocessing script coverage.
- `docs/modeling.md`: documented the installed supervised smoke console-script command alongside `python -m`.
- `README.md`: documented the packaged supervised smoke console command.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 033 progress and completion evidence.
- `INBOX.md`: reset the active Task 033 block to the commented empty template before PR handoff.

## 實作摘要
- Added a package metadata console-script alias: `abc-quant-supervised-smoke`.
- Kept the script target exactly `abc_quant.cli.supervised_smoke:main`.
- Added `tomllib`-based tests for the supervised script entry in `pyproject.toml`.
- Verified the configured target imports and resolves to the existing supervised `main` function.
- Verified the resolved function accepts `--indent 2`, returns `0`, and emits valid JSON.
- Existing modeling/preprocessing console-script tests and supervised CLI tests remain covered.
- No supervised calculation, summary key, split default, CLI argument semantic, estimator implementation, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was changed.

## 測試方式
- `python -m pytest tests\test_cli_entrypoints.py tests\test_cli_supervised_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused entrypoint/supervised CLI tests: 14 passed in 3.91s.
- `pytest`: 210 passed in 14.29s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only exposes the existing supervised smoke CLI as an installed console script. It does not add package-script aliases for future CLIs and does not alter smoke diagnostics behavior.

## 建議下一步
- Wait for GitHub Actions on the draft PR, then have ChatGPT Pro review the pyproject script entry, entrypoint tests, and documentation wording.

## 2026-07-05 Closed-Loop Task 032 - Supervised Dataset Smoke CLI

## 修改檔案
- `src/abc_quant/cli/supervised_smoke.py`: added the module-executable supervised dataset smoke CLI.
- `tests/test_cli_supervised_smoke.py`: added module execution, deterministic stdout JSON, indent, custom split, invalid boundary, and forbidden-key tests.
- `docs/modeling.md`: documented `python -m abc_quant.cli.supervised_smoke`.
- `README.md`: documented the supervised dataset smoke CLI.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 032 progress and completion evidence.
- `INBOX.md`: reset the active Task 032 block to the commented empty template before PR handoff.

## 實作摘要
- Added `main(argv=None) -> int` in `src/abc_quant/cli/supervised_smoke.py`.
- The CLI is a thin wrapper around `run_supervised_dataset_smoke(...)`.
- Supports `--train-end`, `--validation-end`, and `--indent`.
- Valid invocations write sorted deterministic JSON to stdout and return `0`.
- Invalid temporal boundaries return non-zero and write a concise `error:` message to stderr.
- Existing modeling and preprocessing CLI behavior remains unchanged.
- No estimator implementation, supervised dataset calculation change, summary key change, split default change, package script change, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_cli_supervised_smoke.py tests\test_cli_preprocessing_smoke.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused supervised/modeling/preprocessing CLI tests: 17 passed in 8.87s.
- `pytest`: 207 passed in 13.97s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only adds a module-executable CLI. It does not add a packaged console-script alias or train estimators.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-05 Closed-Loop Task 031 - Supervised Dataset Smoke Summary Validator

## 修改檔案
- `src/abc_quant/pipeline/contracts.py`: added supervised dataset smoke summary constants and `validate_supervised_dataset_smoke_summary(...)`.
- `src/abc_quant/pipeline/supervised.py`: validates the summary before returning it.
- `src/abc_quant/pipeline/__init__.py`: exported the new constants and validator.
- `tests/test_pipeline_supervised.py`: switched supervised smoke tests to shared constants and validator.
- `tests/test_pipeline_contracts.py`: added valid and invalid supervised summary shape tests.
- `docs/modeling.md`: documented the supervised dataset smoke summary contract validator.
- `README.md`: documented the shared validator under modeling preparation.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 031 progress and completion evidence.
- `INBOX.md`: reset the active Task 031 block to the commented empty template before PR handoff.

## 實作摘要
- Added `SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS`.
- Added `SUPERVISED_DATASET_SMOKE_SPLITS`.
- Added `SUPERVISED_DATASET_SMOKE_SPLIT_SHAPE_KEYS`.
- Added `validate_supervised_dataset_smoke_summary(summary)`.
- The validator returns the original summary object unchanged when valid.
- The validator rejects non-dict summaries, missing/unknown top-level keys, non-dict split count mappings, missing/unknown split keys, non-dict split shape, missing/unknown split shapes, malformed split shape entries, and missing/unknown `rows` / `columns` shape keys.
- `run_supervised_dataset_smoke(...)` now validates the summary before returning.
- Default supervised dataset smoke output values remain unchanged.
- Existing modeling and preprocessing smoke summary contracts remain unchanged.
- No estimator implementation, existing smoke output value change, CLI behavior change, package script change, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_supervised.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused contract/supervised tests: 50 passed in 3.72s.
- `pytest`: 202 passed in 11.43s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only hardens the supervised dataset smoke summary shape. It does not add a CLI or train estimators.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-05 Closed-Loop Task 030 - Supervised Dataset Smoke Diagnostics

## 修改檔案
- `src/abc_quant/pipeline/supervised.py`: added `run_supervised_dataset_smoke(...)` and default split constants.
- `src/abc_quant/pipeline/__init__.py`: exported `run_supervised_dataset_smoke`.
- `tests/test_pipeline_supervised.py`: added deterministic, JSON-serializable, direct dataset parity, train non-empty, feature/label preservation, label-drop count, and forbidden-key tests.
- `docs/modeling.md`: documented supervised dataset smoke diagnostics and safety boundaries.
- `README.md`: documented the supervised dataset smoke diagnostic under modeling preparation.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 030 progress and completion evidence.
- `INBOX.md`: reset the active Task 030 block to the commented empty template before PR handoff.

## 實作摘要
- Added a deterministic supervised dataset smoke path that uses feature-complete synthetic smoke rows.
- The path wires together `build_feature_matrix(...)`, `build_temporal_split(...)`, `fit_standard_scaler(...)`, `transform_with_standard_scaler(...)`, and `build_supervised_split_dataset(..., drop_missing_labels=True)`.
- The returned summary is JSON-friendly and includes `row_count`, `feature_columns`, `label_column`, `split_counts_before_label_drop`, `split_counts_after_label_drop`, `dropped_label_counts`, and `split_shape`.
- Split counts before label drop are derived from standardized split feature frames.
- Split counts after label drop and dropped label counts are derived from the direct `SupervisedSplitDataset`.
- No estimator implementation, existing smoke output change, CLI behavior change, package script change, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_supervised.py`
- `python -m pytest tests\test_pipeline_supervised.py tests\test_models_dataset.py tests\test_pipeline_preprocessing.py tests\test_preprocessing_scaling.py tests\test_features_matrix.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused supervised pipeline tests: 7 passed in 1.44s.
- Related supervised/dataset/preprocessing tests: 36 passed in 2.35s.
- `pytest`: 183 passed in 10.46s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only adds deterministic in-memory supervised dataset diagnostics. It does not train estimators or expose a new CLI.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-05 Closed-Loop Task 029 - Supervised Split Dataset Contract

## 修改檔案
- `src/abc_quant/models/dataset.py`: added `SupervisedSplitDataset` and `build_supervised_split_dataset(...)`.
- `src/abc_quant/models/__init__.py`: exported the supervised dataset dataclass and builder.
- `tests/test_models_dataset.py`: added construction, label alignment, missing-label filtering, no-drop error, empty train, copy isolation, type, index, and column-order tests.
- `docs/modeling.md`: documented the supervised split dataset contract and safety rules.
- `README.md`: documented the supervised split dataset contract in the modeling preparation section.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 029 progress and completion evidence.
- `INBOX.md`: reset the active Task 029 block to the commented empty template before PR handoff.

## 實作摘要
- Added a frozen `SupervisedSplitDataset` dataclass with `feature_columns`, `label_column`, train/validation/test feature and label splits, and `dropped_label_counts`.
- Added `build_supervised_split_dataset(feature_matrix, standardized_features, drop_missing_labels=True)`.
- The builder requires `FeatureMatrix` and `StandardizedFeatureMatrix` inputs and validates standardized split indices/columns against the fitted scaler metadata.
- Labels are aligned from `FeatureMatrix.y` using the split indices stored in `standardized_features.fitted`.
- Missing labels are dropped independently per split by default and counted under train/validation/test.
- `drop_missing_labels=False` rejects missing labels with a `ValueError`.
- Empty train data after label filtering is rejected.
- Returned feature frames and label Series are copied to avoid later caller mutation changing the dataset.
- No estimator implementation, smoke output change, CLI behavior change, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_models_dataset.py`
- `python -m pytest tests\test_models_dataset.py tests\test_preprocessing_scaling.py tests\test_features_matrix.py tests\test_pipeline_preprocessing.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused dataset tests: 8 passed in 1.19s.
- Related feature/preprocessing tests: 29 passed in 1.85s.
- `pytest`: 176 passed in 10.07s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only prepares in-memory supervised split inputs. It does not train estimators or wire the dataset into smoke pipeline outputs.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 028 - Preprocessing Smoke Console Script Alias

## 修改檔案
- `pyproject.toml`: added the `abc-quant-preprocessing-smoke` project script pointing to `abc_quant.cli.preprocessing_smoke:main`.
- `tests/test_cli_entrypoints.py`: added preprocessing console-script metadata, import resolution, and callable JSON-output tests while keeping existing modeling console-script coverage.
- `docs/modeling.md`: documented the installed preprocessing console-script command alongside `python -m`.
- `README.md`: documented the packaged preprocessing console command.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 028 progress and completion evidence.
- `INBOX.md`: reset the active Task 028 block to the commented empty template before PR handoff.

## 實作摘要
- Added a package metadata console-script alias: `abc-quant-preprocessing-smoke`.
- The entry point target is exactly `abc_quant.cli.preprocessing_smoke:main`.
- `python -m abc_quant.cli.preprocessing_smoke` remains unchanged.
- Entry-point tests parse `pyproject.toml` with `tomllib`, import the configured target, confirm it resolves to the preprocessing `main`, and call the resolved function with `--indent 2` to verify valid JSON.
- Existing modeling console-script tests and preprocessing CLI tests remain covered.
- No preprocessing calculation, summary key, split default, CLI argument semantic, estimator implementation, file output, outside data access, live account connectivity, parameter search, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_cli_entrypoints.py tests\test_cli_preprocessing_smoke.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- pyproject script-map verification with `tomllib`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused entrypoint/CLI tests: 18 passed in 6.49s.
- `pytest`: 168 passed in 9.64s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- pyproject script-map verification confirmed:
  - `abc-quant-modeling-smoke = abc_quant.cli.modeling_smoke:main`
  - `abc-quant-preprocessing-smoke = abc_quant.cli.preprocessing_smoke:main`
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only adds package-level discoverability for the existing preprocessing CLI. It does not install the package globally or change CLI behavior.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 027 - Preprocessing Smoke Diagnostics CLI

## 修改檔案
- `src/abc_quant/cli/preprocessing_smoke.py`: added the module entry point for deterministic preprocessing smoke diagnostics.
- `tests/test_cli_preprocessing_smoke.py`: added subprocess and direct-main tests for deterministic JSON, sorted keys, split arguments, error handling, and diagnostic-only keys.
- `docs/modeling.md`: documented preprocessing smoke CLI usage, arguments, stdout/stderr behavior, and diagnostic-only boundary.
- `README.md`: documented the preprocessing smoke CLI command and arguments.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 027 progress and completion evidence.
- `INBOX.md`: reset the active Task 027 block to the commented empty template before PR handoff.

## 實作摘要
- Added `python -m abc_quant.cli.preprocessing_smoke` as a thin wrapper around `run_preprocessing_smoke(...)`.
- The CLI supports `--train-end`, `--validation-end`, and `--indent`.
- Successful invocations write sorted deterministic JSON to stdout and return exit code 0.
- Invalid temporal boundaries are caught, return non-zero, and write a concise `error: ...` message to stderr.
- Tests verify stdout JSON equals `run_preprocessing_smoke(...)`, repeated module calls are deterministic, custom split arguments alter `split_counts`, and output keys match `PREPROCESSING_SMOKE_SUMMARY_KEYS`.
- No preprocessing calculation, summary key, split default, modeling smoke CLI behavior, estimator implementation, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was changed.

## 測試方式
- `python -m pytest tests\test_cli_preprocessing_smoke.py tests\test_pipeline_preprocessing.py`
- `python -m pytest tests\test_cli_preprocessing_smoke.py tests\test_cli_modeling_smoke.py tests\test_pipeline_preprocessing.py tests\test_pipeline_contracts.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `$env:PYTHONPATH='src'; python -m abc_quant.cli.preprocessing_smoke --train-end 2026-01-08 --validation-end 2026-01-13 --indent 2`
- `.venv\Scripts\python.exe -m abc_quant.cli.preprocessing_smoke --indent 2`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused CLI/preprocessing tests: 10 passed in 4.19s.
- Related CLI/contract/preprocessing tests: 41 passed in 8.18s.
- `pytest`: 165 passed in 10.22s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Module smoke execution passed with `PYTHONPATH=src` and `.venv` Python.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only exposes preprocessing smoke diagnostics through a module CLI. It does not add a packaged console-script alias and does not wire scaling into model training.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 026 - Preprocessing Smoke Summary Validator

## 修改檔案
- `src/abc_quant/pipeline/contracts.py`: added preprocessing smoke summary key constants, split constants, split-shape constants, and `validate_preprocessing_smoke_summary(...)`.
- `src/abc_quant/pipeline/preprocessing.py`: validates the preprocessing smoke summary before returning it.
- `src/abc_quant/pipeline/__init__.py`: exports preprocessing smoke summary constants and validator.
- `tests/test_pipeline_preprocessing.py`: uses shared preprocessing summary constants and validates the smoke summary contract.
- `tests/test_pipeline_contracts.py`: added focused invalid-shape coverage for preprocessing smoke summaries.
- `docs/modeling.md`: documented the preprocessing smoke summary contract and validator.
- `README.md`: documented the shared preprocessing smoke summary validator.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 026 progress and completion evidence.
- `INBOX.md`: reset the active Task 026 block to the commented empty template before PR handoff.

## 實作摘要
- Centralized the preprocessing smoke summary shape in `abc_quant.pipeline.contracts`.
- Added `PREPROCESSING_SMOKE_SUMMARY_KEYS`, `PREPROCESSING_SMOKE_SPLITS`, and `PREPROCESSING_SMOKE_SPLIT_SHAPE_KEYS`.
- Added `validate_preprocessing_smoke_summary(...)`, which returns the original summary unchanged when valid.
- The validator rejects non-dict summaries, top-level key drift, invalid `split_counts`, invalid `split_shape`, and per-split shape entries that are not exactly `rows` / `columns`.
- `run_preprocessing_smoke(...)` now validates its summary before returning.
- The default preprocessing smoke diagnostic values remained unchanged.
- No modeling smoke summary contract, CLI argument, estimator implementation, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_preprocessing.py`
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_preprocessing.py tests\test_pipeline_modeling.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused contract/preprocessing tests: 29 passed in 2.53s.
- Related pipeline/CLI tests: 42 passed in 5.66s.
- `pytest`: 160 passed in 6.82s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only hardens the preprocessing smoke diagnostics summary shape. It does not add a preprocessing CLI or wire scaling into model training.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 025 - Preprocessing Smoke Diagnostics

## 修改檔案
- `src/abc_quant/pipeline/preprocessing.py`: added `run_preprocessing_smoke(...)` for deterministic train-only scaling diagnostics.
- `src/abc_quant/pipeline/__init__.py`: exported `run_preprocessing_smoke`.
- `tests/test_pipeline_preprocessing.py`: added deterministic summary, JSON serialization, train-only fitted parameter, standardized train mean/std, and split-shape preservation tests.
- `docs/modeling.md`: documented the preprocessing smoke diagnostic path and safety rules.
- `README.md`: documented the preprocessing smoke diagnostic alongside modeling preparation.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 025 progress and completion evidence.
- `INBOX.md`: reset the active Task 025 block to the commented empty template before PR handoff.

## 實作摘要
- Added a deterministic preprocessing smoke path that uses `build_smoke_frame(...)`, `build_feature_matrix(...)`, `build_temporal_split(...)`, `fit_standard_scaler(...)`, and `transform_with_standard_scaler(...)`.
- The smoke path uses feature-complete synthetic fixture rows because the existing rolling smoke features intentionally contain missing early rows for each ticker.
- The returned plain dict is JSON-serializable and includes `row_count`, `feature_columns`, `split_counts`, `fitted_means`, `fitted_stds`, `train_mean_after_scaling`, `train_std_after_scaling`, and `split_shape`.
- Tests compare fitted means/stds against direct train-split calculations, verify train scaled mean/std, and confirm validation/test shape preservation.
- The new path is separate from the existing modeling smoke CLI and modeling smoke summary contract.
- No estimator implementation, parameter search, allocation logic, performance curve, simulation engine, outside data access, live account connectivity, or modeling smoke output change was added.

## 測試方式
- `python -m pytest tests\test_pipeline_preprocessing.py`
- `python -m pytest tests\test_pipeline_preprocessing.py tests\test_preprocessing_scaling.py tests\test_pipeline_modeling.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused preprocessing pipeline tests: 5 passed in 1.29s.
- Related preprocessing/modeling tests: 27 passed in 4.70s.
- `pytest`: 147 passed in 6.44s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This diagnostic does not expose a CLI and does not wire scaling into model training or the modeling smoke summary.

## 下一步建議
- Run full validation after final tracking updates, then open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 024 - Train-Only Feature Standardization

## 修改檔案
- `src/abc_quant/preprocessing/__init__.py`: added preprocessing package exports.
- `src/abc_quant/preprocessing/scaling.py`: added `StandardScalerFit`, `StandardizedFeatureMatrix`, `fit_standard_scaler(...)`, and `transform_with_standard_scaler(...)`.
- `tests/test_preprocessing_scaling.py`: added leakage-focused scaler tests for train-only fit, transform preservation, non-leakage, and invalid inputs.
- `docs/modeling.md`: documented the train-only standardization contract and safety rules.
- `README.md`: documented the preprocessing contract in the modeling preparation section.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 024 progress and completion evidence.
- `INBOX.md`: reset the active Task 024 block to the commented empty template before PR handoff.

## 實作摘要
- Added a frozen `StandardScalerFit` dataclass with feature columns, means, stds, and train/validation/test split indices.
- Added a frozen `StandardizedFeatureMatrix` dataclass with train, validation, test, and fitted fields.
- `fit_standard_scaler(...)` validates a `FeatureMatrix` and `TemporalSplit`, defaults to `feature_matrix.feature_columns`, and fits means/stds using only `temporal_split.train_index`.
- `transform_with_standard_scaler(...)` applies the fitted scaler to train, validation, and test rows without changing row order, row counts, split indices, or feature column order.
- Validation/test extreme values do not affect fitted means/stds.
- The contract rejects empty train splits, unknown feature columns, duplicate feature columns, nonnumeric columns, missing training feature values, zero-variance training features, out-of-range split positions, and transform split mismatches.
- No sklearn dependency, estimator implementation, parameter search, metadata/label mutation, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_preprocessing_scaling.py`
- `python -m pytest tests\test_preprocessing_scaling.py tests\test_features_matrix.py tests\test_validation_temporal.py tests\test_pipeline_modeling.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused preprocessing tests: 9 passed in 1.09s.
- Related feature/split/pipeline tests: 30 passed in 1.82s.
- `pytest`: 142 passed in 5.88s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task adds only the preprocessing contract. It does not wire scaling into the modeling smoke pipeline or any estimator.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 023 - Modeling Smoke Bundle Evaluation Wiring

## 修改檔案
- `src/abc_quant/pipeline/modeling.py`: changed the internal baseline evaluation path to build a constant-baseline prediction bundle and evaluate it with `evaluate_prediction_bundle(...)`.
- `tests/test_pipeline_modeling.py`: added direct bundle-evaluator parity coverage for the modeling smoke summary evaluation metrics.
- `docs/modeling.md`: documented that the modeling smoke pipeline now uses the split prediction bundle evaluation path internally.
- `README.md`: documented the internal bundle evaluation wiring while noting the public summary shape is unchanged.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 023 progress and completion evidence.
- `INBOX.md`: reset the active Task 023 block to the commented empty template before PR handoff.

## 實作摘要
- `run_baseline_modeling_smoke(...)` still builds the deterministic smoke frame, feature matrix, temporal split, and constant baseline exactly as before.
- After fitting the baseline, it now calls `build_constant_baseline_prediction_bundle(...)` and `evaluate_prediction_bundle(...)`.
- The returned summary remains validated by `validate_modeling_smoke_summary(...)`.
- The top-level summary keys, nested evaluation metric keys, default method, fitted values, split counts, metric formulas, CLI arguments, and console-script behavior were not changed.
- Tests compare pipeline evaluation metrics against direct `evaluate_prediction_bundle(...)` output for the same bundle.

## 測試方式
- `python -m pytest tests\test_pipeline_modeling.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused pipeline/CLI tests: 13 passed in 4.12s.
- `pytest`: 133 passed in 5.97s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only changes internal modeling smoke wiring. It does not expose prediction bundles in the summary or CLI output.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 022 - Split Prediction Bundle Evaluator

## 修改檔案
- `src/abc_quant/models/evaluation.py`: added `SplitPredictionBundleEvaluationResult` and `evaluate_prediction_bundle(...)`, delegating each split to `evaluate_predictions(...)`.
- `src/abc_quant/models/__init__.py`: exported the bundle evaluation dataclass and evaluator.
- `tests/test_models_evaluation.py`: added valid bundle evaluation, missing-actual handling, invalid type checks, and parity with existing constant-baseline evaluation.
- `docs/modeling.md`: documented bundle evaluation and its safety rules.
- `README.md`: documented `evaluate_prediction_bundle(...)` in the prediction evaluation section.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 022 progress and completion evidence.
- `INBOX.md`: reset the active Task 022 block to the commented empty template before PR handoff.

## 實作摘要
- Added a frozen `SplitPredictionBundleEvaluationResult` with `model_name`, `method`, `train`, `validation`, and `test`.
- Added `evaluate_prediction_bundle(feature_matrix, prediction_bundle)`.
- The evaluator requires a `FeatureMatrix` and `SplitPredictionBundle` with clear `TypeError` messages.
- It evaluates train, validation, and test predictions by calling `evaluate_predictions(feature_matrix.y, split_predictions, split_name)`.
- It preserves `prediction_bundle.model_name` and `prediction_bundle.method`.
- Constant-baseline bundle evaluation now has test coverage proving split metrics match the existing `evaluate_constant_baseline(...)` output.
- No existing metric formula, baseline calculation, pipeline behavior, CLI behavior, diagnostic summary key, estimator implementation, file output, outside data access, live account connectivity, preprocessing fitting, parameter search, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_models_evaluation.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused evaluation tests: 9 passed in 0.98s.
- `pytest`: 132 passed in 5.58s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only evaluates already-built split prediction bundles. It does not wire bundle evaluation into pipeline summaries or CLI output.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 021 - Constant Baseline Prediction Bundle Adapter

## 修改檔案
- `src/abc_quant/models/predictions.py`: added `build_constant_baseline_prediction_bundle(...)`, with explicit `ConstantBaselineResult` type validation and delegation to the generic split bundle builder.
- `src/abc_quant/models/__init__.py`: exported the constant-baseline prediction bundle adapter.
- `tests/test_models_predictions.py`: added adapter coverage for default model name, custom trimmed model name, method propagation, split indices/values, copy isolation, and invalid input type.
- `docs/modeling.md`: documented the constant-baseline adapter and its delegation to the shared validation/copy contract.
- `README.md`: documented the adapter alongside the generic prediction bundle contract.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 021 progress and completion evidence.
- `INBOX.md`: reset the active Task 021 block to the commented empty template before PR handoff.

## 實作摘要
- Added `build_constant_baseline_prediction_bundle(baseline_result, model_name="constant_baseline")`.
- The helper accepts only `ConstantBaselineResult` and raises a clear `TypeError` for other inputs.
- It propagates `baseline_result.method` and passes the existing train/validation/test prediction Series into `build_split_prediction_bundle(...)`.
- Validation and copy isolation are therefore shared with the generic split prediction bundle contract.
- No baseline calculation, pipeline behavior, CLI arguments, summary keys, estimator implementation, file output, outside data access, live account connectivity, preprocessing fitting, parameter search, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_models_predictions.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused prediction tests: 13 passed in 0.89s.
- `pytest`: 128 passed in 5.48s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only adds an adapter from `ConstantBaselineResult` to `SplitPredictionBundle`. It does not wire the bundle into pipeline summaries or CLI output.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 020 - Split Prediction Bundle Contract

## 修改檔案
- `src/abc_quant/models/predictions.py`: added the frozen `SplitPredictionBundle` dataclass and `build_split_prediction_bundle(...)` validation helper.
- `src/abc_quant/models/__init__.py`: exported the prediction bundle contract.
- `tests/test_models_predictions.py`: covered valid bundles, copied Series isolation, metadata validation, non-Series inputs, empty required splits, duplicate indices, missing values, and split-index overlap.
- `docs/modeling.md`: documented the split prediction bundle contract and safety rules.
- `README.md`: documented the reusable train/validation/test prediction bundle contract.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 020 progress and completion evidence.
- `INBOX.md`: reset the active Task 020 block to the commented empty template before PR handoff.

## 實作摘要
- Added a reusable in-memory prediction-output contract for diagnostic workflows.
- `SplitPredictionBundle` stores `model_name`, optional `method`, and train/validation/test prediction Series.
- `build_split_prediction_bundle(...)` normalizes model metadata, requires pandas Series inputs, rejects empty train/test predictions, duplicate indices, missing prediction values, and overlapping split indices.
- The builder copies all accepted Series so caller mutation after bundle creation cannot change the stored predictions.
- Empty validation predictions are allowed for train/test-only diagnostic flows.
- No estimator implementation, baseline fitted value, split count, metric formula, CLI argument, summary key, file output, outside data access, live account connectivity, preprocessing fitting, parameter search, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_models_predictions.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused prediction bundle tests: 9 passed in 0.93s.
- `pytest`: 124 passed in 5.47s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only adds a reusable prediction bundle shape contract. It does not plug the bundle into the constant baseline, modeling smoke pipeline, or CLI yet.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 019 - Modeling Smoke Console Script Alias

## 修改檔案
- `pyproject.toml`: added the `abc-quant-modeling-smoke` project script pointing to `abc_quant.cli.modeling_smoke:main`.
- `tests/test_cli_entrypoints.py`: added `tomllib` metadata parsing, target import resolution, and resolved-function JSON smoke coverage.
- `docs/modeling.md`: documented the installed console-script command alongside `python -m`.
- `README.md`: documented the packaged console command.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 019 progress and completion evidence.
- `INBOX.md`: reset the active Task 019 block to the commented empty template before PR handoff.

## 實作摘要
- Added a package metadata console-script alias: `abc-quant-modeling-smoke`.
- The entry point target is exactly `abc_quant.cli.modeling_smoke:main`.
- Tests parse `pyproject.toml` with `tomllib`, import the configured target, verify it resolves to the same `main` function, and call it with `--method median` to parse valid JSON.
- `python -m abc_quant.cli.modeling_smoke` remains unchanged.
- No diagnostic calculation, summary key, CLI argument semantic, estimator implementation, file output, outside data access, live account connectivity, preprocessing fitting, parameter search, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_cli_entrypoints.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused entrypoint/CLI tests: 10 passed in 3.66s.
- `pytest`: 115 passed in 5.45s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only adds package-level discoverability for the existing CLI. It does not install the package globally or change CLI behavior.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 018 - Baseline Method Selector

## 修改檔案
- `src/abc_quant/pipeline/modeling.py`: added a `method` argument to `run_baseline_modeling_smoke(...)`, passes it to `fit_constant_baseline(...)`, and records `baseline_method`.
- `src/abc_quant/pipeline/contracts.py`: added `baseline_method` to the summary key contract and validates that it is `mean` or `median`.
- `src/abc_quant/cli/modeling_smoke.py`: added `--method` with `mean` and `median` choices.
- `tests/test_pipeline_modeling.py`: added deterministic mean/median fitted-value coverage.
- `tests/test_cli_modeling_smoke.py`: added CLI `--method median` and invalid-method coverage.
- `tests/test_pipeline_contracts.py`: added invalid `baseline_method` summary validation.
- `docs/modeling.md`: documented `method`, `baseline_method`, and CLI `--method`.
- `README.md`: documented the `--method mean|median` CLI option and summary contract update.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 018 progress and completion evidence.
- `INBOX.md`: reset the active Task 018 block to the commented empty template before PR handoff.

## 實作摘要
- `run_baseline_modeling_smoke(method="mean")` remains the default behavior.
- `run_baseline_modeling_smoke(method="median")` uses the existing constant-baseline median method and records `baseline_method="median"`.
- `python -m abc_quant.cli.modeling_smoke --method median` passes the selected method through and emits deterministic JSON.
- The smoke summary contract now includes `baseline_method` and rejects unsupported method values.
- Tests pin the smoke fixture fitted values for mean and median to prove the method changes the existing baseline selection deterministically.
- No estimator implementation, split construction, metric formula, file output, outside data access, live account connectivity, preprocessing fitting, parameter search, allocation logic, performance curve, or simulation engine was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_modeling.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused contract/pipeline/CLI tests: 23 passed in 4.59s.
- `pytest`: 112 passed in 5.77s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only exposes the existing constant-baseline method selector. It does not add a new estimator or change feature, split, or metric formulas.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 017 - Modeling Summary Contract Validator

## 修改檔案
- `src/abc_quant/pipeline/contracts.py`: added shared modeling smoke summary constants and `validate_modeling_smoke_summary(...)`.
- `src/abc_quant/pipeline/modeling.py`: validates the modeling smoke summary before returning it.
- `src/abc_quant/pipeline/__init__.py`: exports the contract constants and validator.
- `tests/test_pipeline_contracts.py`: added valid and invalid summary-shape tests.
- `tests/test_pipeline_modeling.py`: switched pipeline summary assertions to shared constants and validator.
- `tests/test_cli_modeling_smoke.py`: switched CLI key assertions to shared constants.
- `docs/modeling.md`: documented the summary contract validator.
- `README.md`: documented where the summary shape is centralized.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 017 progress and completion evidence.
- `INBOX.md`: reset the active Task 017 block to the commented empty template before PR handoff.

## 實作摘要
- Added `MODELING_SMOKE_SUMMARY_KEYS` and `EVALUATION_METRIC_KEYS` as the shared diagnostic summary contract.
- Added `validate_modeling_smoke_summary(summary)` to reject non-dict summaries, missing or unknown top-level keys, invalid evaluation containers, missing or unknown train/validation/test splits, and missing or unknown per-split metric keys.
- The validator returns the original summary object unchanged when valid.
- `run_baseline_modeling_smoke(...)` now validates the summary shape immediately before returning.
- CLI and pipeline tests now import shared constants instead of duplicating key sets.
- No numeric model calculation, prediction method, model training, preprocessing fitting, parameter search, outside data access, file writing, allocation logic, performance curve, or simulation engine was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_modeling.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused contract/pipeline/CLI tests: 19 passed in 4.13s.
- `pytest`: 108 passed in 5.62s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task validates the in-memory diagnostic summary shape only. It does not change model calculations or add new modeling behavior.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 016 - Modeling Smoke Diagnostics CLI

## 修改檔案
- `src/abc_quant/cli/__init__.py`: added the CLI package marker.
- `src/abc_quant/cli/modeling_smoke.py`: added the module entry point for deterministic modeling smoke diagnostics.
- `tests/test_cli_modeling_smoke.py`: added subprocess and direct-main tests for deterministic JSON, split arguments, error handling, and diagnostic-only keys.
- `docs/modeling.md`: documented the CLI usage, arguments, stdout/stderr behavior, and diagnostic-only boundary.
- `README.md`: documented the module command and supported arguments.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 016 progress and completion evidence.
- `INBOX.md`: reset the active Task 016 block to the commented empty template before PR handoff.

## 實作摘要
- `python -m abc_quant.cli.modeling_smoke` prints the existing `run_baseline_modeling_smoke(...)` summary as deterministic sorted JSON.
- The CLI supports optional `--train-end`, `--validation-end`, and `--indent` arguments.
- Invalid temporal boundaries return a non-zero exit code and print a concise `error: ...` message to stderr.
- Tests verify repeated module invocations are byte-identical, stdout JSON matches the pipeline contract, custom split arguments change split counts deterministically, and forbidden non-diagnostic keys are absent.
- No file writing, outside data access, live account connectivity, new model type, scaler fitting, hyperparameter tuning, allocation logic, performance curve, or simulation engine was added.

## 測試方式
- `python -m pytest tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused CLI tests: 5 passed in 3.56s.
- `pytest`: 98 passed in 4.64s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This CLI exposes diagnostics only. It does not add model behavior or produce trading, allocation, performance-curve, or simulation outputs.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 015 - Baseline Modeling Smoke Pipeline

## 修改檔案
- `src/abc_quant/pipeline/modeling.py`: added `run_baseline_modeling_smoke(...)` for deterministic model-diagnostics wiring.
- `src/abc_quant/pipeline/__init__.py`: exported the modeling smoke pipeline alongside existing smoke helpers.
- `tests/test_pipeline_modeling.py`: added deterministic summary, split-count, metric-key, label-feature separation, and forbidden-output-key tests.
- `docs/modeling.md`: documented the baseline modeling smoke pipeline and diagnostic-only boundary.
- `README.md`: documented the model-diagnostics smoke pipeline.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 015 progress and completion evidence.
- `INBOX.md`: reset the active Task 015 block to the commented empty template before PR handoff.

## 實作摘要
- `run_baseline_modeling_smoke(...)` builds the existing deterministic synthetic smoke frame, assembles a `FeatureMatrix`, builds a date-based `TemporalSplit`, fits the existing constant baseline, and evaluates train/validation/test predictions.
- The returned plain dictionary includes row counts, ticker counts, rows per ticker, `feature_columns`, `label_column`, label missing/non-missing counts, split counts, `fitted_value`, `training_label_count`, and train/validation/test evaluation metrics.
- The default split uses `train_end="2026-01-07"` and `validation_end="2026-01-12"` against the deterministic synthetic fixture.
- Tests verify deterministic repeated output, expected split counts, evaluation metric keys, label exclusion from feature columns, and absence of market-action, allocation, performance-curve, or simulation-result keys.
- No source adapter, outside data access, live account connectivity, new model type, scaler fitting, hyperparameter tuning, market-action output, allocation logic, performance curve, or simulation engine was added.

## 測試方式
- `python -m pytest tests\test_pipeline_modeling.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused modeling pipeline tests: 4 passed in 1.28s.
- `pytest`: 93 passed in 2.15s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only wires existing contracts into a deterministic diagnostic smoke pipeline. It is not market performance, a market-action output, allocation logic, a performance curve, or a simulation result.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 014 - Prediction Evaluation Metrics

## 修改檔案
- `src/abc_quant/models/evaluation.py`: added typed prediction evaluation results plus evaluation helpers for generic predictions and constant-baseline outputs.
- `src/abc_quant/models/__init__.py`: exported the prediction evaluation contracts.
- `tests/test_models_evaluation.py`: added tests for perfect predictions, biased predictions, missing actual labels, invalid split/index cases, and constant-baseline train/validation/test evaluation.
- `docs/modeling.md`: documented the prediction evaluation contract and no-trading/no-backtest boundary.
- `README.md`: documented the model-output diagnostics layer.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 014 progress and completion evidence.
- `INBOX.md`: reset the active Task 014 block to the commented empty template before PR handoff.

## 實作摘要
- `evaluate_predictions(actual, prediction, split_name)` evaluates one split by aligning prediction indices against actual labels.
- Returned metrics are `row_count`, `non_missing_count`, `missing_actual_count`, `mae`, `rmse`, `mean_error`, and `prediction_mean`.
- Missing actual labels are counted but excluded from `mae`, `rmse`, and `mean_error`.
- Prediction indices outside the actual-label index are rejected, as are empty split names, empty predictions, duplicate indices, missing predictions, and splits with no non-missing actual labels.
- `evaluate_constant_baseline(feature_matrix, baseline_result)` evaluates the train, validation, and test predictions returned by `fit_constant_baseline(...)`.
- No scaler fitting, hyperparameter tuning, trading signals, strategy logic, positions, equity curves, portfolio logic, source adapter, data download, or backtest engine was added.

## 測試方式
- `python -m pytest tests\test_models_evaluation.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused evaluation tests: 5 passed in 1.09s.
- `pytest`: 89 passed in 2.02s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only evaluates model-output prediction errors. It is not a trading signal, strategy, portfolio rule, equity curve, backtest, or performance claim.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 013 - Constant Baseline Model Contract

## 修改檔案
- `src/abc_quant/models/baseline.py`: added `ConstantBaselineResult` and `fit_constant_baseline(...)` for deterministic mean/median baseline predictions.
- `src/abc_quant/models/__init__.py`: exported the baseline model contract.
- `tests/test_models_baseline.py`: added tests for mean/median fitting, validation/test label isolation, missing-label behavior, prediction indices, unsupported methods, empty train split, and all-missing training labels.
- `docs/modeling.md`: documented the constant baseline contract and leakage boundary.
- `README.md`: documented the minimal model baseline and no-strategy/no-backtest boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 013 progress.
- `INBOX.md`: reset the active Task 013 block to the commented empty template before PR handoff.

## 實作摘要
- `fit_constant_baseline(feature_matrix, temporal_split, method="mean")` fits a constant from non-missing labels at `temporal_split.train_index` only.
- Supported methods are `mean` and `median`; unsupported methods raise a clear `ValueError`.
- Empty train splits and all-missing training labels are rejected.
- Returned train/validation/test predictions are pandas Series indexed by the split's sorted matrix positions.
- Validation and test labels are not read when computing `fitted_value`, so they cannot leak into the baseline.
- No new dependency, scaler fitting, hyperparameter tuning, complex ML model, strategy logic, trading signal, portfolio logic, source adapter, data download, or backtest engine was added.

## 測試方式
- `python -m pytest tests\test_models_baseline.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused baseline tests: 5 passed in 1.07s.
- `pytest`: 84 passed in 1.81s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This is a trivial baseline contract for future model validation. It is not a production model, strategy, trading signal, portfolio rule, or performance claim.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 012 - Temporal Split Contract

## 修改檔案
- `src/abc_quant/validation/temporal.py`: added `TemporalSplit` and `build_temporal_split(...)` for deterministic date-based train/test and train/validation/test splits.
- `src/abc_quant/validation/__init__.py`: exported the temporal split contract.
- `tests/test_validation_temporal.py`: added temporal split tests for train/test, train/validation/test, shuffled metadata invariance, missing-label preservation, missing/unsortable dates, non-increasing boundaries, empty splits, and explicit `test_end` no-drop behavior.
- `docs/modeling.md`: documented the temporal split contract and pre-modeling boundary.
- `README.md`: documented modeling-preparation split behavior and constraints.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 012 progress.
- `INBOX.md`: reset the active Task 012 block to the commented empty template before PR handoff.

## 實作摘要
- `build_temporal_split(metadata, train_end, validation_end=None, test_end=None, date_column="date")` validates in-memory metadata and returns positional indices for sorted metadata.
- Rows are sorted deterministically by `date` and then `ticker` when present.
- Train rows use dates `<= train_end`; validation rows, when requested, use dates `> train_end` and `<= validation_end`; test rows start strictly after the prior split boundary.
- Boundaries must be increasing, and requested train/validation/test splits cannot be empty.
- Rows after an explicit `test_end` are rejected instead of silently dropped.
- Missing labels remain untouched; no rows are dropped or filled, and no scaler fitting, model training, strategy logic, trading signal, or backtest engine was added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 79 passed in 1.74s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only creates a temporal split contract. It does not add model baselines, walk-forward orchestration, scalers, feature importance, ablation, strategy logic, trading signals, portfolio logic, or a full backtest engine.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 011 - Feature Matrix Assembly Contract

## 修改檔案
- `src/abc_quant/features/matrix.py`: added `FeatureMatrix` and `build_feature_matrix(...)` for deterministic feature/label/metadata separation.
- `src/abc_quant/features/__init__.py`: exported the new matrix contract alongside existing feature builders.
- `tests/test_features_matrix.py`: added tests for inferred safe features, explicit feature ordering, label leakage rejection, shuffled-input invariance, missing-label preservation, missing label errors, and no-feature errors.
- `tests/test_helpers.py`: added a reusable feature-matrix equality helper for shuffled-output checks.
- `README.md`, `docs/feature_engineering.md`: documented the feature-matrix contract and boundaries.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 011 progress.
- `INBOX.md`: reset the active Task 011 block to the commented empty template before PR handoff.

## 實作摘要
- `build_feature_matrix(frame, label_column, feature_columns=None)` returns `X`, `y`, `metadata`, `feature_columns`, and `label_column`.
- Rows are sorted deterministically by `ticker` then `date`.
- Inferred feature columns exclude `date`, `ticker`, raw OHLCV columns, the explicit label column, and every `label_` column.
- Explicit feature columns preserve caller order but reject metadata, raw OHLCV, label columns, missing columns, and duplicates.
- Missing labels are preserved as evaluator targets; no rows are dropped and no scaling, imputation, filling, train/test split, model training, strategy logic, or backtest logic was added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 71 passed in 1.77s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only assembles already-created features and labels. It does not add feature formulas, source adapters, data downloads, model training, train/test splitting, trading signals, portfolio logic, or a backtest engine.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 010 - Technical Indicators

## 修改檔案
- `src/abc_quant/features/technical.py`: added `add_technical_indicators(...)` for pure-pandas SMA, EMA, and RSI features.
- `tests/test_features_technical.py`: added hand-calculated indicator, ticker-isolation, shuffled-input invariance, future-row mutation, and invalid-window tests.
- `README.md`, `docs/data_pipeline.md`, `docs/feature_engineering.md`: documented the technical feature module and no-signal/no-backtest boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 010 progress.
- `INBOX.md`: reset the active Task 010 block to the commented empty template before PR handoff.

## 實作摘要
- The technical feature module validates OHLCV data before computation and returns a sorted defensive copy by ticker and date.
- SMA, EMA, and RSI are computed per ticker using only current and past rows.
- RSI uses a simple rolling average of gains and losses; flat windows map to 50, gain-only windows to 100, and loss-only windows to 0 through the standard formula behavior.
- No TA-Lib, new dependency, source adapter, data download, broker integration, model training, strategy logic, trading signal, portfolio logic, or full backtest engine was added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 64 passed in 1.65s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- The module adds research features only. It does not define trading rules, model inputs, portfolio decisions, or backtest outcomes.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 009 - Feature and Label Leakage Regression Tests

## 修改檔案
- `tests/test_features_price_volume.py`: added multi-ticker isolation and shuffled-input invariance tests for price momentum, rolling volatility, and rolling volume average.
- `tests/test_labels_returns.py`: added multi-ticker forward-return label isolation, horizon/entry-lag contract, shuffled-input invariance, and missing-tail label tests.
- `tests/test_pipeline_smoke.py`: asserted the smoke label column is not part of the feature column contract.
- `OUTBOX.md`: recorded Task 009 GitHub handoff results.

## 實作摘要
- Locked price momentum to same-ticker current/past rows.
- Locked rolling volatility and volume average against cross-ticker contamination.
- Confirmed shuffled market data produces the same sorted feature and label outputs.
- Confirmed forward-return labels follow `entry_price = close[t + entry_lag]` and `exit_price = close[t + horizon]`.
- Confirmed evaluator labels remain outside feature columns and missing future rows produce missing labels.
- No data downloads, source adapters, broker integration, strategy logic, model training, trading signals, or full backtest engine were added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 58 passed in 1.46s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task`.

## 已知限制
- This is a regression-test-only task; it does not add new feature formulas, labels, strategy logic, or data ingestion.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 008 - Harden Market Data Validation

## 修改檔案
- `src/abc_quant/data/validation.py`: uses schema constants and validates numeric, missing, volume, and OHLC range rules.
- `tests/test_data_validation.py`: added adversarial tests for schema-backed required columns, ticker string normalization, non-numeric OHLCV, missing OHLCV, negative volume, high-low inversion, and open/close range violations.
- `docs/data_pipeline.md`, `README.md`: documented the enforced validation contract and smoke fixture boundary.
- `INBOX.md`: reset the active Task 008 block to the commented empty template before PR handoff.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 008 progress.

## 實作摘要
- `validate_market_data()` still returns a defensive sorted copy by ticker and date.
- Dates are normalized with `pd.to_datetime`; tickers are normalized to pandas string dtype.
- OHLCV columns are converted with `pd.to_numeric`, then checked for missing values.
- Negative volume, `high < low`, `open` outside high-low, and `close` outside high-low now raise `MarketDataValidationError`.
- No data adapters, downloads, model logic, strategy logic, portfolio logic, broker integration, or full backtest logic were added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 54 passed in 1.35s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This validates the deterministic OHLCV contract only; it does not add cleaning, imputation, source freshness, or real market adapters.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review after final validation passes.

## 2026-07-04 Closed-Loop Task 007 - Data Contract Smoke Pipeline

## 修改檔案
- `src/abc_quant/data/schema.py`: added required market columns, numeric columns, and dtype-intent constants.
- `src/abc_quant/data/sample.py`: added deterministic two-ticker OHLCV sample data for smoke checks.
- `src/abc_quant/pipeline/__init__.py`: added pipeline package marker.
- `src/abc_quant/pipeline/smoke.py`: added the deterministic validate -> feature -> label -> metrics smoke pipeline.
- `tests/test_data_schema.py`: added schema and sample fixture tests.
- `tests/test_pipeline_smoke.py`: added smoke pipeline summary, feature, label, metric, and multi-ticker isolation tests.
- `docs/data_pipeline.md`, `README.md`: documented the smoke fixture boundary and no-signal/no-performance-claim status.
- `INBOX.md`: reset the active Task 007 block to the commented empty template before PR handoff.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 007 progress.

## 實作摘要
- The schema contract defines `date`, `ticker`, `open`, `high`, `low`, `close`, and `volume`.
- The synthetic fixture returns two tickers with 12 deterministic rows each.
- The smoke pipeline validates the fixture, creates price/volume features, creates one 3-day forward-return label with next-period entry, computes basic metrics, and returns a summary dictionary.
- The pipeline remains local and deterministic only; it adds no data download, broker integration, strategy logic, model training, or full backtest engine.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 38 passed in 1.18s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- `python -m ruff check .`: unavailable in the current shell (`No module named ruff`); this was not part of Task 007 expected validation.

## 已知限制
- The sample fixture is synthetic and only proves local contracts and wiring.
- The metrics summary is smoke evidence only, not a trading signal, backtest result, or performance claim.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 006 - GitHub Actions CI

## 修改檔案
- `.github/workflows/ci.yml`: added minimal GitHub Actions CI for pull requests and pushes to `main`.
- `README.md`: documented CI quality gates and Python matrix.
- `docs/codex_closed_loop.md`: documented CI workflow behavior and boundaries.
- `INBOX.md`: reset the active Task 006 block to the commented empty template before PR handoff.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 006 governance progress.

## 實作摘要
- CI uses official `actions/checkout@v7` and `actions/setup-python@v6`.
- CI runs Python 3.11 and 3.12 because the project declares Python 3.11+ support.
- CI installs `.[dev]`, then runs `ruff check .`, `python -m pytest`, and `python -m compileall src tests`.
- No deployment, publishing, secrets, data acquisition, broker integration, model training, or trading signal changes were added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 34 passed in 1.14s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- `.github/workflows/ci.yml`: exists.

## 已知限制
- Local `ruff` is not required by the task validation command set; CI installs `ruff` through `.[dev]`.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 PR #3 Review Follow-up - INBOX Closeout

## 修改檔案
- `INBOX.md`: reset the active Task 005 YAML block back to the commented empty template.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`: recorded that Task 005 is complete and the inbox was cleared.

## 實作摘要
- Closed the loop after Task 005 so a merged PR does not leave an active task that returns `status=ready`.
- `scripts/run_codex_closed_loop.ps1` now returns `status=no_task`.
- No `.github/workflows/ci.yml` file was created.
- No trading, data, model, FinLab, broker API, data download, strategy, or backtest code changed.

## 測試方式
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`

## 測試結果
- `run_codex_closed_loop.ps1`: `status=no_task`.
- `pytest`: 34 passed in 1.11s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `.github/workflows/ci.yml`: absent.

## 已知限制
- This is a closeout-only commit for PR #3 review feedback.

## 下一步建議
- Re-run ChatGPT Tech Lead review on PR #3.

## 2026-07-04 Closed-Loop Task 005 - CI Target Root Preparation

## 修改檔案
- `configs/codex_closed_loop.yaml`: added `.github/` to `allowed_target_roots`.
- `tests/test_codex_loop_guard.py`: added tests proving `.github/workflows/ci.yml` is allowed while `.git/config` remains blocked.
- `docs/codex_closed_loop.md`: documented the CI target preparation boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 005 governance progress.

## 實作摘要
- Prepared the guard for a later reviewed CI workflow task without creating any workflow file.
- `.github/` is now an explicit allowed repository target root.
- `.git/` remains blocked through built-in blocked path defaults.
- Built-in blocked content/path defaults remain preserved when config adds custom blockers.
- No trading, data, model, broker, strategy, or backtest code changed.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`

## 測試結果
- `pytest`: 34 passed in 1.22s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.

## 已知限制
- This task only prepares the guard target root; CI workflow files are intentionally not created.

## 下一步建議
- Have ChatGPT Pro review this governance-only PR before any future task adds workflow files.

## 2026-07-04 Closed-Loop Task 004 - Final Review Audit and Guard Defaults

## 修改檔案
- `src/abc_quant/governance/codex_loop.py`: preserved built-in blocked content/path patterns when config adds custom patterns.
- `tests/test_codex_loop_guard.py`: added regression tests proving config cannot remove default `token` or `.git` blockers and cannot enable auto-merge.
- `scripts/build_review_package.py`: added two-pass final audit, output-file trailing-whitespace check, diff-check exclusion for the output file, and clearer SHA metadata.
- `reviews/review_package_002.md`: regenerated as the Task 004 review package after source changes were committed.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`: recorded Task 004 governance results.

## 實作摘要
- `blocked_content_patterns` and `blocked_path_patterns` now merge config additions onto built-in defaults; config can no longer weaken the default guard.
- `allowed_risk_levels` still filters to `normal` only, and `allow_auto_merge` remains forced to `false`.
- Review package metadata now uses `source_head_sha_at_generation`, `review_package_output_file`, and `review_package_commit_sha: unavailable_self_reference`.
- Review package generation excludes `reviews/review_package_002.md` from repo-level diff checks to avoid self-reference, then separately audits the generated output file for trailing whitespace.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `ruff check .`
- `git diff --check`
- `python scripts\build_review_package.py --output reviews\review_package_002.md --title "Codex Closed-Loop Task 004 Review Package" --pr-url "https://github.com/jongyawjong0514/abc-quant/pull/2" --run-validation --include-diff --include-file-contents --assert-clean`

## 測試結果
- `pytest`: 32 passed in 1.18s.
- `compileall`: passed for `src` and `tests`.
- `ruff`: unavailable in the current shell; no package was installed.
- `git diff --check`: passed before source commit; final check after package generation also passed.

## 已知限制
- `review_package_commit_sha` remains `unavailable_self_reference` because committing the review package changes the final commit SHA.
- The package excludes itself from repo-level diff sections to prevent recursive package growth, but it audits the output file directly for trailing whitespace.

## 下一步建議
- Ask ChatGPT Pro to re-review `reviews/review_package_002.md` on PR #2.
- Merge only after review approval; closed-loop policy still forbids auto-merge.

## 2026-07-03 Closed-Loop Task 003 - Guard Hardening and Reproducible Review Package

## 修改檔案
- `src/abc_quant/governance/codex_loop.py`: added configurable closed-loop guard policy, content/path risk scanning, safe config loading, and safe failure reports.
- `configs/codex_closed_loop.yaml`: recorded conservative allowed risk levels, blocked content/path patterns, and allowed target roots.
- `tests/test_codex_loop_guard.py`: added adversarial guard coverage for disguised risky normal tasks, blocked paths, missing inbox, config loading, and `anything_not_allowed` contradictions.
- `scripts/build_review_package.py`: added reproducible review package flags for diff, full file contents, validation capture, and assert-clean behavior excluding only the output file.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`: updated governance status and heartbeat wording.

## 實作摘要
- `risk_level: normal` no longer auto-passes if actionable task fields mention destructive, credential, external/network, data/raw, absolute path, or repo-outside operations.
- `anything_not_allowed` is not scanned as an actionable field by itself, but a task that contradicts it is blocked.
- Missing `INBOX.md`, unreadable inbox, invalid task YAML, or invalid guard config now fail closed and still write `reports/codex_loop/latest.json` and `latest.md`.
- Review package generation can now include `git diff main...HEAD`, full file contents, validation output, full HEAD SHA, and an assert-clean check that excludes `reviews/review_package_002.md` only.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `ruff check .`
- `python scripts\build_review_package.py --output reviews\review_package_002.md --title "Codex Closed-Loop Task 003 Review Package" --pr-url "https://github.com/jongyawjong0514/abc-quant/pull/2" --run-validation --include-diff --include-file-contents --assert-clean`

## 測試結果
- `pytest`: 29 passed in 1.22s.
- `compileall`: passed for `src` and `tests`.
- `ruff`: unavailable in the current shell; no package was installed.
- `build_review_package --assert-clean`: intentionally fails while source files are dirty; final package is generated after the code changes are committed so the assert-clean check is meaningful.

## 已知限制
- A committed review package cannot record its own final Git SHA without creating an infinite self-reference; the package records the HEAD SHA at generation time.
- Existing PR #2 remains draft/review-only; no auto-merge is performed.

## 下一步建議
- Have ChatGPT Pro review `reviews/review_package_002.md` on PR #2.
- Keep future closed-loop tasks limited to one bounded YAML task in `INBOX.md`.

## 2026-07-03 Closed-Loop Task 001 - Repository Hygiene and Review Package

## 修改檔案
- `scripts/build_review_package.py`: added a repeatable review-package builder.
- `reviews/review_package_002.md`: generated tracked review package for ChatGPT Pro review.
- `.gitignore`: explicitly ignored local `_archive/` artifacts.
- `FILE_MANIFEST.txt`, `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: updated project governance records.

## 實作摘要
- Root-level stale `CODEX_REVIEW_PACKAGE.md` and `CODEX_TEST_RESULT.txt` are superseded by a tracked review package under `reviews/`.
- Review package includes branch status, diff summary, changed files, validation output, review pointers, and known local artifacts.
- No strategy, model, broker API, formal signal, or trading-rule logic changed.

## 測試方式
- `E:\abc\.venv\Scripts\python.exe -m pytest`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `E:\abc\.venv\Scripts\python.exe .\scripts\build_review_package.py --output reviews\review_package_002.md --title "Codex Closed-Loop Task 001 Review Package" --pr-url "https://github.com/jongyawjong0514/abc-quant/pull/2" --run-validation`

## 測試結果
- `scripts/build_review_package.py --run-validation`: regenerated `reviews/review_package_002.md`.
- Embedded validation in the review package: `pytest` 19 passed in 0.84s.
- Embedded closed-loop guard check: `status=no_task`, expected because `INBOX.md` currently contains only the commented template.
- Final direct validation: `pytest` 19 passed in 0.94s; `run_codex_closed_loop.ps1` returned `status=no_task`.

## 已知限制
- `.pytest_cache/` may remain as a local Windows ACL residue; it is ignored and not tracked by Git.

## 下一步建議
- Push the updated branch to GitHub PR #2 and have ChatGPT Pro review `reviews/review_package_002.md`.
- Merge PR #2 only after review; the closed-loop policy still forbids auto-merge.

## 2026-07-03 File-Based Closed Loop Guard

## 修改檔案
- `docs/codex_closed_loop.md`: documented the safe file-based closed-loop protocol.
- `configs/codex_closed_loop.yaml`: recorded loop paths, allowed risk levels, and no-auto-merge/no-web-UI boundaries.
- `src/abc_quant/governance/codex_loop.py`: added testable guard logic for `INBOX.md` task validation.
- `scripts/codex_loop_guard.py`: added CLI wrapper for guard execution.
- `scripts/run_codex_closed_loop.ps1`: added PowerShell entrypoint for Codex automation or manual checks.
- `prompts/codex_closed_loop_runner.md`: added reusable automation prompt.
- `tests/test_codex_loop_guard.py`: added guard behavior tests.
- `INBOX.md`, `TECH_LEAD_PROTOCOL.md`, `README.md`, `TODO.md`, `CHANGELOG.md`, `STATUS.md`: updated project workflow records.

## 實作摘要
- The loop executes only when `INBOX.md` contains one complete YAML task with `risk_level: normal`.
- Empty tasks return `no_task`; incomplete tasks return `blocked_invalid`; risky tasks return `blocked_risky`.
- Generated guard reports are written under `reports/codex_loop/`, which remains an ignored local/report artifact path.
- The design deliberately avoids automating ChatGPT Pro web UI and does not allow auto-merge.
- Prepared instructions for an optional hourly Codex heartbeat automation; external scheduler status is not tracked in this repository.

## 測試方式
- `E:\abc\.venv\Scripts\python.exe -m pytest`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest --basetemp=.tmp_pytest`: 19 passed in 0.87s, then 19 passed in 0.84s.
- `E:\abc\.venv\Scripts\python.exe -m pytest`: 19 passed in 0.86s.
- `scripts/run_codex_closed_loop.ps1`: status `no_task`, which is expected because `INBOX.md` currently contains only a commented template.

## 已知限制
- This is a guard and workflow scaffold, not a recursive self-launcher.
- Real unattended automation still needs a Codex app automation schedule and review of the first few runs.

## 下一步建議
- Ask ChatGPT Pro to place the next bounded task into `INBOX.md`.
- Review the first few heartbeat runs and adjust cadence if it is too frequent or too quiet.

## 2026-07-03 ChatGPT Review 001 and PR Hygiene

## 修改檔案
- `.gitignore`: excluded local venv, Python caches, pytest temp/cache, package egg-info, and generated E-drive zip/unpacked bundle.
- `pyproject.toml`: configured pytest to use local basetemp and disabled cache provider to avoid Windows temp/cache permission failures.
- `reviews/review_001.md`: recorded ChatGPT tech-lead review and next-round Codex prompt.
- `TODO.md`: marked first ChatGPT review and review archive item complete.
- `CHANGELOG.md`: recorded review and PR hygiene changes.
- `STATUS.md`: recorded latest validation status.

## 實作摘要
- First scaffold review is complete and accepts the current baseline for scaffold stage.
- No blocking look-ahead, train/test leakage, or modularity defect was found for this stage.
- The main next-step risk is label `horizon` semantics before model/backtest expansion.

## 測試方式
- `E:\abc\.venv\Scripts\python.exe -m pytest`

## 測試結果
- `pytest`: 13 passed in 0.83s.

## 已知限制
- Repository publishing still depends on initializing/pushing `E:\abc` to `jongyawjong0514/abc-quant`.
- GitHub repo is currently empty, so a normal PR requires a base branch commit before opening a feature branch PR.

## 下一步建議
- Publish this scaffold to GitHub with a clean initial branch.
- If a PR workflow is required, create a minimal `main` base first, then open a scaffold PR against it.

## 2026-07-03 Codex Result - RUN_CODEX_NEXT.md

## 修改檔案
- `src/abc_quant/config/settings.py`: hardened YAML config loading and required-key access.
- `src/abc_quant/__init__.py`: bumped package version to `0.0.2`.
- `src/abc_quant/data/validation.py`: added OHLCV column/date/duplicate validation.
- `src/abc_quant/features/price_volume.py`: added rolling momentum, volatility, and volume average features.
- `src/abc_quant/labels/returns.py`: added forward return labels with next-period entry semantics.
- `src/abc_quant/metrics/performance.py`: added total return, CAGR, annual volatility, Sharpe, max drawdown, and summary metrics.
- `tests/test_config_settings.py`: added YAML config loader tests.
- `tests/test_data_validation.py`: added market data validation tests.
- `tests/test_features_price_volume.py`: added no-lookahead rolling feature test.
- `tests/test_labels_returns.py`: added forward label shift tests.
- `tests/test_metrics_performance.py`: added simple performance metric tests.
- `pyproject.toml`: bumped project version to `0.0.2`.
- `CHANGELOG.md`: recorded first executable scaffold changes.
- `TODO.md`: marked first scaffold/data validation/price-volume feature items complete.

## 實作摘要
- Implemented a Pandas-only first executable quant research scaffold.
- Market data must include `date`, `ticker`, `open`, `high`, `low`, `close`, and `volume`.
- Dates are parsed into sortable timestamps, rows are normalized by `ticker,date`, and duplicate `date+ticker` rows are rejected.
- Rolling features are grouped per ticker and use only current or past rows.
- Forward labels use `entry_price = close[t + entry_lag]` and `exit_price = close[t + horizon]`; default entry lag is next period.
- Metrics operate on periodic returns and compound returns consistently.

## 測試方式
- `E:\abc\.venv\Scripts\python.exe -m pytest`
- `E:\abc\.venv\Scripts\python.exe -m pip install -e .`
- `E:\abc\.venv\Scripts\python.exe -m pytest`

## 測試結果
- Editable install succeeded.
- `pytest`: 13 passed.
- Remaining warning: pytest cannot write cache under `E:\abc\.pytest_cache` due `[WinError 5] access denied`.

## 已知限制
- No data download, broker API, complex model, portfolio construction, cost/slippage backtest, or report generation was added in this round.
- The first label helper follows the project example `close[t+horizon] / close[t+entry_lag] - 1`; later tasks should confirm whether `horizon` means exit offset or holding-period count.
- Performance metrics currently cover the task-required minimum only; PROJECT_RULES later require Sortino, Calmar, win rate, profit factor, turnover, average holding period, and trade count.

## 下一步建議
- Add a small sample-data loader plus end-to-end fixture that validates data -> builds features -> creates labels -> computes metrics.
- Add transaction cost and slippage-aware backtest scaffolding.
- Ask ChatGPT Pro to review the horizon/entry label semantics before building model training around it.
