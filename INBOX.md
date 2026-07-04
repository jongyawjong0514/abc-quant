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
# role: technical_lead
# task: "Replace this template with one bounded task."
# target_files_or_folders:
#   - "src/abc_quant/..."
# current_spec_or_decision: "Why this task is valid now."
# constraints:
#   - "Keep the change small and reversible."
# acceptance_criteria:
#   - "Focused tests cover the behavior."
# validation_expected:
#   - "python -m pytest"
# review_notes_or_defects:
#   - "none"
# anything_not_allowed:
#   - "No destructive, credentialed, external, or materially risky work."
# risk_level: normal
```
