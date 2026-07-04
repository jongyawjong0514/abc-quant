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
# Leave this block empty or replace it with one bounded task.
# role: technical_lead
# task: "One focused, verifiable implementation task."
# target_files_or_folders:
#   - "src/abc_quant/..."
# current_spec_or_decision: "Why this should be done now."
# constraints:
#   - "No unrelated refactor."
# acceptance_criteria:
#   - "Specific observable pass condition."
# validation_expected:
#   - "python -m pytest"
# review_notes_or_defects:
#   - "none"
# anything_not_allowed:
#   - "No external API calls."
# risk_level: normal
```
