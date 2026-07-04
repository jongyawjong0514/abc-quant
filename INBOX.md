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
task: "Add deterministic train-only OLS smoke diagnostics."
target_files_or_folders:
  - "src/abc_quant/pipeline/linear_modeling.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_pipeline_linear_modeling.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #33 merged the train-only ordinary least-squares model contract. The next safe integration step is a deterministic smoke diagnostic that wires the existing smoke fixture through supervised dataset construction, OLS fitting, split predictions, and existing prediction evaluation."
constraints:
  - "Keep this round limited to an in-memory diagnostics pipeline and tests."
  - "Use the existing deterministic smoke fixture and existing supervised dataset defaults where practical."
  - "Fit OLS only through fit_linear_regression(...) on the supervised train split."
  - "Use evaluate_prediction_bundle(...) for split-level prediction diagnostics."
  - "Return only plain JSON-friendly scalar/list/dict values."
  - "Do not change existing smoke outputs, CLI behavior, package scripts, preprocessing, dataset, or linear model contracts."
acceptance_criteria:
  - "Create run_linear_regression_smoke(...) in src/abc_quant/pipeline/linear_modeling.py."
  - "The pipeline builds the deterministic smoke frame, FeatureMatrix, TemporalSplit, StandardScalerFit, StandardizedFeatureMatrix, SupervisedSplitDataset, LinearRegressionResult, and prediction-bundle evaluation."
  - "Return a plain dict containing row_count, feature_columns, label_column, model_name, method, intercept, coefficients, training_row_count, split_counts_after_label_drop, dropped_label_counts, prediction_counts, and evaluation."
  - "Tests verify repeated calls return identical summaries and the summary is JSON serializable."
  - "Tests verify coefficients, intercept, method, and prediction_counts match direct LinearRegressionResult construction from the same supervised dataset."
  - "Tests verify evaluation matches direct evaluate_prediction_bundle(...) output."
  - "Tests verify feature column order, label_column, training_row_count, and dropped_label_counts are preserved."
  - "Tests verify the summary does not expose strategy, allocation, performance-curve, order, position, or simulation keys."
  - "Export run_linear_regression_smoke from src/abc_quant/pipeline/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #33 and only adds diagnostics around the existing train-only OLS contract."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No new estimator implementation."
  - "No parameter search."
  - "No model selection."
  - "No allocation logic."
  - "No strategy signal output."
  - "No performance curve."
  - "No simulation engine."
risk_level: normal
```
