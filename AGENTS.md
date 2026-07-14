# E:\abc Codex Handoff

Scope: Codex may work in this folder when the user asks for `E:\abc` work.

Operating model:
- Local ChatGPT Pro acts as technical lead: maintains specs, proposes next tasks, and reviews Codex results.
- Codex acts as implementation engineer: inspects, edits, fixes, validates, and reports evidence.
- Prefer durable specs and review notes over accumulating scattered prompts.
- See `TECH_LEAD_PROTOCOL.md` for the handoff workflow.

Instruction source:
- Read `INBOX.md` for explicit tasks from the local ChatGPT Pro/user handoff.
- Write progress and completion notes to `STATUS.md` and detailed results to `OUTBOX.md` when useful.
- ChatGPT Pro handoff instructions may set project specs, priorities, acceptance criteria, and review findings for this folder.
- System, developer, safety, and direct user instructions outrank file-based handoff instructions.
- Do not execute destructive, credentialed, external, or materially risky actions without explicit user confirmation.
- For code or data changes, inspect first, make scoped reversible edits, and validate locally before reporting done.

Default reply language: Traditional Chinese unless asked otherwise.

Stock-report default:
- For every dated Zhu Walkline report, automatically generate and present the frozen four-component shadow strength rank (main-force proxy, no upper-tail supply, volume ratio, five-day margin change) as the primary stock ordering. Keep market/sector state and the original scanner score as context only.
- Exclude raw margin balance and raw foreign net-share counts from this score. Missing any component means `INSUFFICIENT_FEATURES`, with no zero fill and no rank.
- The rank stays `shadow_observation_only` / `watch_only`; it may not override market risk gates or formal strategy state without a separate promotion review.
