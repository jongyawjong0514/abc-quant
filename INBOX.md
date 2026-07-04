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
task: "Add a modeling diagnostics summary contract validator."
target_files_or_folders:
  - "src/abc_quant/pipeline/contracts.py"
  - "src/abc_quant/pipeline/modeling.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_pipeline_contracts.py"
  - "tests/test_pipeline_modeling.py"
  - "tests/test_cli_modeling_smoke.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #15 added a CLI that prints deterministic modeling diagnostics as JSON. The next safe step is to centralize the summary-shape contract so pipeline and CLI tests rely on the same validator."
constraints:
  - "Keep this round limited to validating in-memory diagnostic summary dictionaries."
  - "Use only Python standard library plus existing project code."
  - "Do not add new prediction methods or change numeric calculations."
  - "Validator should check required top-level keys, evaluation split names, and evaluation metric keys."
  - "Validator should reject unknown top-level keys with deterministic error messages."
  - "Do not write files; all checks must run in memory."
acceptance_criteria:
  - "Create src/abc_quant/pipeline/contracts.py."
  - "Define MODELING_SMOKE_SUMMARY_KEYS and EVALUATION_METRIC_KEYS constants."
  - "Implement validate_modeling_smoke_summary(summary) that returns the validated summary unchanged."
  - "Reject non-dict summaries, missing top-level keys, unknown top-level keys, missing evaluation splits, missing metric keys, and unknown metric keys."
  - "Use the validator in run_baseline_modeling_smoke(...) before returning the summary."
  - "Update CLI and pipeline tests to import the shared constants instead of duplicating key sets."
  - "Tests verify valid smoke summary passes the validator."
  - "Tests verify invalid summary shapes raise clear ValueError messages."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #15 and only hardens the diagnostic summary contract."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No model training."
  - "No preprocessing fitting."
  - "No parameter search."
  - "No allocation logic."
  - "No performance curve."
  - "No simulation engine."
risk_level: normal
```
