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
task: "Add train-only numeric feature standardization without full-sample leakage."
target_files_or_folders:
  - "src/abc_quant/preprocessing/__init__.py"
  - "src/abc_quant/preprocessing/scaling.py"
  - "tests/test_preprocessing_scaling.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "The modeling diagnostics path is now stable through feature matrix, temporal split, baseline prediction bundle, and evaluation. Before adding any non-trivial estimator, preprocessing must guarantee that numeric feature standardization is fitted on training rows only and then applied to later splits."
constraints:
  - "Keep this round limited to preprocessing contracts and leakage-focused tests."
  - "Use only pandas/numpy already available in the project; do not add sklearn or new dependencies."
  - "Fit means and standard deviations using only temporal_split.train_index rows."
  - "Apply the fitted parameters to train, validation, and test rows without changing row order."
  - "Do not alter metadata, labels, feature names, or existing modeling smoke output."
acceptance_criteria:
  - "Create a frozen StandardScalerFit dataclass with feature_columns, means, stds, train_index, validation_index, and test_index fields."
  - "Create a frozen StandardizedFeatureMatrix dataclass with train, validation, test, and fitted fields."
  - "Implement fit_standard_scaler(feature_matrix, temporal_split, feature_columns=None)."
  - "Implement transform_with_standard_scaler(feature_matrix, fitted_scaler, temporal_split)."
  - "Validation/test extreme feature values must not change fitted train means or stds."
  - "Transformed outputs must preserve split indices, row counts, and feature column order."
  - "Reject empty train split, unknown feature columns, duplicate feature columns, nonnumeric columns, missing train feature values, and zero-variance training features with clear ValueError messages."
  - "Tests cover train-only fit, validation/test non-leakage, index/column preservation, and error cases."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #22 and prepares safe modeling without training any estimator."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No estimator implementation."
  - "No parameter search."
  - "No allocation logic."
  - "No performance curve."
  - "No simulation engine."
risk_level: normal
```
