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
task: "Add a command-line entry point for deterministic modeling smoke diagnostics."
target_files_or_folders:
  - "src/abc_quant/cli/__init__.py"
  - "src/abc_quant/cli/modeling_smoke.py"
  - "tests/test_cli_modeling_smoke.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #14 merged the baseline modeling smoke pipeline. The next safe usability step is a small CLI wrapper that prints the existing deterministic diagnostic summary as JSON without adding new modeling behavior."
constraints:
  - "Keep this round limited to a CLI wrapper around the existing run_baseline_modeling_smoke(...) contract."
  - "Use only Python standard library plus existing project code."
  - "Do not add new model types, fit preprocessing transforms, tune model settings, compute feature importance, or run ablation studies."
  - "Do not write files; output JSON only to stdout and errors only to stderr."
  - "The CLI output must stay limited to the documented diagnostic summary contract."
acceptance_criteria:
  - "Create src/abc_quant/cli/modeling_smoke.py with main(argv=None) -> int."
  - "Support python -m abc_quant.cli.modeling_smoke."
  - "Support optional --train-end, --validation-end, and --indent arguments."
  - "Valid invocation prints deterministic JSON with sorted keys and returns exit code 0."
  - "Invalid date boundaries return non-zero and print a concise error message to stderr."
  - "Tests parse stdout JSON and verify it matches the modeling smoke summary contract."
  - "Tests verify CLI output is deterministic across repeated calls."
  - "Tests verify custom split arguments are passed through and alter split counts deterministically."
  - "Tests verify CLI output contains only documented diagnostic summary keys."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #14 and exposes diagnostics only."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No scaler fitting."
  - "No hyperparameter tuning."
  - "No allocation logic."
  - "No performance curve."
  - "No simulation engine."
risk_level: normal
```
