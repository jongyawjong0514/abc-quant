# Codex Closed-Loop Task 003 Review Package

## Metadata

- as_of: `2026-07-03T23:47:58+08:00`
- project_root: `E:\abc`
- pr_url: `https://github.com/jongyawjong0514/abc-quant/pull/2`
- branch: `codex/file-closed-loop-guard`
- head_sha: `35d1a58e0340426aee14ae1e97babfded411b32e`
- status_excludes_output_file: true
- output_file: reviews/review_package_002.md

## Objective

Harden the file-based closed-loop guard, make the review package reproducible, and keep this PR limited to repository governance.

## Git Status

Command: `git status --short --branch`

```text
## codex/file-closed-loop-guard...origin/codex/file-closed-loop-guard [ahead 1]
 M reviews/review_package_002.md
(exit_code=0)
```

## Assert Clean

- clean_excluding_output_file: true

Output-file entries excluded from assert-clean:

```text
 M reviews/review_package_002.md
```

## Git Diff Check

Command: `git diff --check`

```text
reviews/review_package_002.md:171: trailing whitespace.
++
reviews/review_package_002.md:187: trailing whitespace.
++
reviews/review_package_002.md:191: trailing whitespace.
++
reviews/review_package_002.md:355: trailing whitespace.
++
reviews/review_package_002.md:359: trailing whitespace.
++
reviews/review_package_002.md:405: trailing whitespace.
++
reviews/review_package_002.md:417: trailing whitespace.
++
reviews/review_package_002.md:473: trailing whitespace.
++
reviews/review_package_002.md:681: trailing whitespace.
++
reviews/review_package_002.md:699: trailing whitespace.
++
reviews/review_package_002.md:727: trailing whitespace.
++
reviews/review_package_002.md:773: trailing whitespace.
++
reviews/review_package_002.md:801: trailing whitespace.
++
reviews/review_package_002.md:1243: trailing whitespace.
++
reviews/review_package_002.md:8483: trailing whitespace.
+
reviews/review_package_002.md:8491: trailing whitespace.
+
reviews/review_package_002.md:8493: trailing whitespace.
+
reviews/review_package_002.md:8575: trailing whitespace.
+
reviews/review_package_002.md:8577: trailing whitespace.
+
reviews/review_package_002.md:8600: trailing whitespace.
+
reviews/review_package_002.md:8606: trailing whitespace.
+
reviews/review_package_002.md:8634: trailing whitespace.
+
reviews/review_package_002.md:8738: trailing whitespace.
+
reviews/review_package_002.md:8747: trailing whitespace.
+
reviews/review_package_002.md:8761: trailing whitespace.
+
reviews/review_package_002.md:8784: trailing whitespace.
+
reviews/review_package_002.md:8798: trailing whitespace.
+
reviews/review_package_002.md:9019: trailing whitespace.
+
(exit_code=2)
```

## Branch Diff Stat Versus Main

Command: `git diff --stat main...HEAD`

```text
 .gitignore                             |   2 +
 CHANGELOG.md                           |   4 +
 FILE_MANIFEST.txt                      |  24 +-
 INBOX.md                               |  43 ++-
 OUTBOX.md                              | 102 ++++++
 README.md                              |  12 +
 STATUS.md                              |   8 +
 TECH_LEAD_PROTOCOL.md                  |  18 +-
 TODO.md                                |   2 +
 configs/codex_closed_loop.yaml         |  73 ++++
 docs/codex_closed_loop.md              |  82 +++++
 prompts/codex_closed_loop_runner.md    |  14 +
 pyproject.toml                         |   2 +-
 reviews/review_package_002.md          | 136 ++++++++
 scripts/build_review_package.py        | 408 +++++++++++++++++++++++
 scripts/codex_loop_guard.py            |  31 ++
 scripts/run_codex_closed_loop.ps1      |  27 ++
 src/abc_quant/governance/__init__.py   |   2 +
 src/abc_quant/governance/codex_loop.py | 590 +++++++++++++++++++++++++++++++++
 tests/test_codex_loop_guard.py         | 214 ++++++++++++
 20 files changed, 1776 insertions(+), 18 deletions(-)
(exit_code=0)
```

## Branch Changed Files Versus Main

Command: `git diff --name-only main...HEAD`

```text
.gitignore
CHANGELOG.md
FILE_MANIFEST.txt
INBOX.md
OUTBOX.md
README.md
STATUS.md
TECH_LEAD_PROTOCOL.md
TODO.md
configs/codex_closed_loop.yaml
docs/codex_closed_loop.md
prompts/codex_closed_loop_runner.md
pyproject.toml
reviews/review_package_002.md
scripts/build_review_package.py
scripts/codex_loop_guard.py
scripts/run_codex_closed_loop.ps1
src/abc_quant/governance/__init__.py
src/abc_quant/governance/codex_loop.py
tests/test_codex_loop_guard.py
(exit_code=0)
```

## Branch Diff Versus Main

Command: `git diff main...HEAD`

