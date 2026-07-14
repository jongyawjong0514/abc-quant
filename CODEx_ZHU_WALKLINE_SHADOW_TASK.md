以下是**完整重寫版**，可直接貼給 Codex。

# Codex 任務書：建立「走圖／走線心法」台股本地資料庫＋網路輔助掃描器

## 任務名稱

建立一套台股盤後 shadow 掃描器，使用本地資料庫為主、必要時網路搜尋為輔，找出：

1. 可能即將上漲的股票候選名單
2. 可能即將下跌的股票風險名單
3. 大盤強弱狀態
4. 類股輪動
5. 概念股輪動
6. 法人籌碼變化
7. 大戶／主力籌碼變化或 proxy
8. 融資融券變化
9. 單檔股票走圖報告
10. 全市場 markdown 報告

輸出語氣採用「走圖教學式口吻」：

```text
同學，走圖第一步不是問會不會漲，是先看趨勢。
同學，股價在均線上面，均線往上，才叫多方控盤。
同學，有下影線不等於轉強，收過壓力才叫轉強。
同學，量縮反彈可以看，但不能追。
同學，跌破支撐還說洗盤，那不是走圖，那是走心。
同學，沒有訊號，就沒有動作。
```

但報告不可宣稱「朱家泓本人推薦」、不可冒充本人、不可保證漲跌。
所有結果皆為：

```text
mode=shadow_advisory_only
formal_champion_changed=False
formal_trade_effect=False
```

---

# 0. 專案總原則

請在本地專案目錄完成此任務：

```text
E:\abc
```

使用 Python 建立一個可執行、可測試、可擴充的台股走圖掃描器。

核心原則：

1. 本地資料庫優先。
2. 必要時才啟用網路搜尋。
3. 網路資料只作為補充，不可取代量價、均線、法人、融資券。
4. 不可使用未來資料。
5. 不可 look-ahead bias。
6. 不可 survivorship bias。
7. 不可自動下單。
8. 不可修改正式策略。
9. 不可修改 formal champion。
10. 不可修改 formal weights。
11. 不可修改正式持倉。
12. 不可產生實盤交易指令。
13. 不可硬編假資料。
14. 缺資料要明確警告，不可 silent failure。
15. 所有結果只作為技術分析教育與 shadow observation。

---

# 1. 本地資料來源

優先使用 SQLite：

```text
C:\Users\User\Desktop\新增資料夾 (4)\state\tw_data_mirror.sqlite
```

可能存在的 FinLab / pickle / parquet / csv 資料目錄：

```text
C:\Users\User\Desktop\finlab_ml_course\history\history\items\
C:\Users\User\Desktop\finlab_ml_course\history\history\items\price
C:\Users\User\Desktop\finlab_ml_course\history\history\items\bargin_report
C:\Users\User\Desktop\finlab_ml_course\history\history\items\forign_hold_ratio
C:\Users\User\Desktop\finlab_ml_course\history\history\items\monthly_report
C:\Users\User\Desktop\finlab_ml_course\history\history\items\pe
C:\Users\User\Desktop\finlab_ml_course\history\history\items\income_sheet
C:\Users\User\Desktop\finlab_ml_course\history\history\items\balance_sheet
C:\Users\User\Desktop\finlab_ml_course\history\history\items\cash_flows
```

請建立資料載入器，自動處理：

1. SQLite table 掃描
2. pickle 掃描
3. parquet 掃描
4. csv 掃描
5. 欄位名稱中英混合
6. 日期格式標準化
7. 股票代號標準化
8. 上市／上櫃合併
9. 大盤指數、櫃買指數讀取
10. 法人買賣超讀取
11. 融資融券讀取
12. 大戶／TDCC／持股級距讀取，如果有資料
13. 缺漏值檢查
14. 最新資料日期檢查
15. 資料品質報告

如果找不到某類資料，不可中止整體流程，但必須在 data quality 報告明確寫出，例如：

```text
融資券資料缺失，本次 margin_score 使用 neutral，不納入加減分。
```

```text
大戶資料缺失，本次 big_holder_score 使用主力代理 proxy，不視為真實大戶持股。
```

---

# 2. 網路搜尋原則

本系統允許必要時網路搜尋，但必須遵守：

```text
本地資料庫優先，網路搜尋為輔。
價格、成交量、法人、融資券等結構化數據，優先使用本地資料庫。
若本地資料缺漏、過舊、沒有概念股分類、沒有公司產業資料、沒有重大訊息、沒有法說會或營收補充資料，才啟用網路搜尋。
```

## 2.1 何時可使用網路搜尋

只有以下情境可用：

1. 本地資料缺少股票名稱。
2. 本地資料缺少產業別。
3. 本地資料缺少類股別。
4. 本地資料缺少概念股分類。
5. 本地資料缺少公司主要產品。
6. 本地資料缺少最新重大訊息。
7. 本地資料缺少最新月營收。
8. 本地資料缺少法說會簡報。
9. 某檔股票異常大漲、大跌，需要查詢是否有重大事件。
10. 需要補充 AI 伺服器、PCB、CCL、機器人、半導體設備等題材來源。
11. 需要查詢公司公告、新聞或產業鏈位置。

## 2.2 網路資料來源優先順序

第一優先，官方資料：

```text
TWSE 台灣證券交易所
TPEx 櫃買中心
MOPS 公開資訊觀測站
公司官方網站
公司法說會簡報
公司年報
公司財報
```

