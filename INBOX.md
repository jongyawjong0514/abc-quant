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
task: "Add a deterministic baseline modeling smoke pipeline without trading or backtesting."
target_files_or_folders:
  - "src/abc_quant/pipeline/modeling.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_pipeline_modeling.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #13 merged prediction evaluation metrics. The next safe step is a deterministic smoke pipeline that wires the existing feature matrix, temporal split, constant baseline, and prediction evaluation contracts together without adding any trading, strategy, or backtest behavior."
constraints:
  - "Keep this round limited to wiring existing contracts into an in-memory smoke pipeline."
  - "Use only synthetic deterministic data created inside the pipeline or tests."
  - "Do not add source adapters, data downloads, broker integration, trading signals, positions, portfolio logic, equity curves, or backtests."
  - "Do not add new model types, scaler fitting, hyperparameter tuning, feature importance, or ablation logic."
  - "Pipeline outputs must be diagnostic summaries only and must not be interpreted as trading performance."
acceptance_criteria:
  - "Create run_baseline_modeling_smoke(...) in src/abc_quant/pipeline/modeling.py."
  - "Pipeline builds a deterministic in-memory frame with date, ticker, safe feature columns, and one explicit label column."
  - "Pipeline uses build_feature_matrix, build_temporal_split, fit_constant_baseline, and evaluate_constant_baseline."
  - "Pipeline returns a plain dict summary containing row counts, feature_columns, label_column, split counts, fitted_value, training_label_count, and train/validation/test evaluation metrics."
  - "Tests verify the summary is deterministic across repeated calls."
  - "Tests verify split counts and evaluation metric keys are present."
  - "Tests verify the label column is not included in feature_columns."
  - "Tests verify the smoke pipeline does not expose trading signals, positions, portfolio values, equity curves, or backtest keys."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #13 and only wires existing model diagnostics together."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No data downloads."
  - "No broker integration."
  - "No scaler fitting."
  - "No hyperparameter tuning."
  - "No trading signals."
  - "No strategy logic."
  - "No positions or portfolio logic."
  - "No equity curve."
  - "No full backtest engine."
risk_level: normal
```
