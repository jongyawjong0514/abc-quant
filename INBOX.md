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
task: "Add a preprocessing smoke summary contract validator."
target_files_or_folders:
  - "src/abc_quant/pipeline/contracts.py"
  - "src/abc_quant/pipeline/preprocessing.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_pipeline_preprocessing.py"
  - "tests/test_pipeline_contracts.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #24 merged deterministic preprocessing smoke diagnostics. The next safe step is to centralize and validate that preprocessing summary shape before adding more usability surfaces."
constraints:
  - "Keep this round limited to shared constants, summary validation, tests, and docs."
  - "Use only existing project code and Python standard library."
  - "The preprocessing smoke summary values must remain unchanged for the default smoke fixture."
  - "The modeling smoke summary contract must remain unchanged."
acceptance_criteria:
  - "Define PREPROCESSING_SMOKE_SUMMARY_KEYS in src/abc_quant/pipeline/contracts.py."
  - "Define PREPROCESSING_SMOKE_SPLITS containing train, validation, and test."
  - "Implement validate_preprocessing_smoke_summary(summary) that returns the original summary unchanged when valid."
  - "Validator rejects non-dict summaries, missing top-level keys, unknown top-level keys, missing split count keys, unknown split count keys, missing split_shape keys, and unknown split_shape keys with clear ValueError messages."
  - "Validator confirms each split_shape entry contains only rows and columns keys."
  - "Use validate_preprocessing_smoke_summary(...) in run_preprocessing_smoke(...) before returning."
  - "Update preprocessing smoke tests to import shared constants instead of maintaining a local key set."
  - "Add focused tests for invalid preprocessing summary shapes."
  - "Export the new constants and validator from src/abc_quant/pipeline/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #24 and only hardens the preprocessing diagnostics summary shape."
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