第二優先，可靠財經資料：

```text
Goodinfo
CMoney
WantGoo
Anue 鉅亨網
MoneyDJ
Yahoo 股市
工商時報
經濟日報
中央社
```

第三優先，只能當參考：

```text
PTT
Dcard
Facebook
YouTube
Telegram
論壇
社群貼文
未具名消息
```

第三優先來源不可納入量化分數，只能作為報告附註，並標示：

```text
此為非官方消息來源，只作為題材參考，不納入核心量化分數。
```

## 2.3 網路資料不可違反事項

嚴格遵守：

1. 不可用網路資料取代本地 OHLCV，除非本地資料缺漏。
2. 不可用未確認網路消息直接判定買進。
3. 不可把論壇、社群、新聞標題直接當作事實。
4. 不可沒有來源就寫入報告。
5. 不可使用 asof_date 之後的資料產生 asof_date 訊號。
6. 不可繞過付費牆。
7. 不可爬取明確禁止爬蟲的網站。
8. 不可複製付費內容全文。
9. 不可把網路消息當成保證漲跌理由。
10. 不可宣稱「朱家泓本人推薦」。

## 2.4 網路資料快取

請建立：

```text
data/web_cache/
data/web_cache/web_search_cache.sqlite
data/web_cache/web_sources.jsonl
```

每一筆網路資料至少記錄：

```json
{
  "fetched_at": "YYYY-MM-DD HH:MM:SS",
  "asof_date": "YYYY-MM-DD",
  "stock_id": "2330",
  "stock_name": "",
  "source_name": "MOPS",
  "url": "",
  "title": "",
  "published_at": "",
  "source_priority": "official|reliable_media|community",
  "content_summary": "",
  "used_in_score": false,
  "used_in_report": true,
  "confidence": "high|medium|low",
  "published_at_unknown": false
}
```

## 2.5 網路分數限制

網路資料最多只能影響：

```text
rise_score 最多 +5 分
fall_risk_score 最多 +5 分
```

分數規則：

1. 官方重大訊息：最多 ±5 分。
2. 公司法說會、月營收、財報：最多 ±5 分。
3. 可靠媒體報導：最多 ±3 分。
4. 社群與論壇：0 分，只能附註。
5. 未具名消息：0 分，不納入分數。
6. published_at_unknown：0 分，只能附註。
7. asof_date 之後資料：完全排除，不可出現在 feature 中。

---

# 3. 建立檔案與模組

請建立或整合以下檔案。若目錄不存在，請建立。

```text
config/zhu_walkline_shadow.yaml
config/concept_stock_map.yaml

src/abc_quant/data/local_tw_loader.py
src/abc_quant/data/web_research.py
src/abc_quant/data/web_cache.py

src/abc_quant/features/walkline_features.py
src/abc_quant/features/chip_features.py
src/abc_quant/features/margin_features.py
src/abc_quant/features/market_rotation.py
src/abc_quant/features/news_event_features.py

src/abc_quant/signals/zhu_walkline_shadow.py

src/abc_quant/reports/zhu_walkline_report.py

scripts/run_zhu_walkline_shadow.py

tests/test_zhu_walkline_features.py
tests/test_zhu_walkline_no_lookahead.py
tests/test_web_research_no_lookahead.py

reports/zhu_walkline_shadow/
data/web_cache/
```

若現有專案已有相似模組，請優先整合，不要重複造輪子。
但必須保留一個清楚可執行入口：

```bash
python scripts/run_zhu_walkline_shadow.py --asof latest
```

支援指定日期：

```bash
python scripts/run_zhu_walkline_shadow.py --asof 2026-07-08
```

支援單檔分析：

```bash
python scripts/run_zhu_walkline_shadow.py --asof latest --stock 6830
python scripts/run_zhu_walkline_shadow.py --asof latest --stock 6274
python scripts/run_zhu_walkline_shadow.py --asof latest --stock 2464
```

支援網路搜尋：

```bash
python scripts/run_zhu_walkline_shadow.py --asof latest --use-web
python scripts/run_zhu_walkline_shadow.py --asof latest --no-web
python scripts/run_zhu_walkline_shadow.py --asof latest --use-web --web-max-results 5
python scripts/run_zhu_walkline_shadow.py --asof latest --stock 6830 --use-web
```

預設為：

```text
--no-web
```

只有使用者明確加上 `--use-web` 才啟用網路搜尋。

---

# 4. 輸出檔案

每次執行後，輸出到：

```text
reports/zhu_walkline_shadow/
```

至少產生：

```text
latest_zhu_walkline_summary.json
latest_zhu_walkline_top_rise_candidates.csv
latest_zhu_walkline_top_fall_risks.csv
latest_zhu_walkline_market_report.md
latest_zhu_walkline_stock_report.md
latest_zhu_walkline_data_quality.md
latest_zhu_walkline_feature_matrix.parquet
latest_zhu_walkline_web_sources.jsonl
```

若指定日期，例如：

```bash
python scripts/run_zhu_walkline_shadow.py --asof 2026-07-08
```

另輸出：

