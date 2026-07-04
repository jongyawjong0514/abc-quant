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
task: "Add a packaged console-script alias for the preprocessing smoke CLI."
target_files_or_folders:
  - "pyproject.toml"
  - "tests/test_cli_entrypoints.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #26 added module execution for preprocessing smoke diagnostics. The next small usability step is to expose the same CLI through package metadata while preserving python -m execution."
constraints:
  - "Keep this round limited to package metadata, importability checks, and documentation."
  - "The new console-script target must call abc_quant.cli.preprocessing_smoke:main."
  - "Preserve python -m abc_quant.cli.preprocessing_smoke behavior."
  - "Use only Python standard library for new tests."
  - "Do not change preprocessing calculations, summary keys, split defaults, or CLI argument semantics."
acceptance_criteria:
  - "Add a project script named abc-quant-preprocessing-smoke in pyproject.toml."
  - "The script target is exactly abc_quant.cli.preprocessing_smoke:main."
  - "Update tests that parse pyproject.toml with tomllib and verify script entries."
  - "Add tests that import the configured target and confirm it resolves to the same preprocessing main function."
  - "Add tests that call the resolved function with --indent 2 and parse valid JSON."
  - "Existing preprocessing CLI tests still pass."
  - "Existing modeling console-script tests still pass."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #26 and only adds package-level discoverability for the existing preprocessing CLI."
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
