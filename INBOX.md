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
task: "Add deterministic preprocessing smoke diagnostics for train-only scaling."
target_files_or_folders:
  - "src/abc_quant/pipeline/preprocessing.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_pipeline_preprocessing.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #23 merged train-only numeric feature standardization. The next safe step is a deterministic preprocessing smoke diagnostic that wires the existing smoke frame, feature matrix, temporal split, and scaler contracts together."
constraints:
  - "Keep this round limited to an in-memory preprocessing diagnostics pipeline and tests."
  - "Use the existing deterministic smoke fixture and existing temporal split defaults where practical."
  - "Keep this new preprocessing smoke path separate from the existing modeling smoke CLI and modeling smoke summary contract."
  - "The returned object should be a plain dictionary with deterministic scalar/list/dict values suitable for JSON serialization."
acceptance_criteria:
  - "Create run_preprocessing_smoke(...) in src/abc_quant/pipeline/preprocessing.py."
  - "The pipeline builds the deterministic smoke frame, FeatureMatrix, TemporalSplit, StandardScalerFit, and StandardizedFeatureMatrix."
  - "Return a plain dict containing row_count, feature_columns, split_counts, fitted_means, fitted_stds, train_mean_after_scaling, train_std_after_scaling, and split_shape diagnostics."
  - "Tests verify repeated calls return identical summaries."
  - "Tests verify fitted_means and fitted_stds are based only on train rows by comparing against direct train-split calculations."
  - "Tests verify train_mean_after_scaling is approximately zero and train_std_after_scaling is approximately one for every feature."
  - "Tests verify validation/test row counts and columns are preserved."
  - "Export run_preprocessing_smoke from src/abc_quant/pipeline/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #23 and only adds deterministic preprocessing diagnostics."
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