```text
2026-07-08_zhu_walkline_summary.json
2026-07-08_zhu_walkline_top_rise_candidates.csv
2026-07-08_zhu_walkline_top_fall_risks.csv
2026-07-08_zhu_walkline_market_report.md
2026-07-08_zhu_walkline_stock_report.md
2026-07-08_zhu_walkline_data_quality.md
2026-07-08_zhu_walkline_feature_matrix.parquet
2026-07-08_zhu_walkline_web_sources.jsonl
```

---

# 5. Config 設計

請建立：

```text
config/zhu_walkline_shadow.yaml
```

內容至少包含：

```yaml
project:
  root: "E:/abc"
  mode: "shadow_advisory_only"
  formal_champion_changed: false
  formal_trade_effect: false

data:
  sqlite_path: "C:/Users/User/Desktop/新增資料夾 (4)/state/tw_data_mirror.sqlite"
  finlab_items_root: "C:/Users/User/Desktop/finlab_ml_course/history/history/items"
  output_dir: "reports/zhu_walkline_shadow"
  web_cache_dir: "data/web_cache"

runtime:
  default_asof: "latest"
  default_top_n: 30
  no_web_default: true
  fail_loud: true

scoring:
  web_score_cap: 5
  rise_min_c: 60
  rise_min_b: 70
  rise_min_a: 80
  fall_watch: 50
  fall_medium: 65
  fall_high: 80

report:
  tone: "walkline_teaching"
  avoid_impersonation: true
  include_non_holder_section: true
  include_holder_section: true
```

---

# 6. 概念股 mapping

請建立：

```text
config/concept_stock_map.yaml
```

初始可用少量模板，不要硬編大量不確定資料。格式如下：

```yaml
AI_SERVER:
  - "6669"
  - "2382"
  - "3231"

PCB:
  - "2368"
  - "2313"

CCL:
  - "2383"
  - "6274"

ROBOTICS:
  - "2464"
  - "1590"

SEMICONDUCTOR_EQUIPMENT:
  - "6830"

CPO_SILICON_PHOTONICS: []

THERMAL: []

HEAVY_ELECTRIC: []
```

報告中必須註明：

```text
概念股 mapping 需人工維護確認，本次僅作為輪動分組輔助。
```

若 `--use-web` 啟用，可用網路補充概念股歸屬，但不可直接覆蓋 config；請輸出建議到：

```text
reports/zhu_walkline_shadow/concept_stock_map_suggestions.md
```

---

# 7. 大盤層分析

分析加權指數與櫃買指數，至少計算：

1. open
2. high
3. low
4. close
5. volume
6. turnover
7. return_1d
8. return_3d
9. return_5d
10. return_10d
11. ma5
12. ma10
13. ma20
14. ma60
15. ma120
16. ma240
17. vol_ma5
18. vol_ma20
19. amount_ma5
20. amount_ma20
21. 頭頭高／頭頭低
22. 底底高／底底低
23. 是否跌破5日線
24. 是否跌破10日線
25. 是否跌破20日線
26. 是否站回5日線
27. 是否站回10日線
28. 是否站回20日線
29. 20日高點
30. 20日低點
31. 60日高點
32. 60日低點
33. 距20日高點回落幅度
34. 距60日高點回落幅度

大盤狀態分為：

```text
MARKET_STRONG_UPTREND
MARKET_PULLBACK_IN_UPTREND
MARKET_RANGE_BOUND
MARKET_WEAK_REBOUND
MARKET_DOWNTREND
MARKET_HIGH_RISK_BREAKDOWN
```

判斷規則：

1. close > ma5 > ma10 > ma20 > ma60，且 ma5、ma10、ma20 向上：`MARKET_STRONG_UPTREND`
2. close < ma5 或 close < ma10，但 close > ma60：`MARKET_PULLBACK_IN_UPTREND`
3. ma5、ma10、ma20 糾結，且價格區間震盪：`MARKET_RANGE_BOUND`
4. 長黑後反彈，但未站回 ma5 或 ma10：`MARKET_WEAK_REBOUND`
5. close < ma20 且 ma5 < ma10 < ma20：`MARKET_DOWNTREND`
6. close < ma60 且放量長黑，或跌破重要區間低點：`MARKET_HIGH_RISK_BREAKDOWN`

大盤狀態影響評分：

1. `MARKET_STRONG_UPTREND`：多方候選股加分。
2. `MARKET_PULLBACK_IN_UPTREND`：只挑強於大盤股票。
3. `MARKET_WEAK_REBOUND`：候選股只能列「觀察」，不可列「強攻」。
4. `MARKET_DOWNTREND`：多方候選股降分，空方風險加分。
5. `MARKET_HIGH_RISK_BREAKDOWN`：所有多方候選股大幅降分，風險名單加分。

---

# 8. 類股輪動層

請依本地資料可用性建立類股分組或代理分組。

至少支援：

1. 半導體
2. 電子零組件
3. AI伺服器
4. PCB
5. CCL
6. 散熱
7. 機器人
8. 自動化
9. 重電
10. 金融
11. 航運
12. 生技
13. 傳產
14. 觀光
15. 軍工
16. 光通訊
17. 半導體設備

類股輪動計算：

1. sector_return_1d
2. sector_return_3d
3. sector_return_5d
4. sector_return_10d
5. sector_return_20d
6. sector_volume_ratio_5
7. sector_volume_ratio_20
8. sector_relative_strength_vs_market_5d
9. sector_relative_strength_vs_market_10d
10. sector_relative_strength_vs_market_20d
11. sector_above_ma20_ratio
12. sector_below_ma20_ratio
13. sector_new_20d_high_ratio
14. sector_new_20d_low_ratio
15. sector_leader_strength
16. sector_laggard_rebound_score
17. sector_distribution_risk

