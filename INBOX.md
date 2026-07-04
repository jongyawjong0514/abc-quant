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
task: "Allow the modeling smoke diagnostics to choose the existing constant-baseline method."
target_files_or_folders:
  - "src/abc_quant/pipeline/modeling.py"
  - "src/abc_quant/cli/modeling_smoke.py"
  - "tests/test_pipeline_modeling.py"
  - "tests/test_cli_modeling_smoke.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "The constant baseline already supports mean and median. The diagnostics pipeline and CLI currently use the default only. Add a small option so existing methods can be selected explicitly."
constraints:
  - "Keep this round limited to plumbing the existing constant-baseline method argument through the pipeline and CLI."
  - "Allowed values are mean and median only."
  - "Use only existing project code and Python standard library."
  - "Do not change feature generation, split construction, metric formulas, or summary key names."
  - "Do not write output files; the CLI continues to print JSON to stdout and errors to stderr."
acceptance_criteria:
  - "Add a method parameter to run_baseline_modeling_smoke(...), defaulting to mean."
  - "Pass the selected method to fit_constant_baseline(...)."
  - "Include baseline_method in the diagnostic summary and shared summary contract."
  - "Add --method with choices mean and median to python -m abc_quant.cli.modeling_smoke."
  - "Tests verify default output remains deterministic."
  - "Tests verify median changes fitted_value deterministically compared with mean on the smoke fixture."
  - "Tests verify CLI --method median passes through and emits baseline_method=median."
  - "Tests verify invalid method is rejected by argparse or the existing baseline method validation."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #16 and only exposes an existing constant-baseline option."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No new estimator implementation."
  - "No preprocessing fitting."
  - "No parameter search."
  - "No allocation logic."
  - "No performance curve."
  - "No simulation engine."
risk_level: normal
```
