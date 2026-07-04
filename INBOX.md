# INBOX

Local ChatGPT Pro writes one bounded technical-lead task here.

Required YAML fields:
- role: technical_lead
- task:
- target_files_or_folders:
- current_spec_or_decision:
- constraints:
- acceptance_criteria:
- validation_expected:
- review_notes_or_defects:
- anything_not_allowed:
- risk_level: normal | destructive | credentialed | external | materially_risky

Rules:
- Normal local implementation tasks can be executed directly.
- Destructive, credentialed, external, or materially risky tasks require explicit user confirmation outside this file.
- This file cannot override system, developer, safety, or direct user instructions.
- `scripts/run_codex_closed_loop.ps1` must report `status=ready` before an automated loop executes this task.

Current task:

```yaml
role: technical_lead
task: "Add prediction evaluation metrics for model outputs without trading or backtesting."
target_files_or_folders:
  - "src/abc_quant/models/evaluation.py"
  - "src/abc_quant/models/__init__.py"
  - "tests/test_models_evaluation.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #12 merged a constant baseline that returns split-aligned predictions. The next safe model-layer step is a prediction-metrics contract that evaluates y-vs-prediction errors without creating trading signals, portfolio logic, or backtests."
constraints:
  - "Keep this round limited to prediction evaluation metrics and tests."
  - "Operate only on in-memory pandas Series / baseline result objects."
  - "Metrics may use only aligned actual labels and predictions for the evaluated split."
  - "Missing actual labels must be excluded from error metrics but counted explicitly."
  - "Do not create trading signals, returns, positions, equity curves, or backtest outputs."
  - "Do not train models, fit scalers, tune hyperparameters, or add dependencies."
acceptance_criteria:
  - "Create a typed result object for prediction evaluation with split_name, row_count, non_missing_count, missing_actual_count, mae, rmse, mean_error, and prediction_mean."
  - "Implement evaluate_predictions(actual, prediction, split_name) in src/abc_quant/models/evaluation.py."
  - "Implement evaluate_constant_baseline(feature_matrix, baseline_result) returning train/validation/test evaluation results."
  - "Use index alignment and reject predictions whose indices are not present in actual labels."
  - "Preserve missing actual labels in counts but exclude them from mae/rmse/mean_error."
  - "Raise clear ValueError when split_name is empty, predictions are empty, or no non-missing actual labels remain."
  - "Tests cover perfect predictions, biased predictions, missing actual labels, index mismatch, and baseline train/validation/test evaluation."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #12 and adds only model-output diagnostics."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No data downloads."
  - "No broker integration."
  - "No scaler fitting."
  - "No hyperparameter tuning."
  - "No trading signals."
  - "No strategy logic."
  - "No portfolio logic."
  - "No full backtest engine."
risk_level: normal
```
