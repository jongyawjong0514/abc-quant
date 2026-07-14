# ChatGPT Review Package 003 - Zhu Walkline Observation Points

請把本檔完整貼給 ChatGPT Pro 審視。

## Role

你現在是 ABC Quant AI Research Platform 的 Quant Tech Lead。請用 code review / quant review 的角度審查本輪 Codex 變更。

## Review Target

- Repository: `https://github.com/jongyawjong0514/abc-quant`
- Branch: `codex/zhu-walkline-shadow-backup`
- Commit: `966ae664734ae267d87ae539b1a177765b62df5b`
- Commit URL: `https://github.com/jongyawjong0514/abc-quant/commit/966ae664734ae267d87ae539b1a177765b62df5b`
- Commit title: `Add Zhu walkline observation points`
- Date: `2026-07-09T20:16:30+08:00`

## User Requirement

把支撐與壓力轉成買賣觀察點，但不可輸出絕對買賣建議。

要求新增欄位：

```text
buy_observation_type
buy_trigger_price
stop_reference
target_resistance_1
target_resistance_2
sell_warning_type
invalidation_price
```

買點觀察類型：

```text
SUPPORT_REBOUND
RESISTANCE_BREAKOUT
RESISTANCE_TURN_SUPPORT
FAILED_BREAKDOWN_RECLAIM
```

賣點警示類型：

```text
RESISTANCE_REJECTION
SUPPORT_BREAKDOWN
ATTACK_K_FAILURE
FALSE_BREAKOUT
MA_SUPPORT_FAILURE
```

硬邊界：

```text
不可產生交易指令
不可修改正式策略
不可修改 formal champion
formal_champion_changed=False
formal_trade_effect=False
mode=shadow_observation_only
```

## Codex Change Summary

本輪 Codex 在 shadow scanner 裡新增支撐壓力觀察欄位：

- `src/abc_quant/signals/zhu_walkline_shadow.py`
  - 新增 `buy_observation_type`
  - 新增 `buy_trigger_price`
  - 新增 `target_resistance_1`
  - 新增 `target_resistance_2`
  - 新增 `sell_warning_type`
  - 新增 `invalidation_price`
  - 有效買點觀察必須同時符合：
    - `close > trigger_price`
    - `volume > vol_ma5 or volume > vol_ma20`
    - `close_position_in_range > 0.6`
    - 不是高檔供給長上影
    - 有明確防守/失敗價
  - 賣點警示涵蓋：
    - 跌破支撐區收不回
    - 跌破攻擊K低點
    - 假突破
    - 壓力區長上影/突破失敗
    - 跌破 5/10/20 日線後無法修復

- `src/abc_quant/reports/zhu_walkline_report.py`
  - 將新欄位輸出到 bullish watchlist CSV、fall risk CSV、shadow log、summary JSON、Markdown 報告。
  - 報告文字仍用「觀察型態」「賣點警示」「訊號失敗價」，避免寫成交易指令。

- `tests/test_zhu_walkline_features.py`
  - 覆蓋 `RESISTANCE_BREAKOUT` 觀察欄位。
  - 覆蓋 `SUPPORT_BREAKDOWN`、`FALSE_BREAKOUT`、`ATTACK_K_FAILURE`、`MA_SUPPORT_FAILURE` 賣點警示。

- `tests/test_zhu_walkline_no_lookahead.py`
  - 新增未來價格列變動不影響 observation fields 的 no-lookahead regression test。

- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`
  - 記錄本輪 shadow-only 變更與驗證。

## Changed Files

```text
CHANGELOG.md
OUTBOX.md
STATUS.md
src/abc_quant/reports/zhu_walkline_report.py
src/abc_quant/signals/zhu_walkline_shadow.py
tests/test_zhu_walkline_features.py
tests/test_zhu_walkline_no_lookahead.py
```

Git stat:

```text
7 files changed, 417 insertions(+), 14 deletions(-)
```

## Validation Evidence

Codex reported and locally verified:

```text
ruff check .
All checks passed!

python -m pytest -q
427 passed

git diff --check
passed

python scripts/run_zhu_walkline_shadow.py --asof latest --top-n 30 --no-web --verbose
passed; wrote 2026-07-09 and latest reports under reports/zhu_walkline_shadow/
```

CSV header spot-check:

```text
latest_zhu_walkline_top_bullish_watchlist.csv:
buy_observation_type, buy_trigger_price, target_resistance_1,
target_resistance_2, sell_warning_type, invalidation_price

latest_zhu_walkline_top_fall_risks.csv:
sell_warning_type, invalidation_price

latest_zhu_walkline_shadow_log.csv:
buy_observation_type, buy_trigger_price, target_resistance_1,
target_resistance_2, sell_warning_type, invalidation_price
```

## Review Focus

請特別檢查：

1. `buy_observation_type` 是否仍只是觀察欄位，而不是正式交易訊號。
2. `sell_warning_type` 是否正確涵蓋支撐跌破、假突破、攻擊K失敗、均線失守。
3. `buy_trigger_price` 是否語意清楚，尤其是尚未觸發時仍可能回傳下一個確認價。
4. `RESISTANCE_TURN_SUPPORT` 的 approximation 是否合理，或是否需要更嚴格的歷史突破後回測定義。
5. 新欄位是否可能誤導使用者以為是直接買賣建議。
6. no-lookahead 測試是否足以證明 observation fields 沒有吃到未來價格列。
7. 是否需要把 `buy_observation_type` / `sell_warning_type` 改成單一最優先型態，而不是用 `|` 串多型態。
8. 是否有欄位缺失時的 NaN / empty-string / type risk。
9. 是否需要在報告中更明確寫 `不是買進名單，不是賣出指令`。
10. 是否仍符合：

```text
mode=shadow_observation_only
formal_champion_changed=False
formal_trade_effect=False
```

## Expected Output

請用以下格式回覆：

```text
## 總評

## 必修問題
1. ...

## 建議問題
1. ...

## 可接受部分
1. ...

## 需要 Codex 下一輪修正的 Prompt
請產生可直接貼給 Codex 的修正任務。

## 是否可接受
accepted / accepted_with_minor_followups / needs_revision
```

