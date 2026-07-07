# CHANGELOG

## Unreleased

- 新增 Task 051 optional LightGBM evaluation smoke diagnostics：`run_lightgbm_evaluation_smoke(...)` 預設只回 dependency/default-parameter diagnostics，`fitting_enabled=True` 且 optional package 可用時才透過既有 train-only `fit_lightgbm_regressor(...)` 產生 in-memory train/validation/test evaluation summary；新增 summary validator/constants 與 focused tests，不改 dependency-smoke/CLI outputs、不新增 mandatory dependency。
- 新增 Task 050 LightGBM dependency smoke summary contract package exports：`abc_quant.pipeline` 直接匯出 `LIGHTGBM_DEPENDENCY_SMOKE_*` constants 與 `validate_lightgbm_dependency_smoke_summary(...)`，讓 callers 可用 public pipeline import 驗證 diagnostics summary，不改輸出 schema、不改 validator semantics。
- 新增 Task 049 LightGBM dependency smoke summary contract validator：集中定義 diagnostics summary/default params key constants 與 `validate_lightgbm_dependency_smoke_summary(...)`，`run_lightgbm_dependency_smoke(...)` 回傳前會驗證 shape、JSON-friendly values 與 forbidden keys，不改輸出 schema、不 require/fitting/search/select/strategy/backtest。
- 新增 Task 048 packaged LightGBM dependency smoke command alias：`pyproject.toml` 宣告 `abc-quant-lightgbm-dependency-smoke = abc_quant.cli.lightgbm_dependency_smoke:main`，並以 `tomllib` 測試 entry point target 可解析、可呼叫與支援 `--indent 2`，不改 diagnostics behavior、不新增 mandatory LightGBM dependency。
- 新增 Task 047 deterministic LightGBM dependency smoke module CLI：`python -m abc_quant.cli.lightgbm_dependency_smoke` 以 sorted JSON 輸出既有 `run_lightgbm_dependency_smoke(...)` summary，支援 `--indent`，不新增 packaged console-script alias、不 require 真套件、不 call `require_lightgbm()` default path、不 fit/search/select/strategy/backtest。
- 新增 Task 046 deterministic LightGBM dependency smoke diagnostics：`run_lightgbm_dependency_smoke(...)` 只使用 `check_lightgbm_dependency()` 回報 optional package status 與 default params metadata，預設 `fitting_enabled=False`，不 require 真套件、不 fit model、不做 parameter search/model selection/strategy/backtest。
- 新增 Task 045 train-only LightGBM regressor fitting contract：`fit_lightgbm_regressor(...)` 透過 optional `require_lightgbm()` 匯入 `lightgbm`，只用 `SupervisedSplitDataset.train_X/train_y` fit，並將 train/validation/test features 轉成 `SplitPredictionBundle`；測試以 fake LightGBM monkeypatch 覆蓋，不新增 mandatory dependency、不做 parameter search/model selection/strategy/backtest。
- 新增 Task 044 optional LightGBM dependency guard and parameter contract：`models/lightgbm.py` 可在未安裝 `lightgbm` 時 import，並以標準函式庫 `importlib` 提供 dependency status、required import helper 與 frozen deterministic regressor parameter validation；不新增 mandatory dependency、不 fit model、不改 pipeline/CLI/smoke outputs。
- 新增 Task 043 packaged model comparison smoke console-script alias：`pyproject.toml` 宣告 `abc-quant-model-comparison-smoke = abc_quant.cli.model_comparison_smoke:main`，並以 `tomllib` 測試 entry point target 可解析、可呼叫與支援 `--baseline-method median`。
- 新增 Task 042 deterministic model comparison smoke diagnostics CLI：`python -m abc_quant.cli.model_comparison_smoke` 以 sorted JSON 輸出既有 `run_model_comparison_smoke(...)` summary，支援 `--train-end`、`--validation-end`、`--baseline-method mean|median` 與 `--indent`，不改計算、summary keys、model selection/ranking/strategy/simulation 行為。
- 新增 Task 041 model comparison smoke summary contract validator：集中定義 `MODEL_COMPARISON_SMOKE_*` summary/model/split/comparison keys 與 `validate_model_comparison_smoke_summary(...)`，`run_model_comparison_smoke(...)` 回傳前會驗證 summary shape，不改預設輸出值、不加入 model selection/ranking/strategy/simulation。
- 新增 Task 040 deterministic baseline versus OLS evaluation comparison smoke diagnostics：`run_model_comparison_smoke(...)` 在相同 supervised prediction rows 上評估 constant-baseline reference 與 OLS candidate，並用 `compare_prediction_evaluations(...)` 回傳 raw metric deltas，不做 winner、ranking、decision 或 model selection。
- 新增 Task 039 prediction evaluation comparison contract：`compare_prediction_evaluations(...)` 比較兩個既有 `SplitPredictionBundleEvaluationResult`，驗證 split row/missing counts 一致後回傳 candidate-minus-reference 的 MAE、RMSE、mean error 與 prediction mean deltas，不做 model selection、ranking、strategy 或 simulation。
- 新增 Task 038 packaged OLS smoke console-script alias：`pyproject.toml` 宣告 `abc-quant-linear-regression-smoke = abc_quant.cli.linear_regression_smoke:main`，並以 `tomllib` 測試 entry point target 可解析與呼叫。
- 新增 Task 037 deterministic OLS smoke diagnostics CLI：`python -m abc_quant.cli.linear_regression_smoke` 以 sorted JSON 輸出既有 `run_linear_regression_smoke(...)` summary，支援 `--train-end`、`--validation-end` 與 `--indent`，錯誤邊界會以 non-zero exit code 與簡短 stderr 回報。
- 新增 Task 036 linear regression smoke summary contract validator：集中定義 `LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS`、`LINEAR_REGRESSION_SMOKE_SPLITS`、`LINEAR_REGRESSION_SMOKE_EVALUATION_KEYS` 與 `validate_linear_regression_smoke_summary(...)`，`run_linear_regression_smoke(...)` 回傳前會驗證 OLS diagnostics summary shape，不改預設輸出值。
- 新增 Task 035 deterministic train-only OLS smoke diagnostics：`run_linear_regression_smoke(...)` 串接 deterministic smoke frame、FeatureMatrix、TemporalSplit、train-only scaler、SupervisedSplitDataset、`fit_linear_regression(...)` 與 `evaluate_prediction_bundle(...)`，回傳 JSON-friendly OLS diagnostics，不產生 strategy/allocation/performance/simulation outputs。
- 新增 Task 034 train-only ordinary least-squares regression model contract：`fit_linear_regression(...)` 只使用 `SupervisedSplitDataset.train_X/train_y` 以 `numpy.linalg.lstsq` 擬合，並回傳 `LinearRegressionResult` 與 `SplitPredictionBundle`，不讀 validation/test labels、不新增 sklearn。
- 新增 Task 033 packaged supervised dataset smoke console-script alias：`pyproject.toml` 宣告 `abc-quant-supervised-smoke = abc_quant.cli.supervised_smoke:main`，並以 `tomllib` 測試 entry point target 可解析與呼叫。
- 新增 Task 032 supervised dataset smoke diagnostics CLI：`python -m abc_quant.cli.supervised_smoke` 以 sorted JSON 輸出既有 supervised dataset smoke summary，支援 `--train-end`、`--validation-end` 與 `--indent`，錯誤邊界會以 non-zero exit code 與簡短 stderr 回報。
- 新增 Task 031 supervised dataset smoke summary contract validator：集中定義 `SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS`、`SUPERVISED_DATASET_SMOKE_SPLITS` 與 `validate_supervised_dataset_smoke_summary(...)`，`run_supervised_dataset_smoke(...)` 回傳前會驗證 summary shape，不改預設輸出值。
- 新增 Task 030 deterministic supervised dataset smoke diagnostics：`run_supervised_dataset_smoke(...)` 串接 deterministic smoke frame、feature matrix、temporal split、train-only scaler 與 supervised split dataset，回傳 JSON-friendly label-drop diagnostics，不訓練 estimator、不改既有 smoke CLI 或 summary。
- 新增 Task 029 supervised split dataset contract：`SupervisedSplitDataset` 與 `build_supervised_split_dataset(...)` 將 standardized split features 與 `FeatureMatrix` labels 對齊，支援 split-level missing-label drop counts，並拒絕 missing-label no-drop 與 empty train data，不訓練 estimator。
- 新增 Task 028 packaged preprocessing smoke console-script alias：`pyproject.toml` 宣告 `abc-quant-preprocessing-smoke = abc_quant.cli.preprocessing_smoke:main`，並以 `tomllib` 測試 entry point target 可解析與呼叫。
- 新增 Task 027 preprocessing smoke diagnostics CLI：`python -m abc_quant.cli.preprocessing_smoke` 以 sorted JSON 輸出既有 preprocessing smoke summary，支援 `--train-end`、`--validation-end` 與 `--indent`，錯誤邊界會以 non-zero exit code 與簡短 stderr 回報。
- 新增 Task 026 preprocessing smoke summary contract validator：集中定義 `PREPROCESSING_SMOKE_SUMMARY_KEYS`、`PREPROCESSING_SMOKE_SPLITS` 與 `validate_preprocessing_smoke_summary(...)`，`run_preprocessing_smoke(...)` 回傳前會驗證 top-level keys、split counts 與 split shape，不改預設輸出值。
- 新增 Task 025 deterministic preprocessing smoke diagnostics：`run_preprocessing_smoke(...)` 串接 deterministic smoke frame、feature matrix、temporal split、train-only scaler fit 與 transform，回傳 JSON-friendly scaling diagnostics，不改 modeling smoke CLI 或 summary contract。
- 新增 Task 024 train-only numeric feature standardization contract：`fit_standard_scaler(...)` 只用 train split 擬合 means/stds，再由 `transform_with_standard_scaler(...)` 套用到 train/validation/test，拒絕 nonnumeric、missing train values 與 zero-variance training features，不新增 sklearn 或 estimator。
- 新增 Task 023 modeling smoke pipeline bundle-evaluation wiring：`run_baseline_modeling_smoke(...)` 內部改用 `build_constant_baseline_prediction_bundle(...)` 與 `evaluate_prediction_bundle(...)`，保持 summary contract、CLI arguments、fitted values、split counts 與 metric formulas 不變。
- 新增 Task 022 split prediction bundle evaluator：`SplitPredictionBundleEvaluationResult` 與 `evaluate_prediction_bundle(...)` 使用既有 `evaluate_predictions(...)` 評估 train/validation/test bundle outputs，保留 `model_name`/`method`，不改 pipeline、CLI 或 summary keys。
- 新增 Task 021 constant-baseline prediction bundle adapter：`build_constant_baseline_prediction_bundle(...)` 將既有 `ConstantBaselineResult` 轉成 `SplitPredictionBundle`，沿用 generic bundle validation 與 copy isolation，不改 baseline、pipeline、CLI 或 summary keys。
- 新增 Task 020 split prediction bundle diagnostics contract：`SplitPredictionBundle` 與 `build_split_prediction_bundle(...)` 固定 train/validation/test prediction Series 形狀，拒絕 duplicate/missing/overlap inputs，並回傳 copied Series，不改 baseline、CLI 或 summary keys。
- 新增 Task 019 packaged console-script alias：`pyproject.toml` 宣告 `abc-quant-modeling-smoke = abc_quant.cli.modeling_smoke:main`，並以 `tomllib` 測試 entry point target 可解析與呼叫。
- 新增 Task 018 modeling smoke baseline method selector：`run_baseline_modeling_smoke(...)` 與 CLI 支援既有 constant-baseline `mean`/`median` method，summary 新增 `baseline_method` 並同步更新 shared contract，不改 split 或 metric 公式。
- 新增 Task 017 modeling diagnostics summary contract validator：集中定義 `MODELING_SMOKE_SUMMARY_KEYS`、`EVALUATION_METRIC_KEYS` 與 `validate_modeling_smoke_summary(...)`，pipeline 回傳前會驗證 summary shape，CLI/pipeline tests 改用共用 constants。
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
