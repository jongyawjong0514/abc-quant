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
task: "Add deterministic LightGBM dependency smoke diagnostics."
target_files_or_folders:
  - "src/abc_quant/pipeline/lightgbm_diagnostics.py"
  - "src/abc_quant/pipeline/__init__.py"
  - "tests/test_pipeline_lightgbm_diagnostics.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #44 merged a train-only LightGBM regressor fit contract behind the optional dependency guard. The next safe integration step is a deterministic diagnostics summary that reports optional dependency status and default parameter metadata without fitting by default."
constraints:
  - "Keep this round limited to an in-memory diagnostics summary, tests, and docs."
  - "Use existing LightGBM dependency and parameter contracts."
  - "Do not require the real lightgbm package for tests or default execution."
  - "Return only JSON-friendly scalar/list/dict values."
  - "Default execution must not fit a model, run parameter search, select a model, or create strategy outputs."
  - "Do not change existing model, pipeline, CLI, package script, or smoke outputs."
acceptance_criteria:
  - "Create run_lightgbm_dependency_smoke(...) in src/abc_quant/pipeline/lightgbm_diagnostics.py."
  - "The summary includes package_name, installed, message, default_params, default_model_name, default_method, and fitting_enabled fields."
  - "default_params is derived from make_default_lightgbm_regressor_params() and contains objective, n_estimators, learning_rate, num_leaves, min_data_in_leaf, feature_fraction, bagging_fraction, bagging_freq, random_state, and verbosity."
  - "Default fitting_enabled is false and no LightGBM model is fit."
  - "The function uses check_lightgbm_dependency() only and does not call require_lightgbm() by default."
  - "Tests verify deterministic JSON-serializable output when lightgbm is absent using monkeypatching."
  - "Tests verify deterministic JSON-serializable output when lightgbm is reported available using monkeypatching."
  - "Tests verify default_params matches make_default_lightgbm_regressor_params()."
  - "Tests verify no winner, ranking, decision, selected-model, strategy, allocation, performance-curve, order, position, or simulation keys appear anywhere in the summary."
  - "Export run_lightgbm_dependency_smoke from src/abc_quant/pipeline/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #44 and only exposes dependency diagnostics; it does not invoke LightGBM fitting."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No mandatory LightGBM dependency."
  - "No model fitting by default."
  - "No parameter search."
  - "No model selection."
  - "No allocation logic."
  - "No strategy signal output."
  - "No performance curve."
  - "No simulation engine."
risk_level: normal
```