輸出欄位：

```text
sector
sector_rotation_rank
sector_strength_score
sector_risk_score
sector_state
sector_reason
```

類股狀態：

```text
SECTOR_LEADING
SECTOR_ROTATING_IN
SECTOR_PULLBACK_HEALTHY
SECTOR_RANGE_BOUND
SECTOR_ROTATING_OUT
SECTOR_WEAK
```

---

# 9. 概念股輪動層

概念股分組來自：

```text
config/concept_stock_map.yaml
```

若 `--use-web` 啟用，網路資料可補充概念股建議，但不可直接覆寫 config。

概念股輪動至少支援：

1. AI_SERVER
2. CPO_SILICON_PHOTONICS
3. PCB
4. CCL
5. ROBOTICS
6. AUTOMATION
7. SEMICONDUCTOR_EQUIPMENT
8. THERMAL
9. HEAVY_ELECTRIC
10. BIOTECH
11. SHIPPING
12. FINANCIAL

概念股計算：

1. concept_return_1d
2. concept_return_3d
3. concept_return_5d
4. concept_return_10d
5. concept_return_20d
6. concept_volume_expansion_ratio
7. concept_above_ma20_ratio
8. concept_below_ma20_ratio
9. concept_new_20d_high_ratio
10. concept_leader_stock
11. concept_leader_breakdown
12. concept_laggard_rebound
13. concept_rotation_rank
14. concept_strength_score
15. concept_risk_score

概念股報告需說明：

```text
同學，概念股不是每一檔都會漲，要看領頭羊有沒有續強，落後股有沒有補漲，還有整個族群是不是同步站上均線。
```

---

# 10. 個股走圖特徵

每一檔股票至少計算以下欄位。

## 10.1 價格與趨勢

```text
open
high
low
close
volume
turnover
return_1d
return_3d
return_5d
return_10d
return_20d
high_20d
low_20d
high_60d
low_60d
drawdown_from_20d_high
drawdown_from_60d_high
distance_to_20d_high
distance_to_60d_high
swing_high_1
swing_high_2
swing_low_1
swing_low_2
higher_high
lower_high
higher_low
lower_low
trend_state
```

`trend_state`：

```text
UPTREND
PULLBACK_IN_UPTREND
RANGE_BOUND
WEAK_REBOUND
DOWNTREND
BREAKDOWN
```

## 10.2 均線

```text
ma5
ma10
ma20
ma60
ma120
ma240
ma5_slope
ma10_slope
ma20_slope
ma60_slope
close_above_ma5
close_above_ma10
close_above_ma20
close_above_ma60
close_above_ma120
close_above_ma240
ma_bull_alignment
ma_bear_alignment
ma_compression
ma_reclaim_5
ma_reclaim_10
ma_reclaim_20
ma_break_5
ma_break_10
ma_break_20
ma_state
```

`ma_state`：

```text
BULL_ALIGNMENT
BULL_PULLBACK
MA_RECLAIM
MA_COMPRESSION
MA_BREAK
BEAR_ALIGNMENT
```

## 10.3 K棒

```text
k_body_pct
upper_shadow_pct
lower_shadow_pct
close_position_in_range
red_k
black_k
long_red_k
long_black_k
gap_up
gap_down
break_prev_high
break_prev_low
close_above_prev_high
close_below_prev_low
hammer_like
shooting_star_like
engulfing_bullish_like
engulfing_bearish_like
inside_bar
outside_bar
failed_breakout
failed_breakdown
kline_state
```

`kline_state`：

```text
ATTACK_RED_K
STOPPING_K
WEAK_REBOUND_K
LONG_BLACK_K
UPPER_SHADOW_SUPPLY
BREAKDOWN_K
RANGE_K
```

## 10.4 量能

```text
vol_ma5
vol_ma20
vol_ratio_5
vol_ratio_20
amount_ma5
amount_ma20
amount_ratio_5
amount_ratio_20
volume_expansion
volume_contraction
price_up_volume_up
price_up_volume_down
price_down_volume_up
price_down_volume_down
high_volume_upper_shadow
high_volume_long_black
low_volume_pullback
volume_state
```

`volume_state`：

```text
ATTACK_VOLUME
HEALTHY_PULLBACK_VOLUME
WEAK_REBOUND_VOLUME
DISTRIBUTION_VOLUME
PANIC_VOLUME
NEUTRAL_VOLUME
```

## 10.5 支撐壓力

```text
support_1
support_2
support_3
resistance_1
resistance_2
resistance_3
nearest_support_distance
nearest_resistance_distance
risk_reward_proxy
support_broken_today
resistance_reclaimed_today
stop_reference
entry_observation
```

支撐壓力來源：

1. 最近 swing low
2. 最近 swing high
3. 前一日高低點
4. 20日高低點
5. 60日高低點
6. ma5
7. ma10
8. ma20
9. ma60
10. 整數關卡

---

# 11. 法人籌碼層

從 SQLite 或本地 `bargin_report` 讀取。

至少計算：

