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
task: "Add deterministic baseline versus OLS evaluation comparison smoke diagnostics."
target_files_or_folders:
  - "src/abc_quant/pipeline/model_comparison.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_pipeline_model_comparison.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #38 merged a diagnostic-only prediction evaluation comparison contract. The next safe integration step is a deterministic smoke diagnostic that compares constant-baseline and OLS evaluations on the same supervised prediction rows."
constraints:
  - "Keep this round limited to an in-memory diagnostics pipeline and tests."
  - "Use the existing deterministic smoke fixture and existing supervised dataset defaults where practical."
  - "Use the existing constant baseline, OLS, prediction bundle, evaluation, and comparison contracts."
  - "Ensure reference and candidate evaluations use identical prediction indices and split counts before comparison."
  - "Return only plain JSON-friendly scalar/list/dict values."
  - "Do not change existing smoke outputs, CLI behavior, package scripts, preprocessing, dataset, baseline, OLS, or comparison contracts."
acceptance_criteria:
  - "Create run_model_comparison_smoke(...) in src/abc_quant/pipeline/model_comparison.py."
  - "The pipeline builds the deterministic smoke frame, FeatureMatrix, TemporalSplit, train-only scaling, StandardizedFeatureMatrix, and SupervisedSplitDataset."
  - "Fit the constant baseline with train labels only and fit OLS with the supervised train split."
  - "Evaluate both models on the same supervised train, validation, and test prediction indices."
  - "Use compare_prediction_evaluations(...) to compute candidate-minus-reference deltas."
  - "Return a plain dict containing row_count, feature_columns, label_column, reference_model, candidate_model, split_counts, dropped_label_counts, reference_evaluation, candidate_evaluation, and comparison."
  - "Reference model metadata identifies the constant baseline and its method."
  - "Candidate model metadata identifies ordinary least squares and its method."
  - "Tests verify repeated calls return identical summaries and the summary is JSON serializable."
  - "Tests verify split counts match between reference evaluation, candidate evaluation, and comparison."
  - "Tests verify comparison deltas match direct compare_prediction_evaluations(...) output."
  - "Tests verify no winner, ranking, decision, selected-model, strategy, allocation, performance-curve, order, position, or simulation keys appear anywhere in the summary."
  - "Export run_model_comparison_smoke from src/abc_quant/pipeline/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #38 and only compares already-computed diagnostic metrics on aligned prediction rows."
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