```text
diff --git a/.gitignore b/.gitignore
index 57d4c81..10c7fc9 100644
--- a/.gitignore
+++ b/.gitignore
@@ -4,8 +4,10 @@ __pycache__/
 *.egg-info/
 .pytest_cache/
 .pytest-tmp/
+.tmp_pytest/
 .mypy_cache/
 .ruff_cache/
+_archive/

 abc_project_E_drive_ready/
 abc_project_E_drive_ready.zip
diff --git a/CHANGELOG.md b/CHANGELOG.md
index 2586add..28110f5 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -2,6 +2,10 @@

 ## Unreleased

+- 強化 Codex closed-loop guard：即使 `risk_level: normal`，仍會封鎖破壞性、憑證、外部網路、絕對路徑、repo 外路徑與資料原始區目標。
+- 擴充 `scripts/build_review_package.py`，支援完整 diff、完整檔案內容、驗證結果、完整 HEAD SHA 與排除輸出檔的 `--assert-clean`。
+- 新增 tracked review package 生成腳本與本輪 `reviews/review_package_002.md`，取代根目錄一次性 review 輸出。
+- 建立 Codex/ChatGPT Pro 檔案式閉環守門器、閉環文件、automation prompt 與測試。
 - 完成 ChatGPT Review 001，確認第一輪 scaffold 可接受並記錄下一輪修正 prompt。
 - 固定 pytest 本地暫存目錄並停用 cache provider，避免 Windows 受限暫存/cache 目錄造成驗收失敗或警告。
 - 新增 `.gitignore`，排除 venv、cache、egg-info、打包 zip、解壓副本與本機 Codex context capsule。
diff --git a/FILE_MANIFEST.txt b/FILE_MANIFEST.txt
index 787fc2a..25daf12 100644
--- a/FILE_MANIFEST.txt
+++ b/FILE_MANIFEST.txt
@@ -1,12 +1,21 @@
+.gitignore
+AGENTS.md
 CHANGELOG.md
+FILE_MANIFEST.txt
+INBOX.md
+OUTBOX.md
 PROJECT_RULES.md
 README.md
 RUN_CODEX_NEXT.md
+STATUS.md
+TECH_LEAD_PROTOCOL.md
 TODO.md
+configs/codex_closed_loop.yaml
 configs/default.yaml
 data/processed/.gitkeep
 data/raw/.gitkeep
 docs/architecture.md
+docs/codex_closed_loop.md
 docs/data_pipeline.md
 docs/feature_engineering.md
 docs/model_design.md
@@ -14,6 +23,7 @@ docs/strategy.md
 docs/testing.md
 notebooks/.gitkeep
 prompts/bugfix_prompt.md
+prompts/codex_closed_loop_runner.md
 prompts/codex_master.md
 prompts/research_prompt.md
 prompts/review_prompt.md
@@ -24,8 +34,12 @@ research/experiments.md
 research/ideas.md
 research/papers.md
 reviews/review_001.md
+reviews/review_package_002.md
+scripts/build_review_package.py
 scripts/check_project.ps1
 scripts/check_project.sh
+scripts/codex_loop_guard.py
+scripts/run_codex_closed_loop.ps1
 src/abc_quant/__init__.py
 src/abc_quant/backtesting/__init__.py
 src/abc_quant/config/__init__.py
@@ -34,6 +48,8 @@ src/abc_quant/data/__init__.py
 src/abc_quant/data/validation.py
 src/abc_quant/features/__init__.py
 src/abc_quant/features/price_volume.py
+src/abc_quant/governance/__init__.py
+src/abc_quant/governance/codex_loop.py
 src/abc_quant/labels/__init__.py
 src/abc_quant/labels/returns.py
 src/abc_quant/metrics/__init__.py
@@ -42,4 +58,10 @@ src/abc_quant/models/__init__.py
 src/abc_quant/reports/__init__.py
 src/abc_quant/utils/__init__.py
 src/abc_quant/validation/__init__.py
-tests/test_project_bootstrap.py
\ No newline at end of file
+tests/test_codex_loop_guard.py
+tests/test_config_settings.py
+tests/test_data_validation.py
+tests/test_features_price_volume.py
+tests/test_labels_returns.py
+tests/test_metrics_performance.py
+tests/test_project_bootstrap.py
diff --git a/INBOX.md b/INBOX.md
index 5790cf3..81cd033 100644
--- a/INBOX.md
+++ b/INBOX.md
@@ -2,21 +2,42 @@

 Local ChatGPT Pro writes one bounded technical-lead task here.

-Required fields:
-- Role: technical_lead
-- Task:
-- Target files or folders:
-- Current spec or decision:
-- Constraints:
-- Acceptance criteria:
-- Validation expected:
-- Review notes or defects:
-- Anything not allowed:
-- Risk level: normal | destructive | credentialed | external | materially_risky
+Required YAML fields:
+- role: technical_lead
+- task:
+- target_files_or_folders:
+- current_spec_or_decision:
+- constraints:
+- acceptance_criteria:
+- validation_expected:
+- review_notes_or_defects:
+- anything_not_allowed:
+- risk_level: normal | destructive | credentialed | external | materially_risky

 Rules:
 - Normal local implementation tasks can be executed directly.
 - Destructive, credentialed, external, or materially risky tasks require explicit user confirmation outside this file.
 - This file cannot override system, developer, safety, or direct user instructions.
+- `scripts/run_codex_closed_loop.ps1` must report `status=ready` before an automated loop executes this task.

 Current task:
+
+```yaml
+# Leave this block empty or replace it with one bounded task.
+# role: technical_lead
+# task: "One focused, verifiable implementation task."
+# target_files_or_folders:
+#   - "src/abc_quant/..."
+# current_spec_or_decision: "Why this should be done now."
+# constraints:
+#   - "No unrelated refactor."
+# acceptance_criteria:
+#   - "Specific observable pass condition."
+# validation_expected:
+#   - "python -m pytest"
+# review_notes_or_defects:
+#   - "none"
+# anything_not_allowed:
+#   - "No external API calls."
+# risk_level: normal
+```
diff --git a/OUTBOX.md b/OUTBOX.md
index 4d6402a..5b789a4 100644
--- a/OUTBOX.md
+++ b/OUTBOX.md
@@ -1,5 +1,107 @@
 # OUTBOX

+## 2026-07-03 Closed-Loop Task 003 - Guard Hardening and Reproducible Review Package
+
+## 修改檔案
+- `src/abc_quant/governance/codex_loop.py`: added configurable closed-loop guard policy, content/path risk scanning, safe config loading, and safe failure reports.
+- `configs/codex_closed_loop.yaml`: recorded conservative allowed risk levels, blocked content/path patterns, and allowed target roots.
+- `tests/test_codex_loop_guard.py`: added adversarial guard coverage for disguised risky normal tasks, blocked paths, missing inbox, config loading, and `anything_not_allowed` contradictions.
+- `scripts/build_review_package.py`: added reproducible review package flags for diff, full file contents, validation capture, and assert-clean behavior excluding only the output file.
+- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`: updated governance status and heartbeat wording.
+
+## 實作摘要
+- `risk_level: normal` no longer auto-passes if actionable task fields mention destructive, credential, external/network, data/raw, absolute path, or repo-outside operations.
+- `anything_not_allowed` is not scanned as an actionable field by itself, but a task that contradicts it is blocked.
+- Missing `INBOX.md`, unreadable inbox, invalid task YAML, or invalid guard config now fail closed and still write `reports/codex_loop/latest.json` and `latest.md`.
+- Review package generation can now include `git diff main...HEAD`, full file contents, validation output, full HEAD SHA, and an assert-clean check that excludes `reviews/review_package_002.md` only.
+
+## 測試方式
+- `python -m pytest`
+- `python -m compileall src tests`
+- `ruff check .`
+- `python scripts\build_review_package.py --output reviews\review_package_002.md --title "Codex Closed-Loop Task 003 Review Package" --pr-url "https://github.com/jongyawjong0514/abc-quant/pull/2" --run-validation --include-diff --include-file-contents --assert-clean`
+
+## 測試結果
+- `pytest`: 29 passed in 1.22s.
+- `compileall`: passed for `src` and `tests`.
+- `ruff`: unavailable in the current shell; no package was installed.
+- `build_review_package --assert-clean`: intentionally fails while source files are dirty; final package is generated after the code changes are committed so the assert-clean check is meaningful.
+
+## 已知限制
+- A committed review package cannot record its own final Git SHA without creating an infinite self-reference; the package records the HEAD SHA at generation time.
+- Existing PR #2 remains draft/review-only; no auto-merge is performed.
+
+## 下一步建議
+- Have ChatGPT Pro review `reviews/review_package_002.md` on PR #2.
+- Keep future closed-loop tasks limited to one bounded YAML task in `INBOX.md`.
+
+## 2026-07-03 Closed-Loop Task 001 - Repository Hygiene and Review Package
+
+## 修改檔案
+- `scripts/build_review_package.py`: added a repeatable review-package builder.
+- `reviews/review_package_002.md`: generated tracked review package for ChatGPT Pro review.
+- `.gitignore`: explicitly ignored local `_archive/` artifacts.
+- `FILE_MANIFEST.txt`, `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: updated project governance records.
+
+## 實作摘要
+- Root-level stale `CODEX_REVIEW_PACKAGE.md` and `CODEX_TEST_RESULT.txt` are superseded by a tracked review package under `reviews/`.
+- Review package includes branch status, diff summary, changed files, validation output, review pointers, and known local artifacts.
+- No strategy, model, broker API, formal signal, or trading-rule logic changed.
+
+## 測試方式
+- `E:\abc\.venv\Scripts\python.exe -m pytest`
+- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
+- `E:\abc\.venv\Scripts\python.exe .\scripts\build_review_package.py --output reviews\review_package_002.md --title "Codex Closed-Loop Task 001 Review Package" --pr-url "https://github.com/jongyawjong0514/abc-quant/pull/2" --run-validation`
+
+## 測試結果
+- `scripts/build_review_package.py --run-validation`: regenerated `reviews/review_package_002.md`.
+- Embedded validation in the review package: `pytest` 19 passed in 0.84s.
+- Embedded closed-loop guard check: `status=no_task`, expected because `INBOX.md` currently contains only the commented template.
+- Final direct validation: `pytest` 19 passed in 0.94s; `run_codex_closed_loop.ps1` returned `status=no_task`.
+
+## 已知限制
+- `.pytest_cache/` may remain as a local Windows ACL residue; it is ignored and not tracked by Git.
+
+## 下一步建議
+- Push the updated branch to GitHub PR #2 and have ChatGPT Pro review `reviews/review_package_002.md`.
+- Merge PR #2 only after review; the closed-loop policy still forbids auto-merge.
+
+## 2026-07-03 File-Based Closed Loop Guard
+
+## 修改檔案
+- `docs/codex_closed_loop.md`: documented the safe file-based closed-loop protocol.
+- `configs/codex_closed_loop.yaml`: recorded loop paths, allowed risk levels, and no-auto-merge/no-web-UI boundaries.
+- `src/abc_quant/governance/codex_loop.py`: added testable guard logic for `INBOX.md` task validation.
+- `scripts/codex_loop_guard.py`: added CLI wrapper for guard execution.
+- `scripts/run_codex_closed_loop.ps1`: added PowerShell entrypoint for Codex automation or manual checks.
+- `prompts/codex_closed_loop_runner.md`: added reusable automation prompt.
+- `tests/test_codex_loop_guard.py`: added guard behavior tests.
+- `INBOX.md`, `TECH_LEAD_PROTOCOL.md`, `README.md`, `TODO.md`, `CHANGELOG.md`, `STATUS.md`: updated project workflow records.
+
+## 實作摘要
+- The loop executes only when `INBOX.md` contains one complete YAML task with `risk_level: normal`.
+- Empty tasks return `no_task`; incomplete tasks return `blocked_invalid`; risky tasks return `blocked_risky`.
+- Generated guard reports are written under `reports/codex_loop/`, which remains an ignored local/report artifact path.
+- The design deliberately avoids automating ChatGPT Pro web UI and does not allow auto-merge.
+- Prepared instructions for an optional hourly Codex heartbeat automation; external scheduler status is not tracked in this repository.
+
+## 測試方式
+- `E:\abc\.venv\Scripts\python.exe -m pytest`
+- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
+
+## 測試結果
+- `pytest --basetemp=.tmp_pytest`: 19 passed in 0.87s, then 19 passed in 0.84s.
+- `E:\abc\.venv\Scripts\python.exe -m pytest`: 19 passed in 0.86s.
+- `scripts/run_codex_closed_loop.ps1`: status `no_task`, which is expected because `INBOX.md` currently contains only a commented template.
+
+## 已知限制
+- This is a guard and workflow scaffold, not a recursive self-launcher.
+- Real unattended automation still needs a Codex app automation schedule and review of the first few runs.
+
+## 下一步建議
+- Ask ChatGPT Pro to place the next bounded task into `INBOX.md`.
+- Review the first few heartbeat runs and adjust cadence if it is too frequent or too quiet.
+
 ## 2026-07-03 ChatGPT Review 001 and PR Hygiene

 ## 修改檔案
diff --git a/README.md b/README.md
index dbf1b48..0cb65d9 100644
--- a/README.md
+++ b/README.md
@@ -39,6 +39,18 @@ abc/
 4. ChatGPT 根據 `PROJECT_RULES.md` 審查，產生下一輪修正 Prompt。
 5. 重複以上流程。

+## 檔案式閉環
+
+本專案支援保守的 Codex/ChatGPT Pro 閉環：
+
+1. ChatGPT Pro 將一個 bounded task 寫入 `INBOX.md` 的 YAML 區塊。
+2. Codex 執行 `.\scripts\run_codex_closed_loop.ps1`。
+3. 只有 guard 回傳 `status=ready` 且 `risk_level=normal` 時才執行。
+4. Codex 完成後更新 `OUTBOX.md`、`STATUS.md`，必要時開 draft PR。
+5. ChatGPT Pro 讀回結果，再產生下一輪任務。
+
+詳細規則見 `docs/codex_closed_loop.md`。
+
 ## 快速開始

 在 Windows PowerShell：
diff --git a/STATUS.md b/STATUS.md
index 6a2408e..d1b658a 100644
--- a/STATUS.md
+++ b/STATUS.md
@@ -4,3 +4,11 @@
 - 2026-07-03: Technical-lead operating model recorded. ChatGPT Pro may own specs, next tasks, and review notes for `E:\abc`; Codex remains implementation engineer. Override of system/safety/direct-user rules was not accepted.
 - 2026-07-03: Completed `RUN_CODEX_NEXT.md` first implementation round. Editable install succeeded as `abc-quant==0.0.2` and `pytest` passed: 13 passed, 1 pytest cache warning from `E:\abc\.pytest_cache` access denied.
 - 2026-07-03: Completed ChatGPT Review 001, added PR hygiene `.gitignore`, fixed pytest temp/cache behavior, and revalidated `pytest`: 13 passed in 0.83s.
+- 2026-07-03: Added file-based Codex/ChatGPT Pro closed-loop guard, runnable PowerShell entrypoint, documentation, prompt, and tests.
+- 2026-07-03: Closed-loop guard validation passed with `pytest` 19 passed in 0.86s and `run_codex_closed_loop.ps1` returned expected `no_task` for the empty commented inbox template.
+- 2026-07-03: Prepared instructions for an optional hourly Codex heartbeat automation; external scheduler status is not tracked in this repository.
+- 2026-07-03: Started closed-loop task 001 for repository hygiene, tracked review package generation, validation, and GitHub push.
+- 2026-07-03: Generated tracked `reviews/review_package_002.md`; embedded validation shows `pytest` 19 passed in 0.84s and closed-loop guard `status=no_task`.
+- 2026-07-03: Final task 001 direct validation passed: `pytest` 19 passed in 0.94s; closed-loop guard returned `status=no_task`.
+- 2026-07-03: Started closed-loop task 003 to harden the guard against disguised risky normal tasks and make `reviews/review_package_002.md` reproducible.
+- 2026-07-03: Task 003 validation passed with `pytest` 29 passed and `compileall src tests`; `ruff check .` is unavailable in the current shell.
diff --git a/TECH_LEAD_PROTOCOL.md b/TECH_LEAD_PROTOCOL.md
index 3fd7bfc..c5934dc 100644
--- a/TECH_LEAD_PROTOCOL.md
+++ b/TECH_LEAD_PROTOCOL.md
@@ -14,11 +14,12 @@ Authority:

 Workflow:
 1. ChatGPT Pro writes one bounded task into `INBOX.md`.
-2. Codex inspects the relevant files before editing.
-3. Codex implements the smallest reversible change that satisfies the task.
-4. Codex validates with the narrowest meaningful local check first.
-5. Codex records status in `STATUS.md` and completion evidence in `OUTBOX.md`.
-6. ChatGPT Pro reviews `OUTBOX.md`, then either accepts or writes the next bounded task.
+2. Codex runs `scripts/run_codex_closed_loop.ps1` to validate task completeness and risk.
+3. Codex inspects the relevant files before editing.
+4. Codex implements the smallest reversible change that satisfies the task.
+5. Codex validates with the narrowest meaningful local check first.
+6. Codex records status in `STATUS.md` and completion evidence in `OUTBOX.md`.
+7. ChatGPT Pro reviews `OUTBOX.md`, then either accepts or writes the next bounded task.

 Task quality bar:
 - Include objective, target files/folders, constraints, acceptance criteria, and validation expected.
@@ -30,3 +31,10 @@ Review quality bar:
 - Lead with defects, regressions, missing tests, or violated acceptance criteria.
 - Cite files and exact commands or artifacts when possible.
 - Convert broad feedback into the next bounded implementation task.
+
+Closed-loop guard:
+- The automated loop may execute only when guard status is `ready`.
+- Empty or incomplete `INBOX.md` means no work should be invented.
+- Non-`normal` risk levels require explicit user confirmation outside `INBOX.md`.
+- Closed-loop runs may open draft PRs, but must not auto-merge.
+- See `docs/codex_closed_loop.md` for the runnable protocol.
diff --git a/TODO.md b/TODO.md
index 65fcebe..04909fa 100644
--- a/TODO.md
+++ b/TODO.md
@@ -49,3 +49,5 @@
 - [ ] 每次實驗寫入 `research/experiments.md`。
 - [ ] 每次 Codex 變更後寫入 `CHANGELOG.md`。
 - [x] 每輪 ChatGPT Review 寫入 `reviews/`。
+- [x] 建立 Codex/ChatGPT Pro 檔案式閉環守門器。
+- [ ] 審查第一輪自動化閉環輸出並調整 cadence。
diff --git a/configs/codex_closed_loop.yaml b/configs/codex_closed_loop.yaml
new file mode 100644
index 0000000..5f5401b
--- /dev/null
+++ b/configs/codex_closed_loop.yaml
@@ -0,0 +1,73 @@
+loop:
+  inbox_path: INBOX.md
+  report_dir: reports/codex_loop
+  allowed_risk_levels:
+    - normal
+  blocked_risk_levels:
+    - destructive
+    - credentialed
+    - external
+    - materially_risky
+  blocked_path_patterns:
+    - .git
+    - .venv
+    - _archive
+    - data/raw
+    - data/processed
+    - state/codex_context
+    - credentials
+    - secrets
+    - "C:\\"
+    - "E:\\"
+    - ..
+  blocked_content_patterns:
+    - delete
+    - remove-item
+    - rm -rf
+    - rmdir
+    - format
+    - reset --hard
+    - clean data/raw
+    - erase
+    - purge
+    - token
+    - password
+    - secret
+    - api_key
+    - apikey
+    - ssh key
+    - credential
+    - .env
+    - curl
+    - wget
+    - requests.get
+    - requests.post
+    - download
+    - upload
+    - external api
+    - broker api
+    - finlab download
+  allowed_target_roots:
+    - .gitignore
+    - AGENTS.md
+    - CHANGELOG.md
+    - FILE_MANIFEST.txt
+    - INBOX.md
+    - OUTBOX.md
+    - PROJECT_RULES.md
+    - README.md
+    - RUN_CODEX_NEXT.md
+    - STATUS.md
+    - TECH_LEAD_PROTOCOL.md
+    - TODO.md
+    - configs/
+    - docs/
+    - prompts/
+    - research/
+    - reviews/
+    - scripts/
+    - src/
+    - tests/
+    - pyproject.toml
+    - requirements.txt
+  allow_auto_merge: false
diff --git a/docs/codex_closed_loop.md b/docs/codex_closed_loop.md
new file mode 100644
index 0000000..5f70b94
--- /dev/null
+++ b/docs/codex_closed_loop.md
@@ -0,0 +1,82 @@
+# Codex Closed Loop
+
+本專案採用檔案式閉環，不使用 ChatGPT Pro 網頁 UI 當自動化後端。
+
+## 目標
+
+建立可重複、可審查、可暫停的工作迴圈：
+
+```text
+ChatGPT Pro writes one bounded task
+-> INBOX.md
+-> Codex guard validates scope and risk
+-> Codex implements only safe local tasks
+-> pytest and focused checks
+-> OUTBOX.md, STATUS.md, reviews/
+-> ChatGPT Pro reviews and writes the next task
+```
+
+## 安全邊界
+
+- 每輪只允許一個 bounded task。
+- `risk_level` 只有 `normal` 可自動執行。
+- `destructive`、`credentialed`、`external`、`materially_risky` 必須停下來等使用者明確確認。
+- 不自動 merge PR。
+- 不自動提升正式交易規則、正式 champion、正式買賣權重或實盤流程。
+- 不透過 ChatGPT Pro 網頁 UI 互貼內容；結果以檔案、GitHub PR、GitHub comment 或明確 API/connector 傳遞。
+
+## 任務格式
+
+`INBOX.md` 的 `Current task:` 後方應放一個 YAML 區塊：
+
+```yaml
+role: technical_lead
+task: "Implement one small verifiable change."
+target_files_or_folders:
+  - "src/abc_quant/..."
+current_spec_or_decision: "Why this task is valid now."
+constraints:
+  - "Do not change formal trading signals."
+acceptance_criteria:
+  - "The focused test covers the behavior."
+validation_expected:
+  - "python -m pytest"
+review_notes_or_defects:
+  - "none"
+anything_not_allowed:
+  - "No data download."
+risk_level: normal
+```
+
+## 執行方式
+
+先檢查任務是否可執行：
+
+```powershell
+.\scripts\run_codex_closed_loop.ps1
+```
+
+腳本會輸出 guard 報告到：
+
+```text
+reports/codex_loop/latest.json
+reports/codex_loop/latest.md
+```
+
+Codex automation 或人工 Codex thread 應先看 guard 結果：
+
+- `ready`: 可以依 `INBOX.md` 任務執行。
+- `no_task`: 沒有任務，不要自行發明工作。
+- `blocked_invalid`: 任務格式不足，回報缺欄位。
+- `blocked_risky`: 風險等級不允許自動執行，等待使用者確認。
+
+## 自動化建議
+
+適合建立 Codex worktree automation，每次喚醒時：
+
+1. 讀 `PROJECT_RULES.md`、`AGENTS.md`、`TECH_LEAD_PROTOCOL.md`。
+2. 執行 `scripts/run_codex_closed_loop.ps1`。
+3. 只有 guard 狀態為 `ready` 且風險為 `normal` 時才實作。
+4. 完成後執行測試，更新 `STATUS.md` 與 `OUTBOX.md`。
+5. 開 draft PR 或把結果寫入可審查檔案。
+6. 若 guard 不是 `ready`，只回報原因，不改程式。
diff --git a/prompts/codex_closed_loop_runner.md b/prompts/codex_closed_loop_runner.md
new file mode 100644
index 0000000..a6f82f7
--- /dev/null
+++ b/prompts/codex_closed_loop_runner.md
@@ -0,0 +1,14 @@
+# Codex Closed Loop Runner Prompt
+
+Use this prompt for a Codex automation or a manual closed-loop run in `E:\abc`.
+
+1. Read `AGENTS.md`, `PROJECT_RULES.md`, `TECH_LEAD_PROTOCOL.md`, and `docs/codex_closed_loop.md`.
+2. Run `scripts/run_codex_closed_loop.ps1`.
+3. If guard status is `no_task`, report that there is no current task and stop.
+4. If guard status is `blocked_invalid` or `blocked_risky`, report the exact blocker and stop.
+5. If guard status is `ready`, execute only the task in `INBOX.md`.
+6. Implement the smallest reversible change that satisfies the task.
+7. Run the validation requested in `INBOX.md`; at minimum run `python -m pytest` when code changed.
+8. Update `STATUS.md`, `OUTBOX.md`, `TODO.md` or `CHANGELOG.md` when relevant.
+9. Open a draft PR for review when files changed.
+10. Never auto-merge, never automate ChatGPT Pro web UI, and never execute destructive, credentialed, external, or materially risky work without explicit user confirmation.
diff --git a/pyproject.toml b/pyproject.toml
index fc38fb3..e0194cb 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -26,7 +26,7 @@ where = ["src"]
 [tool.pytest.ini_options]
 testpaths = ["tests"]
 pythonpath = ["src"]
-addopts = "--basetemp=.pytest-tmp -p no:cacheprovider"
+addopts = "--basetemp=.tmp_pytest -p no:cacheprovider"

 [tool.ruff]
 line-length = 100
diff --git a/reviews/review_package_002.md b/reviews/review_package_002.md
new file mode 100644
index 0000000..b7385d6
--- /dev/null
+++ b/reviews/review_package_002.md
@@ -0,0 +1,136 @@
+# Codex Closed-Loop Task 001 Review Package
+
+- as_of: `2026-07-03T22:28:24+08:00`
+- project_root: `E:\abc`
+- branch: `codex/file-closed-loop-guard`
+- head_commit: `efcfde6`
+- pr_url: `https://github.com/jongyawjong0514/abc-quant/pull/2`
+
+## Objective
+
+Finish repository hygiene, provide a tracked review package, verify the project, and push the current work to GitHub for ChatGPT Pro review.
+
+## Git Status
+
+```text
+## codex/file-closed-loop-guard...origin/codex/file-closed-loop-guard
+ M .gitignore
+ M CHANGELOG.md
+ M FILE_MANIFEST.txt
+ M OUTBOX.md
+ M STATUS.md
+?? reviews/review_package_002.md
+?? scripts/build_review_package.py
+(exit_code=0)
+```
+
+## Branch Diff Stat Versus Main
+
+```text
+ .gitignore                             |   1 +
+ CHANGELOG.md                           |   1 +
+ FILE_MANIFEST.txt                      |  22 +++-
+ INBOX.md                               |  43 ++++--
+ OUTBOX.md                              |  36 ++++++
+ README.md                              |  12 ++
+ STATUS.md                              |   3 +
+ TECH_LEAD_PROTOCOL.md                  |  18 ++-
+ TODO.md                                |   2 +
+ configs/codex_closed_loop.yaml         |  16 +++
+ docs/codex_closed_loop.md              |  82 ++++++++++++
+ prompts/codex_closed_loop_runner.md    |  14 ++
+ pyproject.toml                         |   2 +-
+ scripts/codex_loop_guard.py            |  31 +++++
+ scripts/run_codex_closed_loop.ps1      |  27 ++++
+ src/abc_quant/governance/__init__.py   |   2 +
+ src/abc_quant/governance/codex_loop.py | 230 +++++++++++++++++++++++++++++++++
+ tests/test_codex_loop_guard.py         |  91 +++++++++++++
+ 18 files changed, 615 insertions(+), 18 deletions(-)
+(exit_code=0)
+```
+
+## Branch Changed Files Versus Main
+
+```text
+.gitignore
+CHANGELOG.md
+FILE_MANIFEST.txt
+INBOX.md
+OUTBOX.md
+README.md
+STATUS.md
+TECH_LEAD_PROTOCOL.md
+TODO.md
+configs/codex_closed_loop.yaml
+docs/codex_closed_loop.md
+prompts/codex_closed_loop_runner.md
+pyproject.toml
+scripts/codex_loop_guard.py
+scripts/run_codex_closed_loop.ps1
+src/abc_quant/governance/__init__.py
+src/abc_quant/governance/codex_loop.py
+tests/test_codex_loop_guard.py
+(exit_code=0)
+```
+
+## Working Tree Diff Stat
+
+```text
+ .gitignore        |  1 +
+ CHANGELOG.md      |  1 +
+ FILE_MANIFEST.txt |  2 ++
+ OUTBOX.md         | 27 +++++++++++++++++++++++++++
+ STATUS.md         |  1 +
+ 5 files changed, 32 insertions(+)
+(exit_code=0)
+```
+
+## Validation
+
+### pytest
+
+```text
+============================= test session starts =============================
+platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
+rootdir: E:\abc
+configfile: pyproject.toml
+testpaths: tests
+collected 19 items
+
+tests\test_codex_loop_guard.py ......                                    [ 31%]
+tests\test_config_settings.py ..                                         [ 42%]
+tests\test_data_validation.py ....                                       [ 63%]
+tests\test_features_price_volume.py .                                    [ 68%]
+tests\test_labels_returns.py ..                                          [ 78%]
+tests\test_metrics_performance.py ..                                     [ 89%]
+tests\test_project_bootstrap.py ..                                       [100%]
+
+============================= 19 passed in 0.84s ==============================
+(exit_code=0)
+```
+
+### closed-loop guard
+
+```text
+status=no_task
+report=E:\abc\reports\codex_loop\latest.md
+(exit_code=0)
+```
+
+## Review Pointers
+
+- `docs/codex_closed_loop.md`: closed-loop protocol and safety boundaries.
+- `src/abc_quant/governance/codex_loop.py`: guard implementation.
+- `tests/test_codex_loop_guard.py`: guard behavior coverage.
+- `OUTBOX.md`: Codex execution summary.
+- `STATUS.md`: project status log.
+
+## Known Local Artifacts
+
+- `.venv/`, `.tmp_pytest/`, `state/codex_context/`, and `reports/codex_loop/` are local/ignored artifacts.
+- Old root-level `CODEX_REVIEW_PACKAGE.md` and `CODEX_TEST_RESULT.txt` are superseded by this tracked review package.
+- `.pytest_cache/` may remain as a Windows ACL residue on this machine; it is ignored and not part of Git history.
+
+## Promotion Boundary
+
+This package contains repository governance work only. It does not add trading strategy logic, model training, broker integration, or formal signal promotion.
diff --git a/scripts/build_review_package.py b/scripts/build_review_package.py
new file mode 100644
index 0000000..d7ad5fa
--- /dev/null
+++ b/scripts/build_review_package.py
@@ -0,0 +1,408 @@
+"""Build a tracked Markdown review package for ChatGPT Pro review."""
+
+from __future__ import annotations
+
+import argparse
+from dataclasses import dataclass
+from datetime import datetime
+from pathlib import Path
+import subprocess
+import sys
+from zoneinfo import ZoneInfo
+
+
+MANDATORY_CONTENT_FILES: tuple[str, ...] = (
+    "src/abc_quant/governance/codex_loop.py",
+    "tests/test_codex_loop_guard.py",
+    "scripts/build_review_package.py",
+    "scripts/codex_loop_guard.py",
+    "scripts/run_codex_closed_loop.ps1",
+    "configs/codex_closed_loop.yaml",
+    "docs/codex_closed_loop.md",
+    "INBOX.md",
+    "STATUS.md",
+    "OUTBOX.md",
+)
+
+
+@dataclass(frozen=True)
+class CommandResult:
+    """Captured command output for review-package rendering."""
+
+    command: str
+    output: str
+    exit_code: int | str
+
+
+@dataclass(frozen=True)
+class CleanStatus:
+    """Git cleanliness state with the output file excluded."""
+
+    output_file: str
+    status_excludes_output_file: bool
+    dirty_entries_excluding_output: tuple[str, ...]
+    dirty_entries_output_file: tuple[str, ...]
+
+    @property
+    def is_clean_excluding_output(self) -> bool:
+        return not self.dirty_entries_excluding_output
+
+
+def main() -> int:
+    parser = argparse.ArgumentParser(description="Build an ABC Quant review package.")
+    parser.add_argument("--output", type=Path, required=True, help="Markdown file to write.")
+    parser.add_argument("--title", default="Codex Review Package", help="Package title.")
+    parser.add_argument("--pr-url", default="", help="GitHub PR URL, if available.")
+    parser.add_argument(
+        "--run-validation",
+        action="store_true",
+        help="Run pytest, compileall, and ruff before writing the package.",
+    )
+    parser.add_argument(
+        "--include-diff",
+        action="store_true",
+        help="Include the full `git diff main...HEAD` output.",
+    )
+    parser.add_argument(
+        "--include-file-contents",
+        action="store_true",
+        help="Include full contents for changed and mandatory review files.",
+    )
+    parser.add_argument(
+        "--assert-clean",
+        action="store_true",
+        help="Fail if the working tree is dirty except for the output file.",
+    )
+    args = parser.parse_args()
+
+    root = Path.cwd()
+    output = resolve_output(root, args.output)
+    clean_status = inspect_clean_status(root, output)
+    if args.assert_clean and not clean_status.is_clean_excluding_output:
+        print("Working tree is dirty outside the review package output file:", file=sys.stderr)
+        for entry in clean_status.dirty_entries_excluding_output:
+            print(entry, file=sys.stderr)
+        return 2
+
+    validations: list[tuple[str, CommandResult]] = []
+    if args.run_validation:
+        validations.extend(run_validations(root))
+
+    output.parent.mkdir(parents=True, exist_ok=True)
+    package_text = strip_trailing_whitespace(
+        render_package(
+            root=root,
+            output=output,
+            title=args.title,
+            pr_url=args.pr_url,
+            validations=validations,
+            include_diff=args.include_diff,
+            include_file_contents=args.include_file_contents,
+            clean_status=clean_status,
+        )
+    )
+    with output.open("w", encoding="utf-8", newline="\n") as handle:
+        handle.write(package_text)
+    print(output)
+    return 0
+
+
+def resolve_output(root: Path, output: Path) -> Path:
+    """Return an absolute output path."""
+
+    if output.is_absolute():
+        return output
+    return root / output
+
+
+def run_validations(root: Path) -> list[tuple[str, CommandResult]]:
+    """Run review-package validation commands."""
+
+    return [
+        ("pytest", run_command([sys.executable, "-m", "pytest"], root)),
+        ("compileall", run_command([sys.executable, "-m", "compileall", "src", "tests"], root)),
+        ("ruff", run_optional_command(["ruff", "check", "."], root)),
+    ]
+
+
+def render_package(
+    *,
+    root: Path,
+    output: Path,
+    title: str,
+    pr_url: str,
+    validations: list[tuple[str, CommandResult]],
+    include_diff: bool,
+    include_file_contents: bool,
+    clean_status: CleanStatus,
+) -> str:
+    as_of = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
+    output_relative = relative_to_root(output, root)
+    branch = git_value(["branch", "--show-current"], root)
+    head_sha = git_value(["rev-parse", "HEAD"], root)
+    git_status = git(["status", "--short", "--branch"], root)
+    diff_check = git(["diff", "--check"], root)
+    diff_stat = git(["diff", "--stat", "main...HEAD"], root)
+    diff_names_result = run_command(["git", "diff", "--name-only", "main...HEAD"], root)
+    diff_names = diff_names_result.output.rstrip() + f"\n(exit_code={diff_names_result.exit_code})"
+    full_diff = git(["diff", "main...HEAD"], root) if include_diff else "_Not requested._"
+
+    sections = [
+        f"# {title}",
+        "",
+        "## Metadata",
+        "",
+        f"- as_of: `{as_of}`",
+        f"- project_root: `{root}`",
+        f"- pr_url: `{pr_url}`" if pr_url else "- pr_url: ``",
+        f"- branch: `{branch}`",
+        f"- head_sha: `{head_sha}`",
+        f"- status_excludes_output_file: {str(clean_status.status_excludes_output_file).lower()}",
+        f"- output_file: {output_relative}",
+        "",
+        "## Objective",
+        "",
+        "Harden the file-based closed-loop guard, make the review package reproducible, and keep this PR limited to repository governance.",
+        "",
+        "## Git Status",
+        "",
+        "Command: `git status --short --branch`",
+        "",
+        fenced(git_status),
+        "",
+        "## Assert Clean",
+        "",
+        f"- clean_excluding_output_file: {str(clean_status.is_clean_excluding_output).lower()}",
+        "",
+    ]
+    if clean_status.dirty_entries_excluding_output:
+        sections.extend(["Dirty entries excluding output:", "", fenced("\n".join(clean_status.dirty_entries_excluding_output)), ""])
+    if clean_status.dirty_entries_output_file:
+        sections.extend(["Output-file entries excluded from assert-clean:", "", fenced("\n".join(clean_status.dirty_entries_output_file)), ""])
+
+    sections.extend(
+        [
+            "## Git Diff Check",
+            "",
+            "Command: `git diff --check`",
+            "",
+            fenced(diff_check),
+            "",
+            "## Branch Diff Stat Versus Main",
+            "",
+            "Command: `git diff --stat main...HEAD`",
+            "",
+            fenced(diff_stat),
+            "",
+            "## Branch Changed Files Versus Main",
+            "",
+            "Command: `git diff --name-only main...HEAD`",
+            "",
+            fenced(diff_names),
+            "",
+            "## Branch Diff Versus Main",
+            "",
+            "Command: `git diff main...HEAD`",
+            "",
+            fenced(full_diff),
+            "",
+            "## Validation",
+            "",
+        ]
+    )
+
+    if validations:
+        for name, result in validations:
+            sections.extend(
+                [
+                    f"### {name}",
+                    "",
+                    f"Command: `{result.command}`",
+                    "",
+                    fenced(result.output.rstrip() + f"\n(exit_code={result.exit_code})"),
+                    "",
+                ]
+            )
+    else:
+        sections.append("_No validation commands were run by the package builder._")
+
+    if include_file_contents:
+        sections.extend(render_file_contents(root, output, diff_names_result.output))
+    else:
+        sections.extend(["", "## File Contents", "", "_Not requested._", ""])
+
+    sections.extend(
+        [
+            "## Known Local Artifacts",
+            "",
+            "- `.venv/`, `.tmp_pytest/`, `state/codex_context/`, and `reports/codex_loop/` are local/ignored artifacts.",
+            "- Old root-level `CODEX_REVIEW_PACKAGE.md` and `CODEX_TEST_RESULT.txt` are superseded by `reviews/review_package_002.md`.",
+            "- `.pytest_cache/` may remain as a Windows ACL residue on this machine; it is ignored and not part of Git history.",
+            "",
+            "## Promotion Boundary",
+            "",
+            "This package contains repository governance work only. It does not add trading strategy logic, model training, broker integration, FinLab download logic, data downloads, or formal signal promotion.",
+            "",
+        ]
+    )
+    return "\n".join(sections)
+
+
+def render_file_contents(root: Path, output: Path, diff_names: str) -> list[str]:
+    """Render full file contents for changed files and required review files."""
+
+    files = ordered_unique(
+        [
+            *[line.strip() for line in diff_names.splitlines() if line.strip()],
+            *MANDATORY_CONTENT_FILES,
+        ]
+    )
+    output_relative = relative_to_root(output, root)
+
+    sections = ["", "## File Contents", ""]
+    for relative in files:
+        if relative == output_relative:
+            sections.extend([f"### `{relative}`", "", "_Skipped output file to avoid recursive package growth._", ""])
+            continue
+        path = root / relative
+        sections.extend([f"### `{relative}`", ""])
+        if not path.exists():
+            sections.extend(["_Missing._", ""])
+            continue
+        if not path.is_file():
+            sections.extend(["_Not a regular file._", ""])
+            continue
+        try:
+            text = path.read_text(encoding="utf-8", errors="replace")
+        except OSError as exc:
+            sections.extend([f"_Could not read file: {exc}_", ""])
+            continue
+        sections.extend([fenced(text), ""])
+    return sections
+
+
+def inspect_clean_status(root: Path, output: Path) -> CleanStatus:
+    """Return porcelain status entries, excluding only the output file."""
+
+    output_relative = relative_to_root(output, root)
+    completed = subprocess.run(
+        ["git", "status", "--porcelain=v1", "--untracked-files=normal"],
+        cwd=root,
+        text=True,
+        stdout=subprocess.PIPE,
+        stderr=subprocess.STDOUT,
+        check=False,
+    )
+    entries = tuple(line for line in completed.stdout.splitlines() if line.strip())
+    output_entries: list[str] = []
+    other_entries: list[str] = []
+    for entry in entries:
+        if status_entry_mentions_path(entry, output_relative):
+            output_entries.append(entry)
+        else:
+            other_entries.append(entry)
+    return CleanStatus(
+        output_file=output_relative,
+        status_excludes_output_file=True,
+        dirty_entries_excluding_output=tuple(other_entries),
+        dirty_entries_output_file=tuple(output_entries),
+    )
+
+
+def status_entry_mentions_path(entry: str, relative_path: str) -> bool:
+    """Return true when a porcelain status entry refers to the given path."""
+
+    normalized = normalize_path(relative_path)
+    payload = normalize_path(entry[3:].strip().strip('"')) if len(entry) > 3 else ""
+    if " -> " in payload:
+        old_path, new_path = payload.split(" -> ", 1)
+        return old_path == normalized or new_path == normalized
+    return payload == normalized
+
+
+def relative_to_root(path: Path, root: Path) -> str:
+    """Return a repo-relative path with forward slashes."""
+
+    try:
+        relative = path.resolve().relative_to(root.resolve())
+    except ValueError:
+        return normalize_path(str(path))
+    return normalize_path(relative.as_posix())
+
+
+def normalize_path(path: str) -> str:
+    return path.replace("\\", "/")
+
+
+def git(args: list[str], cwd: Path) -> str:
+    result = run_command(["git", *args], cwd)
+    return result.output.rstrip() + f"\n(exit_code={result.exit_code})"
+
+
+def git_value(args: list[str], cwd: Path) -> str:
+    result = run_command(["git", *args], cwd)
+    value = result.output.strip()
+    if result.exit_code != 0:
+        return f"{value} (exit_code={result.exit_code})"
+    return value
+
+
+def run_command(args: list[str], cwd: Path) -> CommandResult:
+    completed = subprocess.run(
+        args,
+        cwd=cwd,
+        text=True,
+        stdout=subprocess.PIPE,
+        stderr=subprocess.STDOUT,
+        check=False,
+    )
+    return CommandResult(
+        command=shell_join(args),
+        output=completed.stdout.rstrip(),
+        exit_code=completed.returncode,
+    )
+
+
+def run_optional_command(args: list[str], cwd: Path) -> CommandResult:
+    try:
+        return run_command(args, cwd)
+    except FileNotFoundError:
+        return CommandResult(
+            command=shell_join(args),
+            output=f"unavailable: `{args[0]}` executable was not found",
+            exit_code="unavailable",
+        )
+
+
+def shell_join(args: list[str]) -> str:
+    return " ".join(quote_arg(arg) for arg in args)
+
+
+def quote_arg(arg: str) -> str:
+    if not arg or any(char.isspace() for char in arg):
+        return '"' + arg.replace('"', '\\"') + '"'
+    return arg
+
+
+def fenced(text: str) -> str:
+    return "```text\n" + text.rstrip() + "\n```"
+
+
+def strip_trailing_whitespace(text: str) -> str:
+    """Normalize generated Markdown so `git diff --check` stays clean."""
+
+    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
+
+
+def ordered_unique(values: list[str]) -> list[str]:
+    seen: set[str] = set()
+    output: list[str] = []
+    for value in values:
+        if value not in seen:
+            output.append(value)
+            seen.add(value)
+    return output
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/scripts/codex_loop_guard.py b/scripts/codex_loop_guard.py
new file mode 100644
index 0000000..1a31a4d
--- /dev/null
+++ b/scripts/codex_loop_guard.py
@@ -0,0 +1,31 @@
+"""CLI wrapper for the Codex closed-loop inbox guard."""
+
+from __future__ import annotations
+
+import argparse
+from pathlib import Path
+import sys
+
+from abc_quant.governance.codex_loop import run_guard
+
+
+def main() -> int:
+    parser = argparse.ArgumentParser(description="Validate the current Codex closed-loop task.")
+    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root.")
+    parser.add_argument("--strict", action="store_true", help="Exit nonzero unless status is ready.")
+    args = parser.parse_args()
+
+    root = args.root.resolve()
+    result = run_guard(root=root)
+    print(f"status={result.status}")
+    print(f"report={root / 'reports' / 'codex_loop' / 'latest.md'}")
+
+    if args.strict and not result.is_ready:
+        return 2
+    if result.status in {"blocked_invalid", "blocked_risky"}:
+        return 2
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/scripts/run_codex_closed_loop.ps1 b/scripts/run_codex_closed_loop.ps1
new file mode 100644
index 0000000..d7c6310
--- /dev/null
+++ b/scripts/run_codex_closed_loop.ps1
@@ -0,0 +1,27 @@
+param(
+    [switch]$Strict
+)
+
+$ErrorActionPreference = "Stop"
+
+$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
+$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
+
+if (Test-Path $VenvPython) {
+    $Python = $VenvPython
+} else {
+    $Python = "python"
+}
+
+$ScriptArgs = @(
+    (Join-Path $ProjectRoot "scripts\codex_loop_guard.py"),
+    "--root",
+    $ProjectRoot
+)
+
+if ($Strict) {
+    $ScriptArgs += "--strict"
+}
+
+& $Python @ScriptArgs
+exit $LASTEXITCODE
diff --git a/src/abc_quant/governance/__init__.py b/src/abc_quant/governance/__init__.py
new file mode 100644
index 0000000..12cd50a
--- /dev/null
+++ b/src/abc_quant/governance/__init__.py
@@ -0,0 +1,2 @@
+"""Governance helpers for Codex/ChatGPT handoff workflows."""
+
diff --git a/src/abc_quant/governance/codex_loop.py b/src/abc_quant/governance/codex_loop.py
new file mode 100644
index 0000000..c429ec8
--- /dev/null
+++ b/src/abc_quant/governance/codex_loop.py
@@ -0,0 +1,590 @@
+"""Guard rails for the file-based Codex/ChatGPT closed loop."""
+
+from __future__ import annotations
+
+from dataclasses import asdict, dataclass
+from pathlib import Path
+import json
+import re
+from typing import Any
+
+import yaml
+
+REQUIRED_TASK_FIELDS: tuple[str, ...] = (
+    "role",
+    "task",
+    "target_files_or_folders",
+    "current_spec_or_decision",
+    "constraints",
+    "acceptance_criteria",
+    "validation_expected",
+    "review_notes_or_defects",
+    "anything_not_allowed",
+    "risk_level",
+)
+
+KNOWN_RISK_LEVELS: frozenset[str] = frozenset(
+    {"normal", "destructive", "credentialed", "external", "materially_risky"}
+)
+DEFAULT_REPORT_DIR = Path("reports/codex_loop")
+DEFAULT_CONFIG_PATH = Path("configs/codex_closed_loop.yaml")
+
+DEFAULT_BLOCKED_CONTENT_PATTERNS: tuple[str, ...] = (
+    "delete",
+    "remove-item",
+    "rm -rf",
+    "rmdir",
+    "format",
+    "reset --hard",
+    "clean data/raw",
+    "erase",
+    "purge",
+    "token",
+    "password",
+    "secret",
+    "api_key",
+    "apikey",
+    "ssh key",
+    "credential",
+    ".env",
+    "curl",
+    "wget",
+    "requests.get",
+    "requests.post",
+    "download",
+    "upload",
+    "external api",
+    "broker api",
+    "finlab download",
+)
+DEFAULT_BLOCKED_PATH_PATTERNS: tuple[str, ...] = (
+    ".git",
+    ".venv",
+    "_archive",
+    "data/raw",
+    "data/processed",
+    "state/codex_context",
+    "credentials",
+    "secrets",
+    "c:\\",
+    "e:\\",
+    "..",
+)
+DEFAULT_ALLOWED_TARGET_ROOTS: tuple[str, ...] = (
+    ".gitignore",
+    "AGENTS.md",
+    "CHANGELOG.md",
+    "FILE_MANIFEST.txt",
+    "INBOX.md",
+    "OUTBOX.md",
+    "PROJECT_RULES.md",
+    "README.md",
+    "RUN_CODEX_NEXT.md",
+    "STATUS.md",
+    "TECH_LEAD_PROTOCOL.md",
+    "TODO.md",
+    "configs/",
+    "docs/",
+    "prompts/",
+    "research/",
+    "reviews/",
+    "scripts/",
+    "src/",
+    "tests/",
+    "pyproject.toml",
+    "requirements.txt",
+)
+
+
+class TaskParseError(ValueError):
+    """Raised when the current task block cannot be parsed as YAML or key-value text."""
+
+
+@dataclass(frozen=True)
+class LoopGuardConfig:
+    """Configuration for closed-loop task validation."""
+
+    inbox_path: Path = Path("INBOX.md")
+    report_dir: Path = DEFAULT_REPORT_DIR
+    allowed_risk_levels: frozenset[str] = frozenset({"normal"})
+    blocked_risk_levels: frozenset[str] = frozenset(
+        {"destructive", "credentialed", "external", "materially_risky"}
+    )
+    blocked_path_patterns: tuple[str, ...] = DEFAULT_BLOCKED_PATH_PATTERNS
+    blocked_content_patterns: tuple[str, ...] = DEFAULT_BLOCKED_CONTENT_PATTERNS
+    allowed_target_roots: tuple[str, ...] = DEFAULT_ALLOWED_TARGET_ROOTS
+    allow_auto_merge: bool = False
+
+
+@dataclass(frozen=True)
+class LoopGuardResult:
+    """Result of validating the current closed-loop inbox task."""
+
+    status: str
+    risk_level: str | None
+    missing_fields: tuple[str, ...]
+    messages: tuple[str, ...]
+    task: dict[str, Any]
+
+    @property
+    def is_ready(self) -> bool:
+        return self.status == "ready"
+
+
+def default_guard_config() -> LoopGuardConfig:
+    """Return the conservative built-in guard configuration."""
+
+    return LoopGuardConfig()
+
+
+def load_guard_config(root: Path, config_path: Path | None = None) -> LoopGuardConfig:
+    """Load closed-loop config, falling back to conservative defaults when absent."""
+
+    path = config_path or root / DEFAULT_CONFIG_PATH
+    if not path.exists():
+        return default_guard_config()
+
+    try:
+        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
+    except OSError as exc:
+        raise ValueError(f"Could not read closed-loop config: {path}") from exc
+    except yaml.YAMLError as exc:
+        raise ValueError(f"Invalid closed-loop config YAML: {path}") from exc
+
+    if not isinstance(raw, dict):
+        raise ValueError(f"Closed-loop config root must be a mapping: {path}")
+    data = raw.get("loop", raw)
+    if not isinstance(data, dict):
+        raise ValueError(f"Closed-loop config `loop` must be a mapping: {path}")
+
+    defaults = default_guard_config()
+    allowed = _string_set(data.get("allowed_risk_levels"), defaults.allowed_risk_levels)
+    blocked = _string_set(data.get("blocked_risk_levels"), defaults.blocked_risk_levels)
+    allowed = frozenset(level for level in allowed if level == "normal")
+    if not allowed:
+        allowed = defaults.allowed_risk_levels
+
+    return LoopGuardConfig(
+        inbox_path=Path(str(data.get("inbox_path", defaults.inbox_path))),
+        report_dir=Path(str(data.get("report_dir", defaults.report_dir))),
+        allowed_risk_levels=allowed,
+        blocked_risk_levels=blocked.union(defaults.blocked_risk_levels),
+        blocked_path_patterns=_string_tuple(
+            data.get("blocked_path_patterns"), defaults.blocked_path_patterns
+        ),
+        blocked_content_patterns=_string_tuple(
+            data.get("blocked_content_patterns"), defaults.blocked_content_patterns
+        ),
+        allowed_target_roots=_string_tuple(
+            data.get("allowed_target_roots"), defaults.allowed_target_roots
+        ),
+        allow_auto_merge=False,
+    )
+
+
+def evaluate_inbox(
+    inbox_text: str,
+    *,
+    allowed_risk_levels: set[str] | frozenset[str] | None = None,
+    config: LoopGuardConfig | None = None,
+) -> LoopGuardResult:
+    """Validate the `Current task` section of `INBOX.md`."""
+
+    active_config = config or default_guard_config()
+    if allowed_risk_levels is not None:
+        active_config = LoopGuardConfig(
+            inbox_path=active_config.inbox_path,
+            report_dir=active_config.report_dir,
+            allowed_risk_levels=frozenset(allowed_risk_levels),
+            blocked_risk_levels=active_config.blocked_risk_levels,
+            blocked_path_patterns=active_config.blocked_path_patterns,
+            blocked_content_patterns=active_config.blocked_content_patterns,
+            allowed_target_roots=active_config.allowed_target_roots,
+            allow_auto_merge=False,
+        )
+
+    current_task = extract_current_task(inbox_text)
+    if not current_task:
+        return _result("no_task", None, (), ("No current task found after `Current task:`.",), {})
+
+    try:
+        task = parse_task_block(current_task)
+    except TaskParseError as exc:
+        return _result("blocked_invalid", None, (), (str(exc),), {})
+
+    if not task:
+        return _result(
+            "no_task",
+            None,
+            (),
+            ("No parseable current task found after `Current task:`.",),
+            {},
+        )
+
+    missing = tuple(field for field in REQUIRED_TASK_FIELDS if _is_blank(task.get(field)))
+    if missing:
+        return _result(
+            "blocked_invalid",
+            _normalize_risk(task.get("risk_level")),
+            missing,
+            ("Current task is missing required fields.",),
+            task,
+        )
+
+    risk_level = _normalize_risk(task.get("risk_level"))
+    if risk_level not in KNOWN_RISK_LEVELS:
+        return _result(
+            "blocked_invalid",
+            risk_level,
+            (),
+            (f"Unknown risk level: {risk_level!r}.",),
+            task,
+        )
+    if risk_level in active_config.blocked_risk_levels:
+        return _result(
+            "blocked_risky",
+            risk_level,
+            (),
+            (f"Risk level `{risk_level}` requires explicit user confirmation.",),
+            task,
+        )
+    if risk_level not in active_config.allowed_risk_levels:
+        return _result(
+            "blocked_risky",
+            risk_level,
+            (),
+            (f"Risk level `{risk_level}` is not allowed for automation.",),
+            task,
+        )
+
+    if str(task.get("role", "")).strip().lower() != "technical_lead":
+        return _result(
+            "blocked_invalid",
+            risk_level,
+            (),
+            ("Task role must be `technical_lead`.",),
+            task,
+        )
+
+    risk_messages = scan_task_risks(task, active_config)
+    if risk_messages:
+        return _result("blocked_risky", risk_level, (), tuple(risk_messages), task)
+
+    return _result(
+        "ready",
+        risk_level,
+        (),
+        ("Current task is complete and allowed for local closed-loop execution.",),
+        task,
+    )
+
+
+def scan_task_risks(task: dict[str, Any], config: LoopGuardConfig) -> list[str]:
+    """Return safety blockers found in actionable task fields."""
+
+    messages: list[str] = []
+    actionable_text = _actionable_task_text(task)
+    normalized_actionable = _normalize_text(actionable_text)
+    for pattern in config.blocked_content_patterns:
+        normalized_pattern = _normalize_text(pattern)
+        if normalized_pattern and normalized_pattern in normalized_actionable:
+            messages.append(f"Blocked risky content pattern: `{pattern}`.")
+
+    for target in _as_list(task.get("target_files_or_folders")):
+        target_text = str(target).strip()
+        if not target_text:
+            continue
+        blocked_pattern = _blocked_target_pattern(target_text, config)
+        if blocked_pattern:
+            messages.append(
+                f"Blocked target path `{target_text}` by pattern `{blocked_pattern}`."
+            )
+            continue
+        if not _target_is_allowed(target_text, config.allowed_target_roots):
+            messages.append(f"Target path `{target_text}` is outside allowed target roots.")
+
+    contradiction = _not_allowed_contradiction(task, normalized_actionable)
+    if contradiction:
+        messages.append(contradiction)
+
+    return _dedupe(messages)
+
+
+def extract_current_task(inbox_text: str) -> str:
+    """Return the text after the first `Current task:` marker."""
+
+    match = re.search(r"(?im)^Current task:\s*$", inbox_text)
+    if not match:
+        return ""
+    return inbox_text[match.end() :].strip()
+
+
+def parse_task_block(task_text: str) -> dict[str, Any]:
+    """Parse a fenced YAML task block or simple `Field: value` lines."""
+
+    fenced = re.search(r"```(?:ya?ml)?\s*(.*?)```", task_text, flags=re.DOTALL | re.I)
+    source = fenced.group(1) if fenced else task_text
+
+    try:
+        parsed = yaml.safe_load(source)
+    except yaml.YAMLError as exc:
+        raise TaskParseError(f"Current task YAML parse error: {exc}") from exc
+
+    if isinstance(parsed, dict):
+        return {_normalize_key(str(key)): value for key, value in parsed.items()}
+    if parsed is None:
+        return {}
+
+    task: dict[str, Any] = {}
+    for line in source.splitlines():
+        if line.lstrip().startswith("#"):
+            continue
+        match = re.match(r"^\s*-?\s*([^:]+):\s*(.*)$", line)
+        if match:
+            task[_normalize_key(match.group(1))] = match.group(2).strip()
+    return task
+
+
+def run_guard(
+    *,
+    root: Path,
+    inbox_path: Path | None = None,
+    report_dir: Path | None = None,
+    config_path: Path | None = None,
+) -> LoopGuardResult:
+    """Read the inbox, evaluate it, and always write latest guard reports."""
+
+    root = root.resolve()
+    try:
+        config = load_guard_config(root, config_path=config_path)
+        inbox = inbox_path or root / config.inbox_path
+        output_dir = report_dir or root / config.report_dir
+        try:
+            inbox_text = inbox.read_text(encoding="utf-8")
+        except FileNotFoundError:
+            result = _result(
+                "blocked_invalid",
+                None,
+                (),
+                (f"INBOX file is missing: {inbox}",),
+                {},
+            )
+        except OSError as exc:
+            result = _result(
+                "blocked_invalid",
+                None,
+                (),
+                (f"Could not read INBOX file {inbox}: {exc}",),
+                {},
+            )
+        else:
+            result = evaluate_inbox(inbox_text, config=config)
+    except Exception as exc:
+        output_dir = report_dir or root / DEFAULT_REPORT_DIR
+        result = _result(
+            "blocked_invalid",
+            None,
+            (),
+            (f"Closed-loop guard failed safely: {exc}",),
+            {},
+        )
+
+    write_guard_reports(result, output_dir)
+    return result
+
+
+def write_guard_reports(result: LoopGuardResult, report_dir: Path) -> None:
+    """Write JSON and Markdown guard reports."""
+
+    report_dir.mkdir(parents=True, exist_ok=True)
+    payload = asdict(result)
+    (report_dir / "latest.json").write_text(
+        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
+        encoding="utf-8",
+    )
+    (report_dir / "latest.md").write_text(render_markdown_report(result), encoding="utf-8")
+
+
+def render_markdown_report(result: LoopGuardResult) -> str:
+    """Render a human-readable guard report."""
+
+    lines = [
+        "# Codex Closed Loop Guard",
+        "",
+        f"- status: `{result.status}`",
+        f"- risk_level: `{result.risk_level or ''}`",
+    ]
+    if result.missing_fields:
+        lines.append(f"- missing_fields: `{', '.join(result.missing_fields)}`")
+    lines.append("")
+    lines.append("## Messages")
+    for message in result.messages:
+        lines.append(f"- {message}")
+    if result.task:
+        lines.extend(["", "## Task", ""])
+        for key in REQUIRED_TASK_FIELDS:
+            lines.append(f"- `{key}`: {result.task.get(key)!r}")
+    return "\n".join(lines) + "\n"
+
+
+def _result(
+    status: str,
+    risk_level: str | None,
+    missing_fields: tuple[str, ...],
+    messages: tuple[str, ...],
+    task: dict[str, Any],
+) -> LoopGuardResult:
+    return LoopGuardResult(
+        status=status,
+        risk_level=risk_level,
+        missing_fields=missing_fields,
+        messages=messages,
+        task=task,
+    )
+
+
+def _actionable_task_text(task: dict[str, Any]) -> str:
+    fields = (
+        "task",
+        "target_files_or_folders",
+        "current_spec_or_decision",
+        "constraints",
+        "acceptance_criteria",
+        "validation_expected",
+    )
+    return "\n".join(_flatten_text(task.get(field)) for field in fields)
+
+
+def _not_allowed_contradiction(task: dict[str, Any], normalized_actionable: str) -> str | None:
+    for item in _as_list(task.get("anything_not_allowed")):
+        phrase = _forbidden_phrase(str(item))
+        if phrase and phrase in normalized_actionable:
+            return f"Task contradicts `anything_not_allowed`: `{item}`."
+    return None
+
+
+def _forbidden_phrase(value: str) -> str:
+    phrase = _normalize_text(value)
+    for prefix in ("do not ", "dont ", "don't ", "no ", "without "):
+        if phrase.startswith(prefix):
+            phrase = phrase[len(prefix) :]
+    phrase = phrase.strip()
+    return phrase if len(phrase) >= 4 else ""
+
+
+def _blocked_target_pattern(target: str, config: LoopGuardConfig) -> str | None:
+    normalized = _normalize_path_text(target)
+    components = tuple(part for part in normalized.split("/") if part)
+    if _is_absolute_path(normalized):
+        return "absolute path"
+
+    for pattern in config.blocked_path_patterns:
+        normalized_pattern = _normalize_path_text(pattern)
+        if normalized_pattern == ".." and ".." in components:
+            return pattern
+        if normalized_pattern in {".git", ".venv", "_archive", "credentials", "secrets"}:
+            if normalized_pattern in components:
+                return pattern
+            continue
+        if normalized_pattern in {"c:/", "e:/"} and normalized.startswith(normalized_pattern):
+            return pattern
+        if normalized == normalized_pattern or normalized.startswith(normalized_pattern + "/"):
+            return pattern
+    return None
+
+
+def _target_is_allowed(target: str, allowed_roots: tuple[str, ...]) -> bool:
+    normalized = _normalize_path_text(target).rstrip("/")
+    for root in allowed_roots:
+        allowed = _normalize_path_text(root).rstrip("/")
+        if not allowed:
+            continue
+        if normalized == allowed or normalized.startswith(allowed + "/"):
+            return True
+        if root.endswith("/") and normalized == allowed:
+            return True
+    return False
+
+
+def _is_absolute_path(path_text: str) -> bool:
+    return bool(re.match(r"^[a-z]:/", path_text, flags=re.I)) or path_text.startswith("/")
+
+
+def _normalize_key(key: str) -> str:
+    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", key.strip().lower()).strip("_")
+    aliases = {
+        "target_files_or_folders": "target_files_or_folders",
+        "target_files_folders": "target_files_or_folders",
+        "review_notes_or_defects": "review_notes_or_defects",
+        "review_notes_defects": "review_notes_or_defects",
+        "anything_not_allowed": "anything_not_allowed",
+        "not_allowed": "anything_not_allowed",
+        "risk": "risk_level",
+    }
+    return aliases.get(normalized, normalized)
+
+
+def _normalize_risk(value: Any) -> str | None:
+    if value is None:
+        return None
+    return str(value).strip().lower().replace("-", "_").replace(" ", "_")
+
+
+def _normalize_text(value: str) -> str:
+    return re.sub(r"\s+", " ", value.strip().lower().replace("\\", "/"))
+
+
+def _normalize_path_text(value: str) -> str:
+    return re.sub(r"/+", "/", value.strip().lower().replace("\\", "/"))
+
+
+def _flatten_text(value: Any) -> str:
+    if value is None:
+        return ""
+    if isinstance(value, dict):
+        return "\n".join(f"{key}: {_flatten_text(val)}" for key, val in value.items())
+    if isinstance(value, (list, tuple, set)):
+        return "\n".join(_flatten_text(item) for item in value)
+    return str(value)
+
+
+def _as_list(value: Any) -> list[Any]:
+    if value is None:
+        return []
+    if isinstance(value, list):
+        return value
+    if isinstance(value, tuple):
+        return list(value)
+    return [value]
+
+
+def _is_blank(value: Any) -> bool:
+    if value is None:
+        return True
+    if isinstance(value, str):
+        return not value.strip()
+    if isinstance(value, (list, tuple, set, dict)):
+        return len(value) == 0
+    return False
+
+
+def _string_tuple(value: Any, default: tuple[str, ...]) -> tuple[str, ...]:
+    if value is None:
+        return default
+    return tuple(str(item).strip() for item in _as_list(value) if str(item).strip())
+
+
+def _string_set(value: Any, default: frozenset[str]) -> frozenset[str]:
+    if value is None:
+        return default
+    return frozenset(str(item).strip().lower() for item in _as_list(value) if str(item).strip())
+
+
+def _dedupe(messages: list[str]) -> list[str]:
+    seen: set[str] = set()
+    output: list[str] = []
+    for message in messages:
+        if message not in seen:
+            output.append(message)
+            seen.add(message)
+    return output
diff --git a/tests/test_codex_loop_guard.py b/tests/test_codex_loop_guard.py
new file mode 100644
index 0000000..b573c59
--- /dev/null
+++ b/tests/test_codex_loop_guard.py
@@ -0,0 +1,214 @@
+import json
+
+from abc_quant.governance.codex_loop import evaluate_inbox, load_guard_config, run_guard
+
+
+def _task_yaml(
+    *,
+    risk_level: str = "normal",
+    role: str = "technical_lead",
+    task: str = "Add one focused test.",
+    target_files_or_folders: list[str] | None = None,
+    constraints: list[str] | None = None,
+    validation_expected: list[str] | None = None,
+    anything_not_allowed: list[str] | None = None,
+) -> str:
+    targets = target_files_or_folders or ["tests/"]
+    constraints = constraints or ["No unrelated refactor."]
+    validation_expected = validation_expected or ["python -m pytest"]
+    anything_not_allowed = anything_not_allowed or ["No external network."]
+
+    return f"""# INBOX
+
+Current task:
+
+```yaml
+role: {role}
+task: "{task}"
+target_files_or_folders:
+{_yaml_list(targets)}
+current_spec_or_decision: "Guard test fixture."
+constraints:
+{_yaml_list(constraints)}
+acceptance_criteria:
+  - "pytest passes."
+validation_expected:
+{_yaml_list(validation_expected)}
+review_notes_or_defects:
+  - "none"
+anything_not_allowed:
+{_yaml_list(anything_not_allowed)}
+risk_level: {risk_level}
+```
+"""
+
+
+def _yaml_list(values: list[str]) -> str:
+    return "\n".join(f"  - {_yaml_quote(value)}" for value in values)
+
+
+def _yaml_quote(value: str) -> str:
+    return "'" + value.replace("'", "''") + "'"
+
+
+def test_empty_current_task_returns_no_task() -> None:
+    result = evaluate_inbox("# INBOX\n\nCurrent task:\n")
+
+    assert result.status == "no_task"
+    assert not result.is_ready
+
+
+def test_commented_template_returns_no_task() -> None:
+    inbox = """# INBOX
+
+Current task:
+
+```yaml
+# role: technical_lead
+# task: "Replace this template."
+# risk_level: normal
+```
+"""
+
+    result = evaluate_inbox(inbox)
+
+    assert result.status == "no_task"
+    assert not result.is_ready
+
+
+def test_complete_normal_task_is_ready() -> None:
+    result = evaluate_inbox(_task_yaml())
+
+    assert result.status == "ready"
+    assert result.is_ready
+    assert result.risk_level == "normal"
+    assert result.task["task"] == "Add one focused test."
+
+
+def test_missing_required_field_blocks_execution() -> None:
+    inbox = _task_yaml().replace("validation_expected:\n  - 'python -m pytest'\n", "")
+
+    result = evaluate_inbox(inbox)
+
+    assert result.status == "blocked_invalid"
+    assert "validation_expected" in result.missing_fields
+
+
+def test_risky_task_requires_user_confirmation() -> None:
+    result = evaluate_inbox(_task_yaml(risk_level="credentialed"))
+
+    assert result.status == "blocked_risky"
+    assert result.risk_level == "credentialed"
+
+
+def test_run_guard_writes_reports(tmp_path) -> None:
+    root = tmp_path
+    (root / "INBOX.md").write_text(_task_yaml(), encoding="utf-8")
+
+    result = run_guard(root=root)
+
+    assert result.status == "ready"
+    payload = json.loads((root / "reports/codex_loop/latest.json").read_text(encoding="utf-8"))
+    assert payload["status"] == "ready"
+    assert (root / "reports/codex_loop/latest.md").exists()
+
+
+def test_normal_task_with_destructive_keyword_is_blocked() -> None:
+    result = evaluate_inbox(_task_yaml(task="delete old generated files"))
+
+    assert result.status == "blocked_risky"
+    assert any("delete" in message for message in result.messages)
+
+
+def test_normal_task_with_credential_keyword_is_blocked() -> None:
+    result = evaluate_inbox(_task_yaml(task="read API token setup"))
+
+    assert result.status == "blocked_risky"
+    assert any("token" in message for message in result.messages)
+
+
+def test_normal_task_with_external_network_keyword_is_blocked() -> None:
+    result = evaluate_inbox(_task_yaml(validation_expected=["curl https://example.test"]))
+
+    assert result.status == "blocked_risky"
+    assert any("curl" in message for message in result.messages)
+
+
+def test_target_path_outside_repo_is_blocked() -> None:
+    result = evaluate_inbox(_task_yaml(target_files_or_folders=[r"E:\abc\STATUS.md"]))
+
+    assert result.status == "blocked_risky"
+    assert any("absolute path" in message or r"E:\abc" in message for message in result.messages)
+
+
+def test_target_path_dot_git_is_blocked() -> None:
+    result = evaluate_inbox(_task_yaml(target_files_or_folders=[".git/config"]))
+
+    assert result.status == "blocked_risky"
+    assert any(".git" in message for message in result.messages)
+
+
+def test_target_path_data_raw_is_blocked() -> None:
+    result = evaluate_inbox(_task_yaml(target_files_or_folders=["data/raw/prices.csv"]))
+
+    assert result.status == "blocked_risky"
+    assert any("data/raw" in message for message in result.messages)
+
+
+def test_missing_inbox_file_returns_blocked_invalid_and_writes_report(tmp_path) -> None:
+    result = run_guard(root=tmp_path)
+
+    assert result.status == "blocked_invalid"
+    report = tmp_path / "reports/codex_loop/latest.json"
+    assert report.exists()
+    payload = json.loads(report.read_text(encoding="utf-8"))
+    assert payload["status"] == "blocked_invalid"
+    assert "missing" in payload["messages"][0].lower()
+
+
+def test_config_file_is_loaded(tmp_path) -> None:
+    config_dir = tmp_path / "configs"
+    config_dir.mkdir()
+    (config_dir / "codex_closed_loop.yaml").write_text(
+        """
+loop:
+  inbox_path: INBOX.md
+  report_dir: custom_reports
+  allowed_risk_levels:
+    - normal
+  blocked_content_patterns:
+    - custom-risk
+  blocked_path_patterns:
+    - .git
+  allowed_target_roots:
+    - tests/
+  allow_auto_merge: true
+""",
+        encoding="utf-8",
+    )
+    (tmp_path / "INBOX.md").write_text(_task_yaml(task="custom-risk task"), encoding="utf-8")
+
+    config = load_guard_config(tmp_path)
+    result = run_guard(root=tmp_path)
+
+    assert config.report_dir.as_posix() == "custom_reports"
+    assert not config.allow_auto_merge
+    assert result.status == "blocked_risky"
+    assert (tmp_path / "custom_reports/latest.json").exists()
+
+
+def test_anything_not_allowed_alone_does_not_block() -> None:
+    result = evaluate_inbox(
+        _task_yaml(task="Add a local docs test.", anything_not_allowed=["No download"])
+    )
+
+    assert result.status == "ready"
+
+
+def test_task_contradicts_anything_not_allowed_blocks() -> None:
+    result = evaluate_inbox(
+        _task_yaml(task="download a sample file", anything_not_allowed=["No download"])
+    )
+
+    assert result.status == "blocked_risky"
+    assert any("anything_not_allowed" in message for message in result.messages)
(exit_code=0)
```

## Validation

### pytest

Command: `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe -m pytest`

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\abc
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.13.0
collected 29 items

tests\test_codex_loop_guard.py ................                          [ 55%]
tests\test_config_settings.py ..                                         [ 62%]
tests\test_data_validation.py ....                                       [ 75%]
tests\test_features_price_volume.py .                                    [ 79%]
tests\test_labels_returns.py ..                                          [ 86%]
tests\test_metrics_performance.py ..                                     [ 93%]
tests\test_project_bootstrap.py ..                                       [100%]

============================= 29 passed in 1.13s ==============================
(exit_code=0)
```

