# ChatGPT Review 003 - Zhu Walkline Observation Points

Source: local ChatGPT UI review of `reviews/review_package_003_zhu_walkline_observation_points.md`

## 總評

結論：方向正確，但不建議直接接受；判定為 `needs_revision`。

這輪確實把觀察欄位接進 signal、CSV、summary JSON、shadow log 與 Markdown 報告。`formal_champion_changed=False`、`formal_trade_effect=False` 也在結果物件中硬設為 False。

但有幾個語意與邊界問題會讓使用者誤以為這是「買賣指令」，尤其報告仍出現「減碼條件」「停損條件」這類交易動作語句。

## 必修問題

1. `mode` 不是硬鎖死。
   目前 mode 是從 config 讀取，預設才是 `shadow_observation_only`。如果 config 被改錯，輸出可能不再符合硬邊界。應改成硬固定或偵測非 shadow mode 直接 raise。

2. 報告仍有交易動作語言。
   `不是買賣指令` 有寫在 fixed statement，但 stock report 內仍有「續抱條件」「減碼條件」「停損條件」，這與「不可輸出絕對買賣建議」衝突。
   建議改成：「續強觀察條件」「風險升高觀察條件」「訊號失效觀察條件」。

3. `stop_reference` 欄位輸出不完整。
   `stop_reference` 有出現在 bullish CSV 欄位與 summary candidate records，但沒有進 `FALL_CSV_COLUMNS` 與 `SHADOW_LOG_COLUMNS`。使用者需求明列 `stop_reference`，shadow log 應完整保留。

4. `buy_trigger_price` 語意需要更清楚。
   目前如果沒有觸發任何買點觀察，仍會回傳 `confirm_price / resistance / prev_high / ma5` 作為下一個確認價。這邏輯可接受，但欄位名稱容易被解讀為「已觸發買點」。
   至少要新增欄位或報告文字：`buy_trigger_price_role = TRIGGERED_PRICE / NEXT_CONFIRMATION_PRICE`。

5. `RESISTANCE_TURN_SUPPORT` 定義太鬆。
   現在用 `breakout_zone_high`、目前支撐區、今日 low retest 與 `support_zone_holding_today` 近似，但沒有嚴格確認「先突破壓力 -> 後回測不破 -> 壓力轉支撐」。
   建議至少要求：前一日或近 N 日已站上舊壓力、今日低點回測舊壓力、收盤仍站上舊壓力，而且不是同一根 K 棒同時突破又回測。

6. `SUPPORT_BREAKDOWN` 可能被過度標記。
   `_sell_warning_type` 只要 `support_zone_failed_today=True` 就標 `SUPPORT_BREAKDOWN`。但 `support_zone_failed_today` 的來源包含 `price_down_volume_up`，這不一定是真跌破支撐。
   建議支撐跌破必須明確符合 `close < support/broken support` 或 `close_below_prev_low`；單純價跌量增不要直接標成支撐跌破。

7. no-lookahead 測試不足以完全證明 observation fields 無未來資料。
   現有測試只改一個未來 price row，並檢查 observation 欄位不變。這是好的 regression test，但不足以覆蓋多股票、排序、未來 chip/margin/holder 資料、以及支撐壓力 zone 的歷史視窗邊界。

## 建議問題

1. `buy_observation_type / sell_warning_type` 目前用 `|` 串多型態。
   建議主欄位改為單一最高優先型態，另加 `buy_observation_detail_types / sell_warning_detail_types` 保留完整多型態。現在的 `dict.fromkeys(...).join("|")` 對機器可讀，但對報告使用者容易誤解。

2. `target_resistance_1/2` 應保證是目前 close 上方的壓力。
   現在 fallback 到 `prev_high` 或 `high_20d` 時，可能出現低於或接近現價的「目標壓力」，建議過濾 `target > close`。

3. `_invalid_price / _confirm_price` 建議改用 `_first_price`。
   目前 `_invalid_price` 只檢查 `pd.notna(value)` 後直接 `float(value)`，遇到空字串有 type risk。