```text
foreign_buy_sell
investment_trust_buy_sell
dealer_buy_sell
dealer_hedge_buy_sell
institutional_total_buy_sell
foreign_3d
foreign_5d
foreign_10d
foreign_20d
investment_trust_3d
investment_trust_5d
investment_trust_10d
investment_trust_20d
dealer_3d
dealer_5d
dealer_10d
dealer_20d
foreign_consecutive_buy_days
foreign_consecutive_sell_days
investment_trust_consecutive_buy_days
investment_trust_consecutive_sell_days
institutional_buy_ratio_to_volume
institutional_sell_ratio_to_volume
institutional_score
foreign_score
investment_trust_score
dealer_score
```

法人判斷：

1. 外資、投信同步買超：加分。
2. 投信連買且股價創高：加分。
3. 法人買超但股價不漲：標示「上方供給」。
4. 法人連賣且跌破均線：列入下跌風險。
5. 外資轉買第一天：只列觀察，不可過度加分。
6. 法人買超占成交量比例過高但股價收黑：標示「買盤被倒貨吸收」。

---

# 12. 大戶／主力籌碼層

若有 TDCC、大戶、分點、主力資料，請讀取。
若沒有，請建立 proxy，不可硬編。

## 12.1 若有 TDCC

計算：

```text
holder_400_lots_ratio
holder_1000_lots_ratio
large_holder_ratio
large_holder_weekly_change
retail_holder_ratio
retail_holder_weekly_change
concentration_score
big_holder_score
```

## 12.2 若無 TDCC，用 proxy

proxy 包含：

```text
high_volume_red_k
high_volume_black_k
low_volume_pullback
support_hold_after_pullback
failed_breakout_supply
high_volume_upper_shadow
institution_buy_price_weak
institution_sell_price_strong
main_force_proxy_score
supply_pressure_score
```

判斷：

1. 量縮不跌：籌碼穩定，加分。
2. 拉回守20日線：加分。
3. 高檔爆量長上影：供給壓力，加風險。
4. 法人買但價格弱：供給壓力。
5. 法人賣但價格強：可能有人承接，但只能列觀察。
6. 跌破支撐爆量：列入風險。

---

# 13. 融資融券層

若本地資料有 margin / short selling，請計算：

```text
margin_balance
margin_change_1d
margin_change_3d
margin_change_5d
margin_change_10d
margin_usage_ratio
short_balance
short_change_1d
short_change_3d
short_change_5d
short_change_10d
short_margin_ratio
margin_consecutive_increase_days
margin_consecutive_decrease_days
short_consecutive_increase_days
short_consecutive_decrease_days
short_covering_pressure
price_up_margin_up
price_down_margin_up
price_up_margin_down
price_breakout_short_up
margin_score
short_squeeze_score
retail_crowding_risk
margin_risk_score
```

融資券判斷：

1. 股價上漲、融資大增：散戶追價風險。
2. 股價下跌、融資大增：融資攤平風險。
3. 股價上漲、融資下降：籌碼較乾淨，加分。
4. 股價強勢、融券增加：可能有軋空條件，但需搭配量價。
5. 股價跌破支撐、融資未減：下跌風險加分。
6. 融資連增但股價不創高：風險加分。
7. 融券回補但股價不漲：軋空力道不足。

---

# 14. 網路事件特徵

若 `--use-web` 啟用，請在 `news_event_features.py` 建立：

```text
has_recent_mops_event
has_recent_revenue_news
has_recent_earnings_news
has_recent_law_conference
has_recent_product_news
has_recent_customer_news
has_recent_warning_news
event_sentiment_score
event_confidence_score
event_source_quality_score
event_score_for_rise
event_score_for_fall
```

規則：

1. 官方重大訊息，最高 ±5。
2. 月營收明確成長或衰退，最高 ±5。
3. 法說會展望明確，最高 ±5。
4. 可靠媒體，最高 ±3。
5. 社群消息，0 分。
6. published_at_unknown，0 分。
7. asof_date 之後新聞，完全排除。

---

# 15. 即將上漲候選邏輯

建立 `rise_score`，滿分 100 分。

建議權重：

```text
market_score: 10
sector_rotation_score: 15
concept_rotation_score: 10
trend_score: 15
ma_score: 15
kline_score: 10
volume_score: 10
institutional_score: 10
big_holder_score: 5
margin_clean_score: 5
web_event_score: 0 to 5
risk_penalty: -0 to -30
```

多方候選條件：

1. 大盤不是 `MARKET_HIGH_RISK_BREAKDOWN`。
2. 類股強於大盤。
3. 概念股輪動排名在前段。
4. 股價站上5日或10日線。
5. 5日線或10日線向上。
6. 今日收盤突破昨日高點，或站回關鍵均線。
7. 成交量大於5日均量或20日均量。
8. 外資或投信出現買超。
9. 未出現高檔爆量長上影。
10. 未出現跌破支撐。
11. 停損點可明確定義。
12. 風險報酬比合理。

候選等級：

```text
A: rise_score >= 80，高勝率觀察
B: rise_score >= 70，可觀察
C: rise_score >= 60，只列追蹤
```

注意：

即使 A 級，也只能輸出：

```text
觀察買點
轉強條件
防守點
```

不可輸出：

```text
明天買
一定漲
保證噴出
歐印
```

---

# 16. 即將下跌風險邏輯

建立 `fall_risk_score`，滿分 100 分。

建議權重：