### compileall

Command: `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe -m compileall src tests`

```text
Listing 'src'...
Listing 'src\\abc_quant'...
Listing 'src\\abc_quant\\backtesting'...
Listing 'src\\abc_quant\\config'...
Listing 'src\\abc_quant\\data'...
Listing 'src\\abc_quant\\features'...
Listing 'src\\abc_quant\\governance'...
Listing 'src\\abc_quant\\labels'...
Listing 'src\\abc_quant\\metrics'...
Listing 'src\\abc_quant\\models'...
Listing 'src\\abc_quant\\reports'...
Listing 'src\\abc_quant\\utils'...
Listing 'src\\abc_quant\\validation'...
Listing 'tests'...
(exit_code=0)
```

### ruff

Command: `ruff check .`

```text
unavailable: `ruff` executable was not found
(exit_code=unavailable)
```


## File Contents

### `.gitignore`

```text
.venv/
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.pytest-tmp/
.tmp_pytest/
.mypy_cache/
.ruff_cache/
_archive/

abc_project_E_drive_ready/
abc_project_E_drive_ready.zip

data/raw/*
!data/raw/.gitkeep
data/processed/*
!data/processed/.gitkeep
reports/*
!reports/.gitkeep

state/codex_context/

CODEX_REVIEW_PACKAGE.md
CODEX_TEST_RESULT.txt
```