4. Markdown 報告應在「未持有者」「已持有者」段落旁邊再放一次明確提示：
   「不是買進名單，不是賣出指令，僅為觀察價與失效價」。目前 market report 有寫不是買進名單，但 stock report 主要段落仍不夠保守。

5. 測試覆蓋應補齊四種買點觀察。
   目前明確測到 `RESISTANCE_BREAKOUT`，但 `SUPPORT_REBOUND`、`RESISTANCE_TURN_SUPPORT`、`FAILED_BREAKDOWN_RECLAIM` 仍需要 positive/negative cases。

6. 賣點警示測試目前把多個條件塞在同一筆資料。
   建議每一種 sell warning 各自獨立測試，避免某個 warning 實作壞掉但被其他條件掩蓋。

## 可接受部分

1. 核心欄位已接進 feature matrix。
   `buy_observation_type`、`buy_trigger_price`、`target_resistance_1/2`、`sell_warning_type`、`invalidation_price` 都在 `_add_signal_stage_and_failure_fields` 裡產生。

2. 買點觀察條件有基本紀律。
   `_effective_buy_observation` 要求 close > trigger、量能高於 5 日或 20 日均量、收盤位置 > 0.6、排除高檔長上影，並要求明確 stop reference。

3. 賣點警示涵蓋範圍基本符合需求。
   已涵蓋支撐跌破、攻擊 K 低點跌破、假突破、壓力區失敗、均線失守。只是部分定義需更精準。

4. CSV / summary JSON / shadow log 輸出大致已接上。
   bullish、fall risk、shadow log 欄位都有新增主要 observation 欄位；summary JSON 也會輸出 candidate/risk records。

5. 正式策略邊界目前沒有直接破壞。
   `formal_champion_changed=False`、`formal_trade_effect=False` 是硬設 False；未看到正式 champion 或正式交易邏輯被修改。

## 需要 Codex 下一輪修正的 Prompt

你現在是 ABC Quant AI Research Platform 的 Quant Tech Lead，請在 branch `codex/zhu-walkline-shadow-backup` 上修正 Zhu walkline observation points。

本輪只能修 shadow/advisory/report/test，不可修改 formal strategy、formal champion、formal weights、正式持倉或正式交易邏輯。

硬邊界必須維持：

```text
mode=shadow_observation_only
formal_champion_changed=False
formal_trade_effect=False
不可產生交易指令
不可輸出絕對買賣建議
```

請完成以下修正：

1. 硬鎖 shadow mode
   - `ZhuWalklineResult.mode` 不可被 config 改成其他值。
   - 若 config 裡 `project.mode` 不是 `shadow_observation_only`，請 either：
     - 直接 override 成 `shadow_observation_only`，並加入 `run_notes` warning；或
     - raise `ValueError`。
   - 新增測試：config 傳入非 shadow mode 時，結果不可輸出非 shadow mode。

2. 修正報告交易語言
   - 移除或改寫以下交易動作語句：
     - 續抱條件
     - 減碼條件
     - 停損條件
     - 降低部位
   - 改成觀察語言，例如：
     - 續強觀察條件
     - 風險升高觀察條件
     - 訊號失效觀察條件
     - 降低風險暴露觀察
   - 在 market report 與 stock report 的「未持有者」「已持有者」段落附近明確寫：
     - 不是買進名單，不是賣出指令，僅為支撐壓力觀察價與訊號失效價。

3. 補齊 `stop_reference` 輸出
   - `stop_reference` 必須出現在：
     - bullish watchlist CSV
     - fall risk CSV
     - shadow log CSV
     - summary JSON 的 `top_bullish_watchlist`
     - summary JSON 的 `top_fall_risks`
   - 若缺值，輸出空字串，不要輸出 `NaN`、`<NA>` 或 `None` 字串。

