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
task: "Wire prediction-bundle evaluation into the modeling smoke pipeline without output changes."
target_files_or_folders:
  - "src/abc_quant/pipeline/modeling.py"
  - "tests/test_pipeline_modeling.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #21 merged generic evaluation for SplitPredictionBundle. The next safe integration step is to use the bundle adapter and bundle evaluator inside the existing modeling smoke pipeline while preserving the public diagnostic summary shape."
constraints:
  - "Keep this round limited to internal pipeline wiring and tests."
  - "Use build_constant_baseline_prediction_bundle(...) and evaluate_prediction_bundle(...) after fitting the existing constant baseline."
  - "The returned summary must keep the same top-level keys and nested evaluation metric keys."
  - "Do not change default method, fitted values, split counts, metric formulas, CLI arguments, or console script behavior."
acceptance_criteria:
  - "Update run_baseline_modeling_smoke(...) to build a constant-baseline prediction bundle and evaluate that bundle."
  - "Continue returning the same diagnostic summary contract validated by validate_modeling_smoke_summary(...)."
  - "Tests verify the default smoke summary remains deterministic and retains the exact expected key set."
  - "Tests verify mean and median fitted_value and baseline_method behavior remain unchanged."
  - "Tests verify evaluation metrics produced through the pipeline match direct evaluate_prediction_bundle(...) results for the same bundle."
  - "Tests verify CLI JSON output remains unchanged in shape and still supports --method median."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #21 and only wires existing bundle contracts into the existing smoke pipeline."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No estimator implementation."
  - "No preprocessing fitting."
  - "No parameter search."
  - "No allocation logic."
  - "No performance curve."
  - "No simulation engine."
risk_level: normal
```
