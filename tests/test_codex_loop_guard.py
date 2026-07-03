import json

from abc_quant.governance.codex_loop import evaluate_inbox, run_guard


def _task_yaml(risk_level: str = "normal", role: str = "technical_lead") -> str:
    return f"""# INBOX

Current task:

```yaml
role: {role}
task: "Add one focused test."
target_files_or_folders:
  - "tests/"
current_spec_or_decision: "Guard test fixture."
constraints:
  - "No unrelated refactor."
acceptance_criteria:
  - "pytest passes."
validation_expected:
  - "python -m pytest"
review_notes_or_defects:
  - "none"
anything_not_allowed:
  - "No external network."
risk_level: {risk_level}
```
"""


def test_empty_current_task_returns_no_task() -> None:
    result = evaluate_inbox("# INBOX\n\nCurrent task:\n")

    assert result.status == "no_task"
    assert not result.is_ready


def test_commented_template_returns_no_task() -> None:
    inbox = """# INBOX

Current task:

```yaml
# role: technical_lead
# task: "Replace this template."
# risk_level: normal
```
"""

    result = evaluate_inbox(inbox)

    assert result.status == "no_task"
    assert not result.is_ready


def test_complete_normal_task_is_ready() -> None:
    result = evaluate_inbox(_task_yaml())

    assert result.status == "ready"
    assert result.is_ready
    assert result.risk_level == "normal"
    assert result.task["task"] == "Add one focused test."


def test_missing_required_field_blocks_execution() -> None:
    inbox = _task_yaml().replace("validation_expected:\n  - \"python -m pytest\"\n", "")

    result = evaluate_inbox(inbox)

    assert result.status == "blocked_invalid"
    assert "validation_expected" in result.missing_fields


def test_risky_task_requires_user_confirmation() -> None:
    result = evaluate_inbox(_task_yaml(risk_level="credentialed"))

    assert result.status == "blocked_risky"
    assert result.risk_level == "credentialed"


def test_run_guard_writes_reports(tmp_path) -> None:
    root = tmp_path
    (root / "INBOX.md").write_text(_task_yaml(), encoding="utf-8")

    result = run_guard(root=root)

    assert result.status == "ready"
    payload = json.loads((root / "reports/codex_loop/latest.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ready"
    assert (root / "reports/codex_loop/latest.md").exists()
