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
task: "Add a minimal constant-baseline model contract using only training labels."
target_files_or_folders:
  - "src/abc_quant/models/__init__.py"
  - "src/abc_quant/models/baseline.py"
  - "tests/test_models_baseline.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #11 merged temporal split validation. The first safe model-layer step is a deterministic constant baseline that fits only on training labels and produces validation/test predictions without trading logic or backtesting."
constraints:
  - "Keep this round limited to a minimal baseline prediction contract and tests."
  - "Use only pandas/numpy already available in the project; do not add sklearn or new dependencies."
  - "The fitted value may use only non-missing y values from train_index."
  - "Validation and test labels must never affect the fitted baseline value."
  - "Do not fit scalers, tune hyperparameters, train ML models, create trading signals, run backtests, or add source adapters."
  - "Do not drop rows from the feature matrix; predictions should be returned for each split index."
acceptance_criteria:
  - "Create a typed result object for baseline predictions with fitted_value, train_predictions, validation_predictions, test_predictions, and training_label_count."
  - "Implement fit_constant_baseline(feature_matrix, temporal_split, method='mean') in src/abc_quant/models/baseline.py."
  - "Support method='mean' and method='median' with clear ValueError for unsupported methods."
  - "Use only temporal_split.train_index and non-missing training labels to fit the constant."
  - "Raise clear ValueError when all training labels are missing or train_index is empty."
  - "Return predictions as pandas Series indexed by the original sorted matrix positions for train/validation/test."
  - "Tests prove changing validation/test labels does not change fitted_value."
  - "Tests prove missing training labels are excluded from the fit and counted explicitly."
  - "Tests verify train/validation/test prediction lengths and indices match the temporal split."
  - "Tests verify unsupported method and all-missing-train-label errors."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #11 and introduces only a trivial baseline, not a production model."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No data downloads."
  - "No broker integration."
  - "No scaler fitting."
  - "No hyperparameter tuning."
  - "No trading signal changes."
  - "No strategy logic."
  - "No full backtest engine."
risk_level: normal
```