### `CHANGELOG.md`

```text
# CHANGELOG

## Unreleased

- 強化 Codex closed-loop guard：即使 `risk_level: normal`，仍會封鎖破壞性、憑證、外部網路、絕對路徑、repo 外路徑與資料原始區目標。
- 擴充 `scripts/build_review_package.py`，支援完整 diff、完整檔案內容、驗證結果、完整 HEAD SHA 與排除輸出檔的 `--assert-clean`。
- 新增 tracked review package 生成腳本與本輪 `reviews/review_package_002.md`，取代根目錄一次性 review 輸出。
- 建立 Codex/ChatGPT Pro 檔案式閉環守門器、閉環文件、automation prompt 與測試。
- 完成 ChatGPT Review 001，確認第一輪 scaffold 可接受並記錄下一輪修正 prompt。
- 固定 pytest 本地暫存目錄並停用 cache provider，避免 Windows 受限暫存/cache 目錄造成驗收失敗或警告。
- 新增 `.gitignore`，排除 venv、cache、egg-info、打包 zip、解壓副本與本機 Codex context capsule。

## 0.0.1 - Project bootstrap

- 建立 ABC Quant AI Research Platform 專案骨架。
- 建立 `PROJECT_RULES.md` 作為 Codex 與 ChatGPT 協作規範。
- 建立初始文件、Prompt、程式碼目錄與測試目錄。

## 0.0.2 - First executable research scaffold

- 建立 YAML 設定載入、OHLCV 資料驗證、價量 rolling 特徵、forward return label 與基礎績效指標。
- 新增資料驗證、防未來資料洩漏、label shift 與績效指標測試。
```

