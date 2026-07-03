# Codex Closed Loop

本專案採用檔案式閉環，不使用 ChatGPT Pro 網頁 UI 當自動化後端。

## 目標

建立可重複、可審查、可暫停的工作迴圈：

```text
ChatGPT Pro writes one bounded task
-> INBOX.md
-> Codex guard validates scope and risk
-> Codex implements only safe local tasks
-> pytest and focused checks
-> OUTBOX.md, STATUS.md, reviews/
-> ChatGPT Pro reviews and writes the next task
```

## 安全邊界

- 每輪只允許一個 bounded task。
- `risk_level` 只有 `normal` 可自動執行。
- `destructive`、`credentialed`、`external`、`materially_risky` 必須停下來等使用者明確確認。
- 不自動 merge PR。
- 不自動提升正式交易規則、正式 champion、正式買賣權重或實盤流程。
- 不透過 ChatGPT Pro 網頁 UI 互貼內容；結果以檔案、GitHub PR、GitHub comment 或明確 API/connector 傳遞。
- Guard 設定允許 `.github/` 作為未來 CI workflow 的 repository target root，但本輪不建立 workflow 檔；`.git/` 仍是 blocked path。

## 任務格式

`INBOX.md` 的 `Current task:` 後方應放一個 YAML 區塊：

```yaml
role: technical_lead
task: "Implement one small verifiable change."
target_files_or_folders:
  - "src/abc_quant/..."
current_spec_or_decision: "Why this task is valid now."
constraints:
  - "Do not change formal trading signals."
acceptance_criteria:
  - "The focused test covers the behavior."
validation_expected:
  - "python -m pytest"
review_notes_or_defects:
  - "none"
anything_not_allowed:
  - "No data download."
risk_level: normal
```

## 執行方式

先檢查任務是否可執行：

```powershell
.\scripts\run_codex_closed_loop.ps1
```

腳本會輸出 guard 報告到：

```text
reports/codex_loop/latest.json
reports/codex_loop/latest.md
```

Codex automation 或人工 Codex thread 應先看 guard 結果：

- `ready`: 可以依 `INBOX.md` 任務執行。
- `no_task`: 沒有任務，不要自行發明工作。
- `blocked_invalid`: 任務格式不足，回報缺欄位。
- `blocked_risky`: 風險等級不允許自動執行，等待使用者確認。

## 自動化建議

適合建立 Codex worktree automation，每次喚醒時：

1. 讀 `PROJECT_RULES.md`、`AGENTS.md`、`TECH_LEAD_PROTOCOL.md`。
2. 執行 `scripts/run_codex_closed_loop.ps1`。
3. 只有 guard 狀態為 `ready` 且風險為 `normal` 時才實作。
4. 完成後執行測試，更新 `STATUS.md` 與 `OUTBOX.md`。
5. 開 draft PR 或把結果寫入可審查檔案。
6. 若 guard 不是 `ready`，只回報原因，不改程式。

## CI Target Preparation

`.github/` is an allowed closed-loop target root so a later reviewed task can add workflow files. This does not grant access to `.git/`, credentials, external APIs, data downloads, or auto-merge behavior.

## CI Workflow

The repository CI workflow lives at `.github/workflows/ci.yml`. It runs on pull requests and pushes to `main`, uses official GitHub Actions for checkout and Python setup, installs `.[dev]`, and executes:

- `ruff check .`
- `python -m pytest`
- `python -m compileall src tests`

The matrix covers Python 3.11 and 3.12 to match the repository's Python 3.11+ support boundary.
