"""Build a tracked Markdown review package for ChatGPT Pro review."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an ABC Quant review package.")
    parser.add_argument("--output", type=Path, required=True, help="Markdown file to write.")
    parser.add_argument("--title", default="Codex Review Package", help="Package title.")
    parser.add_argument("--pr-url", default="", help="GitHub PR URL, if available.")
    parser.add_argument(
        "--run-validation",
        action="store_true",
        help="Run pytest and the closed-loop guard before writing the package.",
    )
    args = parser.parse_args()

    root = Path.cwd()
    validation_sections: list[tuple[str, str]] = []
    if args.run_validation:
        validation_sections.append(
            (
                "pytest",
                run_command([sys.executable, "-m", "pytest"], root),
            )
        )
        validation_sections.append(
            (
                "closed-loop guard",
                run_command(
                    [
                        "pwsh",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        ".\\scripts\\run_codex_closed_loop.ps1",
                    ],
                    root,
                ),
            )
        )

    output = args.output
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_package(root=root, title=args.title, pr_url=args.pr_url, validations=validation_sections),
        encoding="utf-8",
    )
    print(output)
    return 0


def render_package(
    *,
    root: Path,
    title: str,
    pr_url: str,
    validations: list[tuple[str, str]],
) -> str:
    as_of = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    sections = [
        f"# {title}",
        "",
        f"- as_of: `{as_of}`",
        f"- project_root: `{root}`",
        f"- branch: `{git_value(['branch', '--show-current'], root)}`",
        f"- head_commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`",
        f"- pr_url: `{pr_url}`" if pr_url else "- pr_url: ``",
        "",
        "## Objective",
        "",
        "Finish repository hygiene, provide a tracked review package, verify the project, and push the current work to GitHub for ChatGPT Pro review.",
        "",
        "## Git Status",
        "",
        fenced(git(["status", "--short", "--branch"], root)),
        "",
        "## Branch Diff Stat Versus Main",
        "",
        fenced(git(["diff", "--stat", "main...HEAD"], root)),
        "",
        "## Branch Changed Files Versus Main",
        "",
        fenced(git(["diff", "--name-only", "main...HEAD"], root)),
        "",
        "## Working Tree Diff Stat",
        "",
        fenced(git(["diff", "--stat"], root)),
        "",
        "## Validation",
        "",
    ]

    if validations:
        for name, output in validations:
            sections.extend([f"### {name}", "", fenced(output), ""])
    else:
        sections.append("_No validation commands were run by the package builder._")

    sections.extend(
        [
            "## Review Pointers",
            "",
            "- `docs/codex_closed_loop.md`: closed-loop protocol and safety boundaries.",
            "- `src/abc_quant/governance/codex_loop.py`: guard implementation.",
            "- `tests/test_codex_loop_guard.py`: guard behavior coverage.",
            "- `OUTBOX.md`: Codex execution summary.",
            "- `STATUS.md`: project status log.",
            "",
            "## Known Local Artifacts",
            "",
            "- `.venv/`, `.tmp_pytest/`, `state/codex_context/`, and `reports/codex_loop/` are local/ignored artifacts.",
            "- Old root-level `CODEX_REVIEW_PACKAGE.md` and `CODEX_TEST_RESULT.txt` are superseded by this tracked review package.",
            "- `.pytest_cache/` may remain as a Windows ACL residue on this machine; it is ignored and not part of Git history.",
            "",
            "## Promotion Boundary",
            "",
            "This package contains repository governance work only. It does not add trading strategy logic, model training, broker integration, or formal signal promotion.",
            "",
        ]
    )
    return "\n".join(sections)


def git(args: list[str], cwd: Path) -> str:
    return run_command(["git", *args], cwd)


def git_value(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    value = completed.stdout.strip()
    if completed.returncode != 0:
        return f"{value} (exit_code={completed.returncode})"
    return value


def run_command(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.stdout.rstrip() + f"\n(exit_code={completed.returncode})"


def fenced(text: str) -> str:
    return "```text\n" + text.rstrip() + "\n```"


if __name__ == "__main__":
    sys.exit(main())
