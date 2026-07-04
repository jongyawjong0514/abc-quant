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
task: "Add no-lookahead regression tests for price-volume features and forward-return labels before expanding indicators."
target_files_or_folders:
  - "src/abc_quant/features/price_volume.py"
  - "src/abc_quant/labels/returns.py"
  - "tests/test_no_lookahead_contracts.py"
  - "tests/test_price_volume_features.py"
  - "tests/test_labels.py"
  - "docs/data_pipeline.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #7 merged stronger market data validation. Before adding technical indicators, source adapters, models, or backtest logic, the project needs explicit regression tests proving existing feature and label functions preserve ticker isolation and do not let features read future rows."
constraints:
  - "Keep this round limited to no-lookahead and ticker-isolation tests for existing feature and label functions."
  - "Prefer adding tests first; modify production code only if tests reveal a real contract defect."
  - "Features at row t may use only values from the same ticker at or before t."
  - "Forward-return labels may use future prices only as evaluator targets and must remain clearly separate from feature columns."
  - "Do not add new indicators, source adapters, ML logic, strategy logic, portfolio logic, or full backtest logic."
acceptance_criteria:
  - "Tests prove price momentum is computed per ticker and the first momentum row per ticker is missing."
  - "Tests prove rolling volatility is computed per ticker and does not bleed across tickers."
  - "Tests prove rolling volume averages are computed per ticker using only current and prior rows."
  - "Tests prove shuffled input produces the same feature and label values after sorting by ticker and date."
  - "Tests prove forward-return labels respect horizon and entry_lag definitions."
  - "Tests prove final rows without enough future bars have missing labels."
  - "Tests define a reusable assertion pattern for comparing results by date and ticker."
  - "Existing smoke pipeline tests continue to pass."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #7 and protects against the most dangerous quant defect: feature leakage."
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
