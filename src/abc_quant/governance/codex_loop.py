"""Guard rails for the file-based Codex/ChatGPT closed loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import re
from typing import Any

import yaml

REQUIRED_TASK_FIELDS: tuple[str, ...] = (
    "role",
    "task",
    "target_files_or_folders",
    "current_spec_or_decision",
    "constraints",
    "acceptance_criteria",
    "validation_expected",
    "review_notes_or_defects",
    "anything_not_allowed",
    "risk_level",
)

KNOWN_RISK_LEVELS: frozenset[str] = frozenset(
    {"normal", "destructive", "credentialed", "external", "materially_risky"}
)
DEFAULT_ALLOWED_RISK_LEVELS: frozenset[str] = frozenset({"normal"})
DEFAULT_REPORT_DIR = Path("reports/codex_loop")


@dataclass(frozen=True)
class LoopGuardResult:
    """Result of validating the current closed-loop inbox task."""

    status: str
    risk_level: str | None
    missing_fields: tuple[str, ...]
    messages: tuple[str, ...]
    task: dict[str, Any]

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"


def evaluate_inbox(
    inbox_text: str,
    *,
    allowed_risk_levels: set[str] | frozenset[str] = DEFAULT_ALLOWED_RISK_LEVELS,
) -> LoopGuardResult:
    """Validate the `Current task` section of `INBOX.md`."""

    current_task = extract_current_task(inbox_text)
    if not current_task:
        return LoopGuardResult(
            status="no_task",
            risk_level=None,
            missing_fields=(),
            messages=("No current task found after `Current task:`.",),
            task={},
        )

    task = parse_task_block(current_task)
    if not task:
        return LoopGuardResult(
            status="no_task",
            risk_level=None,
            missing_fields=(),
            messages=("No parseable current task found after `Current task:`.",),
            task={},
        )

    missing = tuple(field for field in REQUIRED_TASK_FIELDS if _is_blank(task.get(field)))
    if missing:
        return LoopGuardResult(
            status="blocked_invalid",
            risk_level=_normalize_risk(task.get("risk_level")),
            missing_fields=missing,
            messages=("Current task is missing required fields.",),
            task=task,
        )

    risk_level = _normalize_risk(task.get("risk_level"))
    if risk_level not in KNOWN_RISK_LEVELS:
        return LoopGuardResult(
            status="blocked_invalid",
            risk_level=risk_level,
            missing_fields=(),
            messages=(f"Unknown risk level: {risk_level!r}.",),
            task=task,
        )
    if risk_level not in allowed_risk_levels:
        return LoopGuardResult(
            status="blocked_risky",
            risk_level=risk_level,
            missing_fields=(),
            messages=(f"Risk level `{risk_level}` requires explicit user confirmation.",),
            task=task,
        )

    if str(task.get("role", "")).strip().lower() != "technical_lead":
        return LoopGuardResult(
            status="blocked_invalid",
            risk_level=risk_level,
            missing_fields=(),
            messages=("Task role must be `technical_lead`.",),
            task=task,
        )

    return LoopGuardResult(
        status="ready",
        risk_level=risk_level,
        missing_fields=(),
        messages=("Current task is complete and allowed for local closed-loop execution.",),
        task=task,
    )


def extract_current_task(inbox_text: str) -> str:
    """Return the text after the first `Current task:` marker."""

    match = re.search(r"(?im)^Current task:\s*$", inbox_text)
    if not match:
        return ""
    return inbox_text[match.end() :].strip()


def parse_task_block(task_text: str) -> dict[str, Any]:
    """Parse a fenced YAML task block or simple `Field: value` lines."""

    fenced = re.search(r"```(?:ya?ml)?\s*(.*?)```", task_text, flags=re.DOTALL | re.I)
    source = fenced.group(1) if fenced else task_text

    try:
        parsed = yaml.safe_load(source)
    except yaml.YAMLError:
        parsed = None

    if isinstance(parsed, dict):
        return {_normalize_key(str(key)): value for key, value in parsed.items()}

    task: dict[str, Any] = {}
    for line in source.splitlines():
        if line.lstrip().startswith("#"):
            continue
        match = re.match(r"^\s*-?\s*([^:]+):\s*(.*)$", line)
        if match:
            task[_normalize_key(match.group(1))] = match.group(2).strip()
    return task


def run_guard(
    *,
    root: Path,
    inbox_path: Path | None = None,
    report_dir: Path | None = None,
) -> LoopGuardResult:
    """Read the inbox, evaluate it, and write latest guard reports."""

    inbox = inbox_path or root / "INBOX.md"
    result = evaluate_inbox(inbox.read_text(encoding="utf-8"))
    output_dir = report_dir or root / DEFAULT_REPORT_DIR
    write_guard_reports(result, output_dir)
    return result


def write_guard_reports(result: LoopGuardResult, report_dir: Path) -> None:
    """Write JSON and Markdown guard reports."""

    report_dir.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    (report_dir / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (report_dir / "latest.md").write_text(render_markdown_report(result), encoding="utf-8")


def render_markdown_report(result: LoopGuardResult) -> str:
    """Render a human-readable guard report."""

    lines = [
        "# Codex Closed Loop Guard",
        "",
        f"- status: `{result.status}`",
        f"- risk_level: `{result.risk_level or ''}`",
    ]
    if result.missing_fields:
        lines.append(f"- missing_fields: `{', '.join(result.missing_fields)}`")
    lines.append("")
    lines.append("## Messages")
    for message in result.messages:
        lines.append(f"- {message}")
    if result.task:
        lines.extend(["", "## Task", ""])
        for key in REQUIRED_TASK_FIELDS:
            lines.append(f"- `{key}`: {result.task.get(key)!r}")
    return "\n".join(lines) + "\n"


def _normalize_key(key: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", key.strip().lower()).strip("_")
    aliases = {
        "target_files_or_folders": "target_files_or_folders",
        "target_files_folders": "target_files_or_folders",
        "review_notes_or_defects": "review_notes_or_defects",
        "review_notes_defects": "review_notes_or_defects",
        "anything_not_allowed": "anything_not_allowed",
        "not_allowed": "anything_not_allowed",
        "risk": "risk_level",
    }
    return aliases.get(normalized, normalized)


def _normalize_risk(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False
