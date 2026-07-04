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
task: "Add a temporal split contract that prevents time leakage before modeling work."
target_files_or_folders:
  - "src/abc_quant/validation/temporal.py"
  - "src/abc_quant/validation/__init__.py"
  - "tests/test_validation_temporal.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #10 merged the feature-matrix contract. Before any model training or backtest work, the project needs an explicit temporal split contract so future train/test definitions cannot leak future dates into training."
constraints:
  - "Keep this round limited to temporal split validation and tests."
  - "Do not train models, fit scalers, build strategies, run backtests, or add source adapters."
  - "Operate on in-memory metadata or data frames only."
  - "Splits must be date-based and deterministic."
  - "Training dates must be strictly before validation/test dates."
  - "Do not drop rows or fill missing labels in this task."
acceptance_criteria:
  - "Create a typed result object for temporal splits with train_index, validation_index, test_index, and date boundary fields."
  - "Implement build_temporal_split(metadata, train_end, validation_end=None, test_end=None, date_column='date')."
  - "Support train/test split and optional train/validation/test split."
  - "Reject missing date column, unsortable dates, empty train split, empty test split, and non-increasing boundaries."
  - "Validation/test rows must not overlap with training rows."
  - "Tests prove train dates are strictly earlier than validation/test dates."
  - "Tests prove shuffled metadata produces identical index membership after sorting."
  - "Tests cover boundary errors and empty split errors."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #10 and prepares for safe model validation later without doing model work now."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No data downloads."
  - "No broker integration."
  - "No model training."
  - "No scaler fitting."
  - "No trading signal changes."
  - "No full backtest engine."
risk_level: normal
```
