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
task: "Add a supervised split dataset contract from standardized features and labels."
target_files_or_folders:
  - "src/abc_quant/models/dataset.py"
  - "src/abc_quant/models/__init__.py"
  - "tests/test_models_dataset.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "The preprocessing and modeling smoke CLIs are now discoverable through package scripts. The next safe modeling foundation is a reusable in-memory contract that combines standardized split features with aligned labels before any estimator work."
constraints:
  - "Keep this round limited to dataset-shape contracts, validation, tests, and docs."
  - "Use FeatureMatrix labels and StandardizedFeatureMatrix split frames already produced by existing contracts."
  - "Preserve feature column order, split order, and pandas indices after label filtering."
  - "Do not change existing preprocessing smoke output, modeling smoke output, CLI behavior, or package scripts."
acceptance_criteria:
  - "Create src/abc_quant/models/dataset.py."
  - "Define a frozen SupervisedSplitDataset dataclass with feature_columns, label_column, train_X, train_y, validation_X, validation_y, test_X, test_y, and dropped_label_counts fields."
  - "Implement build_supervised_split_dataset(feature_matrix, standardized_features, drop_missing_labels=True)."
  - "Require feature_matrix to be a FeatureMatrix and standardized_features to be a StandardizedFeatureMatrix, with clear TypeError messages."
  - "Align labels from feature_matrix.y using the split indices stored in standardized_features.fitted."
  - "When drop_missing_labels is true, drop rows with missing labels independently per split and record counts by split."
  - "When drop_missing_labels is false, reject any missing label with a clear ValueError message."
  - "Reject empty train data after label filtering."
  - "Return copied feature frames and label Series so later caller mutation cannot change the dataset."
  - "Tests verify valid construction, label alignment, missing-label filtering, dropped counts, no-drop error behavior, copied-data isolation, and feature column order preservation."
  - "Export the new dataclass and builder from src/abc_quant/models/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #27 and only prepares supervised model input data in memory."
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
