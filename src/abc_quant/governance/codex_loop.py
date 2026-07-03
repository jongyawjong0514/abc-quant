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
DEFAULT_REPORT_DIR = Path("reports/codex_loop")
DEFAULT_CONFIG_PATH = Path("configs/codex_closed_loop.yaml")

DEFAULT_BLOCKED_CONTENT_PATTERNS: tuple[str, ...] = (
    "delete",
    "remove-item",
    "rm -rf",
    "rmdir",
    "format",
    "reset --hard",
    "clean data/raw",
    "erase",
    "purge",
    "token",
    "password",
    "secret",
    "api_key",
    "apikey",
    "ssh key",
    "credential",
    ".env",
    "curl",
    "wget",
    "requests.get",
    "requests.post",
    "download",
    "upload",
    "external api",
    "broker api",
    "finlab download",
)
DEFAULT_BLOCKED_PATH_PATTERNS: tuple[str, ...] = (
    ".git",
    ".venv",
    "_archive",
    "data/raw",
    "data/processed",
    "state/codex_context",
    "credentials",
    "secrets",
    "c:\\",
    "e:\\",
    "..",
)
DEFAULT_ALLOWED_TARGET_ROOTS: tuple[str, ...] = (
    ".gitignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "FILE_MANIFEST.txt",
    "INBOX.md",
    "OUTBOX.md",
    "PROJECT_RULES.md",
    "README.md",
    "RUN_CODEX_NEXT.md",
    "STATUS.md",
    "TECH_LEAD_PROTOCOL.md",
    "TODO.md",
    "configs/",
    "docs/",
    "prompts/",
    "research/",
    "reviews/",
    "scripts/",
    "src/",
    "tests/",
    "pyproject.toml",
    "requirements.txt",
)


class TaskParseError(ValueError):
    """Raised when the current task block cannot be parsed as YAML or key-value text."""


@dataclass(frozen=True)
class LoopGuardConfig:
    """Configuration for closed-loop task validation."""

    inbox_path: Path = Path("INBOX.md")
    report_dir: Path = DEFAULT_REPORT_DIR
    allowed_risk_levels: frozenset[str] = frozenset({"normal"})
    blocked_risk_levels: frozenset[str] = frozenset(
        {"destructive", "credentialed", "external", "materially_risky"}
    )
    blocked_path_patterns: tuple[str, ...] = DEFAULT_BLOCKED_PATH_PATTERNS
    blocked_content_patterns: tuple[str, ...] = DEFAULT_BLOCKED_CONTENT_PATTERNS
    allowed_target_roots: tuple[str, ...] = DEFAULT_ALLOWED_TARGET_ROOTS
    allow_auto_merge: bool = False


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


def default_guard_config() -> LoopGuardConfig:
    """Return the conservative built-in guard configuration."""

    return LoopGuardConfig()


