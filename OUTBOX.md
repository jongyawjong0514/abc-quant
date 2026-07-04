# OUTBOX

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
