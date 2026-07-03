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
task: "Create the first deterministic market data contract and an end-to-end smoke pipeline for the ABC Quant project."
target_files_or_folders:
  - "src/abc_quant/data/schema.py"
  - "src/abc_quant/data/sample.py"
  - "src/abc_quant/pipeline/smoke.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_data_schema.py"
  - "tests/test_pipeline_smoke.py"
  - "docs/data_pipeline.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "CI is now merged. The next safe step is to add a tiny deterministic market data contract and a smoke pipeline that proves validate, feature, label, and metric modules can run together."
constraints:
  - "Keep this round limited to local deterministic fixtures and pipeline smoke checks."
  - "Do not add live market source integration."
  - "Do not add ML training, strategy rules, portfolio logic, or full backtest engine logic."
  - "Use only repository code and in-memory deterministic fixtures."
  - "Keep changes small, typed, documented, and tested."
acceptance_criteria:
  - "A schema module defines required market columns, numeric columns, and expected dtype intent."
  - "A sample helper returns deterministic multi-ticker market data with at least two tickers and at least ten rows per ticker."
  - "A smoke pipeline validates the sample, creates price and volume features, creates one forward-return label, computes basic metrics, and returns a summary dictionary."
  - "Tests cover the schema constants and the sample helper."
  - "Tests cover the smoke pipeline output keys, feature columns, label column, metric keys, and multi-ticker isolation."
  - "Docs state that the fixture is only for smoke checks and is not a trading signal or performance claim."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
review_notes_or_defects:
  - "This task follows CI setup and prepares the project for safer future data-layer work."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No data downloads."
  - "No broker integration."
  - "No model training."
  - "No trading signal changes."
  - "No full backtest engine."
risk_level: normal
```
