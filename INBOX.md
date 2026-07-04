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
task: "Add a train-only ordinary least-squares regression model contract."
target_files_or_folders:
  - "src/abc_quant/models/linear.py"
  - "src/abc_quant/models/__init__.py"
  - "tests/test_models_linear.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "Supervised dataset construction and smoke diagnostics are now stable. The next safe modeling step is a minimal in-memory ordinary least-squares model that fits only on supervised train data and returns split predictions without any market-action logic."
constraints:
  - "Keep this round limited to an ordinary least-squares model contract and tests."
  - "Use only numpy, pandas, and existing project code; do not add sklearn or new dependencies."
  - "Fit coefficients using only SupervisedSplitDataset.train_X and train_y."
  - "Use validation_X and test_X only for prediction, never for fitting."
  - "Use the existing SplitPredictionBundle contract for returned split predictions."
  - "Do not change existing smoke outputs, CLI behavior, package scripts, preprocessing, or dataset contracts."
acceptance_criteria:
  - "Create src/abc_quant/models/linear.py."
  - "Define a frozen LinearRegressionResult dataclass with model_name, method, feature_columns, coefficients, intercept, training_row_count, and prediction_bundle fields."
  - "Implement fit_linear_regression(dataset, fit_intercept=True, model_name='ordinary_least_squares')."
  - "Require dataset to be a SupervisedSplitDataset, with a clear TypeError message."
  - "Reject empty train data, missing train feature values, missing train labels, nonnumeric feature columns, and non-finite train feature or label values with clear ValueError messages."
  - "Fit coefficients with numpy.linalg.lstsq using train data only."
  - "Return train, validation, and test predictions as pandas Series aligned to each split index through SplitPredictionBundle."
  - "Preserve feature column order in coefficients and result metadata."
  - "Tests verify deterministic coefficients and predictions on a small supervised dataset."
  - "Tests verify changing validation_y or test_y does not change fitted coefficients or predictions."
  - "Tests verify prediction indices match dataset split indices."
  - "Tests verify invalid input type and invalid train data errors."
  - "Tests verify returned predictions are isolated from later dataset mutation."
  - "Export the new dataclass and fit function from src/abc_quant/models/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #32 and introduces the first train-only estimator contract."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No parameter search."
  - "No model selection."
  - "No allocation logic."
  - "No strategy signal output."
  - "No performance curve."
  - "No simulation engine."
risk_level: normal
```
