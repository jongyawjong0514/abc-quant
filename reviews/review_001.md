# Review 001

狀態：完成。

審查日期：2026-07-03

## 總評

第一輪 Codex 產出符合 `RUN_CODEX_NEXT.md` 的 scaffold 目標：專案已可安裝、核心模組分層清楚，且 `pytest` 驗收通過。此輪不是可交易策略或模型系統，仍應維持 research scaffold 狀態，不得視為正式交易訊號。

## 必修問題

1. 無阻擋第一輪 scaffold 驗收的必修問題。
2. 進入模型或回測前，必須先確認 `horizon` 語意：目前 label 使用 `exit_price = close[t + horizon]` 與 `entry_price = close[t + entry_lag]`，當 `entry_lag=1` 時，實際持有長度是 `horizon - entry_lag` 個 bar。此點已在 Codex OUTBOX 中標示，下一輪需定稿後再擴充模型訓練。

## 建議問題

1. 增加 end-to-end fixture：`validate data -> build features -> create labels -> compute metrics`，避免各模組單測通過但串接契約漂移。
2. 在下一輪回測 scaffold 加入交易成本、交易稅、滑價與部位限制的資料結構，即使先不做完整策略，也要先固定接口。
3. 特徵測試可再加入多 ticker、打亂輸入順序、缺值與不同 window 的交叉案例。
4. 資料驗證後續應補 OHLC 合理性檢查，例如 `high >= max(open, close)`、`low <= min(open, close)`、`volume >= 0`。

## 可接受部分

1. `validate_market_data` 檢查必要 OHLCV 欄位、可排序日期、缺失 ticker/date 與 `date+ticker` 重複列，符合第一輪資料層要求。
2. rolling momentum、volatility、volume average 皆以 ticker group 後的過去與當期資料計算，現有測試有檢查未來尾端值改變不影響當期特徵。
3. forward return label 明確使用下一期進場假設，避免同日收盤決策又同日成交的前視問題。
4. 績效指標涵蓋任務要求的 total return、CAGR、annual volatility、Sharpe ratio、max drawdown。
5. 專案使用 `src/` layout、type hints、pytest 測試與小型模組，符合可維護 scaffold 方向。

## 下一輪 Codex Prompt

請執行第二輪小步修正，目標是固定資料到研究結果的端到端契約，不要建立複雜模型或下載資料。

1. 先閱讀 `PROJECT_RULES.md`、`RUN_CODEX_NEXT.md`、`reviews/review_001.md`。
2. 定義並記錄 label horizon 語意，決定 `horizon` 是 exit offset 還是 holding-period count；更新 `src/abc_quant/labels/returns.py` docstring 與測試。
3. 新增一個小型端到端測試 fixture，串接 `validate_market_data`、`add_price_volume_features`、`add_forward_return_label`、`performance_summary`。
4. 擴充資料驗證，加入 OHLC 合理性與非負成交量檢查。
5. 新增最小 backtesting cost config/data structure，不需要完整策略，但要能承載 fee、tax、slippage 與 position limit。
6. 執行 `pytest`，更新 `CHANGELOG.md`、`TODO.md`、`STATUS.md`、`OUTBOX.md`。
