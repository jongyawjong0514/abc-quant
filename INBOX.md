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
task: "Add a generic split prediction bundle contract for diagnostics."
target_files_or_folders:
  - "src/abc_quant/models/predictions.py"
  - "src/abc_quant/models/__init__.py"
  - "tests/test_models_predictions.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #18 added package-level discoverability for the existing modeling smoke CLI. The next small model-layer hardening step is a reusable contract for train/validation/test prediction bundles, separate from any specific estimator."
constraints:
  - "Keep this round limited to dataclasses, validation helpers, tests, and docs."
  - "Use pandas Series and existing project dependencies only."
  - "Do not change existing baseline fitted values, split counts, metric formulas, CLI arguments, or summary keys."
  - "Validation must run in memory and avoid side effects."
acceptance_criteria:
  - "Create src/abc_quant/models/predictions.py."
  - "Define a frozen SplitPredictionBundle dataclass with model_name, method, train_predictions, validation_predictions, and test_predictions fields."
  - "Implement build_split_prediction_bundle(model_name, train_predictions, validation_predictions, test_predictions, method=None)."
  - "Normalize non-empty model_name and optional method strings."
  - "Require each prediction input to be a pandas Series with unique index values."
  - "Reject empty train or test predictions, missing prediction values, duplicate indices, and overlapping indices across splits."
  - "Return copied prediction Series so later caller mutation cannot change the bundle."
  - "Tests verify valid bundles, copied series isolation, duplicate-index errors, missing-value errors, overlap errors, and empty split errors."
  - "Export the new contract from src/abc_quant/models/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #18 and adds only a reusable prediction-output shape contract."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No estimator implementation."
  - "No preprocessing fitting."
  - "No parameter search."
  - "No allocation logic."
  - "No performance curve."
  - "No simulation engine."
risk_level: normal
```
