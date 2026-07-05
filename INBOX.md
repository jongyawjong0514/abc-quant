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
task: "Add a prediction evaluation comparison contract."
target_files_or_folders:
  - "src/abc_quant/models/comparison.py"
  - "src/abc_quant/models/__init__.py"
  - "tests/test_models_comparison.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "The baseline, OLS, prediction bundle, and split evaluation contracts are now stable. The next safe modeling foundation is a small in-memory comparison contract that computes metric deltas between two already-evaluated prediction bundles."
constraints:
  - "Keep this round limited to comparison dataclasses, validation, tests, and docs."
  - "Use existing SplitPredictionBundleEvaluationResult and PredictionEvaluationResult objects."
  - "Use only Python standard library and existing project code."
  - "Compute candidate-minus-reference deltas for numeric evaluation metrics only."
  - "Do not refit models, recompute predictions, read market data, or alter existing smoke outputs."
acceptance_criteria:
  - "Create src/abc_quant/models/comparison.py."
  - "Define a frozen SplitEvaluationComparison dataclass with split_name, reference_name, candidate_name, row_count, non_missing_count, missing_actual_count, mae_delta, rmse_delta, mean_error_delta, and prediction_mean_delta fields."
  - "Define a frozen PredictionEvaluationComparison dataclass with reference_name, candidate_name, train, validation, and test fields."
  - "Implement compare_prediction_evaluations(reference, candidate, reference_name='reference', candidate_name='candidate')."
  - "Require reference and candidate to be SplitPredictionBundleEvaluationResult instances, with clear TypeError messages."
  - "Normalize reference_name and candidate_name as non-empty strings, with clear ValueError messages."
  - "Reject mismatched row_count, non_missing_count, or missing_actual_count within any split with clear ValueError messages."
  - "For each split, compute candidate minus reference for mae, rmse, mean_error, and prediction_mean."
  - "Preserve split names train, validation, and test in the returned dataclasses."
  - "Tests verify exact deterministic deltas on small evaluation objects."
  - "Tests verify negative deltas are preserved and not converted into rankings or decisions."
  - "Tests verify invalid input types, blank names, and mismatched split counts are rejected."
  - "Tests verify dataclasses are frozen."
  - "Export the new dataclasses and compare function from src/abc_quant/models/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #37 and only compares already-computed diagnostic metrics."
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