### `FILE_MANIFEST.txt`

```text
.gitignore
AGENTS.md
CHANGELOG.md
FILE_MANIFEST.txt
INBOX.md
OUTBOX.md
PROJECT_RULES.md
README.md
RUN_CODEX_NEXT.md
STATUS.md
TECH_LEAD_PROTOCOL.md
TODO.md
configs/codex_closed_loop.yaml
configs/default.yaml
data/processed/.gitkeep
data/raw/.gitkeep
docs/architecture.md
docs/codex_closed_loop.md
docs/data_pipeline.md
docs/feature_engineering.md
docs/model_design.md
docs/strategy.md
docs/testing.md
notebooks/.gitkeep
prompts/bugfix_prompt.md
prompts/codex_closed_loop_runner.md
prompts/codex_master.md
prompts/research_prompt.md
prompts/review_prompt.md
pyproject.toml
reports/.gitkeep
requirements.txt
research/experiments.md
research/ideas.md
research/papers.md
reviews/review_001.md
reviews/review_package_002.md
scripts/build_review_package.py
scripts/check_project.ps1
scripts/check_project.sh
scripts/codex_loop_guard.py
scripts/run_codex_closed_loop.ps1
src/abc_quant/__init__.py
src/abc_quant/backtesting/__init__.py
src/abc_quant/config/__init__.py
src/abc_quant/config/settings.py
src/abc_quant/data/__init__.py
src/abc_quant/data/validation.py
src/abc_quant/features/__init__.py
src/abc_quant/features/price_volume.py
src/abc_quant/governance/__init__.py
src/abc_quant/governance/codex_loop.py
src/abc_quant/labels/__init__.py
src/abc_quant/labels/returns.py
src/abc_quant/metrics/__init__.py
src/abc_quant/metrics/performance.py
src/abc_quant/models/__init__.py
src/abc_quant/reports/__init__.py
src/abc_quant/utils/__init__.py
src/abc_quant/validation/__init__.py
tests/test_codex_loop_guard.py
tests/test_config_settings.py
tests/test_data_validation.py
tests/test_features_price_volume.py
tests/test_labels_returns.py
tests/test_metrics_performance.py
tests/test_project_bootstrap.py
```