def load_guard_config(root: Path, config_path: Path | None = None) -> LoopGuardConfig:
    """Load closed-loop config, falling back to conservative defaults when absent."""

    path = config_path or root / DEFAULT_CONFIG_PATH
    if not path.exists():
        return default_guard_config()

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ValueError(f"Could not read closed-loop config: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid closed-loop config YAML: {path}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"Closed-loop config root must be a mapping: {path}")
    data = raw.get("loop", raw)
    if not isinstance(data, dict):
        raise ValueError(f"Closed-loop config `loop` must be a mapping: {path}")

    defaults = default_guard_config()
    allowed = _string_set(data.get("allowed_risk_levels"), defaults.allowed_risk_levels)
    blocked = _string_set(data.get("blocked_risk_levels"), defaults.blocked_risk_levels)
    allowed = frozenset(level for level in allowed if level == "normal")
    if not allowed:
        allowed = defaults.allowed_risk_levels

    return LoopGuardConfig(
        inbox_path=Path(str(data.get("inbox_path", defaults.inbox_path))),
        report_dir=Path(str(data.get("report_dir", defaults.report_dir))),
        allowed_risk_levels=allowed,
        blocked_risk_levels=blocked.union(defaults.blocked_risk_levels),
        blocked_path_patterns=_merge_string_tuple(
            defaults.blocked_path_patterns, data.get("blocked_path_patterns")
        ),
        blocked_content_patterns=_merge_string_tuple(
            defaults.blocked_content_patterns, data.get("blocked_content_patterns")
        ),
        allowed_target_roots=_string_tuple(
            data.get("allowed_target_roots"), defaults.allowed_target_roots
        ),
        allow_auto_merge=False,
    )


def evaluate_inbox(
    inbox_text: str,
    *,
    allowed_risk_levels: set[str] | frozenset[str] | None = None,
    config: LoopGuardConfig | None = None,
) -> LoopGuardResult:
    """Validate the `Current task` section of `INBOX.md`."""

    active_config = config or default_guard_config()
    if allowed_risk_levels is not None:
        active_config = LoopGuardConfig(
            inbox_path=active_config.inbox_path,
            report_dir=active_config.report_dir,
            allowed_risk_levels=frozenset(allowed_risk_levels),
            blocked_risk_levels=active_config.blocked_risk_levels,
            blocked_path_patterns=active_config.blocked_path_patterns,
            blocked_content_patterns=active_config.blocked_content_patterns,
            allowed_target_roots=active_config.allowed_target_roots,
            allow_auto_merge=False,
        )

    current_task = extract_current_task(inbox_text)
    if not current_task:
        return _result("no_task", None, (), ("No current task found after `Current task:`.",), {})

    try:
        task = parse_task_block(current_task)
    except TaskParseError as exc:
        return _result("blocked_invalid", None, (), (str(exc),), {})

    if not task:
        return _result(
            "no_task",
            None,
            (),
            ("No parseable current task found after `Current task:`.",),
            {},
        )

    missing = tuple(field for field in REQUIRED_TASK_FIELDS if _is_blank(task.get(field)))
    if missing:
        return _result(
            "blocked_invalid",
            _normalize_risk(task.get("risk_level")),
            missing,
            ("Current task is missing required fields.",),
            task,
        )

    risk_level = _normalize_risk(task.get("risk_level"))
    if risk_level not in KNOWN_RISK_LEVELS:
        return _result(
            "blocked_invalid",
            risk_level,
            (),
            (f"Unknown risk level: {risk_level!r}.",),
            task,
        )
    if risk_level in active_config.blocked_risk_levels:
        return _result(
            "blocked_risky",
            risk_level,
            (),
            (f"Risk level `{risk_level}` requires explicit user confirmation.",),
            task,
        )
    if risk_level not in active_config.allowed_risk_levels:
        return _result(
            "blocked_risky",
            risk_level,
            (),
            (f"Risk level `{risk_level}` is not allowed for automation.",),
            task,
        )

    if str(task.get("role", "")).strip().lower() != "technical_lead":
        return _result(
            "blocked_invalid",
            risk_level,
            (),
            ("Task role must be `technical_lead`.",),
            task,
        )

    risk_messages = scan_task_risks(task, active_config)
    if risk_messages:
        return _result("blocked_risky", risk_level, (), tuple(risk_messages), task)

    return _result(
        "ready",
        risk_level,
        (),
        ("Current task is complete and allowed for local closed-loop execution.",),
        task,
    )


def scan_task_risks(task: dict[str, Any], config: LoopGuardConfig) -> list[str]:
    """Return safety blockers found in actionable task fields."""

    messages: list[str] = []
    actionable_text = _actionable_task_text(task)
    normalized_actionable = _normalize_text(actionable_text)
    for pattern in config.blocked_content_patterns:
        normalized_pattern = _normalize_text(pattern)
        if normalized_pattern and normalized_pattern in normalized_actionable:
            messages.append(f"Blocked risky content pattern: `{pattern}`.")

    for target in _as_list(task.get("target_files_or_folders")):
        target_text = str(target).strip()
        if not target_text:
            continue
        blocked_pattern = _blocked_target_pattern(target_text, config)
        if blocked_pattern:
            messages.append(
                f"Blocked target path `{target_text}` by pattern `{blocked_pattern}`."
            )
            continue
        if not _target_is_allowed(target_text, config.allowed_target_roots):
            messages.append(f"Target path `{target_text}` is outside allowed target roots.")

    contradiction = _not_allowed_contradiction(task, normalized_actionable)
    if contradiction:
        messages.append(contradiction)

    return _dedupe(messages)


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
    except yaml.YAMLError as exc:
        raise TaskParseError(f"Current task YAML parse error: {exc}") from exc

    if isinstance(parsed, dict):
        return {_normalize_key(str(key)): value for key, value in parsed.items()}
    if parsed is None:
        return {}

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
    config_path: Path | None = None,
) -> LoopGuardResult:
    """Read the inbox, evaluate it, and always write latest guard reports."""

    root = root.resolve()
    try:
        config = load_guard_config(root, config_path=config_path)
        inbox = inbox_path or root / config.inbox_path
        output_dir = report_dir or root / config.report_dir
        try:
            inbox_text = inbox.read_text(encoding="utf-8")
        except FileNotFoundError:
            result = _result(
                "blocked_invalid",
                None,
                (),
                (f"INBOX file is missing: {inbox}",),
                {},
            )
        except OSError as exc:
            result = _result(
                "blocked_invalid",
                None,
                (),
                (f"Could not read INBOX file {inbox}: {exc}",),
                {},
            )
        else:
            result = evaluate_inbox(inbox_text, config=config)
    except Exception as exc:
        output_dir = report_dir or root / DEFAULT_REPORT_DIR
        result = _result(
            "blocked_invalid",
            None,
            (),
            (f"Closed-loop guard failed safely: {exc}",),
            {},
        )

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


