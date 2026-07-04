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
task: "Create a feature-matrix assembly contract that safely separates features, labels, and metadata."
target_files_or_folders:
  - "src/abc_quant/features/matrix.py"
  - "src/abc_quant/features/__init__.py"
  - "tests/test_features_matrix.py"
  - "tests/test_helpers.py"
  - "docs/feature_engineering.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #9 merged price/volume and technical feature modules. Before any model or backtest work, the project needs a safe feature-matrix contract that prevents label leakage and preserves date/ticker metadata."
constraints:
  - "Keep this round limited to dataset assembly contracts and tests."
  - "Do not train models, build strategies, run backtests, or add source adapters."
  - "Feature columns must exclude date, ticker, OHLCV raw columns, and any column whose name starts with label_."
  - "Label columns must be explicit and may not be included in the feature matrix."
  - "Return sorted outputs by date and ticker or by ticker and date, but make the ordering deterministic and documented."
  - "Do not scale, impute, fill missing values, or split train/test in this task."
acceptance_criteria:
  - "Create a dataclass or typed result object for feature matrix assembly with X, y, metadata, feature_columns, and label_column fields."
  - "Implement build_feature_matrix(frame, label_column, feature_columns=None) in src/abc_quant/features/matrix.py."
  - "If feature_columns is None, infer only safe feature columns and exclude metadata, OHLCV, and label columns."
  - "Raise clear ValueError when label_column is missing, included in feature_columns, or no feature columns remain."
  - "Metadata must include date and ticker and preserve one row per input row after deterministic sorting."
  - "Tests verify inferred features exclude labels and raw OHLCV columns."
  - "Tests verify explicit feature column selection preserves order and rejects label leakage."
  - "Tests verify shuffled input produces the same X, y, and metadata after deterministic sorting."
  - "Tests verify missing labels are preserved, not silently dropped or filled."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #9 and prepares for safe modeling later without doing model work now."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No data downloads."
  - "No broker integration."
  - "No model training."
  - "No trading signal changes."
  - "No train/test split."
  - "No full backtest engine."
risk_level: normal
```
