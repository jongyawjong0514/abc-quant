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
task: "Add an optional LightGBM dependency guard and parameter contract."
target_files_or_folders:
  - "src/abc_quant/models/lightgbm.py"
  - "src/abc_quant/models/__init__.py"
  - "tests/test_models_lightgbm.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "The deterministic baseline, OLS, evaluation, comparison, and CLI surfaces are stable. The next safe step toward LightGBM support is an optional dependency guard and validated parameter contract without fitting a model yet."
constraints:
  - "Keep this round limited to dependency detection, parameter validation, tests, and docs."
  - "Do not add lightgbm to mandatory project dependencies in this task."
  - "Use importlib from the Python standard library for dependency detection."
  - "The module must be importable even when lightgbm is not installed."
  - "Do not train or fit any LightGBM model in this task."
  - "Do not change existing model, pipeline, CLI, or smoke outputs."
acceptance_criteria:
  - "Create src/abc_quant/models/lightgbm.py."
  - "Define a frozen LightGBMDependencyStatus dataclass with package_name, installed, and message fields."
  - "Define a frozen LightGBMRegressorParams dataclass with objective, n_estimators, learning_rate, num_leaves, min_data_in_leaf, feature_fraction, bagging_fraction, bagging_freq, random_state, and verbosity fields."
  - "Implement check_lightgbm_dependency() returning LightGBMDependencyStatus without importing lightgbm when it is not present."
  - "Implement require_lightgbm() that returns the imported lightgbm module when available and raises ImportError with a clear message when unavailable."
  - "Implement make_default_lightgbm_regressor_params() returning deterministic conservative defaults."
  - "Validate LightGBMRegressorParams values in __post_init__: positive n_estimators, positive learning_rate, num_leaves at least 2, positive min_data_in_leaf, feature_fraction and bagging_fraction in (0, 1], nonnegative bagging_freq, integer random_state, and objective must be a non-empty string."
  - "Tests verify the module imports when lightgbm is absent."
  - "Tests verify dependency status and require_lightgbm behavior using monkeypatching, without requiring the real package."
  - "Tests verify default parameters are deterministic and valid."
  - "Tests verify invalid parameter values raise clear ValueError messages."
  - "Export the new dataclasses and functions from src/abc_quant/models/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #42 and prepares for optional LightGBM work without adding model fitting yet."
  - "Open a new draft PR for ChatGPT Tech Lead review after completion."
anything_not_allowed:
  - "No secrets."
  - "No outside data access."
  - "No live account connectivity."
  - "No mandatory LightGBM dependency."
  - "No model fitting."
  - "No parameter search."
  - "No model selection."
  - "No allocation logic."
  - "No strategy signal output."
  - "No performance curve."
  - "No simulation engine."
risk_level: normal
```
