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
task: "Add a packaged console-script alias for the model comparison smoke CLI."
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
current_spec_or_decision: "PR #41 added module execution for model comparison smoke diagnostics. The next small usability step is to expose the same CLI through package metadata while preserving python -m execution."
constraints:
  - "Keep this round limited to package metadata, importability checks, and documentation."
  - "The new console-script target must call abc_quant.cli.model_comparison_smoke:main."
  - "Preserve python -m abc_quant.cli.model_comparison_smoke behavior."
  - "Use only Python standard library for new tests."
  - "Do not change model comparison calculations, summary keys, split defaults, baseline-method choices, or CLI argument semantics."
acceptance_criteria:
  - "Add a project script named abc-quant-model-comparison-smoke in pyproject.toml."
  - "The script target is exactly abc_quant.cli.model_comparison_smoke:main."
  - "Update tests that parse pyproject.toml with tomllib and verify modeling, preprocessing, supervised, linear-regression, and model-comparison script entries."
  - "Add tests that import the configured target and confirm it resolves to the same model-comparison main function."
  - "Add tests that call the resolved function with --indent 2 and parse valid JSON."
  - "Add tests that call the resolved function with --baseline-method median and parse valid JSON."
  - "Existing model-comparison CLI tests still pass."
  - "Existing modeling, preprocessing, supervised, and OLS console-script tests still pass."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #41 and only adds package-level discoverability for the existing model comparison diagnostics CLI."
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
