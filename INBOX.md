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
task: "Prepare the closed-loop guard for a future CI workflow target by allowing the `.github/` repository folder and adding tests that prove `.git/` remains blocked."
target_files_or_folders:
  - "configs/codex_closed_loop.yaml"
  - "tests/test_codex_loop_guard.py"
  - "docs/codex_closed_loop.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
current_spec_or_decision: "PR #2 has been merged. The next governance step is to prepare the guard for a later CI workflow round. The current guard allows only known repository roots, so `.github/` must be made explicit before workflow files are added later."
constraints:
  - "Keep this round limited to guard configuration, documentation, and tests."
  - "Do not create workflow files in this round."
  - "Do not change trading, data, model, broker, strategy, or backtest code."
  - "Preserve all built-in blocked content and blocked path defaults."
acceptance_criteria:
  - "`configs/codex_closed_loop.yaml` includes `.github/` as an allowed target root."
  - "Tests prove `.github/workflows/ci.yml` is allowed as a target."
  - "Tests prove `.git/config` remains blocked."
  - "Tests prove built-in blocked content patterns are still preserved when config adds custom patterns."
  - "`pytest` passes."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
review_notes_or_defects:
  - "This is a preparatory governance task after PR #2 merge."
  - "A later task may add CI files after this guard update is reviewed."
anything_not_allowed:
  - "No workflow file creation in this round."
  - "No data acquisition."
  - "No broker integration."
  - "No model training."
risk_level: normal
```
