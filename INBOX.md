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
task: "Harden market data validation so the schema contract is enforced before future data-layer work expands."
target_files_or_folders:
  - "src/abc_quant/data/validation.py"
  - "src/abc_quant/data/schema.py"
  - "tests/test_data_validation.py"
  - "tests/test_data_schema.py"
  - "tests/test_pipeline_smoke.py"
  - "docs/data_pipeline.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #6 merged the deterministic smoke pipeline. Before adding richer features or real source adapters, market data validation must enforce schema constants, numeric OHLCV, non-negative volume, and OHLC consistency."
constraints:
  - "Keep this round limited to market data validation hardening and tests."
  - "Use schema.py constants instead of duplicated literal column sets where practical."
  - "Return a defensive normalized copy sorted by ticker and date."
  - "Use clear MarketDataValidationError messages for invalid rows or invalid columns."
  - "Do not add source adapters, ML logic, strategy logic, portfolio logic, or full backtest logic."
acceptance_criteria:
  - "validation.py imports and uses schema.py constants for required and numeric market columns."
  - "validate_market_data converts date to datetime and ticker to string in the returned copy."
  - "validate_market_data rejects non-numeric OHLCV values with MarketDataValidationError."
  - "validate_market_data rejects missing OHLCV values with MarketDataValidationError."
  - "validate_market_data rejects negative volume."
  - "validate_market_data rejects high lower than low."
  - "validate_market_data rejects open outside the high-low range."
  - "validate_market_data rejects close outside the high-low range."
  - "Existing smoke pipeline tests continue to pass."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #6. It should strengthen the data contract without adding new research logic."
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
