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
2. Codex inspects the relevant files before editing.
3. Codex implements the smallest reversible change that satisfies the task.
4. Codex validates with the narrowest meaningful local check first.
5. Codex records status in `STATUS.md` and completion evidence in `OUTBOX.md`.
6. ChatGPT Pro reviews `OUTBOX.md`, then either accepts or writes the next bounded task.

Task quality bar:
- Include objective, target files/folders, constraints, acceptance criteria, and validation expected.
- Keep each task independently testable.
- Mark hypotheses, assumptions, and open questions explicitly.
- For risky actions, request user approval instead of encoding approval in the task file.

Review quality bar:
- Lead with defects, regressions, missing tests, or violated acceptance criteria.
- Cite files and exact commands or artifacts when possible.
- Convert broad feedback into the next bounded implementation task.
