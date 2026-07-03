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
task: "Create a minimal GitHub Actions CI workflow for the ABC Quant repository that runs Python quality gates on pull requests and pushes."
target_files_or_folders:
  - ".github/workflows/ci.yml"
  - "docs/codex_closed_loop.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
current_spec_or_decision: "PR #3 merged and `.github/` is now an allowed closed-loop target root. The next governance step is to add a minimal CI workflow so future Codex PRs have repeatable repository checks."
constraints:
  - "Keep this round limited to CI workflow setup and related governance docs."
  - "Use supported official GitHub Actions for checkout and Python setup."
  - "Use Python 3.11 and 3.12 if practical; otherwise use Python 3.12 only and document the reason."
  - "Run pytest, compileall, and ruff when available in the CI environment."
  - "Keep the workflow small, readable, and easy to maintain."
acceptance_criteria:
  - "`.github/workflows/ci.yml` exists."
  - "CI runs on pull_request and push to main."
  - "CI installs the project with development extras or equivalent test dependencies."
  - "CI runs `python -m pytest`."
  - "CI runs `python -m compileall src tests`."
  - "CI runs `ruff check .` or documents why ruff is skipped."
  - "Local validation passes before opening a PR."
  - "`INBOX.md` is reset to the commented empty template before the PR is marked ready."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
review_notes_or_defects:
  - "This task follows PR #3, which prepared `.github/` as an allowed target root."
  - "After implementation, open a new draft PR for ChatGPT review."
anything_not_allowed:
  - "No secrets."
  - "No deployment."
  - "No publishing."
  - "No data acquisition."
  - "No broker integration."
  - "No model training."
  - "No trading signal changes."
risk_level: normal
```
