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
task: "Add a model comparison smoke summary contract validator."
target_files_or_folders:
  - "src/abc_quant/pipeline/contracts.py"
  - "src/abc_quant/pipeline/model_comparison.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_pipeline_model_comparison.py"
  - "tests/test_pipeline_contracts.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #39 merged deterministic baseline-versus-OLS comparison smoke diagnostics. The next safe step is to centralize and validate that model-comparison summary shape before adding CLI surfaces."
constraints:
  - "Keep this round limited to shared constants, summary validation, tests, and docs."
  - "Use only existing project code and Python standard library."
  - "The model comparison smoke summary values must remain unchanged for the default smoke fixture."
  - "Existing modeling, preprocessing, supervised, and linear-regression smoke summary contracts must remain unchanged."
acceptance_criteria:
  - "Define MODEL_COMPARISON_SMOKE_SUMMARY_KEYS in src/abc_quant/pipeline/contracts.py."
  - "Define MODEL_COMPARISON_SMOKE_SPLITS containing train, validation, and test."
  - "Define MODEL_COMPARISON_SMOKE_MODEL_KEYS containing model_name and method."
  - "Define MODEL_COMPARISON_SMOKE_COMPARISON_KEYS for reference_name, candidate_name, train, validation, and test."
  - "Define MODEL_COMPARISON_SMOKE_SPLIT_COMPARISON_KEYS for split_name, reference_name, candidate_name, row_count, non_missing_count, missing_actual_count, mae_delta, rmse_delta, mean_error_delta, and prediction_mean_delta."
  - "Implement validate_model_comparison_smoke_summary(summary) that returns the original summary unchanged when valid."
  - "Validator rejects non-dict summaries, missing top-level keys, unknown top-level keys, malformed model metadata, missing split mappings, unknown split mappings, missing evaluation splits, unknown evaluation splits, missing comparison keys, and unknown comparison keys with clear ValueError messages."
  - "Validator checks split_counts, dropped_label_counts, reference_evaluation, candidate_evaluation, and comparison all use the expected split names."
  - "Validator checks reference_model and candidate_model contain exactly model_name and method."
  - "Validator checks reference_evaluation and candidate_evaluation have model_name, method, train, validation, and test keys."
  - "Validator checks each evaluation split contains the existing EVALUATION_METRIC_KEYS."
  - "Validator checks each comparison split contains the expected split comparison keys."
  - "Use validate_model_comparison_smoke_summary(...) in run_model_comparison_smoke(...) before returning."
  - "Update model comparison smoke tests to import shared constants instead of maintaining local key sets if applicable."
  - "Add focused tests for invalid model comparison summary shapes."
  - "Export the new constants and validator from src/abc_quant/pipeline/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #39 and only hardens the model comparison diagnostics summary shape."
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