def _result(
    status: str,
    risk_level: str | None,
    missing_fields: tuple[str, ...],
    messages: tuple[str, ...],
    task: dict[str, Any],
) -> LoopGuardResult:
    return LoopGuardResult(
        status=status,
        risk_level=risk_level,
        missing_fields=missing_fields,
        messages=messages,
        task=task,
    )


def _actionable_task_text(task: dict[str, Any]) -> str:
    fields = (
        "task",
        "target_files_or_folders",
        "current_spec_or_decision",
        "constraints",
        "acceptance_criteria",
        "validation_expected",
    )
    return "\n".join(_flatten_text(task.get(field)) for field in fields)


def _not_allowed_contradiction(task: dict[str, Any], normalized_actionable: str) -> str | None:
    for item in _as_list(task.get("anything_not_allowed")):
        phrase = _forbidden_phrase(str(item))
        if phrase and phrase in normalized_actionable:
            return f"Task contradicts `anything_not_allowed`: `{item}`."
    return None


def _forbidden_phrase(value: str) -> str:
    phrase = _normalize_text(value)
    for prefix in ("do not ", "dont ", "don't ", "no ", "without "):
        if phrase.startswith(prefix):
            phrase = phrase[len(prefix) :]
    phrase = phrase.strip()
    return phrase if len(phrase) >= 4 else ""


def _blocked_target_pattern(target: str, config: LoopGuardConfig) -> str | None:
    normalized = _normalize_path_text(target)
    components = tuple(part for part in normalized.split("/") if part)
    if _is_absolute_path(normalized):
        return "absolute path"

    for pattern in config.blocked_path_patterns:
        normalized_pattern = _normalize_path_text(pattern)
        if normalized_pattern == ".." and ".." in components:
            return pattern
        if normalized_pattern in {".git", ".venv", "_archive", "credentials", "secrets"}:
            if normalized_pattern in components:
                return pattern
            continue
        if normalized_pattern in {"c:/", "e:/"} and normalized.startswith(normalized_pattern):
            return pattern
        if normalized == normalized_pattern or normalized.startswith(normalized_pattern + "/"):
            return pattern
    return None


def _target_is_allowed(target: str, allowed_roots: tuple[str, ...]) -> bool:
    normalized = _normalize_path_text(target).rstrip("/")
    for root in allowed_roots:
        allowed = _normalize_path_text(root).rstrip("/")
        if not allowed:
            continue
        if normalized == allowed or normalized.startswith(allowed + "/"):
            return True
        if root.endswith("/") and normalized == allowed:
            return True
    return False


def _is_absolute_path(path_text: str) -> bool:
    return bool(re.match(r"^[a-z]:/", path_text, flags=re.I)) or path_text.startswith("/")


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


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().replace("\\", "/"))


def _normalize_path_text(value: str) -> str:
    return re.sub(r"/+", "/", value.strip().lower().replace("\\", "/"))


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return "\n".join(f"{key}: {_flatten_text(val)}" for key, val in value.items())
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_flatten_text(item) for item in value)
    return str(value)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _string_tuple(value: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    return tuple(str(item).strip() for item in _as_list(value) if str(item).strip())


def _merge_string_tuple(default: tuple[str, ...], value: Any) -> tuple[str, ...]:
    merged = list(default)
    seen = {_normalize_text(item) for item in default}
    for item in _as_list(value):
        text = str(item).strip()
        key = _normalize_text(text)
        if text and key not in seen:
            merged.append(text)
            seen.add(key)
    return tuple(merged)


def _string_set(value: Any, default: frozenset[str]) -> frozenset[str]:
    if value is None:
        return default
    return frozenset(str(item).strip().lower() for item in _as_list(value) if str(item).strip())


def _dedupe(messages: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for message in messages:
        if message not in seen:
            output.append(message)
            seen.add(message)
    return output