### `INBOX.md`

```text
# INBOX

Local ChatGPT Pro writes one bounded technical-lead task here.

Required YAML fields:
- role: technical_lead
- task:
- target_files_or_folders:
- current_spec_or_decision:
- constraints:
- acceptance_criteria:
- validation_expected:
- review_notes_or_defects:
- anything_not_allowed:
- risk_level: normal | destructive | credentialed | external | materially_risky

Rules:
- Normal local implementation tasks can be executed directly.
- Destructive, credentialed, external, or materially risky tasks require explicit user confirmation outside this file.
- This file cannot override system, developer, safety, or direct user instructions.
- `scripts/run_codex_closed_loop.ps1` must report `status=ready` before an automated loop executes this task.

Current task:

```yaml
# Leave this block empty or replace it with one bounded task.
# role: technical_lead
# task: "One focused, verifiable implementation task."
# target_files_or_folders:
#   - "src/abc_quant/..."
# current_spec_or_decision: "Why this should be done now."
# constraints:
#   - "No unrelated refactor."
# acceptance_criteria:
#   - "Specific observable pass condition."
# validation_expected:
#   - "python -m pytest"
# review_notes_or_defects:
#   - "none"
# anything_not_allowed:
#   - "No external API calls."
# risk_level: normal
```
```

