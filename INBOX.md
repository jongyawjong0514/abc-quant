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
task: "Add a helper that converts constant-baseline results into split prediction bundles."
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
current_spec_or_decision: "PR #19 added a generic SplitPredictionBundle. The next safe integration step is a small helper that adapts the existing ConstantBaselineResult into that bundle shape."
constraints:
  - "Keep this round limited to one helper, exports, tests, and docs."
  - "Use the existing ConstantBaselineResult prediction Series exactly as inputs to the bundle builder."
  - "Preserve existing baseline calculation behavior and public CLI behavior."
  - "Do not change existing diagnostic summary keys."
acceptance_criteria:
  - "Implement build_constant_baseline_prediction_bundle(baseline_result, model_name='constant_baseline') in src/abc_quant/models/predictions.py."
  - "Require baseline_result to be a ConstantBaselineResult and raise TypeError otherwise."
  - "Return a SplitPredictionBundle with model_name, method=baseline_result.method, and the train/validation/test prediction Series from baseline_result."
  - "Use build_split_prediction_bundle(...) internally so the same validation and copy-isolation rules apply."
  - "Tests verify default model_name, custom trimmed model_name, method propagation, indices/values, and copied Series isolation."
  - "Tests verify invalid baseline_result type raises a clear TypeError."
  - "Export the helper from src/abc_quant/models/__init__.py."
  - "Existing prediction, baseline, pipeline, and CLI tests still pass."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #19 and only adapts an existing result object to the new bundle shape."
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
