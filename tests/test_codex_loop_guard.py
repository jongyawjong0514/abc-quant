import json

from abc_quant.governance.codex_loop import evaluate_inbox, load_guard_config, run_guard


def _task_yaml(
    *,
    risk_level: str = "normal",
    role: str = "technical_lead",
    task: str = "Add one focused test.",
    target_files_or_folders: list[str] | None = None,
    constraints: list[str] | None = None,
    validation_expected: list[str] | None = None,
    anything_not_allowed: list[str] | None = None,
) -> str:
    targets = target_files_or_folders or ["tests/"]
    constraints = constraints or ["No unrelated refactor."]
    validation_expected = validation_expected or ["python -m pytest"]
    anything_not_allowed = anything_not_allowed or ["No external network."]

    return f"""# INBOX

Current task:

```yaml
role: {role}
task: "{task}"
target_files_or_folders:
{_yaml_list(targets)}
current_spec_or_decision: "Guard test fixture."
constraints:
{_yaml_list(constraints)}
acceptance_criteria:
  - "pytest passes."
validation_expected:
{_yaml_list(validation_expected)}
review_notes_or_defects:
  - "none"
anything_not_allowed:
{_yaml_list(anything_not_allowed)}
risk_level: {risk_level}
```
"""


def _yaml_list(values: list[str]) -> str:
    return "\n".join(f"  - {_yaml_quote(value)}" for value in values)


def _yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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
    inbox = _task_yaml().replace("validation_expected:\n  - 'python -m pytest'\n", "")

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


def test_normal_task_with_destructive_keyword_is_blocked() -> None:
    result = evaluate_inbox(_task_yaml(task="delete old generated files"))

    assert result.status == "blocked_risky"
    assert any("delete" in message for message in result.messages)


def test_normal_task_with_credential_keyword_is_blocked() -> None:
    result = evaluate_inbox(_task_yaml(task="read API token setup"))

    assert result.status == "blocked_risky"
    assert any("token" in message for message in result.messages)


def test_normal_task_with_external_network_keyword_is_blocked() -> None:
    result = evaluate_inbox(_task_yaml(validation_expected=["curl https://example.test"]))

    assert result.status == "blocked_risky"
    assert any("curl" in message for message in result.messages)


def test_target_path_outside_repo_is_blocked() -> None:
    result = evaluate_inbox(_task_yaml(target_files_or_folders=[r"E:\abc\STATUS.md"]))

    assert result.status == "blocked_risky"
    assert any("absolute path" in message or r"E:\abc" in message for message in result.messages)


def test_target_path_dot_git_is_blocked() -> None:
    result = evaluate_inbox(_task_yaml(target_files_or_folders=[".git/config"]))

    assert result.status == "blocked_risky"
    assert any(".git" in message for message in result.messages)


def test_target_path_data_raw_is_blocked() -> None:
    result = evaluate_inbox(_task_yaml(target_files_or_folders=["data/raw/prices.csv"]))

    assert result.status == "blocked_risky"
    assert any("data/raw" in message for message in result.messages)


def test_missing_inbox_file_returns_blocked_invalid_and_writes_report(tmp_path) -> None:
    result = run_guard(root=tmp_path)

    assert result.status == "blocked_invalid"
    report = tmp_path / "reports/codex_loop/latest.json"
    assert report.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "blocked_invalid"
    assert "missing" in payload["messages"][0].lower()


def test_config_file_is_loaded(tmp_path) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "codex_closed_loop.yaml").write_text(
        """
loop:
  inbox_path: INBOX.md
  report_dir: custom_reports
  allowed_risk_levels:
    - normal
  blocked_content_patterns:
    - custom-risk
  blocked_path_patterns:
    - .git
  allowed_target_roots:
    - tests/
  allow_auto_merge: true
""",
        encoding="utf-8",
    )
    (tmp_path / "INBOX.md").write_text(_task_yaml(task="custom-risk task"), encoding="utf-8")

    config = load_guard_config(tmp_path)
    result = run_guard(root=tmp_path)

    assert config.report_dir.as_posix() == "custom_reports"
    assert not config.allow_auto_merge
    assert result.status == "blocked_risky"
    assert (tmp_path / "custom_reports/latest.json").exists()


def test_config_cannot_remove_default_blocked_content_patterns(tmp_path) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "codex_closed_loop.yaml").write_text(
        """
loop:
  allowed_risk_levels:
    - normal
  blocked_content_patterns:
    - custom-risk
  blocked_path_patterns:
    - custom-blocked-path
  allow_auto_merge: true
""",
        encoding="utf-8",
    )
    (tmp_path / "INBOX.md").write_text(_task_yaml(task="read token"), encoding="utf-8")

    config = load_guard_config(tmp_path)
    result = run_guard(root=tmp_path)

    assert "token" in config.blocked_content_patterns
    assert "custom-risk" in config.blocked_content_patterns
    assert result.status == "blocked_risky"
    assert any("token" in message for message in result.messages)


def test_config_cannot_remove_default_blocked_path_patterns(tmp_path) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "codex_closed_loop.yaml").write_text(
        """
loop:
  allowed_risk_levels:
    - normal
  blocked_content_patterns:
    - custom-risk
  blocked_path_patterns:
    - custom-blocked-path
  allow_auto_merge: true
""",
        encoding="utf-8",
    )
    (tmp_path / "INBOX.md").write_text(
        _task_yaml(target_files_or_folders=[".git/config"]), encoding="utf-8"
    )

    config = load_guard_config(tmp_path)
    result = run_guard(root=tmp_path)

    assert ".git" in config.blocked_path_patterns
    assert "custom-blocked-path" in config.blocked_path_patterns
    assert result.status == "blocked_risky"
    assert any(".git" in message for message in result.messages)


def test_config_cannot_enable_auto_merge(tmp_path) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "codex_closed_loop.yaml").write_text(
        """
loop:
  allowed_risk_levels:
    - normal
  blocked_content_patterns:
    - custom-risk
  blocked_path_patterns:
    - custom-blocked-path
  allow_auto_merge: true
""",
        encoding="utf-8",
    )

    config = load_guard_config(tmp_path)

    assert not config.allow_auto_merge


def test_anything_not_allowed_alone_does_not_block() -> None:
    result = evaluate_inbox(
        _task_yaml(task="Add a local docs test.", anything_not_allowed=["No download"])
    )

    assert result.status == "ready"


def test_task_contradicts_anything_not_allowed_blocks() -> None:
    result = evaluate_inbox(
        _task_yaml(task="download a sample file", anything_not_allowed=["No download"])
    )

    assert result.status == "blocked_risky"
    assert any("anything_not_allowed" in message for message in result.messages)