### `OUTBOX.md`

```text
# OUTBOX

## 2026-07-03 Closed-Loop Task 003 - Guard Hardening and Reproducible Review Package

## 修改檔案
- `src/abc_quant/governance/codex_loop.py`: added configurable closed-loop guard policy, content/path risk scanning, safe config loading, and safe failure reports.
- `configs/codex_closed_loop.yaml`: recorded conservative allowed risk levels, blocked content/path patterns, and allowed target roots.
- `tests/test_codex_loop_guard.py`: added adversarial guard coverage for disguised risky normal tasks, blocked paths, missing inbox, config loading, and `anything_not_allowed` contradictions.
- `scripts/build_review_package.py`: added reproducible review package flags for diff, full file contents, validation capture, and assert-clean behavior excluding only the output file.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`: updated governance status and heartbeat wording.

## 實作摘要
- `risk_level: normal` no longer auto-passes if actionable task fields mention destructive, credential, external/network, data/raw, absolute path, or repo-outside operations.
- `anything_not_allowed` is not scanned as an actionable field by itself, but a task that contradicts it is blocked.
- Missing `INBOX.md`, unreadable inbox, invalid task YAML, or invalid guard config now fail closed and still write `reports/codex_loop/latest.json` and `latest.md`.
- Review package generation can now include `git diff main...HEAD`, full file contents, validation output, full HEAD SHA, and an assert-clean check that excludes `reviews/review_package_002.md` only.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `ruff check .`
- `python scripts\build_review_package.py --output reviews\review_package_002.md --title "Codex Closed-Loop Task 003 Review Package" --pr-url "https://github.com/jongyawjong0514/abc-quant/pull/2" --run-validation --include-diff --include-file-contents --assert-clean`

## 測試結果
- `pytest`: 29 passed in 1.22s.
- `compileall`: passed for `src` and `tests`.
- `ruff`: unavailable in the current shell; no package was installed.
- `build_review_package --assert-clean`: intentionally fails while source files are dirty; final package is generated after the code changes are committed so the assert-clean check is meaningful.

## 已知限制
- A committed review package cannot record its own final Git SHA without creating an infinite self-reference; the package records the HEAD SHA at generation time.
- Existing PR #2 remains draft/review-only; no auto-merge is performed.

## 下一步建議
- Have ChatGPT Pro review `reviews/review_package_002.md` on PR #2.
- Keep future closed-loop tasks limited to one bounded YAML task in `INBOX.md`.

## 2026-07-03 Closed-Loop Task 001 - Repository Hygiene and Review Package

## 修改檔案
- `scripts/build_review_package.py`: added a repeatable review-package builder.
- `reviews/review_package_002.md`: generated tracked review package for ChatGPT Pro review.
- `.gitignore`: explicitly ignored local `_archive/` artifacts.
- `FILE_MANIFEST.txt`, `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: updated project governance records.

## 實作摘要
- Root-level stale `CODEX_REVIEW_PACKAGE.md` and `CODEX_TEST_RESULT.txt` are superseded by a tracked review package under `reviews/`.
- Review package includes branch status, diff summary, changed files, validation output, review pointers, and known local artifacts.
- No strategy, model, broker API, formal signal, or trading-rule logic changed.

## 測試方式
- `E:\abc\.venv\Scripts\python.exe -m pytest`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `E:\abc\.venv\Scripts\python.exe .\scripts\build_review_package.py --output reviews\review_package_002.md --title "Codex Closed-Loop Task 001 Review Package" --pr-url "https://github.com/jongyawjong0514/abc-quant/pull/2" --run-validation`

## 測試結果
- `scripts/build_review_package.py --run-validation`: regenerated `reviews/review_package_002.md`.
- Embedded validation in the review package: `pytest` 19 passed in 0.84s.
- Embedded closed-loop guard check: `status=no_task`, expected because `INBOX.md` currently contains only the commented template.
- Final direct validation: `pytest` 19 passed in 0.94s; `run_codex_closed_loop.ps1` returned `status=no_task`.

## 已知限制
- `.pytest_cache/` may remain as a local Windows ACL residue; it is ignored and not tracked by Git.

## 下一步建議
- Push the updated branch to GitHub PR #2 and have ChatGPT Pro review `reviews/review_package_002.md`.
- Merge PR #2 only after review; the closed-loop policy still forbids auto-merge.

## 2026-07-03 File-Based Closed Loop Guard

## 修改檔案
- `docs/codex_closed_loop.md`: documented the safe file-based closed-loop protocol.
- `configs/codex_closed_loop.yaml`: recorded loop paths, allowed risk levels, and no-auto-merge/no-web-UI boundaries.
- `src/abc_quant/governance/codex_loop.py`: added testable guard logic for `INBOX.md` task validation.
- `scripts/codex_loop_guard.py`: added CLI wrapper for guard execution.
- `scripts/run_codex_closed_loop.ps1`: added PowerShell entrypoint for Codex automation or manual checks.
- `prompts/codex_closed_loop_runner.md`: added reusable automation prompt.
- `tests/test_codex_loop_guard.py`: added guard behavior tests.
- `INBOX.md`, `TECH_LEAD_PROTOCOL.md`, `README.md`, `TODO.md`, `CHANGELOG.md`, `STATUS.md`: updated project workflow records.

## 實作摘要
- The loop executes only when `INBOX.md` contains one complete YAML task with `risk_level: normal`.
- Empty tasks return `no_task`; incomplete tasks return `blocked_invalid`; risky tasks return `blocked_risky`.
- Generated guard reports are written under `reports/codex_loop/`, which remains an ignored local/report artifact path.
- The design deliberately avoids automating ChatGPT Pro web UI and does not allow auto-merge.
- Prepared instructions for an optional hourly Codex heartbeat automation; external scheduler status is not tracked in this repository.

## 測試方式
- `E:\abc\.venv\Scripts\python.exe -m pytest`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest --basetemp=.tmp_pytest`: 19 passed in 0.87s, then 19 passed in 0.84s.
- `E:\abc\.venv\Scripts\python.exe -m pytest`: 19 passed in 0.86s.
- `scripts/run_codex_closed_loop.ps1`: status `no_task`, which is expected because `INBOX.md` currently contains only a commented template.

## 已知限制
- This is a guard and workflow scaffold, not a recursive self-launcher.
- Real unattended automation still needs a Codex app automation schedule and review of the first few runs.

## 下一步建議
- Ask ChatGPT Pro to place the next bounded task into `INBOX.md`.
- Review the first few heartbeat runs and adjust cadence if it is too frequent or too quiet.

## 2026-07-03 ChatGPT Review 001 and PR Hygiene

## 修改檔案
- `.gitignore`: excluded local venv, Python caches, pytest temp/cache, package egg-info, and generated E-drive zip/unpacked bundle.
- `pyproject.toml`: configured pytest to use local basetemp and disabled cache provider to avoid Windows temp/cache permission failures.
- `reviews/review_001.md`: recorded ChatGPT tech-lead review and next-round Codex prompt.
- `TODO.md`: marked first ChatGPT review and review archive item complete.
- `CHANGELOG.md`: recorded review and PR hygiene changes.
- `STATUS.md`: recorded latest validation status.

## 實作摘要
- First scaffold review is complete and accepts the current baseline for scaffold stage.
- No blocking look-ahead, train/test leakage, or modularity defect was found for this stage.
- The main next-step risk is label `horizon` semantics before model/backtest expansion.

## 測試方式
- `E:\abc\.venv\Scripts\python.exe -m pytest`

## 測試結果
- `pytest`: 13 passed in 0.83s.

## 已知限制
- Repository publishing still depends on initializing/pushing `E:\abc` to `jongyawjong0514/abc-quant`.
- GitHub repo is currently empty, so a normal PR requires a base branch commit before opening a feature branch PR.

## 下一步建議
- Publish this scaffold to GitHub with a clean initial branch.
- If a PR workflow is required, create a minimal `main` base first, then open a scaffold PR against it.

## 2026-07-03 Codex Result - RUN_CODEX_NEXT.md

