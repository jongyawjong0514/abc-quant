# Codex Closed Loop Runner Prompt

Use this prompt for a Codex automation or a manual closed-loop run in `E:\abc`.

1. Read `AGENTS.md`, `PROJECT_RULES.md`, `TECH_LEAD_PROTOCOL.md`, and `docs/codex_closed_loop.md`.
2. Run `scripts/run_codex_closed_loop.ps1`.
3. If guard status is `no_task`, report that there is no current task and stop.
4. If guard status is `blocked_invalid` or `blocked_risky`, report the exact blocker and stop.
5. If guard status is `ready`, execute only the task in `INBOX.md`.
6. Implement the smallest reversible change that satisfies the task.
7. Run the validation requested in `INBOX.md`; at minimum run `python -m pytest` when code changed.
8. Update `STATUS.md`, `OUTBOX.md`, `TODO.md` or `CHANGELOG.md` when relevant.
9. Open a draft PR for review when files changed.
10. Never auto-merge, never automate ChatGPT Pro web UI, and never execute destructive, credentialed, external, or materially risky work without explicit user confirmation.