4. 釐清 `buy_trigger_price` 語意
   - 目前無觸發時仍會回傳下一個確認價，請避免誤導。
   - 新增欄位：
     - `buy_trigger_price_role`
   - 允許值：
     - `TRIGGERED_PRICE`
     - `NEXT_CONFIRMATION_PRICE`
     - `EMPTY`
   - 若 `buy_observation_type` 為空但 `buy_trigger_price` 有值，role 必須是 `NEXT_CONFIRMATION_PRICE`。
   - Markdown 報告需顯示：若尚未觸發，該價格只是下一個確認觀察價，不是買進價。

5. 收斂 `buy_observation_type / sell_warning_type` 主欄位
   - 主欄位建議改成單一最高優先型態：
     - `buy_observation_type`
     - `sell_warning_type`
   - 另新增完整明細欄位：
     - `buy_observation_detail_types`
     - `sell_warning_detail_types`
   - detail 欄位可用 `|` 串接；主欄位不可用 `|`。
   - 建議優先序：
     - buy：
       1. `RESISTANCE_BREAKOUT`
       2. `RESISTANCE_TURN_SUPPORT`
       3. `FAILED_BREAKDOWN_RECLAIM`
       4. `SUPPORT_REBOUND`
     - sell：
       1. `SUPPORT_BREAKDOWN`
       2. `FALSE_BREAKOUT`
       3. `ATTACK_K_FAILURE`
       4. `MA_SUPPORT_FAILURE`
       5. `RESISTANCE_REJECTION`

6. 嚴格化 `RESISTANCE_TURN_SUPPORT`
   - 不可只用今日 `breakout_zone_high` 近似。
   - 至少需符合：
     - 舊壓力價存在；
     - 前一日或近 N 日已站上該壓力；
     - 今日 low 回測該壓力附近；
     - 今日 close 仍收在該壓力上方；
     - 今日不是單純同一根 K 的首次突破；
     - 不得有高檔長上影供給壓力。
   - 新增 positive test 與 negative test：
     - true case：先突破、後回測不破。
     - false case：同一天突破但尚未回測，不可標成 `RESISTANCE_TURN_SUPPORT`。

7. 修正 `SUPPORT_BREAKDOWN` 過度標記
   - `price_down_volume_up` 不得單獨導致 `SUPPORT_BREAKDOWN`。
   - `SUPPORT_BREAKDOWN` 必須明確跌破：
     - broken support zone；或
     - support zone；或
     - previous low。
   - 價跌量增可留在 `risk_reason`，但不要誤標為支撐跌破。

8. 保證 target resistance 合理
   - `target_resistance_1 / target_resistance_2` 必須是 close 上方壓力。
   - 若 fallback 價低於或等於 close，輸出空值。
   - 新增測試避免 target resistance 低於現價。

9. 加強 NaN / empty-string / type safety
   - `_invalid_price`、`_confirm_price` 改用 `_first_price` 或同等安全函式。
   - Markdown / CSV / JSON 不可輸出 `<NA>`、`nan`、`None` 字串。
   - 新增缺欄位、`pd.NA`、空字串測試。

10. 加強 no-lookahead 測試
    - 保留現有未來 price row mutation 測試。
    - 新增：
      - 多股票 future row mutation；
      - future chip/margin/holder rows 不影響 observation fields；
      - future high/low/volume 不影響 support/resistance/observation；
      - `RESISTANCE_TURN_SUPPORT` 不可吃到 asof 之後的突破或回測資料。

驗證要求：

```text
ruff check .
python -m pytest -q
git diff --check
python scripts/run_zhu_walkline_shadow.py --asof latest --top-n 30 --no-web --verbose
```

最後更新 `CHANGELOG.md`、`STATUS.md`、`OUTBOX.md`，明確記錄：

```text
mode=shadow_observation_only
formal_champion_changed=False
formal_trade_effect=False
no formal strategy modified
no formal champion modified
no formal trade effect
```

## 是否可接受

`needs_revision`

