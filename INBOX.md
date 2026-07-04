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
task: "Add a small technical-indicator feature module with strict no-lookahead tests."
target_files_or_folders:
  - "src/abc_quant/features/technical.py"
  - "tests/test_features_technical.py"
  - "tests/test_helpers.py"
  - "docs/data_pipeline.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #8 merged feature/label leakage regression tests. The next safe feature-engineering step is a tiny technical-indicator module with deterministic tests before any model, source adapter, strategy, or backtest work."
constraints:
  - "Keep this round limited to technical-indicator feature engineering and tests."
  - "Implement indicators in pure pandas; do not add TA-Lib or other new dependencies."
  - "Use validate_market_data before computing indicators."
  - "All indicator values at row t may use only the same ticker values at or before t."
  - "Prefer simple indicators only: SMA, EMA, and RSI."
  - "Do not add trading signals, strategy rules, portfolio logic, model training, source adapters, or full backtest logic."
acceptance_criteria:
  - "Create add_technical_indicators(...) in src/abc_quant/features/technical.py."
  - "Support configurable SMA windows, EMA spans, and RSI windows with positive integer validation."
  - "Return a defensive sorted copy by ticker and date."
  - "Feature column names are deterministic, for example sma_3d, ema_3d, and rsi_3d."
  - "Tests verify indicator values for at least one ticker using hand-calculated expectations."
  - "Tests prove indicators are isolated by ticker and do not bleed across tickers."
  - "Tests prove shuffled input produces the same sorted outputs using the existing date+ticker helper."
  - "Tests prove changing future rows does not affect earlier indicator values."
  - "Tests cover invalid or empty window inputs."
  - "Update README, docs, STATUS, OUTBOX, CHANGELOG, and TODO."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #8 and should remain feature-engineering only."
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
