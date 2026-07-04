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
task: "Add a linear regression smoke summary contract validator."
target_files_or_folders:
  - "src/abc_quant/pipeline/contracts.py"
  - "src/abc_quant/pipeline/linear_modeling.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_pipeline_linear_modeling.py"
  - "tests/test_pipeline_contracts.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #34 merged deterministic train-only OLS smoke diagnostics. The next safe step is to centralize and validate that linear-regression summary shape before adding CLI surfaces."
constraints:
  - "Keep this round limited to shared constants, summary validation, tests, and docs."
  - "Use only existing project code and Python standard library."
  - "The linear regression smoke summary values must remain unchanged for the default smoke fixture."
  - "Existing modeling, preprocessing, and supervised smoke summary contracts must remain unchanged."
acceptance_criteria:
  - "Define LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS in src/abc_quant/pipeline/contracts.py."
  - "Define LINEAR_REGRESSION_SMOKE_SPLITS containing train, validation, and test."
  - "Define LINEAR_REGRESSION_SMOKE_EVALUATION_KEYS using the existing evaluation metric keys."
  - "Implement validate_linear_regression_smoke_summary(summary) that returns the original summary unchanged when valid."
  - "Validator rejects non-dict summaries, missing top-level keys, unknown top-level keys, missing split mappings, unknown split mappings, missing evaluation splits, unknown evaluation splits, missing evaluation metric keys, and unknown evaluation metric keys with clear ValueError messages."
  - "Validator checks split_counts_after_label_drop, dropped_label_counts, prediction_counts, and evaluation all use the expected split names."
  - "Validator checks coefficients is a dict and feature_columns is a list."
  - "Use validate_linear_regression_smoke_summary(...) in run_linear_regression_smoke(...) before returning."
  - "Update linear regression smoke tests to import shared constants instead of maintaining local key sets if applicable."
  - "Add focused tests for invalid linear regression summary shapes."
  - "Export the new constants and validator from src/abc_quant/pipeline/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #34 and only hardens the OLS diagnostics summary shape."
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
