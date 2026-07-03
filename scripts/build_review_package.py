"""Build a tracked Markdown review package for ChatGPT Pro review."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo


MANDATORY_CONTENT_FILES: tuple[str, ...] = (
    "src/abc_quant/governance/codex_loop.py",
    "tests/test_codex_loop_guard.py",
    "scripts/build_review_package.py",
    "scripts/codex_loop_guard.py",
    "scripts/run_codex_closed_loop.ps1",
    "configs/codex_closed_loop.yaml",
    "docs/codex_closed_loop.md",
    "INBOX.md",
    "STATUS.md",
    "OUTBOX.md",
)


@dataclass(frozen=True)
class CommandResult:
    """Captured command output for review-package rendering."""

    command: str
    output: str
    exit_code: int | str


@dataclass(frozen=True)
class CleanStatus:
    """Git cleanliness state with the output file excluded."""

    output_file: str
    status_excludes_output_file: bool
    dirty_entries_excluding_output: tuple[str, ...]
    dirty_entries_output_file: tuple[str, ...]

    @property
    def is_clean_excluding_output(self) -> bool:
        return not self.dirty_entries_excluding_output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an ABC Quant review package.")
    parser.add_argument("--output", type=Path, required=True, help="Markdown file to write.")
    parser.add_argument("--title", default="Codex Review Package", help="Package title.")
    parser.add_argument("--pr-url", default="", help="GitHub PR URL, if available.")
    parser.add_argument(
        "--run-validation",
        action="store_true",
        help="Run pytest, compileall, and ruff before writing the package.",
    )
    parser.add_argument(
        "--include-diff",
        action="store_true",
        help="Include the full `git diff main...HEAD` output.",
    )
    parser.add_argument(
        "--include-file-contents",
        action="store_true",
        help="Include full contents for changed and mandatory review files.",
    )
    parser.add_argument(
        "--assert-clean",
        action="store_true",
        help="Fail if the working tree is dirty except for the output file.",
    )
    args = parser.parse_args()

    root = Path.cwd()
    output = resolve_output(root, args.output)
    clean_status = inspect_clean_status(root, output)
    if args.assert_clean and not clean_status.is_clean_excluding_output:
        print("Working tree is dirty outside the review package output file:", file=sys.stderr)
        for entry in clean_status.dirty_entries_excluding_output:
            print(entry, file=sys.stderr)
        return 2

    validations: list[tuple[str, CommandResult]] = []
    if args.run_validation:
        validations.extend(run_validations(root))

    output.parent.mkdir(parents=True, exist_ok=True)
    package_text = strip_trailing_whitespace(
        render_package(
            root=root,
            output=output,
            title=args.title,
            pr_url=args.pr_url,
            validations=validations,
            include_diff=args.include_diff,
            include_file_contents=args.include_file_contents,
            clean_status=clean_status,
        )
    )
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(package_text)
    print(output)
    return 0


def resolve_output(root: Path, output: Path) -> Path:
    """Return an absolute output path."""

    if output.is_absolute():
        return output
    return root / output


def run_validations(root: Path) -> list[tuple[str, CommandResult]]:
    """Run review-package validation commands."""

    return [
        ("pytest", run_command([sys.executable, "-m", "pytest"], root)),
        ("compileall", run_command([sys.executable, "-m", "compileall", "src", "tests"], root)),
        ("ruff", run_optional_command(["ruff", "check", "."], root)),
    ]


def render_package(
    *,
    root: Path,
    output: Path,
    title: str,
    pr_url: str,
    validations: list[tuple[str, CommandResult]],
    include_diff: bool,
    include_file_contents: bool,
    clean_status: CleanStatus,
) -> str:
    as_of = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    output_relative = relative_to_root(output, root)
    branch = git_value(["branch", "--show-current"], root)
    head_sha = git_value(["rev-parse", "HEAD"], root)
    git_status = git(["status", "--short", "--branch"], root)
    diff_check = git(["diff", "--check"], root)
    diff_stat = git(["diff", "--stat", "main...HEAD"], root)
    diff_names_result = run_command(["git", "diff", "--name-only", "main...HEAD"], root)
    diff_names = diff_names_result.output.rstrip() + f"\n(exit_code={diff_names_result.exit_code})"
    full_diff = git(["diff", "main...HEAD"], root) if include_diff else "_Not requested._"

    sections = [
        f"# {title}",
        "",
        "## Metadata",
        "",
        f"- as_of: `{as_of}`",
        f"- project_root: `{root}`",
        f"- pr_url: `{pr_url}`" if pr_url else "- pr_url: ``",
        f"- branch: `{branch}`",
        f"- head_sha: `{head_sha}`",
        f"- status_excludes_output_file: {str(clean_status.status_excludes_output_file).lower()}",
        f"- output_file: {output_relative}",
        "",
        "## Objective",
        "",
        "Harden the file-based closed-loop guard, make the review package reproducible, and keep this PR limited to repository governance.",
        "",
        "## Git Status",
        "",
        "Command: `git status --short --branch`",
        "",
        fenced(git_status),
        "",
        "## Assert Clean",
        "",
        f"- clean_excluding_output_file: {str(clean_status.is_clean_excluding_output).lower()}",
        "",
    ]
    if clean_status.dirty_entries_excluding_output:
        sections.extend(["Dirty entries excluding output:", "", fenced("\n".join(clean_status.dirty_entries_excluding_output)), ""])
    if clean_status.dirty_entries_output_file:
        sections.extend(["Output-file entries excluded from assert-clean:", "", fenced("\n".join(clean_status.dirty_entries_output_file)), ""])

    sections.extend(
        [
            "## Git Diff Check",
            "",
            "Command: `git diff --check`",
            "",
            fenced(diff_check),
            "",
            "## Branch Diff Stat Versus Main",
            "",
            "Command: `git diff --stat main...HEAD`",
            "",
            fenced(diff_stat),
            "",
            "## Branch Changed Files Versus Main",
            "",
            "Command: `git diff --name-only main...HEAD`",
            "",
            fenced(diff_names),
            "",
            "## Branch Diff Versus Main",
            "",
            "Command: `git diff main...HEAD`",
            "",
            fenced(full_diff),
            "",
            "## Validation",
            "",
        ]
    )

    if validations:
        for name, result in validations:
            sections.extend(
                [
                    f"### {name}",
                    "",
                    f"Command: `{result.command}`",
                    "",
                    fenced(result.output.rstrip() + f"\n(exit_code={result.exit_code})"),
                    "",
                ]
            )
    else:
        sections.append("_No validation commands were run by the package builder._")

    if include_file_contents:
        sections.extend(render_file_contents(root, output, diff_names_result.output))
    else:
        sections.extend(["", "## File Contents", "", "_Not requested._", ""])

    sections.extend(
        [
            "## Known Local Artifacts",
            "",
            "- `.venv/`, `.tmp_pytest/`, `state/codex_context/`, and `reports/codex_loop/` are local/ignored artifacts.",
            "- Old root-level `CODEX_REVIEW_PACKAGE.md` and `CODEX_TEST_RESULT.txt` are superseded by `reviews/review_package_002.md`.",
            "- `.pytest_cache/` may remain as a Windows ACL residue on this machine; it is ignored and not part of Git history.",
            "",
            "## Promotion Boundary",
            "",
            "This package contains repository governance work only. It does not add trading strategy logic, model training, broker integration, FinLab download logic, data downloads, or formal signal promotion.",
            "",
        ]
    )
    return "\n".join(sections)


def render_file_contents(root: Path, output: Path, diff_names: str) -> list[str]:
    """Render full file contents for changed files and required review files."""

    files = ordered_unique(
        [
            *[line.strip() for line in diff_names.splitlines() if line.strip()],
            *MANDATORY_CONTENT_FILES,
        ]
    )
    output_relative = relative_to_root(output, root)

    sections = ["", "## File Contents", ""]
    for relative in files:
        if relative == output_relative:
            sections.extend([f"### `{relative}`", "", "_Skipped output file to avoid recursive package growth._", ""])
            continue
        path = root / relative
        sections.extend([f"### `{relative}`", ""])
        if not path.exists():
            sections.extend(["_Missing._", ""])
            continue
        if not path.is_file():
            sections.extend(["_Not a regular file._", ""])
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            sections.extend([f"_Could not read file: {exc}_", ""])
            continue
        sections.extend([fenced(text), ""])
    return sections


def inspect_clean_status(root: Path, output: Path) -> CleanStatus:
    """Return porcelain status entries, excluding only the output file."""

    output_relative = relative_to_root(output, root)
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=normal"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    entries = tuple(line for line in completed.stdout.splitlines() if line.strip())
    output_entries: list[str] = []
    other_entries: list[str] = []
    for entry in entries:
        if status_entry_mentions_path(entry, output_relative):
            output_entries.append(entry)
        else:
            other_entries.append(entry)
    return CleanStatus(
        output_file=output_relative,
        status_excludes_output_file=True,
        dirty_entries_excluding_output=tuple(other_entries),
        dirty_entries_output_file=tuple(output_entries),
    )


def status_entry_mentions_path(entry: str, relative_path: str) -> bool:
    """Return true when a porcelain status entry refers to the given path."""

    normalized = normalize_path(relative_path)
    payload = normalize_path(entry[3:].strip().strip('"')) if len(entry) > 3 else ""
    if " -> " in payload:
        old_path, new_path = payload.split(" -> ", 1)
        return old_path == normalized or new_path == normalized
    return payload == normalized


def relative_to_root(path: Path, root: Path) -> str:
    """Return a repo-relative path with forward slashes."""

    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return normalize_path(str(path))
    return normalize_path(relative.as_posix())


def normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def git(args: list[str], cwd: Path) -> str:
    result = run_command(["git", *args], cwd)
    return result.output.rstrip() + f"\n(exit_code={result.exit_code})"


def git_value(args: list[str], cwd: Path) -> str:
    result = run_command(["git", *args], cwd)
    value = result.output.strip()
    if result.exit_code != 0:
        return f"{value} (exit_code={result.exit_code})"
    return value


def run_command(args: list[str], cwd: Path) -> CommandResult:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return CommandResult(
        command=shell_join(args),
        output=completed.stdout.rstrip(),
        exit_code=completed.returncode,
    )


def run_optional_command(args: list[str], cwd: Path) -> CommandResult:
    try:
        return run_command(args, cwd)
    except FileNotFoundError:
        return CommandResult(
            command=shell_join(args),
            output=f"unavailable: `{args[0]}` executable was not found",
            exit_code="unavailable",
        )


def shell_join(args: list[str]) -> str:
    return " ".join(quote_arg(arg) for arg in args)


def quote_arg(arg: str) -> str:
    if not arg or any(char.isspace() for char in arg):
        return '"' + arg.replace('"', '\\"') + '"'
    return arg


def fenced(text: str) -> str:
    return "```text\n" + text.rstrip() + "\n```"


def strip_trailing_whitespace(text: str) -> str:
    """Normalize generated Markdown so `git diff --check` stays clean."""

    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output


if __name__ == "__main__":
    sys.exit(main())
