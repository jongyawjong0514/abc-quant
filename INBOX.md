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
task: "Add a module CLI for LightGBM dependency smoke diagnostics."
target_files_or_folders:
  - "src/abc_quant/cli/lightgbm_dependency_smoke.py"
  - "tests/test_cli_lightgbm_dependency_smoke.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #45 added run_lightgbm_dependency_smoke(...) as a deterministic in-memory diagnostics summary that reports optional LightGBM status and default parameter metadata without fitting. The next safe integration step is a thin module CLI that prints that summary as JSON without adding a packaged console-script alias yet."
constraints:
  - "Keep this round limited to a thin CLI wrapper, tests, and docs/tracking updates."
  - "Use the existing run_lightgbm_dependency_smoke(...) pipeline helper."
  - "Default CLI execution must not require the real lightgbm package."
  - "Default CLI execution must not call require_lightgbm()."
  - "Do not fit any model."
  - "Do not add parameter search, model selection, winner, ranking, or decision output."
  - "Do not add strategy signal, allocation, performance curve, order, position, or simulation output."
  - "Do not add or change packaged console-script entry points in pyproject.toml in this task."
  - "Do not change existing smoke outputs or model/pipeline computation."
acceptance_criteria:
  - "Create src/abc_quant/cli/lightgbm_dependency_smoke.py."
  - "The module exposes main(argv: list[str] | None = None) -> int."
  - "`python -m abc_quant.cli.lightgbm_dependency_smoke` writes the run_lightgbm_dependency_smoke() summary as sorted JSON to stdout and returns exit code 0."
  - "Support an optional --indent integer argument with deterministic JSON output."
  - "The CLI calls run_lightgbm_dependency_smoke() exactly once per invocation."
  - "Tests verify default CLI stdout is JSON-decodable and contains package_name, installed, message, default_params, default_model_name, default_method, and fitting_enabled."
  - "Tests verify --indent changes formatting without changing decoded content."
  - "Tests verify monkeypatched CLI execution does not require real LightGBM and does not expose winner, ranking, decision, selected-model, strategy, allocation, performance-curve, order, position, or simulation keys anywhere in the decoded summary."
  - "Docs describe the module invocation and safety boundary."
  - "Tracking files are updated."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest tests/test_cli_lightgbm_dependency_smoke.py"
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "python -m abc_quant.cli.lightgbm_dependency_smoke --indent 2"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #45 and only adds a module CLI for existing dependency diagnostics."
  - "Do not add a packaged console-script alias in this PR; that can be a separate bounded follow-up if needed."
  - "Open a draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No mandatory LightGBM dependency."
  - "No require_lightgbm() call in default CLI execution."
  - "No model fitting."
  - "No parameter search."
  - "No model selection."
  - "No winner/ranking/decision output."
  - "No allocation logic."
  - "No strategy signal output."
  - "No performance curve."
  - "No order or position output."
  - "No simulation engine."
risk_level: normal
```