```text
market_risk_score: 15
sector_weakness_score: 15
concept_weakness_score: 10
trend_break_score: 15
ma_break_score: 15
kline_weakness_score: 10
volume_distribution_score: 10
institutional_selling_score: 10
margin_risk_score: 10
support_break_penalty: 10
web_event_risk_score: 0 to 5
```

下跌風險條件：

1. 跌破5日、10日、20日線。
2. 高點降低、低點降低。
3. 跌破前一日低點。
4. 收盤接近當日低點。
5. 高檔爆量長黑。
6. 高檔爆量長上影。
7. 法人連續賣超。
8. 融資增加但股價下跌。
9. 類股轉弱。
10. 概念股領頭股轉弱。
11. 跌破近期重要支撐。
12. 大盤進入弱勢反彈或高風險跌破。

風險等級：

```text
HIGH_RISK: fall_risk_score >= 80
MEDIUM_RISK: fall_risk_score >= 65
WATCH_RISK: fall_risk_score >= 50
```

---

# 17. 單檔走圖報告格式

每一檔股票 markdown 報告格式如下：

```markdown
# 股票代號 股票名稱｜走圖分析

## 一、先講結論

同學，這張圖現在是：

- 趨勢：
- 均線：
- K棒：
- 量能：
- 法人：
- 大戶／主力：
- 融資券：
- 大盤背景：
- 類股輪動：
- 概念股輪動：
- 結論：

## 二、趨勢

說明頭頭高、底底高，或頭頭低、底底低。

## 三、均線

說明5日、10日、20日、60日均線位置與股價關係。

## 四、K線

說明今日K棒是攻擊K、止跌K、弱反彈、長上影、長黑、破底K。

## 五、量能

說明量增、量縮、價漲量增、價跌量增、量縮反彈。

## 六、法人籌碼

說明外資、投信、自營商買賣超與連買連賣。

## 七、大戶／主力代理

說明是否有承接、出貨、上方供給、量價背離。

## 八、融資券

說明融資是否過熱、融券是否有軋空條件。

## 九、大盤與類股背景

說明大盤狀態、類股輪動與概念股輪動。

## 十、支撐與壓力

| 價位 | 意義 |
|---:|---|
| 支撐1 | |
| 支撐2 | |
| 壓力1 | |
| 壓力2 | |

## 十一、明日劇本

### 劇本A：轉強

條件：
1.
2.
3.

### 劇本B：續弱

條件：
1.
2.
3.

### 劇本C：整理

條件：
1.
2.
3.

## 十二、未持有者

同學，未持有不要急。
要等什麼訊號？

## 十三、已持有者

同學，已持有先看防守點。
跌破什麼位置要減碼或停損？

## 十四、網路補充資料

| 來源 | 日期 | 重點 | 是否納入分數 |
|---|---|---|---|

若未使用網路資料，寫：

本次分析未使用網路補充資料，僅依本地資料庫計算。

若有使用網路資料，寫：

本次網路資料僅作為題材與事件補充，核心評分仍以本地量價、均線、法人、融資券資料為主。

## 十五、一句話

用一句話總結。
```

---

# 18. 報告語氣規範

可以使用：

```text
同學，走圖第一步，不是問會不會漲，是先看趨勢。
同學，股價在均線上面，均線往上，才叫多方控盤。
同學，有下影線不等於轉強，收過壓力才叫轉強。
同學，量縮反彈可以看，但不能追。
同學，跌破支撐還說洗盤，那不是走圖，那是走心。
同學，空手不是沒有操作，空手是在等勝率。
同學，沒有訊號，就沒有動作。
同學，強勢股不是永遠強，跌破均線就要重新判斷。
同學，法人買不代表一定漲，還要看價格有沒有跟上。
同學，融資大增但股價不漲，這叫籌碼壓力，不叫安全。
```

不可使用：

```text
朱家泓老師推薦
朱家泓本人看好
本人推薦
保證上漲
一定噴出
明天必漲
現在歐印
無腦買
內線
穩賺
必勝
```

---

# 19. JSON summary 欄位

`latest_zhu_walkline_summary.json` 至少包含：

```json
{
  "asof_date": "YYYY-MM-DD",
  "mode": "shadow_advisory_only",
  "formal_champion_changed": false,
  "formal_trade_effect": false,
  "web_research_used": false,
  "web_research_is_supplementary": true,
  "data_sources": [],
  "data_quality": {
    "missing_tables": [],
    "missing_fields": [],
    "latest_price_date": null,
    "latest_chip_date": null,
    "latest_margin_date": null,
    "latest_big_holder_date": null,
    "warnings": []
  },
  "market": {
    "market_state": "",
    "market_score": 0,
    "market_risk_score": 0,
    "support_levels": [],
    "resistance_levels": []
  },
  "sector_rotation": [],
  "concept_rotation": [],
  "top_rise_candidates": [],
  "top_fall_risks": [],
  "run_notes": []
}
```

每一檔 rise candidate：

```json
{
  "stock_id": "",
  "stock_name": "",
  "close": 0,
  "rise_score": 0,
  "grade": "",
  "sector": "",
  "concepts": [],
  "trend_state": "",
  "ma_state": "",
  "kline_state": "",
  "volume_state": "",
  "institutional_score": 0,
  "big_holder_score": 0,
  "margin_score": 0,
  "web_event_score": 0,
  "support": [],
  "resistance": [],
  "entry_observation": "",
  "stop_reference": "",
  "reason": []
}
```