## 修改檔案
- `src/abc_quant/config/settings.py`: hardened YAML config loading and required-key access.
- `src/abc_quant/__init__.py`: bumped package version to `0.0.2`.
- `src/abc_quant/data/validation.py`: added OHLCV column/date/duplicate validation.
- `src/abc_quant/features/price_volume.py`: added rolling momentum, volatility, and volume average features.
- `src/abc_quant/labels/returns.py`: added forward return labels with next-period entry semantics.
- `src/abc_quant/metrics/performance.py`: added total return, CAGR, annual volatility, Sharpe, max drawdown, and summary metrics.
- `tests/test_config_settings.py`: added YAML config loader tests.
- `tests/test_data_validation.py`: added market data validation tests.
- `tests/test_features_price_volume.py`: added no-lookahead rolling feature test.
- `tests/test_labels_returns.py`: added forward label shift tests.
- `tests/test_metrics_performance.py`: added simple performance metric tests.
- `pyproject.toml`: bumped project version to `0.0.2`.
- `CHANGELOG.md`: recorded first executable scaffold changes.
- `TODO.md`: marked first scaffold/data validation/price-volume feature items complete.

## 實作摘要
- Implemented a Pandas-only first executable quant research scaffold.
- Market data must include `date`, `ticker`, `open`, `high`, `low`, `close`, and `volume`.
- Dates are parsed into sortable timestamps, rows are normalized by `ticker,date`, and duplicate `date+ticker` rows are rejected.
- Rolling features are grouped per ticker and use only current or past rows.
- Forward labels use `entry_price = close[t + entry_lag]` and `exit_price = close[t + horizon]`; default entry lag is next period.
- Metrics operate on periodic returns and compound returns consistently.

## 測試方式
- `E:\abc\.venv\Scripts\python.exe -m pytest`
- `E:\abc\.venv\Scripts\python.exe -m pip install -e .`
- `E:\abc\.venv\Scripts\python.exe -m pytest`

## 測試結果
- Editable install succeeded.
- `pytest`: 13 passed.
- Remaining warning: pytest cannot write cache under `E:\abc\.pytest_cache` due `[WinError 5] access denied`.

## 已知限制
- No data download, broker API, complex model, portfolio construction, cost/slippage backtest, or report generation was added in this round.
- The first label helper follows the project example `close[t+horizon] / close[t+entry_lag] - 1`; later tasks should confirm whether `horizon` means exit offset or holding-period count.
- Performance metrics currently cover the task-required minimum only; PROJECT_RULES later require Sortino, Calmar, win rate, profit factor, turnover, average holding period, and trade count.

## 下一步建議
- Add a small sample-data loader plus end-to-end fixture that validates data -> builds features -> creates labels -> computes metrics.
- Add transaction cost and slippage-aware backtest scaffolding.
- Ask ChatGPT Pro to review the horizon/entry label semantics before building model training around it.
```

### `README.md`

```text
# ABC Quant AI Research Platform

本專案是為台股量化研究、AI 選股、策略回測與 Codex 協作而建立的工作區。

## 專案定位

本專案不是單一策略腳本，而是一套可長期演進的研究平台。核心目標是：

1. 建立乾淨、可重現的資料管線。
2. 建立嚴格避免資料洩漏與前視偏誤的特徵工程流程。
3. 建立可比較、可回測、可審查的模型訓練流程。
4. 建立可由 ChatGPT 擔任 Tech Lead、Codex 擔任工程實作者的固定協作流程。

## 目錄結構

```text
abc/
├── PROJECT_RULES.md              # 專案憲法：Codex 每次修改前必讀
├── RUN_CODEX_NEXT.md             # 下一步要交給 Codex 的任務
├── TODO.md                       # 待辦事項
├── CHANGELOG.md                  # 變更紀錄
├── pyproject.toml                # Python 專案設定
├── requirements.txt              # 基礎依賴
├── configs/                      # 設定檔
├── prompts/                      # 給 Codex / ChatGPT 的固定提示詞
├── docs/                         # 架構與研究文件
├── reviews/                      # ChatGPT 審查報告
├── research/                     # 文獻、想法、實驗紀錄
├── src/abc_quant/                # 主要程式碼
├── tests/                        # 測試
└── scripts/                      # 工具腳本
```

## 建議工作流程

1. 你把 `RUN_CODEX_NEXT.md` 的內容貼給 Codex。
2. Codex 修改專案。
3. 將 Codex 的變更摘要、重要檔案或 diff 貼回 ChatGPT。
4. ChatGPT 根據 `PROJECT_RULES.md` 審查，產生下一輪修正 Prompt。
5. 重複以上流程。

## 檔案式閉環

本專案支援保守的 Codex/ChatGPT Pro 閉環：

1. ChatGPT Pro 將一個 bounded task 寫入 `INBOX.md` 的 YAML 區塊。
2. Codex 執行 `.\scripts\run_codex_closed_loop.ps1`。
3. 只有 guard 回傳 `status=ready` 且 `risk_level=normal` 時才執行。
4. Codex 完成後更新 `OUTBOX.md`、`STATUS.md`，必要時開 draft PR。
5. ChatGPT Pro 讀回結果，再產生下一輪任務。

詳細規則見 `docs/codex_closed_loop.md`。

## 快速開始

在 Windows PowerShell：

```powershell
cd E:\abc
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

若 `pytest` 尚未安裝，請先執行：

```powershell
pip install pytest
```

## 重要原則

Codex 不應直接「自由發揮」整套系統。每次任務都應包含：

- 目標
- 範圍
- 禁止事項
- 驗收標準
- 測試要求
- 修改檔案清單

這些規則已寫入 `PROJECT_RULES.md` 與 `prompts/codex_master.md`。
```

### `STATUS.md`

```text
# STATUS

- 2026-07-03: Handoff folder initialized by Codex. Waiting for a concrete task in `INBOX.md` or a direct user instruction.
- 2026-07-03: Technical-lead operating model recorded. ChatGPT Pro may own specs, next tasks, and review notes for `E:\abc`; Codex remains implementation engineer. Override of system/safety/direct-user rules was not accepted.
- 2026-07-03: Completed `RUN_CODEX_NEXT.md` first implementation round. Editable install succeeded as `abc-quant==0.0.2` and `pytest` passed: 13 passed, 1 pytest cache warning from `E:\abc\.pytest_cache` access denied.
- 2026-07-03: Completed ChatGPT Review 001, added PR hygiene `.gitignore`, fixed pytest temp/cache behavior, and revalidated `pytest`: 13 passed in 0.83s.
- 2026-07-03: Added file-based Codex/ChatGPT Pro closed-loop guard, runnable PowerShell entrypoint, documentation, prompt, and tests.
- 2026-07-03: Closed-loop guard validation passed with `pytest` 19 passed in 0.86s and `run_codex_closed_loop.ps1` returned expected `no_task` for the empty commented inbox template.
- 2026-07-03: Prepared instructions for an optional hourly Codex heartbeat automation; external scheduler status is not tracked in this repository.
- 2026-07-03: Started closed-loop task 001 for repository hygiene, tracked review package generation, validation, and GitHub push.
- 2026-07-03: Generated tracked `reviews/review_package_002.md`; embedded validation shows `pytest` 19 passed in 0.84s and closed-loop guard `status=no_task`.
- 2026-07-03: Final task 001 direct validation passed: `pytest` 19 passed in 0.94s; closed-loop guard returned `status=no_task`.
- 2026-07-03: Started closed-loop task 003 to harden the guard against disguised risky normal tasks and make `reviews/review_package_002.md` reproducible.
- 2026-07-03: Task 003 validation passed with `pytest` 29 passed and `compileall src tests`; `ruff check .` is unavailable in the current shell.
```

### `TECH_LEAD_PROTOCOL.md`

```text
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
```

### `TODO.md`

```text
# TODO

## Phase 0：專案基礎

- [x] 建立專案目錄。
- [x] 建立 PROJECT_RULES.md。
- [x] 建立 Codex 主控 Prompt。
- [x] 建立 Review Prompt。
- [x] 建立文件骨架。
- [x] 由 Codex 完成第一版可測試程式骨架。
- [x] 由 ChatGPT 審查 Codex 第一輪產出。

## Phase 1：資料層

- [ ] 定義資料格式。
- [x] 建立資料驗證。
- [ ] 建立資料清洗流程。
- [ ] 建立資料版本管理規範。
- [ ] 加入 FinLab 或本地資料來源介面。

## Phase 2：特徵工程

- [x] 價量特徵。
- [ ] 技術指標特徵。
- [ ] 籌碼特徵。
- [ ] 基本面特徵。
- [ ] 市場狀態特徵。
- [ ] 特徵洩漏測試。

## Phase 3：模型

- [ ] Baseline 模型。
- [ ] LightGBM。
- [ ] Walk-forward validation。
- [ ] 模型解釋。
- [ ] Ablation study。

## Phase 4：回測

- [ ] 交易成本。
- [ ] 滑價。
- [ ] 部位限制。
- [ ] 換手率。
- [ ] 停損停利。
- [ ] 報告產生。

## Phase 5：研究治理

- [ ] 每次實驗寫入 `research/experiments.md`。
- [ ] 每次 Codex 變更後寫入 `CHANGELOG.md`。
- [x] 每輪 ChatGPT Review 寫入 `reviews/`。
- [x] 建立 Codex/ChatGPT Pro 檔案式閉環守門器。
- [ ] 審查第一輪自動化閉環輸出並調整 cadence。
```

### `configs/codex_closed_loop.yaml`

```text
loop:
  inbox_path: INBOX.md
  report_dir: reports/codex_loop
  allowed_risk_levels:
    - normal
  blocked_risk_levels:
    - destructive
    - credentialed
    - external
    - materially_risky
  blocked_path_patterns:
    - .git
    - .venv
    - _archive
    - data/raw
    - data/processed
    - state/codex_context
    - credentials
    - secrets
    - "C:\\"
    - "E:\\"
    - ..
  blocked_content_patterns:
    - delete
    - remove-item
    - rm -rf
    - rmdir
    - format
    - reset --hard
    - clean data/raw
    - erase
    - purge
    - token
    - password
    - secret
    - api_key
    - apikey
    - ssh key
    - credential
    - .env
    - curl
    - wget
    - requests.get
    - requests.post
    - download
    - upload
    - external api
    - broker api
    - finlab download
  allowed_target_roots:
    - .gitignore
    - AGENTS.md
    - CHANGELOG.md
    - FILE_MANIFEST.txt
    - INBOX.md
    - OUTBOX.md
    - PROJECT_RULES.md
    - README.md
    - RUN_CODEX_NEXT.md
    - STATUS.md
    - TECH_LEAD_PROTOCOL.md
    - TODO.md
    - configs/
    - docs/
    - prompts/
    - research/
    - reviews/
    - scripts/
    - src/
    - tests/
    - pyproject.toml
    - requirements.txt
  allow_auto_merge: false
```

### `docs/codex_closed_loop.md`

```text
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
```

### `prompts/codex_closed_loop_runner.md`

```text
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
```

### `pyproject.toml`

```text
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "abc-quant"
version = "0.0.2"
description = "ABC Quant AI Research Platform for Taiwan equity research"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.0",
    "numpy>=1.24",
    "PyYAML>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.5.0",
    "mypy>=1.8.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "--basetemp=.tmp_pytest -p no:cacheprovider"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
strict = false
```

### `reviews/review_package_002.md`

_Skipped output file to avoid recursive package growth._

### `scripts/build_review_package.py`

```text
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
```

### `scripts/codex_loop_guard.py`

```text
"""CLI wrapper for the Codex closed-loop inbox guard."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from abc_quant.governance.codex_loop import run_guard


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the current Codex closed-loop task.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero unless status is ready.")
    args = parser.parse_args()

    root = args.root.resolve()
    result = run_guard(root=root)
    print(f"status={result.status}")
    print(f"report={root / 'reports' / 'codex_loop' / 'latest.md'}")

    if args.strict and not result.is_ready:
        return 2
    if result.status in {"blocked_invalid", "blocked_risky"}:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `scripts/run_codex_closed_loop.ps1`

```text
param(
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = "python"
}

$ScriptArgs = @(
    (Join-Path $ProjectRoot "scripts\codex_loop_guard.py"),
    "--root",
    $ProjectRoot
)

if ($Strict) {
    $ScriptArgs += "--strict"
}

& $Python @ScriptArgs
exit $LASTEXITCODE
```

### `src/abc_quant/governance/__init__.py`

```text
"""Governance helpers for Codex/ChatGPT handoff workflows."""
```

### `src/abc_quant/governance/codex_loop.py`

```text
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
        blocked_path_patterns=_string_tuple(
            data.get("blocked_path_patterns"), defaults.blocked_path_patterns
        ),
        blocked_content_patterns=_string_tuple(
            data.get("blocked_content_patterns"), defaults.blocked_content_patterns
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
```

### `tests/test_codex_loop_guard.py`

```text
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
```

## Known Local Artifacts

- `.venv/`, `.tmp_pytest/`, `state/codex_context/`, and `reports/codex_loop/` are local/ignored artifacts.
- Old root-level `CODEX_REVIEW_PACKAGE.md` and `CODEX_TEST_RESULT.txt` are superseded by `reviews/review_package_002.md`.
- `.pytest_cache/` may remain as a Windows ACL residue on this machine; it is ignored and not part of Git history.

## Promotion Boundary

This package contains repository governance work only. It does not add trading strategy logic, model training, broker integration, FinLab download logic, data downloads, or formal signal promotion.
