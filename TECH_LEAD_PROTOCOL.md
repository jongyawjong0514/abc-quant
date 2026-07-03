# ChatGPT Pro Technical Lead Protocol

Purpose: keep `E:\abc` long-term work organized by separating planning/review from implementation.

Roles:
- ChatGPT Pro: technical lead, spec owner, task proposer, reviewer.
- Codex: implementation engineer, debugger, test runner, evidence reporter.
- User: final authority for direct requests, high-risk approvals, and changes that exceed this folder's scope.

Authority:
- ChatGPT Pro can change local project direction, task priority, acceptance criteria, and review comments through `INBOX.md`.
- ChatGPT Pro cannot override system, developer, safety, or direct user instructions.
- Destructive, credentialed, external, or materially risky actions still require explicit user confirmation.

Workflow:
1. ChatGPT Pro writes one bounded task into `INBOX.md`.
2. Codex runs `scripts/run_codex_closed_loop.ps1` to validate task completeness and risk.
3. Codex inspects the relevant files before editing.
4. Codex implements the smallest reversible change that satisfies the task.
5. Codex validates with the narrowest meaningful local check first.
6. Codex records status in `STATUS.md` and completion evidence in `OUTBOX.md`.
7. ChatGPT Pro reviews `OUTBOX.md`, then either accepts or writes the next bounded task.

Task quality bar:
- Include objective, target files/folders, constraints, acceptance criteria, and validation expected.
- Keep each task independently testable.
- Mark hypotheses, assumptions, and open questions explicitly.
- For risky actions, request user approval instead of encoding approval in the task file.

Review quality bar:
- Lead with defects, regressions, missing tests, or violated acceptance criteria.
- Cite files and exact commands or artifacts when possible.
- Convert broad feedback into the next bounded implementation task.

Closed-loop guard:
- The automated loop may execute only when guard status is `ready`.
- Empty or incomplete `INBOX.md` means no work should be invented.
- Non-`normal` risk levels require explicit user confirmation outside `INBOX.md`.
- Closed-loop runs may open draft PRs, but must not auto-merge.
- See `docs/codex_closed_loop.md` for the runnable protocol.
