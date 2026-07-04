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
task: "Add a command-line entry point for deterministic preprocessing smoke diagnostics."
target_files_or_folders:
  - "src/abc_quant/cli/preprocessing_smoke.py"
  - "src/abc_quant/cli/__init__.py"
  - "tests/test_cli_preprocessing_smoke.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #25 centralized validation for preprocessing smoke summaries. The next safe usability step is a thin CLI wrapper that prints the existing deterministic preprocessing diagnostics as JSON."
constraints:
  - "Keep this round limited to a CLI wrapper around run_preprocessing_smoke(...)."
  - "Use only Python standard library plus existing project code."
  - "Support module execution while preserving the existing modeling smoke CLI behavior."
  - "Do not change preprocessing calculations, summary keys, split defaults, or existing modeling outputs."
  - "The command writes JSON only to stdout and concise errors only to stderr."
acceptance_criteria:
  - "Create src/abc_quant/cli/preprocessing_smoke.py with main(argv=None) -> int."
  - "Support python -m abc_quant.cli.preprocessing_smoke."
  - "Support optional --train-end, --validation-end, and --indent arguments."
  - "Valid invocation prints deterministic JSON with sorted keys and returns exit code 0."
  - "Invalid temporal boundaries return non-zero and print a concise error message to stderr."
  - "Tests parse stdout JSON and verify it matches run_preprocessing_smoke(...)."
  - "Tests verify output is deterministic across repeated module calls."
  - "Tests verify custom split arguments pass through and alter split_counts deterministically."
  - "Tests verify output contains only PREPROCESSING_SMOKE_SUMMARY_KEYS."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #25 and exposes preprocessing diagnostics only."
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
