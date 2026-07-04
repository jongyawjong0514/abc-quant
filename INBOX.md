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
task: "Add deterministic supervised dataset smoke diagnostics."
target_files_or_folders:
  - "src/abc_quant/pipeline/supervised.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_pipeline_supervised.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #28 merged the supervised split dataset contract. The next safe integration step is a deterministic smoke diagnostic that wires the existing smoke fixture through feature matrix, temporal split, train-only scaling, and supervised dataset construction."
constraints:
  - "Keep this round limited to an in-memory supervised dataset diagnostics pipeline and tests."
  - "Use the existing deterministic smoke fixture and existing preprocessing defaults where practical."
  - "Use build_supervised_split_dataset(..., drop_missing_labels=True)."
  - "Return only plain JSON-friendly scalar/list/dict values."
  - "Do not change existing preprocessing smoke output, modeling smoke output, CLI behavior, or package scripts."
acceptance_criteria:
  - "Create run_supervised_dataset_smoke(...) in src/abc_quant/pipeline/supervised.py."
  - "The pipeline builds the deterministic smoke frame, FeatureMatrix, TemporalSplit, StandardScalerFit, StandardizedFeatureMatrix, and SupervisedSplitDataset."
  - "Return a plain dict containing row_count, feature_columns, label_column, split_counts_before_label_drop, split_counts_after_label_drop, dropped_label_counts, and split_shape diagnostics."
  - "Tests verify repeated calls return identical summaries and the summary is JSON serializable."
  - "Tests verify split_counts_before_label_drop are derived from the standardized split frames."
  - "Tests verify split_counts_after_label_drop and dropped_label_counts match direct SupervisedSplitDataset construction."
  - "Tests verify train data remains non-empty after label filtering."
  - "Tests verify feature column order and label_column are preserved."
  - "Tests verify the summary does not expose strategy, allocation, performance-curve, or simulation keys."
  - "Export run_supervised_dataset_smoke from src/abc_quant/pipeline/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #28 and only adds supervised dataset diagnostics."
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
