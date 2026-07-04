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

## CI Quality Gates

GitHub Actions workflow `.github/workflows/ci.yml` runs on pull requests and pushes to `main`.
It installs the project with development dependencies and runs:

- `ruff check .`
- `python -m pytest`
- `python -m compileall src tests`

The workflow uses Python 3.11 and 3.12 because the project declares Python 3.11+ support.

## Deterministic Smoke Pipeline

The first data contract and smoke pipeline live in:

- `src/abc_quant/data/schema.py`
- `src/abc_quant/data/sample.py`
- `src/abc_quant/data/validation.py`
- `src/abc_quant/pipeline/smoke.py`

Validation enforces the schema constants, datetime dates, string tickers, numeric and non-missing OHLCV values, non-negative volume, and OHLC high-low consistency.

The sample fixture is synthetic and deterministic. It is only for local smoke checks and is not a trading signal, market data source, backtest, or performance claim.

## Feature Engineering

The first feature modules are local, deterministic, and no-lookahead:

- `src/abc_quant/features/price_volume.py`: rolling price momentum, rolling return volatility, and rolling volume averages.
- `src/abc_quant/features/technical.py`: simple SMA, EMA, and RSI indicators implemented in pure pandas.
- `src/abc_quant/features/matrix.py`: deterministic feature-matrix assembly that separates `X`, explicit `y`, and `date`/`ticker` metadata.

All feature builders validate OHLCV input first, return a sorted defensive copy by `ticker` and `date`, and compute each ticker independently. The matrix builder excludes metadata, raw OHLCV, and `label_` columns from inferred features and preserves missing labels for evaluator handling. These features are research inputs only; they do not create trading signals, model predictions, portfolio decisions, or backtest results.

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