每一檔 fall risk：

```json
{
  "stock_id": "",
  "stock_name": "",
  "close": 0,
  "fall_risk_score": 0,
  "risk_grade": "",
  "sector": "",
  "concepts": [],
  "trend_break_reason": "",
  "ma_break_reason": "",
  "kline_weakness": "",
  "volume_distribution": "",
  "institutional_selling": "",
  "margin_risk": "",
  "web_event_risk_score": 0,
  "support_broken": [],
  "next_support": [],
  "reason": []
}
```

---

# 20. CSV 欄位

`latest_zhu_walkline_top_rise_candidates.csv` 欄位：

```text
asof_date
stock_id
stock_name
close
rise_score
grade
sector
concepts
market_state
sector_rotation_rank
concept_rotation_rank
trend_state
ma_state
kline_state
volume_state
foreign_5d
investment_trust_5d
dealer_5d
institutional_score
big_holder_score
margin_score
web_event_score
support_1
support_2
resistance_1
resistance_2
entry_observation
stop_reference
reason_summary
```

`latest_zhu_walkline_top_fall_risks.csv` 欄位：

```text
asof_date
stock_id
stock_name
close
fall_risk_score
risk_grade
sector
concepts
market_state
trend_state
ma_state
kline_state
volume_state
foreign_5d
investment_trust_5d
dealer_5d
institutional_selling_score
margin_risk_score
web_event_risk_score
support_broken
next_support
risk_reason_summary
```

---

# 21. Data quality 報告

`latest_zhu_walkline_data_quality.md` 必須列出：

1. 找到哪些 SQLite tables。
2. 找到哪些 pickle / parquet / csv 檔。
3. 使用哪些資料欄位。
4. 缺少哪些欄位。
5. 最新股價日期。
6. 最新法人日期。
7. 最新融資券日期。
8. 最新大戶資料日期。
9. 最新概念股 mapping 日期。
10. 是否啟用網路搜尋。
11. 網路搜尋使用了哪些來源。
12. 哪些網路來源被納入分數。
13. 哪些網路來源只作附註。
14. 是否有資料不足導致降級分析。
15. 是否有任何 no-lookahead 過濾。

若缺融資券：

```text
融資券資料缺失，本次 margin_score 使用 neutral，不納入加減分。
```

若缺大戶資料：

```text
大戶資料缺失，本次 big_holder_score 使用主力代理 proxy，不視為真實大戶持股。
```

若缺網路搜尋能力：

```text
未啟用或無法使用網路搜尋，本次分析僅使用本地資料庫。
```

---

# 22. No-lookahead 測試

建立 `tests/test_zhu_walkline_no_lookahead.py`，至少測試：

1. 指定 `--asof 2026-07-08` 時，不可使用 2026-07-09 之後資料。
2. rolling feature 只能使用 asof_date 之前含當日資料。
3. forward returns 只可用於離線評估，不可進入當日 feature。
4. feature_matrix 不可包含 `future_return`、`label_d1`、`label_d3`、`label_d5` 作為訊號輸入。
5. 若資料日期超過 asof_date，必須被過濾。
6. 網路資料 published_at > asof_date 不可納入 feature。
7. published_at_unknown 不可加分。
8. 社群資料不可加分。
9. 官方資料可加分但最多5分。
10. 網路資料缺失時，程式仍可執行。

---

# 23. Feature 測試

建立 `tests/test_zhu_walkline_features.py`，用 mock dataframe 測試：

1. ma5 / ma10 / ma20 計算正確。
2. ma_bull_alignment 正確。
3. ma_bear_alignment 正確。
4. close_above_prev_high 正確。
5. close_below_prev_low 正確。
6. long_red_k 正確。
7. long_black_k 正確。
8. upper_shadow_pct 正確。
9. lower_shadow_pct 正確。
10. vol_ratio_5 正確。
11. support / resistance 不使用未來資料。
12. rise_score 介於 0 到 100。
13. fall_risk_score 介於 0 到 100。

若真實本地資料不存在，測試不得失敗；請用 mock data。

---

# 24. Web no-lookahead 測試

建立 `tests/test_web_research_no_lookahead.py`，測試：

1. asof_date 之後新聞被排除。
2. published_at_unknown 不納入分數。
3. community source 不納入分數。
4. official source 可納入，但分數 cap = 5。
5. reliable_media source 可納入，但分數 cap = 3。
6. 無網路資料時，event_score = 0。
7. web cache 可正常讀寫。
8. web source JSONL 格式正確。

---

# 25. 離線驗證與 metrics

請新增可選離線評估模式，不影響每日 shadow 掃描。

執行：

```bash
python scripts/run_zhu_walkline_shadow.py --asof 2026-07-08 --evaluate-forward
```

只在評估模式計算：

```text
future_return_d1
future_return_d3
future_return_d5
future_return_d10
hit_d1
hit_d3
hit_d5
hit_d10
max_drawdown_next_5d
max_gain_next_5d
```

注意：

1. 這些欄位不可出現在正式 feature matrix。
2. 只可輸出到 evaluation 檔案。
3. 不可用來當日選股。
4. 必須在報告中標示「離線評估，不可用於當日訊號」。

輸出：

```text
latest_zhu_walkline_evaluation.csv
latest_zhu_walkline_evaluation_summary.json
```

