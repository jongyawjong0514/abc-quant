# CHANGELOG

## Unreleased

- 新增 Task 016 deterministic modeling smoke diagnostics CLI：`python -m abc_quant.cli.modeling_smoke` 以 sorted JSON 輸出既有 smoke summary，支援 `--train-end`、`--validation-end` 與 `--indent`，錯誤邊界會以 non-zero exit code 與簡短 stderr 回報。
- 新增 Task 015 deterministic baseline modeling smoke pipeline：`run_baseline_modeling_smoke(...)` 串接 feature matrix、temporal split、constant baseline 與 prediction evaluation，回傳 plain diagnostic summary，不建立 market-action outputs、allocation logic、performance curves 或 simulation engines。
- 新增 Task 014 prediction evaluation metrics：`evaluate_predictions(...)` 與 `evaluate_constant_baseline(...)` 對 split-aligned predictions 計算 row/missing counts、MAE、RMSE、mean error 與 prediction mean，且不產生交易訊號、部位、equity curve 或 backtest。
- 新增 Task 013 constant-baseline model contract：`fit_constant_baseline(...)` 支援 mean/median 常數 baseline，只使用 train split 的非缺失 label fit，並回傳 train/validation/test positional predictions，避免 validation/test label 洩漏。
- 新增 Task 012 temporal split contract：`build_temporal_split(...)` 支援 train/test 與 train/validation/test date-based split，防止 training dates 洩漏到 validation/test，並覆蓋 shuffled metadata invariance、non-increasing boundary、empty split 與 missing/unsortable date tests。
- 新增 Task 011 feature-matrix assembly contract：`build_feature_matrix(...)` 將 `X`、明確 `y`、`date`/`ticker` metadata 分離，排除 raw OHLCV 與 `label_` 欄位，並覆蓋 shuffled-input invariance 與 missing-label preservation。
- 新增 Task 010 pure-pandas technical indicators：`add_technical_indicators(...)` 支援 SMA、EMA、RSI，並以 no-lookahead、ticker isolation、shuffled-input invariance 與 future-row mutation tests 覆蓋。
- 新增 Task 009 feature/label leakage regression tests，覆蓋 shuffled input invariance、multi-ticker isolation、rolling volatility 數值、forward-return label tail missing 與 label 不混入 feature columns。
- 強化 market data validation，改用 schema constants 並拒絕 non-numeric/missing OHLCV、negative volume、high-low 反轉，以及 open/close 超出 high-low range。
- 新增 deterministic market data contract、合成 sample fixture 與端到端 smoke pipeline，串接資料驗證、價量特徵、forward-return label 與 basic metrics summary。
- 新增最小 GitHub Actions CI workflow，於 pull request 與 push to main 執行 ruff、pytest、compileall，並使用 Python 3.11/3.12 matrix。
- 清空 Task 005 後的 `INBOX.md` active task，讓 closed-loop guard 回到 `status=no_task`，避免 PR #3 merge 後重複執行同一任務。
- 準備未來 CI workflow governance target：closed-loop guard 設定允許 `.github/`，測試確認 `.github/workflows/ci.yml` 可作為 target 且 `.git/config` 仍被封鎖。
- 修正 review package final audit，將 output file 從 repo diff-check 中排除，並單獨驗證輸出檔沒有 trailing whitespace。
- 調整 review package SHA metadata，改用 `source_head_sha_at_generation` 與 `review_package_commit_sha: unavailable_self_reference`，避免把 package 產生前 SHA 誤標為最終 head。
- 保留 closed-loop guard 內建 blocked content/path patterns；config 現在只能增加 blockers，不能移除 `token`、`.git`、`data/raw` 等預設防線。
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
