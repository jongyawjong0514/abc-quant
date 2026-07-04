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
task: "Add a generic evaluator for split prediction bundles."
target_files_or_folders:
  - "src/abc_quant/models/evaluation.py"
  - "src/abc_quant/models/__init__.py"
  - "tests/test_models_evaluation.py"
  - "docs/modeling.md"
  - "README.md"
  - "STATUS.md"
  - "OUTBOX.md"
  - "CHANGELOG.md"
  - "TODO.md"
  - "INBOX.md"
current_spec_or_decision: "PR #20 merged a helper that adapts ConstantBaselineResult into SplitPredictionBundle. The next safe step is a generic in-memory evaluator that evaluates any validated split prediction bundle against FeatureMatrix labels using the existing prediction metrics."
constraints:
  - "Keep this round limited to model-output evaluation contracts and tests."
  - "Use the existing FeatureMatrix, SplitPredictionBundle, PredictionEvaluationResult, and evaluate_predictions(...) contracts."
  - "Do not change existing evaluate_predictions(...), evaluate_constant_baseline(...), pipeline behavior, CLI behavior, or diagnostic summary keys."
  - "Evaluation must use only feature_matrix.y and the prediction Series already stored in the bundle."
acceptance_criteria:
  - "Create a frozen SplitPredictionBundleEvaluationResult dataclass with model_name, method, train, validation, and test fields."
  - "Implement evaluate_prediction_bundle(feature_matrix, prediction_bundle) in src/abc_quant/models/evaluation.py."
  - "Require feature_matrix to be a FeatureMatrix and prediction_bundle to be a SplitPredictionBundle, with clear TypeError messages."
  - "Evaluate train, validation, and test predictions by calling evaluate_predictions(feature_matrix.y, split_predictions, split_name)."
  - "Preserve prediction_bundle.model_name and prediction_bundle.method in the returned result."
  - "Tests verify a valid bundle produces train/validation/test PredictionEvaluationResult objects."
  - "Tests verify missing actual labels are counted and excluded from error metrics through the existing evaluator."
  - "Tests verify invalid input types raise clear TypeError messages."
  - "Tests verify a constant-baseline bundle evaluation matches the existing constant-baseline evaluation split metrics."
  - "Export the new dataclass and evaluator from src/abc_quant/models/__init__.py."
  - "Update docs and tracking files."
  - "INBOX.md is reset to the commented empty template before PR handoff."
validation_expected:
  - "python -m pytest"
  - "python -m compileall src tests"
  - "git diff --check"
  - "GitHub Actions CI should pass on the draft PR."
review_notes_or_defects:
  - "This task follows PR #20 and only evaluates already-built prediction bundles."
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