Metrics：

```text
rise_candidate_d1_hit_rate
rise_candidate_d3_hit_rate
rise_candidate_d5_hit_rate
fall_risk_d1_hit_rate
fall_risk_d3_hit_rate
fall_risk_d5_hit_rate
avg_forward_return_d1
avg_forward_return_d3
avg_forward_return_d5
max_drawdown_next_5d
precision_at_10
precision_at_30
```

---

# 26. 執行入口參數

`scripts/run_zhu_walkline_shadow.py` 需支援：

```bash
python scripts/run_zhu_walkline_shadow.py --asof latest
python scripts/run_zhu_walkline_shadow.py --asof 2026-07-08
python scripts/run_zhu_walkline_shadow.py --asof latest --top-n 50
python scripts/run_zhu_walkline_shadow.py --asof latest --stock 6830
python scripts/run_zhu_walkline_shadow.py --asof latest --stock 6274
python scripts/run_zhu_walkline_shadow.py --asof latest --stock 2464
python scripts/run_zhu_walkline_shadow.py --asof latest --use-web
python scripts/run_zhu_walkline_shadow.py --asof latest --no-web
python scripts/run_zhu_walkline_shadow.py --asof latest --use-web --web-max-results 5
python scripts/run_zhu_walkline_shadow.py --asof 2026-07-08 --evaluate-forward
```

參數：

```text
--asof
--top-n
--stock
--use-web
--no-web
--web-max-results
--evaluate-forward
--output-dir
--config
--verbose
```

---

# 27. 程式品質要求

1. Python 3.10+。
2. 使用 pandas、numpy、sqlite3、pyyaml、pyarrow。
3. 可選 requests、beautifulsoup4，但不可強制。
4. 不強制 TA-Lib。
5. 所有路徑集中到 config。
6. 所有核心函數要有 type hints。
7. 所有資料讀取要 logging。
8. 缺欄要 warning。
9. 不可 silent failure。
10. 測試必須能跑。
11. 程式碼模組化。
12. 不要全部塞在一支 script。
13. 盡量避免全域變數。
14. 報告產生器與 scoring 分開。
15. Data loader 與 feature engineering 分開。
16. 網路搜尋與本地資料分開。
17. score 計算要可追溯 reason list。
18. 每檔股票都要有 reason，不可只給分數。

---

# 28. 執行與測試

完成後請執行：

```bash
cd E:\abc
python -m pytest tests/test_zhu_walkline_features.py tests/test_zhu_walkline_no_lookahead.py tests/test_web_research_no_lookahead.py -q
python scripts/run_zhu_walkline_shadow.py --asof latest --top-n 30
```

若要測試網路補充：

```bash
python scripts/run_zhu_walkline_shadow.py --asof latest --top-n 30 --use-web --web-max-results 5
```

若要測試單檔：

```bash
python scripts/run_zhu_walkline_shadow.py --asof latest --stock 6830
```

---

# 29. 最後回報格式

完成後，請在 Codex 回覆中列出：

1. 新增或修改的檔案。
2. 如何執行。
3. 報告輸出位置。
4. 是否找到 SQLite 資料庫。
5. 是否找到 price 資料。
6. 是否找到大盤資料。
7. 是否找到類股資料。
8. 是否找到概念股 mapping。
9. 是否找到法人資料。
10. 是否找到大戶資料。
11. 是否找到融資券資料。
12. 是否啟用網路搜尋。
13. 網路搜尋來源有哪些。
14. 測試結果。
15. 是否有任何資料缺失。
16. 是否有任何 no-lookahead 風險。
17. 明確寫出：

```text
formal_champion_changed=False
formal_trade_effect=False
mode=shadow_advisory_only
web_research_used=True/False
web_research_is_supplementary=True
```

---

# 30. 驗收標準

此任務完成的標準：

1. `python scripts/run_zhu_walkline_shadow.py --asof latest` 可執行。
2. 可輸出 top rise candidates。
3. 可輸出 top fall risks。
4. 可輸出大盤 markdown 報告。
5. 可輸出單檔 markdown 走圖報告。
6. 報告語氣符合「同學式走圖教學」。
7. 報告不冒充任何本人。
8. 大盤狀態納入評分。
9. 類股輪動納入評分。
10. 概念股輪動納入評分。
11. 法人買賣超納入評分。
12. 大戶或主力 proxy 納入評分。
13. 融資券若有資料則納入評分。
14. 融資券若無資料則明確警告。
15. 必要時可啟用網路搜尋。
16. 網路資料只作補充，不主導評分。
17. 網路分數 cap 正確。
18. 無 look-ahead bias。
19. 測試通過。
20. 不修改正式策略。
21. 不修改 formal champion。
22. 不影響正式交易。
23. 不自動下單。
24. 所有輸出皆標示 shadow/advisory only。

---

# 31. 報告最後固定聲明

每份 markdown 報告最後都要寫：

```text
本報告為技術分析教育與 shadow observation，不是投資建議，不是買賣指令。
mode=shadow_advisory_only
formal_champion_changed=False
formal_trade_effect=False
web_research_used=True/False
web_research_is_supplementary=True
```

---

建議存成：

```text
E:\abc\CODEx_ZHU_WALKLINE_SHADOW_TASK.md
```

然後把整份貼給 Codex 執行。
