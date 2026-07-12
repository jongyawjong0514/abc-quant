# OUTBOX

## 2026-07-12 Window Run - 2026-06-01 to 2026-07-09

### 資料與規則
- Local adjusted/features max date: `2026-07-09`; range contains 28 trading days.
- Observation rule: `driver_score >= 11` plus replicated risk-control cap `close_to_sma5_pct <= 12`.
- Signal time: after as-of close; D+20 evaluator uses next-day adjusted open, D+20 adjusted close, fees, tax, and slippage.
- Same-stock 20-day cooldown is an evaluator de-overlap scope, not a trade command.

### 結果
- Source candidates: 2,031.
- `driver_score >= 11`: 117 rows.
- MA5-gap-capped observations: 76 rows, 60 stocks, 9 dates.
- Latest qualifying observation date: `2026-07-02`; 7/3~7/9 had no full-threshold observation.
- Window-local cooldown: 60 rows; mature D+20: 23 rows over only 2 signal dates; one mature row was next-day locked-limit-up.
- Mature 23-row net avg/median: 4.231% / -6.216%; positive mean is driven by a small number of large winners while the median remains negative.
- `maturity_status=insufficient_mature_horizon`; `action=watch_only`; `promotion_decision=blocked_before_promotion_review`.

### 產出
- `reports/zhu_walkline_strategy_window_2026_06_01_07_09/zhu_walkline_window_summary.md`
- `reports/zhu_walkline_strategy_window_2026_06_01_07_09/zhu_walkline_window_summary.json`
- `reports/zhu_walkline_strategy_window_2026_06_01_07_09/zhu_walkline_window_observations.csv`
- `reports/zhu_walkline_strategy_window_2026_06_01_07_09/zhu_walkline_window_date_stock_codes.csv`
- `reports/zhu_walkline_strategy_window_2026_06_01_07_09/zhu_walkline_window_daily_counts.csv`

### 程式修正
- `scripts/backtest_zhu_walkline_driver_screen.py`: empty/short rolling windows now return a stable empty schema instead of failing report rendering.
- `tests/test_zhu_walkline_driver_screen_backtest.py`: added empty rolling schema regression coverage.

### 驗證
- Focused pytest: 4 passed.
- Full `.venv` pytest: 474 passed.
- `ruff check .`: passed.
- `git diff --check`: passed.
- Latest no-web scanner: passed; asof `2026-07-09`.
- Three output directories passed missing-string audit and summary hard-boundary/count assertions.

### 硬邊界
- `mode=shadow_observation_only`
- `formal_champion_changed=False`
- `formal_trade_effect=False`
- no formal strategy modified
- no formal champion modified
- no formal trade effect
- 不產生交易指令
- 不輸出絕對買賣建議

## 2026-07-12 Recommended Follow-Up - Buyability + Backward-OOS

### 修改與執行
- `scripts/experiment_zhu_walkline_strategy.py`: added next-day one-price limit-up evaluator fields, buyable-entry scopes, `BASELINE_EXCLUDE_STRONG_UPTREND`, and prespecified replication reviews.
- `tests/test_zhu_walkline_strategy_experiment.py`: expanded to 15 focused tests covering limit-up positive/negative cases, buyable scope isolation, future evaluator isolation, market-state membership, and four-way replication gates.
- Exported `reports/zhu_walkline_early_observation_labels_2019_2021/`: 56,098 candidates, 1,736 stocks, 731 trading days, 541 non-empty days.
- Wrote `reports/zhu_walkline_strategy_backward_oos_2019_2021/` using 2019 development, 2020 validation, and 2021 locked holdout.

### Backward-OOS 結果
| variant | 2020 primary avg/median/tail delta | 2021 primary avg/median/tail delta | decision |
|---|---|---|---|
| `BASELINE_MA5_GAP_CAP_12` | -0.153 / +0.298 / -0.628 pct | +0.085 / +0.514 / -0.603 pct | `shadow_replication_supported` |
| `BASELINE_EXCLUDE_STRONG_UPTREND` | +0.501 / -0.757 / +0.090 pct | -2.934 / -2.905 / +7.691 pct | `blocked_before_promotion_review` |

- MA5 cap also passed both years after removing next-day one-price limit-up rows. It is a risk-control shadow candidate, not a formal rule or an absolute return enhancer.
- The market-state exclusion did not generalize backward. Its 2025/2026 improvement is regime-dependent and must not become a fixed gate.
- Next-day one-price limit-up rate in the baseline cooldown scope was 1.813% in 2020 and 0.745% in 2021; the separate buyable scope removes those rows without changing signals.
- Current 2022-2026 rerun remains `selected_by_validation=BASELINE_LIQUIDITY_20M`, yearly holdout pass count `0/3`, and `blocked_before_promotion_review`.

### 產出
- `reports/zhu_walkline_strategy_backward_oos_2019_2021/zhu_walkline_strategy_experiment_summary.md`
- `reports/zhu_walkline_strategy_backward_oos_2019_2021/zhu_walkline_strategy_experiment_summary.json`
- `reports/zhu_walkline_strategy_backward_oos_2019_2021/zhu_walkline_strategy_experiment_metrics.csv`
- `reports/zhu_walkline_strategy_experiment_2022_2026_06_10/zhu_walkline_strategy_experiment_summary.md`

### 驗證
- `.\.venv\Scripts\ruff.exe check .`: passed.
- `.\.venv\Scripts\python.exe -m pytest -q`: 473 passed.
- `git diff --check`: passed.
- Latest no-web scanner: passed; asof `2026-07-09`.
- Backward-OOS and current report audits: no `NaN` / `nan` / `None` / `<NA>` output strings; hard-boundary assertions passed.

### 硬邊界
- `mode=shadow_observation_only`
- `formal_champion_changed=False`
- `formal_trade_effect=False`
- no formal strategy modified
- no formal champion modified
- no formal trade effect
- 不產生交易指令
- 不輸出絕對買賣建議

## 2026-07-12 Direct Follow-Up - Full Zhu Walkline Strategy Experiment

## 修改檔案
- `scripts/experiment_zhu_walkline_strategy.py`: added execution-aware finite-variant comparison, same-stock cooldown, adjusted-price/company-action labels, validation-only selection, yearly walk-forward replication, no-op rejection, and failure attribution.
- `tests/test_zhu_walkline_strategy_experiment.py`: added 10 tests for next-open cost labels, future-label isolation, holdout isolation, no-op rejection, missing fields, cooldown, timing attribution, temporal splits, and multi-file loading.
- `scripts/analyze_zhu_walkline_forward_return_buckets.py`: replaced SciPy-dependent Spearman with mathematically equivalent rank-then-Pearson calculation.
- `README.md`, `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: documented the command, evidence, blockers, and hard boundaries.

## 實驗契約
- Market/currency/timezone: Taiwan TWSE/TPEx common stocks, TWD, Asia/Taipei.
- Candidate period: `2022-01-03`~`2026-06-10`, 79,969 as-of candidate rows.
- Signal time: after as-of close.
- Evaluator entry: next trading day adjusted open.
- Evaluator exit: as-of plus 20 trading days adjusted close.
- Costs: brokerage 0.1425% each side, sell tax 0.3%, slippage 0.1% each side.
- Primary evaluation: 20-trading-day same-stock cooldown.
- Company actions: `tw_adjusted_ohlcv_daily`, plus no-event robustness scope.
- Variant selection: validation only; holdout cannot affect selection.

## 主結果
| period | baseline rows | avg net | median net | hit >=20% | downside <0 | tail <=-10% |
|---|---:|---:|---:|---:|---:|---:|
| 2022~2024 development | 1,169 | -1.390% | -2.945% | 6.587% | 61.335% | 25.064% |
| 2025 validation | 471 | 4.955% | 0.868% | 17.410% | 47.771% | 20.595% |
| 2026H1 holdout | 501 | 10.086% | 3.280% | 24.950% | 42.914% | 20.359% |

- 2025 validation selected `BASELINE_LIQUIDITY_20M`.
- 2026H1 holdout: avg 10.475%, median 4.185%, but tail loss rose to 23.472%; holdout failed.
- Yearly folds: 2023 select -> 2024 test selected unchanged baseline; 2024 select -> 2025 test sector-neutral failed; 2025 select -> 2026H1 liquidity failed. Final pass count `0/3`.
- `BASELINE_MA5_GAP_CAP_12` is post-holdout research only: holdout avg delta -0.1225 pct, median delta +0.4499 pct, tail delta -1.2349 pct, coverage 86.63%. It is not eligible for current selection and needs new replication.
- Signal-date `late_chase_risk_flag`, `upper_tail_flag`, and `volume_exhaustion_flag` removed zero baseline rows. These belong in a later peak/holding lifecycle monitor, not the initial screen.
- Highest failure windows include 2024Q4 tail 65.823%, 2024Q3 tail 50.000%, 2022Q1 tail 45.946%, and 2022Q2 tail 44.118%.

## 產出
- `reports/zhu_walkline_strategy_experiment_2022_2026_06_10/zhu_walkline_strategy_experiment_summary.md`
- `reports/zhu_walkline_strategy_experiment_2022_2026_06_10/zhu_walkline_strategy_experiment_summary.json`
- `reports/zhu_walkline_strategy_experiment_2022_2026_06_10/zhu_walkline_strategy_experiment_metrics.csv`
- `reports/zhu_walkline_strategy_experiment_2022_2026_06_10/zhu_walkline_strategy_experiment_quarterly.csv`
- `reports/zhu_walkline_strategy_experiment_2022_2026_06_10/zhu_walkline_strategy_walk_forward_reviews.csv`
- `reports/zhu_walkline_strategy_experiment_2022_2026_06_10/zhu_walkline_strategy_walk_forward_metrics.csv`
- `reports/zhu_walkline_strategy_experiment_2022_2026_06_10/zhu_walkline_strategy_failure_attribution.csv`

## 驗證
- `.\.venv\Scripts\ruff.exe check .`: passed.
- `.\.venv\Scripts\python.exe -m pytest -q`: 468 passed.
- `git diff --check`: passed.
- `python scripts\run_zhu_walkline_shadow.py --asof latest --top-n 30 --no-web --verbose`: passed; latest asof `2026-07-09`.
- Output audit: no `NaN` / `nan` / `None` / `<NA>` strings.

## 結論與邊界
- `promotion_decision=blocked_before_promotion_review`
- `mode=shadow_observation_only`
- `formal_champion_changed=False`
- `formal_trade_effect=False`
- no formal strategy modified
- no formal champion modified
- no formal trade effect
- 不產生交易指令，不輸出絕對買賣建議。

## 2026-07-11 Direct Follow-Up - Driver Screen Overlay And Rolling Backtest

## 修改檔案
- `scripts/backtest_zhu_walkline_driver_screen.py`: added a shadow-only as-of driver screen and rolling backtest sidecar.
- `tests/test_zhu_walkline_driver_screen_backtest.py`: added coverage for no-forward-label scoring, same-count baseline alignment, and shadow summary boundaries.
- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: recorded the overlay, run outputs, validation, and hard boundaries.

## 篩選規則
Default threshold: `driver_score >= 11`.

Score rules:
- `sector == 電子零組件`: +3
- `sector in 光電, 其他電子`: +1
- `early_observation_rule == STRICT_BREAKOUT`: +2
- `volume_state == ATTACK_VOLUME` or `vol_ratio_20/day_volume_ratio_20 >= 1.8`: +2
- `kline_state == ATTACK_RED_K`: +1
- `open_to_close_pct >= 4%` and `close_location_in_bar >= 0.8`: +1
- `close_to_sma5_pct >= 7%`: +1
- `sector_state == SECTOR_LEADING`: +1
- `signal_stage == CONFIRMED` and `fall_risk_score <= 3`: +1
- no sell/failure warning and `review_bucket == CLEAN_REVIEW`: +1

These rules use only as-of fields. Forward returns are evaluator-only labels.

## 回測指令
```powershell
python scripts\backtest_zhu_walkline_driver_screen.py --output-dir reports\zhu_walkline_driver_screen_backtest_2026_01_06 --min-driver-score 11 --horizon-trading-days 20 --rolling-window-days 20
```

## 產出檔案
- `reports/zhu_walkline_driver_screen_backtest_2026_01_06/zhu_walkline_driver_screen_rows.csv`
- `reports/zhu_walkline_driver_screen_backtest_2026_01_06/zhu_walkline_driver_screen_scored_universe.csv`
- `reports/zhu_walkline_driver_screen_backtest_2026_01_06/zhu_walkline_driver_screen_same_count_top_rise.csv`
- `reports/zhu_walkline_driver_screen_backtest_2026_01_06/zhu_walkline_driver_screen_same_count_random.csv`
- `reports/zhu_walkline_driver_screen_backtest_2026_01_06/zhu_walkline_driver_screen_daily_metrics.csv`
- `reports/zhu_walkline_driver_screen_backtest_2026_01_06/zhu_walkline_driver_screen_monthly_metrics.csv`
- `reports/zhu_walkline_driver_screen_backtest_2026_01_06/zhu_walkline_driver_screen_rolling_metrics.csv`
- `reports/zhu_walkline_driver_screen_backtest_2026_01_06/zhu_walkline_driver_screen_summary.json`
- `reports/zhu_walkline_driver_screen_backtest_2026_01_06/zhu_walkline_driver_screen_summary.md`

## 回測摘要
| cohort | rows | avg 20d return | median | hit >=20% | hit >=50% | downside <0 | tail <=-10% |
|---|---:|---:|---:|---:|---:|---:|---:|
| driver_screen | 1,084 | 14.518% | 6.460% | 30.258% | 13.007% | 37.362% | 17.343% |
| all_candidates | 12,060 | 8.209% | 1.852% | 21.824% | 6.219% | 43.897% | 16.625% |
| same_count_top_rise | 1,084 | 8.944% | 2.872% | 20.019% | 6.827% | 40.683% | 13.469% |
| same_count_random | 1,084 | 9.152% | 2.480% | 23.432% | 7.565% | 42.343% | 17.159% |

## 研究結論
- Driver screen 相對 same-count top-rise baseline：平均 20d return +5.574 pct、hit20 +10.240 pct、hit50 +6.181 pct、downside<0 -3.321 pct。
- 主要 blocker：tail-loss<=-10% 為 17.343%，高於 top-rise baseline 13.469%。因此不能 promotion，只能保留為 shadow research overlay。
- 最新 20 交易日 rolling window (`2026-05-07`~`2026-06-10`)：driver_screen 平均 22.478%、hit20 44.095%、hit50 21.654%，仍高於 same-count baselines。

## 硬邊界
- `mode=shadow_observation_only`
- `formal_champion_changed=False`
- `formal_trade_effect=False`
- no formal strategy modified
- no formal champion modified
- no formal trade effect
- 不產生交易指令
- 不輸出絕對買賣建議

## 目前驗證
- Focused Ruff: `.\.venv\Scripts\ruff.exe check scripts\backtest_zhu_walkline_driver_screen.py tests\test_zhu_walkline_driver_screen_backtest.py`，All checks passed。
- Focused tests: `python -m pytest tests\test_zhu_walkline_driver_screen_backtest.py -q`，3 passed。
- Script smoke/backtest completed and wrote all output artifacts.

## 2026-07-11 Direct Follow-Up - Forward Return Bucket Research

## 修改檔案
- `scripts/analyze_zhu_walkline_forward_return_buckets.py`: added a shadow/evaluator-only analysis sidecar that buckets 20-trading-day forward returns and quantifies feature differences, category lift, and reason drivers.
- `tests/test_zhu_walkline_forward_return_bucket_analysis.py`: added bucket-boundary and reason-driver regression tests.
- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: recorded the research output, validation, and hard boundaries.

## 實作摘要
- Input: `reports/zhu_walkline_early_observation_labels_2026_01_06_fwd20p/zhu_walkline_early_observation_candidates.csv`.
- Buckets:
  - `GAIN_21_30`: `20.0 <= forward_return_pct < 31.0`, label shown as `21%-30%`.
  - `GAIN_31_40`: `31.0 <= forward_return_pct < 41.0`.
  - `GAIN_41_50`: `41.0 <= forward_return_pct < 51.0`.
  - `GAIN_GT_50`: `forward_return_pct >= 51.0`.
- The first bucket starts at 20.0 because the prior filter kept rows with `>=20%`; the display label follows the user's 21%-30% wording.
- Daily OHLCV features are joined as-of by `asof_date` and `stock_id`; future return remains evaluator-only.

## 產出檔案
- `reports/zhu_walkline_forward_return_bucket_research_2026_01_06/zhu_walkline_forward_return_bucket_rows.csv`
- `reports/zhu_walkline_forward_return_bucket_research_2026_01_06/zhu_walkline_forward_return_bucket_summary.csv`
- `reports/zhu_walkline_forward_return_bucket_research_2026_01_06/zhu_walkline_forward_return_numeric_features.csv`
- `reports/zhu_walkline_forward_return_bucket_research_2026_01_06/zhu_walkline_forward_return_category_lift.csv`
- `reports/zhu_walkline_forward_return_bucket_research_2026_01_06/zhu_walkline_forward_return_reason_drivers.csv`
- `reports/zhu_walkline_forward_return_bucket_research_2026_01_06/zhu_walkline_forward_return_bucket_summary.json`
- `reports/zhu_walkline_forward_return_bucket_research_2026_01_06/zhu_walkline_forward_return_bucket_summary.md`

## 量化摘要
- Total bucketed rows: 2,632
- Unique stocks: 523
- Date count: 76
- `21%-30%`: 988 rows, avg forward return 25.0671%, median 24.8540%
- `31%-40%`: 560 rows, avg forward return 35.4777%, median 35.1351%
- `41%-50%`: 366 rows, avg forward return 45.5872%, median 45.3901%
- `>50%`: 718 rows, avg forward return 74.6827%, median 67.1007%

## 初步大漲原因歸因
- `>50%` bucket 的主要類別驅動是 `sector=電子零組件`: 288 rows, bucket share 40.11%, all share 29.41%, lift 1.364。
- `>50%` bucket 的數值驅動較分散，偏向較高短均乖離、較強當日紅K與較高量比：`open_to_close_pct` 平均 4.48% vs all 4.13%，`vol_ratio_20` 1.874 vs all 1.774，`attack_volume_share` 60.86% vs all 58.13%。
- `41%-50%` bucket 類股 lift 偏向 `光電`: bucket share 12.57%, all share 8.62%, lift 1.457。
- `31%-40%` bucket 類股 lift 偏向 `電機機械`、`電子通路`、`通信網路`。
- `21%-30%` bucket 較常見 `金融保險` 與風險警示/供給壓力標籤；平均 fall risk score 1.579，高於其他三桶。

## 硬邊界
- `mode=shadow_observation_only`
- `formal_champion_changed=False`
- `formal_trade_effect=False`
- no formal strategy modified
- no formal champion modified
- no formal trade effect
- 不產生交易指令
- 不輸出絕對買賣建議

## 目前驗證
- Focused Ruff: `.\.venv\Scripts\ruff.exe check scripts\analyze_zhu_walkline_forward_return_buckets.py tests\test_zhu_walkline_forward_return_bucket_analysis.py`，All checks passed。
- Focused tests: `python -m pytest tests\test_zhu_walkline_forward_return_bucket_analysis.py -q`，2 passed。
- Analysis command: `python scripts\analyze_zhu_walkline_forward_return_buckets.py --output-dir reports\zhu_walkline_forward_return_bucket_research_2026_01_06 --min-category-count 8` completed.
- Output audit: no `NaN`/`nan`/`None`/`<NA>` output strings.

## 2026-07-11 Direct Follow-Up - Forward 20 Trading Day Return Filter

## 修改檔案
- `scripts/export_zhu_walkline_early_observation_candidates.py`: added evaluator-only `forward_close_date`, `forward_close`, and `forward_return_pct` labels plus `--min-forward-return-pct`, `--forward-return-trading-days`, and `--include-forward-return-labels`.
- `tests/test_zhu_walkline_early_observation_export.py`: added coverage that candidates below the forward-return threshold or missing the future close are removed from the filtered sidecar.
- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: recorded the filter, output path, validation, and formal-boundary guarantees.

## 實作摘要
- This filter is a manual-label/backtest sidecar only. It uses future close data after candidate selection and must not be treated as an as-of selection rule.
- User-requested rule: keep only rows where the close 20 trading days later is at least 20% above the as-of close.
- Rows without enough future price history are removed from the filtered output because the one-month outcome cannot be confirmed.
- Daily counts now preserve `candidate_count_before_forward_return_filter` and replace `candidate_count` with the final filtered count.

## 區間輸出
- Command: `python scripts/export_zhu_walkline_early_observation_candidates.py --engine fast --start-date 2026-01-01 --end-date 2026-06-30 --max-per-day 0 --min-forward-return-pct 20 --forward-return-trading-days 20 --output-dir reports/zhu_walkline_early_observation_labels_2026_01_06_fwd20p --verbose`
- Output directory: `reports/zhu_walkline_early_observation_labels_2026_01_06_fwd20p/`
- Candidate rows before filter: 13,116
- Missing forward-return rows: 1,056
- Rows removed by forward-return filter: 10,484
- Final candidate rows: 2,632
- Unique stocks: 523
- Non-empty days: 76
- `forward_return_pct < 20`: 0
- Missing final forward return: 0

## 硬邊界
- `mode=shadow_observation_only`
- `formal_champion_changed=False`
- `formal_trade_effect=False`
- no formal strategy modified
- no formal champion modified
- no formal trade effect
- 不產生交易指令
- 不輸出絕對買賣建議

## 目前驗證
- Focused Ruff: `.\.venv\Scripts\ruff.exe check scripts\export_zhu_walkline_early_observation_candidates.py tests\test_zhu_walkline_early_observation_export.py`，All checks passed。
- Focused tests: `python -m pytest tests\test_zhu_walkline_early_observation_export.py -q`，6 passed。
- Output audit: filtered CSV has zero below-threshold rows, zero missing forward returns, and no `NaN`/`nan`/`None`/`<NA>` output strings.

## 2026-07-11 Direct Follow-Up - Zhu Walkline Early Observation Manual Labels

## 修改檔案
- `scripts/export_zhu_walkline_early_observation_candidates.py`: added a shadow-only early-observation label export sidecar with exact scanner mode and fast precomputed daily-OHLCV mode.
- `tests/test_zhu_walkline_early_observation_export.py`: added selector coverage plus a no-lookahead regression that mutating future rows after `end_date` does not affect fast observation fields.
- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: recorded the sidecar, run outputs, validation, and hard boundaries.

## 實作摘要
- The sidecar exports early observation rows for manual labeling only; it does not create orders, positions, holdings, portfolio weights, or formal strategy state.
- Rule layers are `STRICT_BREAKOUT`, `STRICT_SUPPORT_TURN`, `AGGRESSIVE_MA_RECLAIM_REVIEW`, `AGGRESSIVE_BREAKOUT_REVIEW`, and `AGGRESSIVE_SUPPORT_REVIEW`.
- Candidate rows must satisfy `close > ma20`, `ma20_slope > 0`, and `close > ma120`; rows below the monthly line, below the half-year line, or with a non-positive monthly-line slope are removed.
- Fast mode default lookback is 260 calendar days so the 120-day moving average can be computed for early-2026 labels.
- Fast mode uses only local `daily_ohlcv_features` rows up to the requested end date plus rolling historical highs/lows, moving averages, volume ratio, market breadth, and sector rank approximations.
- Fast mode defaults to excluding `00xx` ETF-like tickers; use `--include-etf-like` to include them.
- Output includes `zhu_walkline_early_observation_date_stock_codes.csv` for direct user relabeling.

## 區間輸出
- Command: `python scripts/export_zhu_walkline_early_observation_candidates.py --engine fast --start-date 2026-01-01 --end-date 2026-06-30 --max-per-day 0 --output-dir reports/zhu_walkline_early_observation_labels_2026_01_06 --verbose`
- Output directory: `reports/zhu_walkline_early_observation_labels_2026_01_06/`
- Resolved dates: `2026-01-02`~`2026-06-30`
- Trading days: 116
- Candidate rows: 13,116
- Unique stocks: 1,433
- Non-empty days: 90
- `include_etf_like=false`
- Output audit: no `close<=ma20` rows, no `ma20_slope<=0` rows, no `close<=ma120` rows, and no missing `ma20/ma20_slope/ma120`.

## 測試方式
- `.\.venv\Scripts\ruff.exe check scripts\export_zhu_walkline_early_observation_candidates.py tests\test_zhu_walkline_early_observation_export.py`
- `python -m pytest tests\test_zhu_walkline_early_observation_export.py -q`
- `python scripts\export_zhu_walkline_early_observation_candidates.py --engine fast --start-date 2026-01-01 --end-date 2026-06-30 --max-per-day 0 --output-dir reports\zhu_walkline_early_observation_labels_2026_01_06 --verbose`
- `rg -n "NaN|nan|None|<NA>" reports\zhu_walkline_early_observation_labels_2026_01_06`

## 測試結果
- Focused `ruff check`: passed.
- Focused pytest: 5 passed.
- Jan-Jun fast export completed and wrote candidate, label todo, date/stock code, daily-count, summary JSON, and summary Markdown outputs.
- Output grep found no `NaN`/`nan`/`None`/`<NA>` strings.

## 邊界
- `mode=shadow_observation_only`.
- `formal_champion_changed=False`.
- `formal_trade_effect=False`.
- no formal strategy modified.
- no formal champion modified.
- no formal trade effect.
- No trade instructions, orders, holdings, weights, or formal promotion.

## 2026-07-10 Direct Follow-Up - Zhu Walkline Report Tone Spec

## 修改檔案
- `CODEx_WALKLINE_REPORT_TONE_SPEC.md`: saved the attached walkline teaching-style tone specification.
- `src/abc_quant/reports/zhu_walkline_report.py`: rewrote the single-stock Markdown report into the fixed walkline teaching order and observation-only wording.
- `tests/test_zhu_walkline_features.py`: added regression checks for report section order, scenario order, observation language, and banned deterministic trading phrases.
- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: recorded this follow-up and hard boundaries.

## 實作摘要
- Single-stock reports now use the fixed section order: conclusion, trend, moving averages, K-bar, volume, institutional chips, big-holder/main-force proxy, margin/short data, support/resistance, tomorrow scenarios, non-holder view, holder view, and one-line summary.
- Scenario order is fixed as `劇本A：轉強`, `劇本B：整理`, `劇本C：續弱`.
- Reports use teaching-style observation language: observation price, defense point, signal invalidation, support/resistance, and confirmation watch price.
- The runtime fixed statement remains `本報告為技術分析教育與 shadow observation，不是投資建議，不是買賣指令。`
- The attached spec's example `mode=shadow_advisory_only` is preserved in the spec file only; generated runtime reports remain hard-locked to `mode=shadow_observation_only`.

## 測試方式
- `.\.venv\Scripts\ruff.exe check src\abc_quant\reports\zhu_walkline_report.py tests\test_zhu_walkline_features.py`
- `python -m pytest tests/test_zhu_walkline_features.py::test_reports_use_observation_language_not_trade_commands -q`

## 測試結果
- Focused `ruff check`: passed.
- Focused report-language pytest: 1 passed.

## 邊界
- `mode=shadow_observation_only`.
- `formal_champion_changed=False`.
- `formal_trade_effect=False`.
- no formal strategy modified.
- no formal champion modified.
- no formal trade effect.
- No trade instructions, orders, holdings, weights, or formal promotion.

## 2026-07-10 Direct Follow-Up - Zhu Walkline Range Backtest Metric Review Fix

## 修改檔案
- `src/abc_quant/signals/zhu_walkline_shadow.py`: fixed forward evaluator incomplete-horizon hits so missing future rows stay missing instead of counting as misses.
- `scripts/backtest_zhu_walkline_shadow_range.py`: added row-weighted metrics, daily equal-weighted metrics, horizon completeness, baseline metrics, excess vs baseline, monthly metrics, fixed-seed random same-count baselines, score-decile baselines, and fall downside/adverse-rally semantics.
- `tests/test_zhu_walkline_features.py`: added incomplete-horizon regression coverage.
- `tests/test_zhu_walkline_range_backtest.py`: added sidecar summary, monthly semantics, and baseline regression coverage.
- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: recorded review fix, validation, and hard boundaries.

## 實作摘要
- Missing future rows now produce `future_return_dN` missing and `hit_dN` missing; hit-rate helpers drop missing rows.
- Summary JSON now exposes `daily_equal_weighted_metrics`, `row_weighted_metrics`, `valid_row_count_by_horizon`, `baseline_metrics`, `excess_vs_baseline`, `monthly_preview`, `baseline_rows`, `monthly_rows`, and `max_future_date_used`.
- Range sidecar now writes `zhu_walkline_range_baseline_metrics.csv` and `zhu_walkline_range_monthly_metrics.csv`.
- Fall-risk D5 semantics are split into `fall_tail_down_rate_d5` and `fall_adverse_rally_rate_d5`; rise keeps `rise_tail_loss_rate_d5`.
- Baselines are all-market, fixed-seed random same-count, and score-decile groups, all observation-only.

## 回測輸出
- Command: `python scripts/backtest_zhu_walkline_shadow_range.py --start-date 2026-01-01 --end-date 2026-05-31 --top-n 30 --future-calendar-days 25 --output-dir reports/zhu_walkline_shadow_backtest_2026_01_05 --verbose`
- Output directory: `reports/zhu_walkline_shadow_backtest_2026_01_05/`
- Resolved dates: `2026-01-02`~`2026-05-29`
- Trading days: 95
- Evaluation rows: 5,368
- Baseline rows: 2,280
- Monthly rows: 10
- `max_future_date_used=2026-06-23`
- Row-weighted D5 rise: hit 0.529833, average return 0.028668, median return 0.008547, valid/missing 2514/4.
- Row-weighted D5 fall-risk: correct 0.520924, average forward return 0.004332, median -0.002999, valid/missing 2772/78.
- Fall-risk D5 downside rate: 0.246032.
- Fall-risk D5 adverse rally rate: 0.229437.

## 測試方式
- `.\.venv\Scripts\ruff.exe check .`
- `python -m pytest -q`
- `git diff --check`
- `python scripts/run_zhu_walkline_shadow.py --asof latest --top-n 30 --no-web --verbose`
- `python scripts/backtest_zhu_walkline_shadow_range.py --start-date 2026-01-01 --end-date 2026-05-31 --top-n 30 --future-calendar-days 25 --output-dir reports/zhu_walkline_shadow_backtest_2026_01_05 --verbose`
- `rg -n "NaN|nan|None|<NA>" reports/zhu_walkline_shadow_backtest_2026_01_05`

## 測試結果
- `ruff check .`: passed.
- Full pytest: 445 passed in 38.41s.
- `git diff --check`: passed.
- Latest no-web scanner passed and wrote asof `2026-07-09` outputs.
- Jan-May range backtest completed with empty stderr and wrote evaluation, daily, baseline, monthly, summary JSON, and summary Markdown files.
- Output grep found no `NaN`/`nan`/`None`/`<NA>` strings.

## 邊界
- `mode=shadow_observation_only`.
- `formal_champion_changed=False`.
- `formal_trade_effect=False`.
- no formal strategy modified.
- no formal champion modified.
- no formal trade effect.
- No trade instructions, orders, holdings, weights, or formal promotion.

## 2026-07-09 Direct Follow-Up - Zhu Walkline Support And Resistance Zones

## 修改檔案
- `src/abc_quant/features/walkline_features.py`: added support/resistance zone clustering, zone source features, support-hold/fail flags, resistance-breakout/failure flags, and de-fragmented the feature pipeline to keep scanner CLI output clean.
- `src/abc_quant/signals/zhu_walkline_shadow.py`: made invalid/confirm prices use support-zone lower bound and resistance-zone upper bound, and linked support-zone failure / resistance false-breakout into failure tagging.
- `src/abc_quant/reports/zhu_walkline_report.py`: added zone columns to CSV/shadow-log outputs, structured zone records to summary JSON, and zone wording in the stock Markdown report.
- `tests/test_zhu_walkline_features.py`: added zone clustering and required zone field coverage.
- `tests/test_zhu_walkline_no_lookahead.py`: extended future-row invariance checks to zone lows/highs/labels and support/breakout flags.
- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: recorded this follow-up and validation evidence.

## 實作摘要
- Support/resistance is no longer treated as only a single price. Nearby levels within 1.5% are merged into zones.
- Support sources include previous low, 3/5/20/60-day lows, 5/10/20/60-day moving averages, high-volume red-K lows, long-lower-shadow lows, gap-up support, and round-number support.
- Resistance sources include previous high, 3/5/20/60-day highs, 5/10/20/60-day moving averages, high-volume black-K highs, long-upper-shadow highs, gap-down resistance, and round-number resistance.
- Added `support_zone_holding_today`, `support_zone_failed_today`, `resistance_zone_breakout_today`, and `resistance_zone_breakout_failed_today`.
- Added zone labels and structured zone records to reports so explanations can say "支撐區" / "壓力區" instead of pretending a single price is magic.
- Legacy `support_1/support_2/resistance_1/resistance_2` columns remain for compatibility.

## 測試方式
- `.\.venv\Scripts\ruff.exe check src\abc_quant\features\walkline_features.py src\abc_quant\signals\zhu_walkline_shadow.py src\abc_quant\reports\zhu_walkline_report.py tests\test_zhu_walkline_features.py tests\test_zhu_walkline_no_lookahead.py`
- `.\.venv\Scripts\python.exe -m pytest tests/test_zhu_walkline_features.py tests/test_zhu_walkline_no_lookahead.py tests/test_web_research_no_lookahead.py -q`
- `.\.venv\Scripts\python.exe scripts\run_zhu_walkline_shadow.py --asof latest --top-n 30 --no-web --verbose`

## 測試結果
- Full `ruff check .`: passed.
- Focused Zhu/no-lookahead/web tests: 11 passed.
- Full pytest: 424 passed in 29.28s.
- `git diff --check`: passed.
- Latest no-web scanner smoke passed without pandas fragmentation warnings and wrote asof `2026-07-09` outputs with zone fields in `latest_zhu_walkline_shadow_log.csv`, summary JSON, and stock report.

## 邊界
- `mode=shadow_observation_only`.
- `formal_champion_changed=False`.
- `formal_trade_effect=False`.
- This follow-up does not modify formal champion, formal strategy, weights, orders, positions, or trade instructions.
- Web research remains supplementary and was disabled for the validation smoke (`--no-web`).

## 2026-07-09 Direct Follow-Up - Zhu Walkline Signal Discipline

## 修改檔案
- `config/zhu_walkline_shadow.yaml`: changed default mode to `shadow_observation_only`.
- `src/abc_quant/signals/zhu_walkline_shadow.py`: added bullish watchlist alias, signal lifecycle fields, failure taxonomy, market grade caps, high-level supply pressure, institutional divergence, and margin crowding risk.
- `src/abc_quant/reports/zhu_walkline_report.py`: added `top_bullish_watchlist` CSV/summary output, shadow log CSV, signal/failure columns, and fixed non-holder/holder discipline report text.
- `tests/test_zhu_walkline_features.py`: added regression coverage for shadow mode, required signal fields, market grade caps, and failure-type tagging.
- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: recorded this follow-up and validation evidence.

## 實作摘要
- Renamed the primary bullish output contract to `top_bullish_watchlist` while keeping `top_rise_candidates` as a legacy-compatible alias.
- Added `signal_stage`, `trigger_type`, `invalid_price`, `confirm_price`, `failure_type`, and `reversal_state` to feature/report outputs.
- Added SETUP/TRIGGER/CONFIRMED/FAILED signal staging and trigger labels for MA reclaim, previous-high break, range breakout, bottom reversal, and pullback restart.
- Added hard market-state caps: weak rebound caps bullish grade at B, downtrend caps at C, high-risk breakdown suppresses A/B bullish candidates.
- Added high-level supply-pressure detection for near-60-day-high, high-volume, long-upper-shadow bars that fail to close near the high.
- Added failure tags for institutional buy/price weakness divergence, margin crowding under MA20/support, support break, no-volume follow-through, market drag, sector rotation out, supply pressure, and false breakout.
- Added fixed report language for `未持有者` and `已持有者` with observation/confirmation/defense/stop conditions.
- Added `latest_zhu_walkline_shadow_log.csv` to archive why candidates failed, not only their rank.

## 測試方式
- `.\.venv\Scripts\ruff.exe check .`
- `.\.venv\Scripts\python.exe -m pytest tests/test_zhu_walkline_features.py tests/test_zhu_walkline_no_lookahead.py tests/test_web_research_no_lookahead.py -q`
- `.\.venv\Scripts\python.exe -m pytest -q`
- `.\.venv\Scripts\python.exe scripts\run_zhu_walkline_shadow.py --asof latest --top-n 30 --no-web --verbose`

## 測試結果
- `ruff check .`: passed.
- Focused Zhu walkline tests: 10 passed.
- Full pytest: 423 passed in 29.38s.
- Latest no-web scanner smoke passed and wrote asof `2026-07-08` outputs including `latest_zhu_walkline_top_bullish_watchlist.csv`, legacy `latest_zhu_walkline_top_rise_candidates.csv`, `latest_zhu_walkline_shadow_log.csv`, summary JSON, market report, stock report, and data-quality report.

## 邊界
- `mode=shadow_observation_only`.
- `formal_champion_changed=False`.
- `formal_trade_effect=False`.
- This follow-up does not modify formal champion, formal strategy, weights, orders, positions, or trade instructions.
- Web research remains supplementary and was disabled for the validation smoke (`--no-web`).

## 2026-07-09 Closed-Loop Task 055 - Walk-Forward Constant-Baseline Evaluation Smoke Diagnostics

## 修改檔案
- `src/abc_quant/pipeline/walk_forward_baseline.py`: added deterministic walk-forward constant-baseline evaluation diagnostics, constants, and summary validator.
- `src/abc_quant/pipeline/__init__.py`: exported the walk-forward baseline diagnostics helper, validator, and key constants from `abc_quant.pipeline`.
- `tests/test_pipeline_walk_forward_baseline.py`: added deterministic output, key-order, row-count, method, train-only baseline, train-only scaler, missing-label drop, validator failure, JSON-friendly, forbidden-key, and no-LightGBM-runtime coverage.
- `README.md`: documented the walk-forward constant-baseline smoke diagnostic and its diagnostics-only boundary.
- `docs/modeling.md`: documented the helper flow, summary constants, validator, and safety boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 055 progress and completion evidence.
- `INBOX.md`: reset the active Task 055 block to the commented empty template before PR handoff.

## 實作摘要
- Added `run_walk_forward_baseline_smoke(...)`.
- Added `validate_walk_forward_baseline_smoke_summary(...)`.
- Added summary key, plan key, window key, split key, metric key, index-range key, and forbidden-key constants.
- Default plan uses 18 feature-complete smoke observations, `min_train_size=4`, `validation_size=2`, `test_size=2`, default `step_size=test_size`, and `max_windows=3` so default train/validation/test metrics remain computable before the smoke label tail.
- Each window converts walk-forward positional indices into the existing scaler-compatible split object, fits scaler statistics only from that window's train rows, transforms train/validation/test features, builds the supervised dataset with existing label-drop behavior, fits the existing constant baseline from train labels only, builds a split prediction bundle, and evaluates train/validation/test predictions.
- Summary output is JSON-friendly diagnostics only: observation count, feature columns, label column, baseline method, plan metadata, per-window index ranges, split counts before/after label drop, dropped label counts, scaler feature count, baseline value, training label count, and split evaluation metrics.
- Existing walk-forward split, supervised diagnostics, LightGBM diagnostics/evaluation, CLI, and packaged command outputs were not changed.

## 測試方式
- `python -m pytest tests\test_pipeline_walk_forward_baseline.py`
- `python -m pytest tests\test_pipeline_walk_forward_diagnostics.py tests\test_pipeline_walk_forward_baseline.py`
- `.\.venv\Scripts\python.exe -m ruff check .`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `.\.venv\Scripts\python.exe -m abc_quant.cli.lightgbm_dependency_smoke --indent 2`
- `.\.venv\Scripts\abc-quant-lightgbm-dependency-smoke.exe --indent 2`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused walk-forward baseline diagnostics tests: 9 passed in 1.82s.
- Related walk-forward diagnostics tests: 17 passed in 2.53s.
- `ruff check .`: passed.
- `pytest`: 413 passed in 28.10s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Module dependency-smoke execution: passed with project `.venv` Python and printed sorted indented JSON.
- Packaged dependency-smoke execution: passed with project `.venv` console script and printed sorted indented JSON.
- Bare `abc-quant-lightgbm-dependency-smoke --indent 2`: not recognized in this shell because the project `.venv\Scripts` directory is not on PATH.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task adds constant-baseline evaluation diagnostics only. It does not perform walk-forward model comparison, model selection, LightGBM invocation, strategy logic, allocation logic, performance curves, orders, positions, or simulations.
- The helper uses deterministic in-memory smoke data only and does not add real data adapters.
- The default `max_windows=3` intentionally avoids the synthetic forward-label tail so every default split can produce train/validation/test metrics.

## 建議下一步
- Open a draft PR for ChatGPT Pro Tech Lead fast review, then let GitHub Actions verify Python 3.11 / 3.12 CI.
- A later bounded task can add a walk-forward LightGBM evaluation diagnostic behind the optional dependency guard without adding model selection or strategy behavior.

## 2026-07-08 Closed-Loop Task 053 - Walk-Forward Supervised Dataset Smoke Diagnostics

## 修改檔案
- `src/abc_quant/pipeline/walk_forward_diagnostics.py`: added deterministic walk-forward supervised dataset diagnostics, constants, and summary validator.
- `src/abc_quant/pipeline/__init__.py`: exported the walk-forward supervised diagnostics helper, validator, and key constants from `abc_quant.pipeline`.
- `tests/test_pipeline_walk_forward_diagnostics.py`: added deterministic summary, key-order, row-count, train-only scaler, missing-label drop, validator failure, JSON-friendly, forbidden-key, and no-LightGBM-runtime coverage.
- `README.md`: documented the walk-forward supervised dataset smoke diagnostic and its diagnostics-only boundary.
- `docs/modeling.md`: documented the helper flow, summary constants, validator, and safety boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 053 progress and completion evidence.
- `INBOX.md`: reset the active Task 053 block to the commented empty template before PR handoff.

## 實作摘要
- Added `run_walk_forward_supervised_smoke(...)`.
- Added `validate_walk_forward_supervised_smoke_summary(...)`.
- Added summary key, plan key, window key, split key, index-range key, and forbidden-key constants.
- Default plan uses 18 feature-complete smoke observations, `min_train_size=4`, `validation_size=2`, `test_size=2`, and default `step_size=test_size`, producing 6 deterministic windows.
- Each window converts walk-forward positional indices into the existing scaler-compatible split object, fits scaler statistics only from that window's train rows, transforms train/validation/test, then builds the supervised split dataset with existing missing-label drop behavior.
- Summary output is JSON-friendly metadata only: observation count, feature columns, label column, plan metadata, per-window index ranges, split counts before/after label drop, dropped label counts, and scaler feature count.
- The helper does not emit raw feature values, raw labels, predictions, model metadata, evaluation metrics, downstream choice artifacts, strategy outputs, allocation outputs, performance curves, orders, positions, or simulation outputs.
- Existing temporal split, supervised dataset, LightGBM diagnostics/evaluation, CLI, and packaged command outputs were not changed.

## 測試方式
- `python -m pytest tests\test_pipeline_walk_forward_diagnostics.py`
- `python -m pytest tests\test_validation_walk_forward.py tests\test_pipeline_walk_forward_diagnostics.py`
- `.\.venv\Scripts\python.exe -m ruff check .`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `.\.venv\Scripts\python.exe -m abc_quant.cli.lightgbm_dependency_smoke --indent 2`
- `.\.venv\Scripts\abc-quant-lightgbm-dependency-smoke.exe --indent 2`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused walk-forward supervised diagnostics tests: 8 passed in 1.94s.
- Related walk-forward tests: 26 passed in 1.80s.
- `ruff check .`: passed.
- `pytest`: 404 passed in 32.80s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Module dependency-smoke execution: passed with project `.venv` Python and printed sorted indented JSON.
- Packaged dependency-smoke execution: passed with project `.venv` console script and printed sorted indented JSON.
- Bare `abc-quant-lightgbm-dependency-smoke --indent 2`: not recognized in this shell because the project `.venv\Scripts` directory is not on PATH.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task adds supervised data diagnostics only. It does not perform walk-forward model evaluation, LightGBM invocation, model comparison, model ranking, strategy logic, allocation logic, performance curves, orders, positions, or simulations.
- The helper uses deterministic in-memory smoke data only and does not add real data adapters.
- The summary intentionally excludes scaler means/stds; train-only behavior is covered by tests that spy on fitted scaler metadata.

## 建議下一步
- Open a draft PR for ChatGPT Pro Tech Lead fast review, then let GitHub Actions verify Python 3.11 / 3.12 CI.
- A later bounded task can add a walk-forward model-evaluation diagnostic that consumes the per-window supervised data contract without adding strategy or backtest behavior.

## 2026-07-08 Closed-Loop Task 052 - Deterministic Walk-Forward Split Contract

## 修改檔案
- `src/abc_quant/validation/walk_forward.py`: added frozen walk-forward window/plan dataclasses, deterministic split-plan builder, validator, and forbidden-key constants.
- `src/abc_quant/validation/__init__.py`: exported the walk-forward dataclasses, builder, and validator from `abc_quant.validation`.
- `tests/test_validation_walk_forward.py`: added exact deterministic window tests, default step-size coverage, max-window truncation, invalid configuration coverage, validator malformed-plan coverage, JSON-friendly rejection, and forbidden-key checks.
- `README.md`: documented the walk-forward split contract as a pre-modeling split plan only.
- `docs/modeling.md`: documented builder behavior, validator behavior, and the no-model/no-backtest boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 052 progress and completion evidence.
- `INBOX.md`: reset the active Task 052 block to the commented empty template before PR handoff.

## 實作摘要
- Added `WalkForwardWindow`.
- Added `WalkForwardSplitPlan`.
- Added `build_walk_forward_split_plan(...)`.
- Added `validate_walk_forward_split_plan(...)`.
- Builder uses integer observation positions only.
- Default `step_size` equals `test_size`.
- Generated windows are deterministic and ordered by ascending `window_id`.
- Each generated window is contiguous with train before validation before test.
- Train expands from position 0 while validation/test roll forward by `step_size`.
- Builder stops before validation/test positions exceed `observation_count`.
- Validator rejects non-plan inputs, empty windows, duplicate/out-of-order ids, non-contiguous indices, overlapping indices, out-of-bounds indices, invalid sizes, and non-JSON-friendly values.
- No existing `build_temporal_split(...)`, LightGBM diagnostics/evaluation, model fitting, model comparison, strategy, allocation, performance, order, position, or simulation behavior was changed.

## 測試方式
- `python -m pytest tests\test_validation_walk_forward.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `.\.venv\Scripts\python.exe -m ruff check .`
- `.\.venv\Scripts\python.exe -m abc_quant.cli.lightgbm_dependency_smoke --indent 2`
- `.\.venv\Scripts\abc-quant-lightgbm-dependency-smoke.exe --indent 2`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused walk-forward validation tests: 18 passed in 0.91s.
- `pytest`: 396 passed in 26.68s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Local `.venv` ruff: passed.
- Module dependency-smoke execution: passed with project `.venv` Python and printed sorted indented JSON.
- Packaged dependency-smoke execution: passed with project `.venv` console script and printed sorted indented JSON.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task adds split contracts only. It does not wire walk-forward plans into model evaluation, LightGBM evaluation, model comparison, strategy logic, allocation logic, performance curves, orders, positions, or simulation engines.
- The builder operates on integer observation counts and does not consume date metadata directly.

## 建議下一步
- Open a draft PR for ChatGPT Pro Tech Lead fast review, then let GitHub Actions verify Python 3.11 / 3.12 CI.
- A later bounded task can wire this split plan into model evaluation diagnostics without adding strategy or backtest behavior.

## 2026-07-07 Closed-Loop Task 051 - Optional LightGBM Evaluation Smoke Diagnostics

## 修改檔案
- `src/abc_quant/pipeline/lightgbm_evaluation.py`: added optional LightGBM evaluation smoke diagnostics, fixed summary constants, summary validator, deterministic supervised smoke dataset wiring, and opt-in train-only LightGBM evaluation.
- `src/abc_quant/pipeline/__init__.py`: exported the LightGBM evaluation smoke helper, constants, and validator from `abc_quant.pipeline`.
- `tests/test_pipeline_lightgbm_evaluation.py`: added default no-fit, unavailable explicit-fit, fake-LightGBM opt-in fit, holdout-label non-leakage, validator failure, JSON-friendly, and forbidden-key coverage.
- `docs/modeling.md`: documented the LightGBM evaluation smoke diagnostics contract and opt-in fitting boundary.
- `README.md`: documented the optional LightGBM evaluation smoke helper and no-default-fit behavior.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 051 progress and completion evidence.
- `INBOX.md`: reset the active Task 051 block to the commented empty template before PR handoff.

## 實作摘要
- Added `run_lightgbm_evaluation_smoke(fitting_enabled: bool = False)`.
- Default execution returns dependency/default-parameter diagnostics only and leaves `evaluation` as `None`.
- Default execution does not call `require_lightgbm()` or `fit_lightgbm_regressor(...)`.
- `fitting_enabled=True` with unavailable LightGBM returns a JSON-friendly unavailable summary instead of crashing.
- `fitting_enabled=True` with a fake LightGBM-compatible module builds the deterministic smoke supervised dataset, fits through existing train-only `fit_lightgbm_regressor(...)`, and evaluates the resulting prediction bundle.
- Added `validate_lightgbm_evaluation_smoke_summary(...)` plus summary/default-parameter/split/evaluation/forbidden-key constants.
- The validator rejects non-dict summaries, missing/extra keys, malformed `default_params`, malformed evaluation metrics, non-JSON-friendly values, and forbidden nested keys.
- The fitted summary includes model metadata, feature columns, training row count, default params, and train/validation/test evaluation metrics.
- The summary does not include raw predictions, raw labels, model-selection/ranking/winner/decision fields, strategy/allocation/performance/order/position fields, or simulation outputs.

## 測試方式
- `python -m pytest tests\test_pipeline_lightgbm_evaluation.py`
- `python -m pytest tests\test_models_lightgbm.py tests\test_pipeline_lightgbm_diagnostics.py tests\test_pipeline_lightgbm_evaluation.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `.\.venv\Scripts\python.exe -m ruff check .`
- `.\.venv\Scripts\python.exe -m abc_quant.cli.lightgbm_dependency_smoke --indent 2`
- `.\.venv\Scripts\abc-quant-lightgbm-dependency-smoke.exe --indent 2`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused LightGBM evaluation smoke tests: 7 passed in 4.25s.
- Related LightGBM model/diagnostics/evaluation tests: 49 passed in 1.49s.
- `pytest`: 378 passed in 27.46s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Local `.venv` ruff: passed.
- Module dependency-smoke execution: passed with project `.venv` Python and printed sorted indented JSON.
- Packaged dependency-smoke execution: passed with project `.venv` console script and printed sorted indented JSON.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task adds a pipeline helper, not a new CLI or packaged command for LightGBM evaluation smoke.
- Real LightGBM package execution is not required for default diagnostics and was not used in local validation; opt-in fitting behavior is covered with a fake LightGBM-compatible module.
- The helper uses deterministic fixture data only. It does not add real data adapters, walk-forward validation, model explanation, ablation, strategy logic, allocation logic, performance curves, orders, positions, or simulation engines.

## 建議下一步
- Open a draft PR for ChatGPT Pro Tech Lead fast review, then let GitHub Actions verify Python 3.11 / 3.12 CI.

## 2026-07-07 Closed-Loop Task 050 - LightGBM Dependency Smoke Summary Contract Package Exports

## 修改檔案
- `src/abc_quant/pipeline/__init__.py`: exported the LightGBM dependency smoke summary/default-parameter/forbidden-key constants and validator from `abc_quant.pipeline`, and added the symbols to `__all__`.
- `tests/test_pipeline_lightgbm_diagnostics_exports.py`: added export identity, `__all__`, key-order, exported validator, extra-key rejection, and no-real-LightGBM import tests.
- `docs/modeling.md`: documented the public `abc_quant.pipeline` imports for the LightGBM dependency smoke summary contract.
- `README.md`: documented that callers can import the contract constants and validator from `abc_quant.pipeline`.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 050 progress and completion evidence.
- `INBOX.md`: reset the active Task 050 block to the commented empty template before PR handoff.

## 實作摘要
- Re-exported `LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS`.
- Re-exported `LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS`.
- Re-exported `LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS`.
- Re-exported `validate_lightgbm_dependency_smoke_summary(...)`.
- Added the exported names to `abc_quant.pipeline.__all__`.
- Verified exported objects are identical to the source objects in `abc_quant.pipeline.lightgbm_diagnostics`.
- Did not change `run_lightgbm_dependency_smoke(...)`, diagnostics output schema, validator semantics, CLI behavior, packaged command behavior, mandatory dependencies, fitting, parameter search, model selection, strategy/allocation/performance/order/position outputs, or simulation behavior.

## 測試方式
- `python -m pytest tests\test_pipeline_lightgbm_diagnostics_exports.py`
- `python -m pytest tests\test_pipeline_lightgbm_diagnostics.py tests\test_pipeline_lightgbm_diagnostics_exports.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `.\.venv\Scripts\python.exe -m ruff check .`
- `.\.venv\Scripts\python.exe -m abc_quant.cli.lightgbm_dependency_smoke --indent 2`
- `.\.venv\Scripts\abc-quant-lightgbm-dependency-smoke.exe --indent 2`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused LightGBM dependency export tests: 6 passed in 0.93s.
- Related diagnostics/export tests: 21 passed in 1.04s.
- `pytest`: 371 passed in 27.30s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Local `.venv` ruff: passed.
- Module smoke execution: passed with project `.venv` Python and printed sorted indented JSON.
- Packaged command smoke execution: passed with project `.venv` console script.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- Local system `python -m abc_quant.cli.lightgbm_dependency_smoke --indent 2` remains unavailable because the system Python is not editable-installed for this repo.
- Local system `abc-quant-lightgbm-dependency-smoke --indent 2` remains unavailable unless the package console scripts are installed on PATH; the project `.venv` console script passed.
- This task only exposes existing contract symbols through `abc_quant.pipeline`. It does not change diagnostics behavior, require LightGBM, call `require_lightgbm()` by default, fit models, search/select models, emit strategy/allocation/performance/order/position outputs, or run simulations.

## 建議下一步
- Open a draft PR for ChatGPT Pro Tech Lead fast review, then let GitHub Actions verify Python 3.11 / 3.12 CI.

## 2026-07-07 Closed-Loop Task 049 - LightGBM Dependency Smoke Summary Contract Validator

## 修改檔案
- `src/abc_quant/pipeline/lightgbm_diagnostics.py`: added summary/default-parameter key constants, forbidden-key constants, and `validate_lightgbm_dependency_smoke_summary(...)`; wired `run_lightgbm_dependency_smoke(...)` to validate before returning.
- `tests/test_pipeline_lightgbm_diagnostics.py`: added validator call coverage, valid-summary pass-through, invalid shape failures, JSON-friendly failure coverage, forbidden-key failure coverage, and constants-based key assertions.
- `docs/modeling.md`: documented the LightGBM dependency smoke summary validator and its non-behavior-changing boundary.
- `README.md`: documented the summary validator and default non-fitting/no-optional-import boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 049 progress and completion evidence.
- `INBOX.md`: reset the active Task 049 block to the commented empty template before PR handoff.

## 實作摘要
- Added `LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS`.
- Added `LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS`.
- Added `LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS`.
- Added `validate_lightgbm_dependency_smoke_summary(summary)`.
- The validator rejects non-dict summaries, top-level key mismatches, non-dict `default_params`, default parameter key mismatches, non-JSON-friendly values, and forbidden diagnostic-output keys.
- `run_lightgbm_dependency_smoke(...)` now validates the summary before returning it.
- The default decoded summary content remains unchanged.
- Did not add a mandatory LightGBM dependency, default `require_lightgbm()` calls, model fitting, parameter search, model selection, winners/rankings/decisions, strategy signals, allocation logic, performance curves, orders, positions, or simulation engines.

## 測試方式
- `python -m pytest tests\test_pipeline_lightgbm_diagnostics.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `.\.venv\Scripts\python.exe -m abc_quant.cli.lightgbm_dependency_smoke --indent 2`
- `.\.venv\Scripts\abc-quant-lightgbm-dependency-smoke.exe --indent 2`
- `.\.venv\Scripts\python.exe -m ruff check .`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused LightGBM dependency diagnostics tests: 15 passed in 3.87s.
- `pytest`: 365 passed in 26.67s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Module smoke execution: passed with project `.venv` Python and printed sorted indented JSON.
- Packaged command smoke execution: passed after refreshing the local editable install with `.\.venv\Scripts\python.exe -m pip install -e . --no-deps`.
- Local `.venv` ruff: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- Local system `python -m abc_quant.cli.lightgbm_dependency_smoke --indent 2` is unavailable because the system Python is not editable-installed for this repo.
- Local system `abc-quant-lightgbm-dependency-smoke --indent 2` is unavailable until the package console scripts are installed on PATH; the project `.venv` console script passed after editable install.
- This task only hardens the diagnostics summary contract. It does not change output schema, require LightGBM, call `require_lightgbm()` by default, fit models, search/select models, emit strategy/allocation/performance/order/position outputs, or run simulations.

## 建議下一步
- Open a draft PR for ChatGPT Pro Tech Lead fast review, then let GitHub Actions verify Python 3.11 / 3.12 CI.

## 2026-07-07 Closed-Loop Task 048 - LightGBM Dependency Smoke Packaged Command Alias

## 修改檔案
- `pyproject.toml`: added `abc-quant-lightgbm-dependency-smoke = "abc_quant.cli.lightgbm_dependency_smoke:main"`.
- `tests/test_cli_lightgbm_dependency_smoke_entrypoint.py`: added pyproject parsing, target resolution, resolved-function JSON, `--indent`, monkeypatch, and forbidden-key tests.
- `docs/modeling.md`: documented the packaged command alias and shared CLI target boundary.
- `README.md`: documented both module and packaged command invocation forms.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 048 progress and completion evidence.
- `INBOX.md`: reset the active Task 048 block to the commented empty template before PR handoff.

## 實作摘要
- Added the packaged command alias `abc-quant-lightgbm-dependency-smoke`.
- Reused the existing `abc_quant.cli.lightgbm_dependency_smoke:main` target.
- Added tests that parse `pyproject.toml` with `tomllib`.
- Verified the configured target imports, resolves to the same `main`, and is callable.
- Verified resolved function calls return JSON-decodable output for both `[]` and `["--indent", "2"]`.
- Used monkeypatching in entrypoint tests so no real LightGBM package is required.
- Did not change `run_lightgbm_dependency_smoke(...)` behavior or the module CLI computation.
- Did not add mandatory LightGBM dependency, default `require_lightgbm()` calls, model fitting, parameter search, model selection, strategy signals, allocation logic, performance curves, orders, positions, or simulation engines.

## 測試方式
- `python -m pytest tests\test_cli_lightgbm_dependency_smoke_entrypoint.py`
- `python -m pytest tests\test_cli_lightgbm_dependency_smoke.py tests\test_cli_lightgbm_dependency_smoke_entrypoint.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `.\.venv\Scripts\python.exe -m abc_quant.cli.lightgbm_dependency_smoke --indent 2`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` should be attempted for local parity with CI.

## 測試結果
- Focused LightGBM dependency entrypoint tests: 5 passed in 1.00s.
- Related LightGBM dependency CLI tests: 11 passed in 2.14s.
- `pytest`: 355 passed in 25.98s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Module smoke execution: passed with project `.venv` Python and printed sorted indented JSON.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds the packaged command alias. It does not add or change diagnostics behavior, mandatory dependencies, model fitting, parameter search, model selection, strategy logic, allocation outputs, performance curves, orders, positions, or simulation engines.

## 建議下一步
- Open a draft PR for ChatGPT Pro Tech Lead fast review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-07 Closed-Loop Task 047 - LightGBM Dependency Smoke Module CLI

## 修改檔案
- `src/abc_quant/cli/lightgbm_dependency_smoke.py`: added the module-executable LightGBM dependency smoke CLI.
- `tests/test_cli_lightgbm_dependency_smoke.py`: added module invocation, JSON shape, `--indent`, call-count, monkeypatch, and forbidden-key tests.
- `docs/modeling.md`: documented the module CLI invocation and safety boundary.
- `README.md`: documented the module CLI command and default non-fitting boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 047 progress and completion evidence.
- `INBOX.md`: reset the active Task 047 block to the commented empty template before PR handoff.

## 實作摘要
- Added `python -m abc_quant.cli.lightgbm_dependency_smoke`.
- Added `main(argv: Sequence[str] | None = None) -> int`.
- The CLI calls `run_lightgbm_dependency_smoke()` exactly once per invocation.
- Successful execution writes sorted deterministic JSON to stdout and returns exit code 0.
- Supports optional `--indent`.
- Does not add or change packaged console-script aliases in `pyproject.toml`.
- Does not require the real `lightgbm` package for default execution.
- Does not call `require_lightgbm()` by default.
- Does not fit a model, search parameters, select models, output winners/rankings/decisions, create strategy signals, define allocation logic, build performance curves, create orders or positions, or run simulation engines.

## 測試方式
- `python -m pytest tests\test_cli_lightgbm_dependency_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `.\.venv\Scripts\python.exe -m abc_quant.cli.lightgbm_dependency_smoke --indent 2`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` should be attempted for local parity with CI.

## 測試結果
- Focused LightGBM dependency CLI tests: 6 passed in 2.22s.
- `pytest`: 350 passed in 26.58s.
- Module smoke execution: passed with project `.venv` Python and printed sorted indented JSON.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.
- Local system `python -m abc_quant.cli.lightgbm_dependency_smoke --indent 2`: unavailable because the system Python is not editable-installed for this repo; project `.venv` execution passed and GitHub Actions installs the package in CI.

## 已知限制
- This task only adds the module CLI. It does not add a packaged console-script alias, real LightGBM dependency requirement, default `require_lightgbm()` call, model fitting, parameter search, model selection, strategy logic, allocation outputs, performance curves, orders, positions, or simulation engines.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead fast review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-06 Closed-Loop Task 046 - LightGBM Dependency Smoke Diagnostics

## 修改檔案
- `src/abc_quant/pipeline/lightgbm_diagnostics.py`: added `run_lightgbm_dependency_smoke(...)`.
- `src/abc_quant/pipeline/__init__.py`: exported the new LightGBM dependency smoke helper.
- `tests/test_pipeline_lightgbm_diagnostics.py`: added dependency-status, JSON serialization, default params, top-level key, and forbidden-key tests.
- `docs/modeling.md`: documented the LightGBM dependency smoke diagnostics contract.
- `README.md`: documented the new diagnostics helper and default non-fitting boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 046 progress and completion evidence.
- `INBOX.md`: reset the active Task 046 block to the commented empty template before PR handoff.

## 實作摘要
- Added deterministic `run_lightgbm_dependency_smoke()`.
- Uses `check_lightgbm_dependency()` only.
- Does not call `require_lightgbm()` during default execution.
- Reports `package_name`, `installed`, `message`, `default_params`, `default_model_name`, `default_method`, and `fitting_enabled`.
- Derives `default_params` from `make_default_lightgbm_regressor_params()`.
- Keeps `fitting_enabled=False` by default.
- Does not require the real `lightgbm` package for tests or default execution.
- Does not fit a model, search parameters, select models, change existing smoke outputs, create strategy signals, define allocation logic, build performance curves, or run simulation engines.

## 測試方式
- `python -m pytest tests\test_pipeline_lightgbm_diagnostics.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI.

## 測試結果
- Focused LightGBM dependency diagnostics tests: 5 passed in 1.18s.
- `pytest`: 344 passed in 25.37s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task adds only dependency diagnostics. It does not add a LightGBM diagnostics CLI, packaged script, model fitting by default, parameter search, model selection, strategy logic, allocation outputs, performance curves, or simulation engines.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead fast review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 045 - Train-Only LightGBM Regressor Contract

## 修改檔案
- `src/abc_quant/models/lightgbm.py`: added `LightGBMRegressorResult` and `fit_lightgbm_regressor(...)` behind the optional dependency guard.
- `src/abc_quant/models/__init__.py`: exported the new LightGBM result dataclass and fit function.
- `tests/test_models_lightgbm.py`: added fake-LightGBM tests for train-only fitting, params pass-through, missing dependency behavior, holdout label non-leakage, prediction index alignment, and invalid inputs.
- `docs/modeling.md`: documented the optional train-only LightGBM fitting contract.
- `README.md`: documented the wrapper and safety boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 045 progress and completion evidence.
- `INBOX.md`: reset the active Task 045 block to the commented empty template before PR handoff.

## 實作摘要
- Added frozen `LightGBMRegressorResult`.
- Added `fit_lightgbm_regressor(dataset, params=None, model_name="lightgbm_regressor")`.
- Validates `SupervisedSplitDataset`, optional `LightGBMRegressorParams`, feature columns, train feature values, and train labels.
- Imports the optional package only through `require_lightgbm()`.
- Instantiates `lightgbm.LGBMRegressor(**params)` and fits only `dataset.train_X` / `dataset.train_y`.
- Uses train / validation / test feature frames only for prediction.
- Does not read `validation_y` or `test_y`.
- Returns predictions through the existing `SplitPredictionBundle` contract with split indices preserved.
- Keeps `lightgbm` out of mandatory dependencies.
- Does not add pipeline/CLI smoke outputs, parameter search, model selection, strategy signals, allocation logic, performance curves, or simulation engines.

## 測試方式
- `python -m pytest tests\test_models_lightgbm.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI.

## 測試結果
- Focused LightGBM tests: 27 passed in 1.06s.
- `pytest`: 339 passed in 25.26s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task adds only the optional train-only fitting contract. It does not add a LightGBM smoke pipeline, packaged CLI, parameter search, model selection, strategy logic, allocation outputs, performance curves, or simulation engines.
- This branch is stacked on Task 044 because PR #43 is still draft/open. Retarget or rebase after PR #43 merges.

## 建議下一步
- Open a draft PR against `codex/task-044-lightgbm-dependency-guard` for stacked review, then retarget to `main` after PR #43 merges.

## 2026-07-05 Closed-Loop Task 044 - Optional LightGBM Dependency Guard

## 修改檔案
- `src/abc_quant/models/lightgbm.py`: added optional LightGBM dependency status, required import helper, and deterministic regressor parameter contract.
- `src/abc_quant/models/__init__.py`: exported the new LightGBM dataclasses and helper functions.
- `tests/test_models_lightgbm.py`: added dependency-detection, optional import, defaults, invalid-parameter, and frozen-dataclass tests without requiring the real package.
- `docs/modeling.md`: documented the optional LightGBM guard and parameter boundary.
- `README.md`: documented the LightGBM optional dependency contract.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 044 progress and completion evidence.
- `INBOX.md`: reset the active Task 044 block to the commented empty template before PR handoff.

## 實作摘要
- Added frozen `LightGBMDependencyStatus`.
- Added frozen `LightGBMRegressorParams` with deterministic conservative defaults.
- Added `check_lightgbm_dependency()` using standard-library `importlib.util.find_spec(...)` without importing `lightgbm`.
- Added `require_lightgbm()` to return the imported optional module when available or raise a clear `ImportError`.
- Added `make_default_lightgbm_regressor_params()`.
- Validated objective text, estimator count, learning rate, leaf count, min data in leaf, feature/bagging fractions, bagging frequency, random state, and verbosity.
- Kept `lightgbm` out of mandatory project dependencies.
- Did not fit a model, search parameters, select models, change pipeline/CLI outputs, create strategy signals, define allocation logic, build performance curves, or run simulation engines.

## 測試方式
- `python -m pytest tests\test_models_lightgbm.py`
- `python -m pytest tests\test_models_lightgbm.py tests\test_models_linear.py tests\test_models_baseline.py tests\test_models_predictions.py tests\test_models_comparison.py tests\test_models_evaluation.py tests\test_models_dataset.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI.

## 測試結果
- Focused LightGBM tests: 23 passed in 1.06s.
- Related model tests: 77 passed in 1.63s.
- `pytest`: 335 passed in 25.97s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only prepares optional dependency detection and parameter validation. It does not add a LightGBM estimator, fit any model, add mandatory dependencies, run parameter search, or change diagnostics outputs.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 043 - Model Comparison Smoke Console Script

## 修改檔案
- `pyproject.toml`: added the `abc-quant-model-comparison-smoke` console script.
- `tests/test_cli_entrypoints.py`: added pyproject parsing, target import, resolved-function JSON, and median baseline tests for the model-comparison script.
- `docs/modeling.md`: documented the packaged model-comparison smoke console script.
- `README.md`: documented the installed console-script command.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 043 progress and completion evidence.
- `INBOX.md`: reset the active Task 043 block to the commented empty template before PR handoff.

## 實作摘要
- Added `abc-quant-model-comparison-smoke = "abc_quant.cli.model_comparison_smoke:main"`.
- Kept `python -m abc_quant.cli.model_comparison_smoke` unchanged.
- Extended `tests/test_cli_entrypoints.py` to parse `pyproject.toml` with `tomllib` and verify all existing script entries plus the new model-comparison entry.
- Verified the configured target imports and resolves to `abc_quant.cli.model_comparison_smoke.main`.
- Verified the resolved function emits valid JSON with `--indent 2`.
- Verified the resolved function supports `--baseline-method median`.
- No model-comparison calculation, summary key, split default, baseline-method choice, CLI argument semantic, model selection, ranking, strategy signal, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_cli_entrypoints.py tests\test_cli_model_comparison_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` should be attempted for local parity with CI.

## 測試結果
- Focused entrypoint/model-comparison CLI tests: 22 passed in 4.33s.
- `pytest`: 312 passed in 25.67s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds a packaged console-script alias for the existing CLI. It does not add new diagnostics, model selection, ranking, or strategy/backtest behavior.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 042 - Model Comparison Smoke CLI

## 修改檔案
- `src/abc_quant/cli/model_comparison_smoke.py`: added a module-executable CLI wrapper around `run_model_comparison_smoke(...)`.
- `tests/test_cli_model_comparison_smoke.py`: added module invocation, deterministic output, custom split, median baseline method, invalid-boundary, and key-contract tests.
- `docs/modeling.md`: documented the model-comparison smoke CLI.
- `README.md`: documented the module command and supported arguments.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 042 progress and completion evidence.
- `INBOX.md`: reset the active Task 042 block to the commented empty template before PR handoff.

## 實作摘要
- Added `python -m abc_quant.cli.model_comparison_smoke`.
- Added `main(argv=None) -> int` with the same stdout/stderr wrapper pattern as existing smoke CLIs.
- Supported `--train-end`, `--validation-end`, `--baseline-method mean|median`, and `--indent`.
- Successful runs write sorted deterministic JSON to stdout and return exit code 0.
- Invalid temporal boundaries return exit code 1 and write a concise `error:` message to stderr.
- `--baseline-method median` passes through to the existing constant-baseline reference method.
- The CLI remains a thin wrapper and does not change model-comparison calculations, summary keys, split defaults, existing smoke outputs, model selection, ranking, strategy signals, allocation logic, performance curves, or simulation engines.

## 測試方式
- `python -m abc_quant.cli.model_comparison_smoke --baseline-method median --indent 2`
- `python -m pytest tests\test_cli_model_comparison_smoke.py tests\test_pipeline_model_comparison.py tests\test_pipeline_contracts.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Module smoke execution: passed and printed sorted deterministic JSON.
- Focused CLI/model-comparison/contract tests: 109 passed in 10.59s.
- `pytest`: 308 passed in 25.05s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds the module CLI. It does not add a packaged console-script alias, choose a model, rank models, or add strategy/backtest behavior.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 041 - Model Comparison Smoke Summary Validator

## 修改檔案
- `src/abc_quant/pipeline/contracts.py`: added model comparison smoke summary constants and `validate_model_comparison_smoke_summary(...)`.
- `src/abc_quant/pipeline/model_comparison.py`: validates the model-comparison summary before returning it.
- `src/abc_quant/pipeline/__init__.py`: exported the new constants and validator.
- `tests/test_pipeline_contracts.py`: added valid and invalid model-comparison summary shape tests.
- `tests/test_pipeline_model_comparison.py`: switched model-comparison smoke tests to shared constants and validator.
- `docs/modeling.md`: documented the model-comparison smoke summary contract validator.
- `README.md`: documented the return-time validation boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 041 progress and completion evidence.
- `INBOX.md`: reset the active Task 041 block to the commented empty template before PR handoff.

## 實作摘要
- Added `MODEL_COMPARISON_SMOKE_SUMMARY_KEYS`.
- Added `MODEL_COMPARISON_SMOKE_SPLITS`.
- Added `MODEL_COMPARISON_SMOKE_MODEL_KEYS`.
- Added `MODEL_COMPARISON_SMOKE_COMPARISON_KEYS`.
- Added `MODEL_COMPARISON_SMOKE_SPLIT_COMPARISON_KEYS`.
- Added `validate_model_comparison_smoke_summary(summary)`.
- The validator returns the original summary object unchanged when valid.
- The validator rejects non-dict summaries, missing/unknown top-level keys, malformed reference/candidate model metadata, malformed split count mappings, malformed dropped label counts, malformed reference/candidate evaluations, malformed comparison blocks, and missing/unknown per-split comparison keys.
- The validator checks reference/candidate evaluation split metrics against existing `EVALUATION_METRIC_KEYS`.
- `run_model_comparison_smoke(...)` now validates the summary before returning.
- Default model-comparison smoke output values remain unchanged.
- No winner, ranking, decision, model selection, strategy signal, allocation logic, performance curve, order, position, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_model_comparison.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused contract/model-comparison tests: 103 passed in 7.69s.
- `pytest`: 302 passed in 21.57s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only hardens the model-comparison smoke summary shape. It does not add a CLI, choose a model, or add strategy/backtest behavior.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 040 - Baseline Versus OLS Comparison Smoke

## 修改檔案
- `src/abc_quant/pipeline/model_comparison.py`: added `run_model_comparison_smoke(...)` and local helpers for aligned baseline-vs-OLS diagnostics.
- `src/abc_quant/pipeline/__init__.py`: exported `run_model_comparison_smoke`.
- `tests/test_pipeline_model_comparison.py`: added deterministic JSON, metadata, split-count alignment, direct comparison parity, and forbidden-key tests.
- `docs/modeling.md`: documented the model comparison smoke diagnostic and safety boundary.
- `README.md`: documented the model comparison smoke diagnostic.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 040 progress and completion evidence.
- `INBOX.md`: reset the active Task 040 block to the commented empty template before PR handoff.

## 實作摘要
- Built deterministic comparison diagnostics from the existing smoke fixture.
- Wired `FeatureMatrix`, `TemporalSplit`, train-only scaler fit/transform, and `SupervisedSplitDataset`.
- Fit the constant baseline from training labels only.
- Fit OLS from the supervised training split only.
- Restricted baseline predictions to the same supervised split indices used by OLS after missing-label rows are dropped.
- Evaluated reference and candidate predictions with `evaluate_prediction_bundle(...)`.
- Compared the resulting evaluations with `compare_prediction_evaluations(...)`.
- Returned JSON-friendly `row_count`, `feature_columns`, `label_column`, model metadata, split counts, dropped label counts, reference evaluation, candidate evaluation, and raw comparison deltas.
- No winner, ranking, decision, selected model, model selection, strategy signal, allocation logic, performance curve, order, position, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_model_comparison.py tests\test_models_comparison.py tests\test_pipeline_linear_modeling.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused model-comparison/comparison/OLS-smoke tests: 22 passed in 2.02s.
- `pytest`: 268 passed in 19.62s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds in-memory smoke diagnostics for already-defined contracts. It does not choose a model, change existing smoke outputs, add CLI behavior, or add strategy/backtest behavior.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 039 - Prediction Evaluation Comparison Contract

## 修改檔案
- `src/abc_quant/models/comparison.py`: added frozen comparison dataclasses and `compare_prediction_evaluations(...)`.
- `src/abc_quant/models/__init__.py`: exported the comparison contract.
- `tests/test_models_comparison.py`: added deterministic delta, error-contract, no-decision, and frozen-dataclass tests.
- `docs/modeling.md`: documented the prediction evaluation comparison contract and safety boundary.
- `README.md`: documented the comparison helper in the model-output diagnostics section.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 039 progress and completion evidence.
- `INBOX.md`: reset the active Task 039 block to the commented empty template before PR handoff.

## 實作摘要
- Added `SplitEvaluationComparison` and `PredictionEvaluationComparison` as frozen dataclasses.
- Added `compare_prediction_evaluations(reference, candidate, reference_name="reference", candidate_name="candidate")`.
- The helper accepts only `SplitPredictionBundleEvaluationResult` inputs.
- Reference and candidate names are normalized as non-empty strings.
- Train, validation, and test splits must match on `row_count`, `non_missing_count`, and `missing_actual_count`.
- Each split records candidate-minus-reference deltas for `mae`, `rmse`, `mean_error`, and `prediction_mean`.
- Negative deltas remain raw numeric differences and are not converted into rankings, winners, or decisions.
- No model refit, prediction recomputation, model selection, parameter search, allocation logic, strategy signal output, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_models_comparison.py tests\test_models_evaluation.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused comparison/evaluation tests: 21 passed in 1.06s.
- `pytest`: 263 passed in 18.74s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task compares already-computed diagnostic evaluation objects only. It does not choose a model or modify any smoke summary output.

## 建議下一步
- Open a draft PR for ChatGPT Tech Lead review, then let GitHub Actions run CI including `ruff check .`.

## 2026-07-05 Closed-Loop Task 038 - OLS Smoke Console Script Alias

## 修改檔案
- `pyproject.toml`: added the `abc-quant-linear-regression-smoke` project script pointing to `abc_quant.cli.linear_regression_smoke:main`.
- `tests/test_cli_entrypoints.py`: added linear-regression console-script metadata, import resolution, and callable JSON-output tests while preserving modeling/preprocessing/supervised script coverage.
- `docs/modeling.md`: documented the installed OLS smoke console-script command alongside `python -m`.
- `README.md`: documented the packaged OLS smoke console command.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 038 progress and completion evidence.
- `INBOX.md`: reset the active Task 038 block to the commented empty template before PR handoff.

## 實作摘要
- Added a package metadata console-script alias: `abc-quant-linear-regression-smoke`.
- Kept the script target exactly `abc_quant.cli.linear_regression_smoke:main`.
- Added `tomllib`-based tests for the linear-regression script entry in `pyproject.toml`.
- Verified the configured target imports and resolves to the existing linear-regression smoke `main` function.
- Verified the resolved function accepts `--indent 2`, returns `0`, and emits valid JSON.
- Existing linear-regression CLI tests and modeling/preprocessing/supervised console-script tests remain covered.
- No OLS calculation, summary key, split default, CLI argument semantic, estimator implementation, parameter search, model selection, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was changed.

## 測試方式
- `python -m pytest tests\test_cli_entrypoints.py tests\test_cli_linear_regression_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused entrypoint/OLS CLI tests: 17 passed in 3.99s.
- `pytest`: 251 passed in 18.58s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only exposes the existing OLS smoke CLI as an installed console script. It does not alter OLS diagnostics behavior or add strategy/backtest behavior.

## PR 狀態
- Branch pushed: `codex/task-038-ols-smoke-console-script`.
- Draft PR creation is blocked in this environment because the GitHub connector returned `token_revoked` and local `gh auth status` reports no logged-in GitHub hosts.
- PR creation URL from git push: `https://github.com/jongyawjong0514/abc-quant/pull/new/codex/task-038-ols-smoke-console-script`.

## 建議下一步
- Restore GitHub connector or run `gh auth login`, then open a draft PR from `codex/task-038-ols-smoke-console-script` to `main`.
- After the draft PR exists, have ChatGPT Pro review the pyproject script entry, entrypoint tests, and documentation wording.

## 2026-07-05 Closed-Loop Task 037 - OLS Smoke CLI

## 修改檔案
- `src/abc_quant/cli/linear_regression_smoke.py`: added the module-executable OLS smoke diagnostics CLI.
- `tests/test_cli_linear_regression_smoke.py`: added module execution, deterministic stdout JSON, indent, custom split, invalid boundary, summary-key, and forbidden-key tests.
- `docs/modeling.md`: documented `python -m abc_quant.cli.linear_regression_smoke`.
- `README.md`: documented the OLS smoke CLI.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 037 progress and completion evidence.
- `INBOX.md`: reset the active Task 037 block to the commented empty template before PR handoff.

## 實作摘要
- Added `main(argv=None) -> int` in `src/abc_quant/cli/linear_regression_smoke.py`.
- The CLI is a thin wrapper around `run_linear_regression_smoke(...)`.
- Supports `--train-end`, `--validation-end`, and `--indent`.
- Valid invocations write sorted deterministic JSON to stdout and return `0`.
- Invalid temporal boundaries return non-zero and write a concise `error:` message to stderr.
- Tests verify stdout JSON equals `run_linear_regression_smoke(...)`.
- Tests verify repeated module calls are deterministic.
- Tests verify custom split arguments alter `split_counts_after_label_drop` deterministically.
- Tests verify output contains only `LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS`.
- Existing modeling, preprocessing, and supervised CLI behavior remains unchanged.
- No OLS calculation change, summary key change, split default change, package script change, new estimator implementation, parameter search, model selection, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_cli_linear_regression_smoke.py tests\test_cli_modeling_smoke.py tests\test_cli_preprocessing_smoke.py tests\test_cli_supervised_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused OLS/modeling/preprocessing/supervised CLI tests: 22 passed in 11.55s.
- `pytest`: 248 passed in 21.97s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds a module-executable OLS smoke CLI. It does not add a packaged console-script alias, change OLS diagnostics, or add strategy/backtest behavior.

## 建議下一步
- Wait for GitHub Actions on the draft PR, then have ChatGPT Pro review the CLI wrapper, stdout/stderr behavior, custom split pass-through, and unchanged summary contract boundary.

## 2026-07-05 Closed-Loop Task 036 - OLS Smoke Summary Validator

## 修改檔案
- `src/abc_quant/pipeline/contracts.py`: added OLS smoke summary constants and `validate_linear_regression_smoke_summary(...)`.
- `src/abc_quant/pipeline/linear_modeling.py`: validates the OLS smoke summary before returning it.
- `src/abc_quant/pipeline/__init__.py`: exported the new OLS smoke constants and validator.
- `tests/test_pipeline_contracts.py`: added valid and invalid OLS smoke summary shape tests.
- `tests/test_pipeline_linear_modeling.py`: switched OLS smoke tests to shared constants and validator.
- `docs/modeling.md`: documented the OLS smoke summary contract validator.
- `README.md`: documented the centralized OLS smoke summary shape.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 036 progress and completion evidence.
- `INBOX.md`: reset the active Task 036 block to the commented empty template before PR handoff.

## 實作摘要
- Added `LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS`.
- Added `LINEAR_REGRESSION_SMOKE_SPLITS`.
- Added `LINEAR_REGRESSION_SMOKE_EVALUATION_KEYS` using the shared evaluation metric keys.
- Added `validate_linear_regression_smoke_summary(summary)`.
- The validator returns the original summary object unchanged when valid.
- The validator rejects non-dict summaries, missing/unknown top-level keys, non-dict split mappings, missing/unknown split mappings, non-dict evaluation blocks, missing/unknown evaluation splits, non-dict split metrics, and missing/unknown metric keys.
- The validator checks `split_counts_after_label_drop`, `dropped_label_counts`, `prediction_counts`, and `evaluation` against the train/validation/test split names.
- The validator checks `feature_columns` is a list and `coefficients` is a dict.
- `run_linear_regression_smoke(...)` now validates the summary before returning.
- Default OLS smoke output values remain unchanged.
- Existing modeling, preprocessing, and supervised smoke summary contracts remain unchanged.
- No new estimator implementation, parameter search, model selection, allocation logic, strategy signal output, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_linear_modeling.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused contract/OLS smoke tests: 69 passed in 5.15s.
- `pytest`: 243 passed in 16.37s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only hardens the OLS smoke diagnostics summary shape. It does not add an OLS smoke CLI, package script, model selection, or any strategy/backtest behavior.

## 建議下一步
- Wait for GitHub Actions on the draft PR, then have ChatGPT Pro review the shared constants, validator failure cases, OLS smoke return path, and unchanged output-value boundary.

## 2026-07-05 Closed-Loop Task 035 - Train-Only OLS Smoke Diagnostics

## 修改檔案
- `src/abc_quant/pipeline/linear_modeling.py`: added `run_linear_regression_smoke(...)`.
- `src/abc_quant/pipeline/__init__.py`: exported the new OLS smoke diagnostic helper.
- `tests/test_pipeline_linear_modeling.py`: added deterministic, JSON-serializable, direct OLS-result parity, direct evaluation parity, metadata preservation, and forbidden-key tests.
- `docs/modeling.md`: documented the OLS smoke diagnostics pipeline and safety boundaries.
- `README.md`: documented the deterministic OLS smoke diagnostics helper.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 035 progress and completion evidence.
- `INBOX.md`: reset the active Task 035 block to the commented empty template before PR handoff.

## 實作摘要
- Added `run_linear_regression_smoke(...)` using the existing deterministic smoke frame and feature-complete rows.
- Wired `FeatureMatrix`, `TemporalSplit`, train-only scaler fit/transform, `SupervisedSplitDataset`, `fit_linear_regression(...)`, and `evaluate_prediction_bundle(...)`.
- Returned a JSON-friendly summary with row count, feature columns, label column, model name, method, intercept, ordered coefficients, training row count, split counts after label drop, dropped label counts, prediction counts, and train/validation/test evaluation metrics.
- Kept OLS fitting behind the existing train-only estimator contract.
- Did not change existing smoke outputs, CLI behavior, package scripts, preprocessing, dataset, or linear model contracts.
- No new estimator implementation, parameter search, model selection, strategy signal output, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_linear_modeling.py`
- `python -m pytest tests\test_pipeline_linear_modeling.py tests\test_models_linear.py tests\test_pipeline_supervised.py tests\test_models_evaluation.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused OLS smoke tests: 5 passed in 4.21s.
- Related pipeline/model tests: 28 passed in 2.28s.
- `pytest`: 222 passed in 14.91s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only adds an in-memory diagnostics pipeline. It does not add a CLI for OLS smoke diagnostics, a summary contract validator, model selection, or any strategy/backtest behavior.

## 建議下一步
- Wait for GitHub Actions on the draft PR, then have ChatGPT Pro review summary shape, direct evaluator parity, train-only fitting path, and forbidden-output-key coverage.

## 2026-07-05 Closed-Loop Task 034 - Train-Only OLS Regression Contract

## 修改檔案
- `src/abc_quant/models/linear.py`: added `LinearRegressionResult` and `fit_linear_regression(...)`.
- `src/abc_quant/models/__init__.py`: exported the OLS result dataclass and fit function.
- `tests/test_models_linear.py`: added train-only fit, deterministic coefficient/prediction, holdout-label non-leakage, split-index, invalid-input, invalid-train-data, and copy-isolation tests.
- `docs/modeling.md`: documented the ordinary least-squares regression contract and safety boundaries.
- `README.md`: documented the train-only OLS model contract.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 034 progress and completion evidence.
- `INBOX.md`: reset the active Task 034 block to the commented empty template before PR handoff.

## 實作摘要
- Added a frozen `LinearRegressionResult` with `model_name`, `method`, `feature_columns`, `coefficients`, `intercept`, `training_row_count`, and `prediction_bundle`.
- Added `fit_linear_regression(dataset, fit_intercept=True, model_name="ordinary_least_squares")`.
- The fit path only uses `SupervisedSplitDataset.train_X` and `train_y`.
- Validation/test feature frames are used only for prediction; validation/test labels are not read.
- OLS coefficients are fit with `numpy.linalg.lstsq`; no sklearn or new dependency was added.
- Returned train/validation/test predictions are produced through `build_split_prediction_bundle(...)`.
- Invalid input type, empty train data, missing/non-finite training data, nonnumeric feature columns, index mismatch, and split column mismatch fail loudly.
- No parameter search, model selection, allocation logic, strategy signal output, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_models_linear.py`
- `python -m pytest tests\test_models_linear.py tests\test_models_dataset.py tests\test_models_predictions.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused OLS tests: 7 passed in 1.09s.
- Related model contract tests: 28 passed in 1.27s.
- `pytest`: 217 passed in 14.60s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task introduces only a minimal in-memory OLS estimator contract. It does not wire OLS into smoke CLIs, model selection, evaluation summaries, or training pipelines.

## 建議下一步
- Wait for GitHub Actions on the draft PR, then have ChatGPT Pro review train-only fitting, holdout-label non-leakage, prediction bundle metadata, and invalid-data behavior.

## 2026-07-05 Closed-Loop Task 033 - Supervised Smoke Console Script Alias

## 修改檔案
- `pyproject.toml`: added the `abc-quant-supervised-smoke` project script pointing to `abc_quant.cli.supervised_smoke:main`.
- `tests/test_cli_entrypoints.py`: added supervised console-script metadata, import resolution, and callable JSON-output tests while preserving modeling/preprocessing script coverage.
- `docs/modeling.md`: documented the installed supervised smoke console-script command alongside `python -m`.
- `README.md`: documented the packaged supervised smoke console command.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 033 progress and completion evidence.
- `INBOX.md`: reset the active Task 033 block to the commented empty template before PR handoff.

## 實作摘要
- Added a package metadata console-script alias: `abc-quant-supervised-smoke`.
- Kept the script target exactly `abc_quant.cli.supervised_smoke:main`.
- Added `tomllib`-based tests for the supervised script entry in `pyproject.toml`.
- Verified the configured target imports and resolves to the existing supervised `main` function.
- Verified the resolved function accepts `--indent 2`, returns `0`, and emits valid JSON.
- Existing modeling/preprocessing console-script tests and supervised CLI tests remain covered.
- No supervised calculation, summary key, split default, CLI argument semantic, estimator implementation, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was changed.

## 測試方式
- `python -m pytest tests\test_cli_entrypoints.py tests\test_cli_supervised_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `python -m ruff check .` was attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused entrypoint/supervised CLI tests: 14 passed in 3.91s.
- `pytest`: 210 passed in 14.29s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- Local `ruff`: unavailable (`No module named ruff`); GitHub Actions should run `ruff check .`.

## 已知限制
- This task only exposes the existing supervised smoke CLI as an installed console script. It does not add package-script aliases for future CLIs and does not alter smoke diagnostics behavior.

## 建議下一步
- Wait for GitHub Actions on the draft PR, then have ChatGPT Pro review the pyproject script entry, entrypoint tests, and documentation wording.

## 2026-07-05 Closed-Loop Task 032 - Supervised Dataset Smoke CLI

## 修改檔案
- `src/abc_quant/cli/supervised_smoke.py`: added the module-executable supervised dataset smoke CLI.
- `tests/test_cli_supervised_smoke.py`: added module execution, deterministic stdout JSON, indent, custom split, invalid boundary, and forbidden-key tests.
- `docs/modeling.md`: documented `python -m abc_quant.cli.supervised_smoke`.
- `README.md`: documented the supervised dataset smoke CLI.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 032 progress and completion evidence.
- `INBOX.md`: reset the active Task 032 block to the commented empty template before PR handoff.

## 實作摘要
- Added `main(argv=None) -> int` in `src/abc_quant/cli/supervised_smoke.py`.
- The CLI is a thin wrapper around `run_supervised_dataset_smoke(...)`.
- Supports `--train-end`, `--validation-end`, and `--indent`.
- Valid invocations write sorted deterministic JSON to stdout and return `0`.
- Invalid temporal boundaries return non-zero and write a concise `error:` message to stderr.
- Existing modeling and preprocessing CLI behavior remains unchanged.
- No estimator implementation, supervised dataset calculation change, summary key change, split default change, package script change, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_cli_supervised_smoke.py tests\test_cli_preprocessing_smoke.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused supervised/modeling/preprocessing CLI tests: 17 passed in 8.87s.
- `pytest`: 207 passed in 13.97s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only adds a module-executable CLI. It does not add a packaged console-script alias or train estimators.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-05 Closed-Loop Task 031 - Supervised Dataset Smoke Summary Validator

## 修改檔案
- `src/abc_quant/pipeline/contracts.py`: added supervised dataset smoke summary constants and `validate_supervised_dataset_smoke_summary(...)`.
- `src/abc_quant/pipeline/supervised.py`: validates the summary before returning it.
- `src/abc_quant/pipeline/__init__.py`: exported the new constants and validator.
- `tests/test_pipeline_supervised.py`: switched supervised smoke tests to shared constants and validator.
- `tests/test_pipeline_contracts.py`: added valid and invalid supervised summary shape tests.
- `docs/modeling.md`: documented the supervised dataset smoke summary contract validator.
- `README.md`: documented the shared validator under modeling preparation.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 031 progress and completion evidence.
- `INBOX.md`: reset the active Task 031 block to the commented empty template before PR handoff.

## 實作摘要
- Added `SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS`.
- Added `SUPERVISED_DATASET_SMOKE_SPLITS`.
- Added `SUPERVISED_DATASET_SMOKE_SPLIT_SHAPE_KEYS`.
- Added `validate_supervised_dataset_smoke_summary(summary)`.
- The validator returns the original summary object unchanged when valid.
- The validator rejects non-dict summaries, missing/unknown top-level keys, non-dict split count mappings, missing/unknown split keys, non-dict split shape, missing/unknown split shapes, malformed split shape entries, and missing/unknown `rows` / `columns` shape keys.
- `run_supervised_dataset_smoke(...)` now validates the summary before returning.
- Default supervised dataset smoke output values remain unchanged.
- Existing modeling and preprocessing smoke summary contracts remain unchanged.
- No estimator implementation, existing smoke output value change, CLI behavior change, package script change, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_supervised.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused contract/supervised tests: 50 passed in 3.72s.
- `pytest`: 202 passed in 11.43s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only hardens the supervised dataset smoke summary shape. It does not add a CLI or train estimators.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-05 Closed-Loop Task 030 - Supervised Dataset Smoke Diagnostics

## 修改檔案
- `src/abc_quant/pipeline/supervised.py`: added `run_supervised_dataset_smoke(...)` and default split constants.
- `src/abc_quant/pipeline/__init__.py`: exported `run_supervised_dataset_smoke`.
- `tests/test_pipeline_supervised.py`: added deterministic, JSON-serializable, direct dataset parity, train non-empty, feature/label preservation, label-drop count, and forbidden-key tests.
- `docs/modeling.md`: documented supervised dataset smoke diagnostics and safety boundaries.
- `README.md`: documented the supervised dataset smoke diagnostic under modeling preparation.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 030 progress and completion evidence.
- `INBOX.md`: reset the active Task 030 block to the commented empty template before PR handoff.

## 實作摘要
- Added a deterministic supervised dataset smoke path that uses feature-complete synthetic smoke rows.
- The path wires together `build_feature_matrix(...)`, `build_temporal_split(...)`, `fit_standard_scaler(...)`, `transform_with_standard_scaler(...)`, and `build_supervised_split_dataset(..., drop_missing_labels=True)`.
- The returned summary is JSON-friendly and includes `row_count`, `feature_columns`, `label_column`, `split_counts_before_label_drop`, `split_counts_after_label_drop`, `dropped_label_counts`, and `split_shape`.
- Split counts before label drop are derived from standardized split feature frames.
- Split counts after label drop and dropped label counts are derived from the direct `SupervisedSplitDataset`.
- No estimator implementation, existing smoke output change, CLI behavior change, package script change, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_supervised.py`
- `python -m pytest tests\test_pipeline_supervised.py tests\test_models_dataset.py tests\test_pipeline_preprocessing.py tests\test_preprocessing_scaling.py tests\test_features_matrix.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused supervised pipeline tests: 7 passed in 1.44s.
- Related supervised/dataset/preprocessing tests: 36 passed in 2.35s.
- `pytest`: 183 passed in 10.46s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only adds deterministic in-memory supervised dataset diagnostics. It does not train estimators or expose a new CLI.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-05 Closed-Loop Task 029 - Supervised Split Dataset Contract

## 修改檔案
- `src/abc_quant/models/dataset.py`: added `SupervisedSplitDataset` and `build_supervised_split_dataset(...)`.
- `src/abc_quant/models/__init__.py`: exported the supervised dataset dataclass and builder.
- `tests/test_models_dataset.py`: added construction, label alignment, missing-label filtering, no-drop error, empty train, copy isolation, type, index, and column-order tests.
- `docs/modeling.md`: documented the supervised split dataset contract and safety rules.
- `README.md`: documented the supervised split dataset contract in the modeling preparation section.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 029 progress and completion evidence.
- `INBOX.md`: reset the active Task 029 block to the commented empty template before PR handoff.

## 實作摘要
- Added a frozen `SupervisedSplitDataset` dataclass with `feature_columns`, `label_column`, train/validation/test feature and label splits, and `dropped_label_counts`.
- Added `build_supervised_split_dataset(feature_matrix, standardized_features, drop_missing_labels=True)`.
- The builder requires `FeatureMatrix` and `StandardizedFeatureMatrix` inputs and validates standardized split indices/columns against the fitted scaler metadata.
- Labels are aligned from `FeatureMatrix.y` using the split indices stored in `standardized_features.fitted`.
- Missing labels are dropped independently per split by default and counted under train/validation/test.
- `drop_missing_labels=False` rejects missing labels with a `ValueError`.
- Empty train data after label filtering is rejected.
- Returned feature frames and label Series are copied to avoid later caller mutation changing the dataset.
- No estimator implementation, smoke output change, CLI behavior change, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_models_dataset.py`
- `python -m pytest tests\test_models_dataset.py tests\test_preprocessing_scaling.py tests\test_features_matrix.py tests\test_pipeline_preprocessing.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused dataset tests: 8 passed in 1.19s.
- Related feature/preprocessing tests: 29 passed in 1.85s.
- `pytest`: 176 passed in 10.07s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only prepares in-memory supervised split inputs. It does not train estimators or wire the dataset into smoke pipeline outputs.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 028 - Preprocessing Smoke Console Script Alias

## 修改檔案
- `pyproject.toml`: added the `abc-quant-preprocessing-smoke` project script pointing to `abc_quant.cli.preprocessing_smoke:main`.
- `tests/test_cli_entrypoints.py`: added preprocessing console-script metadata, import resolution, and callable JSON-output tests while keeping existing modeling console-script coverage.
- `docs/modeling.md`: documented the installed preprocessing console-script command alongside `python -m`.
- `README.md`: documented the packaged preprocessing console command.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 028 progress and completion evidence.
- `INBOX.md`: reset the active Task 028 block to the commented empty template before PR handoff.

## 實作摘要
- Added a package metadata console-script alias: `abc-quant-preprocessing-smoke`.
- The entry point target is exactly `abc_quant.cli.preprocessing_smoke:main`.
- `python -m abc_quant.cli.preprocessing_smoke` remains unchanged.
- Entry-point tests parse `pyproject.toml` with `tomllib`, import the configured target, confirm it resolves to the preprocessing `main`, and call the resolved function with `--indent 2` to verify valid JSON.
- Existing modeling console-script tests and preprocessing CLI tests remain covered.
- No preprocessing calculation, summary key, split default, CLI argument semantic, estimator implementation, file output, outside data access, live account connectivity, parameter search, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_cli_entrypoints.py tests\test_cli_preprocessing_smoke.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- pyproject script-map verification with `tomllib`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused entrypoint/CLI tests: 18 passed in 6.49s.
- `pytest`: 168 passed in 9.64s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- pyproject script-map verification confirmed:
  - `abc-quant-modeling-smoke = abc_quant.cli.modeling_smoke:main`
  - `abc-quant-preprocessing-smoke = abc_quant.cli.preprocessing_smoke:main`
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only adds package-level discoverability for the existing preprocessing CLI. It does not install the package globally or change CLI behavior.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 027 - Preprocessing Smoke Diagnostics CLI

## 修改檔案
- `src/abc_quant/cli/preprocessing_smoke.py`: added the module entry point for deterministic preprocessing smoke diagnostics.
- `tests/test_cli_preprocessing_smoke.py`: added subprocess and direct-main tests for deterministic JSON, sorted keys, split arguments, error handling, and diagnostic-only keys.
- `docs/modeling.md`: documented preprocessing smoke CLI usage, arguments, stdout/stderr behavior, and diagnostic-only boundary.
- `README.md`: documented the preprocessing smoke CLI command and arguments.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 027 progress and completion evidence.
- `INBOX.md`: reset the active Task 027 block to the commented empty template before PR handoff.

## 實作摘要
- Added `python -m abc_quant.cli.preprocessing_smoke` as a thin wrapper around `run_preprocessing_smoke(...)`.
- The CLI supports `--train-end`, `--validation-end`, and `--indent`.
- Successful invocations write sorted deterministic JSON to stdout and return exit code 0.
- Invalid temporal boundaries are caught, return non-zero, and write a concise `error: ...` message to stderr.
- Tests verify stdout JSON equals `run_preprocessing_smoke(...)`, repeated module calls are deterministic, custom split arguments alter `split_counts`, and output keys match `PREPROCESSING_SMOKE_SUMMARY_KEYS`.
- No preprocessing calculation, summary key, split default, modeling smoke CLI behavior, estimator implementation, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was changed.

## 測試方式
- `python -m pytest tests\test_cli_preprocessing_smoke.py tests\test_pipeline_preprocessing.py`
- `python -m pytest tests\test_cli_preprocessing_smoke.py tests\test_cli_modeling_smoke.py tests\test_pipeline_preprocessing.py tests\test_pipeline_contracts.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `$env:PYTHONPATH='src'; python -m abc_quant.cli.preprocessing_smoke --train-end 2026-01-08 --validation-end 2026-01-13 --indent 2`
- `.venv\Scripts\python.exe -m abc_quant.cli.preprocessing_smoke --indent 2`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused CLI/preprocessing tests: 10 passed in 4.19s.
- Related CLI/contract/preprocessing tests: 41 passed in 8.18s.
- `pytest`: 165 passed in 10.22s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Module smoke execution passed with `PYTHONPATH=src` and `.venv` Python.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only exposes preprocessing smoke diagnostics through a module CLI. It does not add a packaged console-script alias and does not wire scaling into model training.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 026 - Preprocessing Smoke Summary Validator

## 修改檔案
- `src/abc_quant/pipeline/contracts.py`: added preprocessing smoke summary key constants, split constants, split-shape constants, and `validate_preprocessing_smoke_summary(...)`.
- `src/abc_quant/pipeline/preprocessing.py`: validates the preprocessing smoke summary before returning it.
- `src/abc_quant/pipeline/__init__.py`: exports preprocessing smoke summary constants and validator.
- `tests/test_pipeline_preprocessing.py`: uses shared preprocessing summary constants and validates the smoke summary contract.
- `tests/test_pipeline_contracts.py`: added focused invalid-shape coverage for preprocessing smoke summaries.
- `docs/modeling.md`: documented the preprocessing smoke summary contract and validator.
- `README.md`: documented the shared preprocessing smoke summary validator.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 026 progress and completion evidence.
- `INBOX.md`: reset the active Task 026 block to the commented empty template before PR handoff.

## 實作摘要
- Centralized the preprocessing smoke summary shape in `abc_quant.pipeline.contracts`.
- Added `PREPROCESSING_SMOKE_SUMMARY_KEYS`, `PREPROCESSING_SMOKE_SPLITS`, and `PREPROCESSING_SMOKE_SPLIT_SHAPE_KEYS`.
- Added `validate_preprocessing_smoke_summary(...)`, which returns the original summary unchanged when valid.
- The validator rejects non-dict summaries, top-level key drift, invalid `split_counts`, invalid `split_shape`, and per-split shape entries that are not exactly `rows` / `columns`.
- `run_preprocessing_smoke(...)` now validates its summary before returning.
- The default preprocessing smoke diagnostic values remained unchanged.
- No modeling smoke summary contract, CLI argument, estimator implementation, parameter search, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_preprocessing.py`
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_preprocessing.py tests\test_pipeline_modeling.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused contract/preprocessing tests: 29 passed in 2.53s.
- Related pipeline/CLI tests: 42 passed in 5.66s.
- `pytest`: 160 passed in 6.82s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only hardens the preprocessing smoke diagnostics summary shape. It does not add a preprocessing CLI or wire scaling into model training.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 025 - Preprocessing Smoke Diagnostics

## 修改檔案
- `src/abc_quant/pipeline/preprocessing.py`: added `run_preprocessing_smoke(...)` for deterministic train-only scaling diagnostics.
- `src/abc_quant/pipeline/__init__.py`: exported `run_preprocessing_smoke`.
- `tests/test_pipeline_preprocessing.py`: added deterministic summary, JSON serialization, train-only fitted parameter, standardized train mean/std, and split-shape preservation tests.
- `docs/modeling.md`: documented the preprocessing smoke diagnostic path and safety rules.
- `README.md`: documented the preprocessing smoke diagnostic alongside modeling preparation.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 025 progress and completion evidence.
- `INBOX.md`: reset the active Task 025 block to the commented empty template before PR handoff.

## 實作摘要
- Added a deterministic preprocessing smoke path that uses `build_smoke_frame(...)`, `build_feature_matrix(...)`, `build_temporal_split(...)`, `fit_standard_scaler(...)`, and `transform_with_standard_scaler(...)`.
- The smoke path uses feature-complete synthetic fixture rows because the existing rolling smoke features intentionally contain missing early rows for each ticker.
- The returned plain dict is JSON-serializable and includes `row_count`, `feature_columns`, `split_counts`, `fitted_means`, `fitted_stds`, `train_mean_after_scaling`, `train_std_after_scaling`, and `split_shape`.
- Tests compare fitted means/stds against direct train-split calculations, verify train scaled mean/std, and confirm validation/test shape preservation.
- The new path is separate from the existing modeling smoke CLI and modeling smoke summary contract.
- No estimator implementation, parameter search, allocation logic, performance curve, simulation engine, outside data access, live account connectivity, or modeling smoke output change was added.

## 測試方式
- `python -m pytest tests\test_pipeline_preprocessing.py`
- `python -m pytest tests\test_pipeline_preprocessing.py tests\test_preprocessing_scaling.py tests\test_pipeline_modeling.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused preprocessing pipeline tests: 5 passed in 1.29s.
- Related preprocessing/modeling tests: 27 passed in 4.70s.
- `pytest`: 147 passed in 6.44s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This diagnostic does not expose a CLI and does not wire scaling into model training or the modeling smoke summary.

## 下一步建議
- Run full validation after final tracking updates, then open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 024 - Train-Only Feature Standardization

## 修改檔案
- `src/abc_quant/preprocessing/__init__.py`: added preprocessing package exports.
- `src/abc_quant/preprocessing/scaling.py`: added `StandardScalerFit`, `StandardizedFeatureMatrix`, `fit_standard_scaler(...)`, and `transform_with_standard_scaler(...)`.
- `tests/test_preprocessing_scaling.py`: added leakage-focused scaler tests for train-only fit, transform preservation, non-leakage, and invalid inputs.
- `docs/modeling.md`: documented the train-only standardization contract and safety rules.
- `README.md`: documented the preprocessing contract in the modeling preparation section.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 024 progress and completion evidence.
- `INBOX.md`: reset the active Task 024 block to the commented empty template before PR handoff.

## 實作摘要
- Added a frozen `StandardScalerFit` dataclass with feature columns, means, stds, and train/validation/test split indices.
- Added a frozen `StandardizedFeatureMatrix` dataclass with train, validation, test, and fitted fields.
- `fit_standard_scaler(...)` validates a `FeatureMatrix` and `TemporalSplit`, defaults to `feature_matrix.feature_columns`, and fits means/stds using only `temporal_split.train_index`.
- `transform_with_standard_scaler(...)` applies the fitted scaler to train, validation, and test rows without changing row order, row counts, split indices, or feature column order.
- Validation/test extreme values do not affect fitted means/stds.
- The contract rejects empty train splits, unknown feature columns, duplicate feature columns, nonnumeric columns, missing training feature values, zero-variance training features, out-of-range split positions, and transform split mismatches.
- No sklearn dependency, estimator implementation, parameter search, metadata/label mutation, allocation logic, performance curve, simulation engine, outside data access, or live account connectivity was added.

## 測試方式
- `python -m pytest tests\test_preprocessing_scaling.py`
- `python -m pytest tests\test_preprocessing_scaling.py tests\test_features_matrix.py tests\test_validation_temporal.py tests\test_pipeline_modeling.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused preprocessing tests: 9 passed in 1.09s.
- Related feature/split/pipeline tests: 30 passed in 1.82s.
- `pytest`: 142 passed in 5.88s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task adds only the preprocessing contract. It does not wire scaling into the modeling smoke pipeline or any estimator.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 023 - Modeling Smoke Bundle Evaluation Wiring

## 修改檔案
- `src/abc_quant/pipeline/modeling.py`: changed the internal baseline evaluation path to build a constant-baseline prediction bundle and evaluate it with `evaluate_prediction_bundle(...)`.
- `tests/test_pipeline_modeling.py`: added direct bundle-evaluator parity coverage for the modeling smoke summary evaluation metrics.
- `docs/modeling.md`: documented that the modeling smoke pipeline now uses the split prediction bundle evaluation path internally.
- `README.md`: documented the internal bundle evaluation wiring while noting the public summary shape is unchanged.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 023 progress and completion evidence.
- `INBOX.md`: reset the active Task 023 block to the commented empty template before PR handoff.

## 實作摘要
- `run_baseline_modeling_smoke(...)` still builds the deterministic smoke frame, feature matrix, temporal split, and constant baseline exactly as before.
- After fitting the baseline, it now calls `build_constant_baseline_prediction_bundle(...)` and `evaluate_prediction_bundle(...)`.
- The returned summary remains validated by `validate_modeling_smoke_summary(...)`.
- The top-level summary keys, nested evaluation metric keys, default method, fitted values, split counts, metric formulas, CLI arguments, and console-script behavior were not changed.
- Tests compare pipeline evaluation metrics against direct `evaluate_prediction_bundle(...)` output for the same bundle.

## 測試方式
- `python -m pytest tests\test_pipeline_modeling.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused pipeline/CLI tests: 13 passed in 4.12s.
- `pytest`: 133 passed in 5.97s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only changes internal modeling smoke wiring. It does not expose prediction bundles in the summary or CLI output.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 022 - Split Prediction Bundle Evaluator

## 修改檔案
- `src/abc_quant/models/evaluation.py`: added `SplitPredictionBundleEvaluationResult` and `evaluate_prediction_bundle(...)`, delegating each split to `evaluate_predictions(...)`.
- `src/abc_quant/models/__init__.py`: exported the bundle evaluation dataclass and evaluator.
- `tests/test_models_evaluation.py`: added valid bundle evaluation, missing-actual handling, invalid type checks, and parity with existing constant-baseline evaluation.
- `docs/modeling.md`: documented bundle evaluation and its safety rules.
- `README.md`: documented `evaluate_prediction_bundle(...)` in the prediction evaluation section.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 022 progress and completion evidence.
- `INBOX.md`: reset the active Task 022 block to the commented empty template before PR handoff.

## 實作摘要
- Added a frozen `SplitPredictionBundleEvaluationResult` with `model_name`, `method`, `train`, `validation`, and `test`.
- Added `evaluate_prediction_bundle(feature_matrix, prediction_bundle)`.
- The evaluator requires a `FeatureMatrix` and `SplitPredictionBundle` with clear `TypeError` messages.
- It evaluates train, validation, and test predictions by calling `evaluate_predictions(feature_matrix.y, split_predictions, split_name)`.
- It preserves `prediction_bundle.model_name` and `prediction_bundle.method`.
- Constant-baseline bundle evaluation now has test coverage proving split metrics match the existing `evaluate_constant_baseline(...)` output.
- No existing metric formula, baseline calculation, pipeline behavior, CLI behavior, diagnostic summary key, estimator implementation, file output, outside data access, live account connectivity, preprocessing fitting, parameter search, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_models_evaluation.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused evaluation tests: 9 passed in 0.98s.
- `pytest`: 132 passed in 5.58s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only evaluates already-built split prediction bundles. It does not wire bundle evaluation into pipeline summaries or CLI output.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 021 - Constant Baseline Prediction Bundle Adapter

## 修改檔案
- `src/abc_quant/models/predictions.py`: added `build_constant_baseline_prediction_bundle(...)`, with explicit `ConstantBaselineResult` type validation and delegation to the generic split bundle builder.
- `src/abc_quant/models/__init__.py`: exported the constant-baseline prediction bundle adapter.
- `tests/test_models_predictions.py`: added adapter coverage for default model name, custom trimmed model name, method propagation, split indices/values, copy isolation, and invalid input type.
- `docs/modeling.md`: documented the constant-baseline adapter and its delegation to the shared validation/copy contract.
- `README.md`: documented the adapter alongside the generic prediction bundle contract.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 021 progress and completion evidence.
- `INBOX.md`: reset the active Task 021 block to the commented empty template before PR handoff.

## 實作摘要
- Added `build_constant_baseline_prediction_bundle(baseline_result, model_name="constant_baseline")`.
- The helper accepts only `ConstantBaselineResult` and raises a clear `TypeError` for other inputs.
- It propagates `baseline_result.method` and passes the existing train/validation/test prediction Series into `build_split_prediction_bundle(...)`.
- Validation and copy isolation are therefore shared with the generic split prediction bundle contract.
- No baseline calculation, pipeline behavior, CLI arguments, summary keys, estimator implementation, file output, outside data access, live account connectivity, preprocessing fitting, parameter search, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_models_predictions.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `ruff check .` and `python -m ruff check .` were attempted for local parity with CI, but `ruff` is not installed in this shell.

## 測試結果
- Focused prediction tests: 13 passed in 0.89s.
- `pytest`: 128 passed in 5.48s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- Local `ruff`: unavailable (`ruff` command not found; `No module named ruff`). GitHub Actions should still run ruff.

## 已知限制
- This task only adds an adapter from `ConstantBaselineResult` to `SplitPredictionBundle`. It does not wire the bundle into pipeline summaries or CLI output.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 020 - Split Prediction Bundle Contract

## 修改檔案
- `src/abc_quant/models/predictions.py`: added the frozen `SplitPredictionBundle` dataclass and `build_split_prediction_bundle(...)` validation helper.
- `src/abc_quant/models/__init__.py`: exported the prediction bundle contract.
- `tests/test_models_predictions.py`: covered valid bundles, copied Series isolation, metadata validation, non-Series inputs, empty required splits, duplicate indices, missing values, and split-index overlap.
- `docs/modeling.md`: documented the split prediction bundle contract and safety rules.
- `README.md`: documented the reusable train/validation/test prediction bundle contract.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 020 progress and completion evidence.
- `INBOX.md`: reset the active Task 020 block to the commented empty template before PR handoff.

## 實作摘要
- Added a reusable in-memory prediction-output contract for diagnostic workflows.
- `SplitPredictionBundle` stores `model_name`, optional `method`, and train/validation/test prediction Series.
- `build_split_prediction_bundle(...)` normalizes model metadata, requires pandas Series inputs, rejects empty train/test predictions, duplicate indices, missing prediction values, and overlapping split indices.
- The builder copies all accepted Series so caller mutation after bundle creation cannot change the stored predictions.
- Empty validation predictions are allowed for train/test-only diagnostic flows.
- No estimator implementation, baseline fitted value, split count, metric formula, CLI argument, summary key, file output, outside data access, live account connectivity, preprocessing fitting, parameter search, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_models_predictions.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused prediction bundle tests: 9 passed in 0.93s.
- `pytest`: 124 passed in 5.47s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only adds a reusable prediction bundle shape contract. It does not plug the bundle into the constant baseline, modeling smoke pipeline, or CLI yet.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 019 - Modeling Smoke Console Script Alias

## 修改檔案
- `pyproject.toml`: added the `abc-quant-modeling-smoke` project script pointing to `abc_quant.cli.modeling_smoke:main`.
- `tests/test_cli_entrypoints.py`: added `tomllib` metadata parsing, target import resolution, and resolved-function JSON smoke coverage.
- `docs/modeling.md`: documented the installed console-script command alongside `python -m`.
- `README.md`: documented the packaged console command.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 019 progress and completion evidence.
- `INBOX.md`: reset the active Task 019 block to the commented empty template before PR handoff.

## 實作摘要
- Added a package metadata console-script alias: `abc-quant-modeling-smoke`.
- The entry point target is exactly `abc_quant.cli.modeling_smoke:main`.
- Tests parse `pyproject.toml` with `tomllib`, import the configured target, verify it resolves to the same `main` function, and call it with `--method median` to parse valid JSON.
- `python -m abc_quant.cli.modeling_smoke` remains unchanged.
- No diagnostic calculation, summary key, CLI argument semantic, estimator implementation, file output, outside data access, live account connectivity, preprocessing fitting, parameter search, allocation logic, performance curve, or simulation engine was changed.

## 測試方式
- `python -m pytest tests\test_cli_entrypoints.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused entrypoint/CLI tests: 10 passed in 3.66s.
- `pytest`: 115 passed in 5.45s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only adds package-level discoverability for the existing CLI. It does not install the package globally or change CLI behavior.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 018 - Baseline Method Selector

## 修改檔案
- `src/abc_quant/pipeline/modeling.py`: added a `method` argument to `run_baseline_modeling_smoke(...)`, passes it to `fit_constant_baseline(...)`, and records `baseline_method`.
- `src/abc_quant/pipeline/contracts.py`: added `baseline_method` to the summary key contract and validates that it is `mean` or `median`.
- `src/abc_quant/cli/modeling_smoke.py`: added `--method` with `mean` and `median` choices.
- `tests/test_pipeline_modeling.py`: added deterministic mean/median fitted-value coverage.
- `tests/test_cli_modeling_smoke.py`: added CLI `--method median` and invalid-method coverage.
- `tests/test_pipeline_contracts.py`: added invalid `baseline_method` summary validation.
- `docs/modeling.md`: documented `method`, `baseline_method`, and CLI `--method`.
- `README.md`: documented the `--method mean|median` CLI option and summary contract update.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 018 progress and completion evidence.
- `INBOX.md`: reset the active Task 018 block to the commented empty template before PR handoff.

## 實作摘要
- `run_baseline_modeling_smoke(method="mean")` remains the default behavior.
- `run_baseline_modeling_smoke(method="median")` uses the existing constant-baseline median method and records `baseline_method="median"`.
- `python -m abc_quant.cli.modeling_smoke --method median` passes the selected method through and emits deterministic JSON.
- The smoke summary contract now includes `baseline_method` and rejects unsupported method values.
- Tests pin the smoke fixture fitted values for mean and median to prove the method changes the existing baseline selection deterministically.
- No estimator implementation, split construction, metric formula, file output, outside data access, live account connectivity, preprocessing fitting, parameter search, allocation logic, performance curve, or simulation engine was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_modeling.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused contract/pipeline/CLI tests: 23 passed in 4.59s.
- `pytest`: 112 passed in 5.77s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only exposes the existing constant-baseline method selector. It does not add a new estimator or change feature, split, or metric formulas.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 017 - Modeling Summary Contract Validator

## 修改檔案
- `src/abc_quant/pipeline/contracts.py`: added shared modeling smoke summary constants and `validate_modeling_smoke_summary(...)`.
- `src/abc_quant/pipeline/modeling.py`: validates the modeling smoke summary before returning it.
- `src/abc_quant/pipeline/__init__.py`: exports the contract constants and validator.
- `tests/test_pipeline_contracts.py`: added valid and invalid summary-shape tests.
- `tests/test_pipeline_modeling.py`: switched pipeline summary assertions to shared constants and validator.
- `tests/test_cli_modeling_smoke.py`: switched CLI key assertions to shared constants.
- `docs/modeling.md`: documented the summary contract validator.
- `README.md`: documented where the summary shape is centralized.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 017 progress and completion evidence.
- `INBOX.md`: reset the active Task 017 block to the commented empty template before PR handoff.

## 實作摘要
- Added `MODELING_SMOKE_SUMMARY_KEYS` and `EVALUATION_METRIC_KEYS` as the shared diagnostic summary contract.
- Added `validate_modeling_smoke_summary(summary)` to reject non-dict summaries, missing or unknown top-level keys, invalid evaluation containers, missing or unknown train/validation/test splits, and missing or unknown per-split metric keys.
- The validator returns the original summary object unchanged when valid.
- `run_baseline_modeling_smoke(...)` now validates the summary shape immediately before returning.
- CLI and pipeline tests now import shared constants instead of duplicating key sets.
- No numeric model calculation, prediction method, model training, preprocessing fitting, parameter search, outside data access, file writing, allocation logic, performance curve, or simulation engine was added.

## 測試方式
- `python -m pytest tests\test_pipeline_contracts.py tests\test_pipeline_modeling.py tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused contract/pipeline/CLI tests: 19 passed in 4.13s.
- `pytest`: 108 passed in 5.62s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task validates the in-memory diagnostic summary shape only. It does not change model calculations or add new modeling behavior.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 016 - Modeling Smoke Diagnostics CLI

## 修改檔案
- `src/abc_quant/cli/__init__.py`: added the CLI package marker.
- `src/abc_quant/cli/modeling_smoke.py`: added the module entry point for deterministic modeling smoke diagnostics.
- `tests/test_cli_modeling_smoke.py`: added subprocess and direct-main tests for deterministic JSON, split arguments, error handling, and diagnostic-only keys.
- `docs/modeling.md`: documented the CLI usage, arguments, stdout/stderr behavior, and diagnostic-only boundary.
- `README.md`: documented the module command and supported arguments.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 016 progress and completion evidence.
- `INBOX.md`: reset the active Task 016 block to the commented empty template before PR handoff.

## 實作摘要
- `python -m abc_quant.cli.modeling_smoke` prints the existing `run_baseline_modeling_smoke(...)` summary as deterministic sorted JSON.
- The CLI supports optional `--train-end`, `--validation-end`, and `--indent` arguments.
- Invalid temporal boundaries return a non-zero exit code and print a concise `error: ...` message to stderr.
- Tests verify repeated module invocations are byte-identical, stdout JSON matches the pipeline contract, custom split arguments change split counts deterministically, and forbidden non-diagnostic keys are absent.
- No file writing, outside data access, live account connectivity, new model type, scaler fitting, hyperparameter tuning, allocation logic, performance curve, or simulation engine was added.

## 測試方式
- `python -m pytest tests\test_cli_modeling_smoke.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused CLI tests: 5 passed in 3.56s.
- `pytest`: 98 passed in 4.64s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This CLI exposes diagnostics only. It does not add model behavior or produce trading, allocation, performance-curve, or simulation outputs.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 015 - Baseline Modeling Smoke Pipeline

## 修改檔案
- `src/abc_quant/pipeline/modeling.py`: added `run_baseline_modeling_smoke(...)` for deterministic model-diagnostics wiring.
- `src/abc_quant/pipeline/__init__.py`: exported the modeling smoke pipeline alongside existing smoke helpers.
- `tests/test_pipeline_modeling.py`: added deterministic summary, split-count, metric-key, label-feature separation, and forbidden-output-key tests.
- `docs/modeling.md`: documented the baseline modeling smoke pipeline and diagnostic-only boundary.
- `README.md`: documented the model-diagnostics smoke pipeline.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 015 progress and completion evidence.
- `INBOX.md`: reset the active Task 015 block to the commented empty template before PR handoff.

## 實作摘要
- `run_baseline_modeling_smoke(...)` builds the existing deterministic synthetic smoke frame, assembles a `FeatureMatrix`, builds a date-based `TemporalSplit`, fits the existing constant baseline, and evaluates train/validation/test predictions.
- The returned plain dictionary includes row counts, ticker counts, rows per ticker, `feature_columns`, `label_column`, label missing/non-missing counts, split counts, `fitted_value`, `training_label_count`, and train/validation/test evaluation metrics.
- The default split uses `train_end="2026-01-07"` and `validation_end="2026-01-12"` against the deterministic synthetic fixture.
- Tests verify deterministic repeated output, expected split counts, evaluation metric keys, label exclusion from feature columns, and absence of market-action, allocation, performance-curve, or simulation-result keys.
- No source adapter, outside data access, live account connectivity, new model type, scaler fitting, hyperparameter tuning, market-action output, allocation logic, performance curve, or simulation engine was added.

## 測試方式
- `python -m pytest tests\test_pipeline_modeling.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused modeling pipeline tests: 4 passed in 1.28s.
- `pytest`: 93 passed in 2.15s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only wires existing contracts into a deterministic diagnostic smoke pipeline. It is not market performance, a market-action output, allocation logic, a performance curve, or a simulation result.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 014 - Prediction Evaluation Metrics

## 修改檔案
- `src/abc_quant/models/evaluation.py`: added typed prediction evaluation results plus evaluation helpers for generic predictions and constant-baseline outputs.
- `src/abc_quant/models/__init__.py`: exported the prediction evaluation contracts.
- `tests/test_models_evaluation.py`: added tests for perfect predictions, biased predictions, missing actual labels, invalid split/index cases, and constant-baseline train/validation/test evaluation.
- `docs/modeling.md`: documented the prediction evaluation contract and no-trading/no-backtest boundary.
- `README.md`: documented the model-output diagnostics layer.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 014 progress and completion evidence.
- `INBOX.md`: reset the active Task 014 block to the commented empty template before PR handoff.

## 實作摘要
- `evaluate_predictions(actual, prediction, split_name)` evaluates one split by aligning prediction indices against actual labels.
- Returned metrics are `row_count`, `non_missing_count`, `missing_actual_count`, `mae`, `rmse`, `mean_error`, and `prediction_mean`.
- Missing actual labels are counted but excluded from `mae`, `rmse`, and `mean_error`.
- Prediction indices outside the actual-label index are rejected, as are empty split names, empty predictions, duplicate indices, missing predictions, and splits with no non-missing actual labels.
- `evaluate_constant_baseline(feature_matrix, baseline_result)` evaluates the train, validation, and test predictions returned by `fit_constant_baseline(...)`.
- No scaler fitting, hyperparameter tuning, trading signals, strategy logic, positions, equity curves, portfolio logic, source adapter, data download, or backtest engine was added.

## 測試方式
- `python -m pytest tests\test_models_evaluation.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused evaluation tests: 5 passed in 1.09s.
- `pytest`: 89 passed in 2.02s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only evaluates model-output prediction errors. It is not a trading signal, strategy, portfolio rule, equity curve, backtest, or performance claim.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 013 - Constant Baseline Model Contract

## 修改檔案
- `src/abc_quant/models/baseline.py`: added `ConstantBaselineResult` and `fit_constant_baseline(...)` for deterministic mean/median baseline predictions.
- `src/abc_quant/models/__init__.py`: exported the baseline model contract.
- `tests/test_models_baseline.py`: added tests for mean/median fitting, validation/test label isolation, missing-label behavior, prediction indices, unsupported methods, empty train split, and all-missing training labels.
- `docs/modeling.md`: documented the constant baseline contract and leakage boundary.
- `README.md`: documented the minimal model baseline and no-strategy/no-backtest boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 013 progress.
- `INBOX.md`: reset the active Task 013 block to the commented empty template before PR handoff.

## 實作摘要
- `fit_constant_baseline(feature_matrix, temporal_split, method="mean")` fits a constant from non-missing labels at `temporal_split.train_index` only.
- Supported methods are `mean` and `median`; unsupported methods raise a clear `ValueError`.
- Empty train splits and all-missing training labels are rejected.
- Returned train/validation/test predictions are pandas Series indexed by the split's sorted matrix positions.
- Validation and test labels are not read when computing `fitted_value`, so they cannot leak into the baseline.
- No new dependency, scaler fitting, hyperparameter tuning, complex ML model, strategy logic, trading signal, portfolio logic, source adapter, data download, or backtest engine was added.

## 測試方式
- `python -m pytest tests\test_models_baseline.py`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- Focused baseline tests: 5 passed in 1.07s.
- `pytest`: 84 passed in 1.81s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This is a trivial baseline contract for future model validation. It is not a production model, strategy, trading signal, portfolio rule, or performance claim.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 012 - Temporal Split Contract

## 修改檔案
- `src/abc_quant/validation/temporal.py`: added `TemporalSplit` and `build_temporal_split(...)` for deterministic date-based train/test and train/validation/test splits.
- `src/abc_quant/validation/__init__.py`: exported the temporal split contract.
- `tests/test_validation_temporal.py`: added temporal split tests for train/test, train/validation/test, shuffled metadata invariance, missing-label preservation, missing/unsortable dates, non-increasing boundaries, empty splits, and explicit `test_end` no-drop behavior.
- `docs/modeling.md`: documented the temporal split contract and pre-modeling boundary.
- `README.md`: documented modeling-preparation split behavior and constraints.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 012 progress.
- `INBOX.md`: reset the active Task 012 block to the commented empty template before PR handoff.

## 實作摘要
- `build_temporal_split(metadata, train_end, validation_end=None, test_end=None, date_column="date")` validates in-memory metadata and returns positional indices for sorted metadata.
- Rows are sorted deterministically by `date` and then `ticker` when present.
- Train rows use dates `<= train_end`; validation rows, when requested, use dates `> train_end` and `<= validation_end`; test rows start strictly after the prior split boundary.
- Boundaries must be increasing, and requested train/validation/test splits cannot be empty.
- Rows after an explicit `test_end` are rejected instead of silently dropped.
- Missing labels remain untouched; no rows are dropped or filled, and no scaler fitting, model training, strategy logic, trading signal, or backtest engine was added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 79 passed in 1.74s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only creates a temporal split contract. It does not add model baselines, walk-forward orchestration, scalers, feature importance, ablation, strategy logic, trading signals, portfolio logic, or a full backtest engine.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 011 - Feature Matrix Assembly Contract

## 修改檔案
- `src/abc_quant/features/matrix.py`: added `FeatureMatrix` and `build_feature_matrix(...)` for deterministic feature/label/metadata separation.
- `src/abc_quant/features/__init__.py`: exported the new matrix contract alongside existing feature builders.
- `tests/test_features_matrix.py`: added tests for inferred safe features, explicit feature ordering, label leakage rejection, shuffled-input invariance, missing-label preservation, missing label errors, and no-feature errors.
- `tests/test_helpers.py`: added a reusable feature-matrix equality helper for shuffled-output checks.
- `README.md`, `docs/feature_engineering.md`: documented the feature-matrix contract and boundaries.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 011 progress.
- `INBOX.md`: reset the active Task 011 block to the commented empty template before PR handoff.

## 實作摘要
- `build_feature_matrix(frame, label_column, feature_columns=None)` returns `X`, `y`, `metadata`, `feature_columns`, and `label_column`.
- Rows are sorted deterministically by `ticker` then `date`.
- Inferred feature columns exclude `date`, `ticker`, raw OHLCV columns, the explicit label column, and every `label_` column.
- Explicit feature columns preserve caller order but reject metadata, raw OHLCV, label columns, missing columns, and duplicates.
- Missing labels are preserved as evaluator targets; no rows are dropped and no scaling, imputation, filling, train/test split, model training, strategy logic, or backtest logic was added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 71 passed in 1.77s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This task only assembles already-created features and labels. It does not add feature formulas, source adapters, data downloads, model training, train/test splitting, trading signals, portfolio logic, or a backtest engine.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 010 - Technical Indicators

## 修改檔案
- `src/abc_quant/features/technical.py`: added `add_technical_indicators(...)` for pure-pandas SMA, EMA, and RSI features.
- `tests/test_features_technical.py`: added hand-calculated indicator, ticker-isolation, shuffled-input invariance, future-row mutation, and invalid-window tests.
- `README.md`, `docs/data_pipeline.md`, `docs/feature_engineering.md`: documented the technical feature module and no-signal/no-backtest boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 010 progress.
- `INBOX.md`: reset the active Task 010 block to the commented empty template before PR handoff.

## 實作摘要
- The technical feature module validates OHLCV data before computation and returns a sorted defensive copy by ticker and date.
- SMA, EMA, and RSI are computed per ticker using only current and past rows.
- RSI uses a simple rolling average of gains and losses; flat windows map to 50, gain-only windows to 100, and loss-only windows to 0 through the standard formula behavior.
- No TA-Lib, new dependency, source adapter, data download, broker integration, model training, strategy logic, trading signal, portfolio logic, or full backtest engine was added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 64 passed in 1.65s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- The module adds research features only. It does not define trading rules, model inputs, portfolio decisions, or backtest outcomes.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 009 - Feature and Label Leakage Regression Tests

## 修改檔案
- `tests/test_features_price_volume.py`: added multi-ticker isolation and shuffled-input invariance tests for price momentum, rolling volatility, and rolling volume average.
- `tests/test_labels_returns.py`: added multi-ticker forward-return label isolation, horizon/entry-lag contract, shuffled-input invariance, and missing-tail label tests.
- `tests/test_pipeline_smoke.py`: asserted the smoke label column is not part of the feature column contract.
- `OUTBOX.md`: recorded Task 009 GitHub handoff results.

## 實作摘要
- Locked price momentum to same-ticker current/past rows.
- Locked rolling volatility and volume average against cross-ticker contamination.
- Confirmed shuffled market data produces the same sorted feature and label outputs.
- Confirmed forward-return labels follow `entry_price = close[t + entry_lag]` and `exit_price = close[t + horizon]`.
- Confirmed evaluator labels remain outside feature columns and missing future rows produce missing labels.
- No data downloads, source adapters, broker integration, strategy logic, model training, trading signals, or full backtest engine were added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 58 passed in 1.46s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task`.

## 已知限制
- This is a regression-test-only task; it does not add new feature formulas, labels, strategy logic, or data ingestion.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 008 - Harden Market Data Validation

## 修改檔案
- `src/abc_quant/data/validation.py`: uses schema constants and validates numeric, missing, volume, and OHLC range rules.
- `tests/test_data_validation.py`: added adversarial tests for schema-backed required columns, ticker string normalization, non-numeric OHLCV, missing OHLCV, negative volume, high-low inversion, and open/close range violations.
- `docs/data_pipeline.md`, `README.md`: documented the enforced validation contract and smoke fixture boundary.
- `INBOX.md`: reset the active Task 008 block to the commented empty template before PR handoff.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 008 progress.

## 實作摘要
- `validate_market_data()` still returns a defensive sorted copy by ticker and date.
- Dates are normalized with `pd.to_datetime`; tickers are normalized to pandas string dtype.
- OHLCV columns are converted with `pd.to_numeric`, then checked for missing values.
- Negative volume, `high < low`, `open` outside high-low, and `close` outside high-low now raise `MarketDataValidationError`.
- No data adapters, downloads, model logic, strategy logic, portfolio logic, broker integration, or full backtest logic were added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 54 passed in 1.35s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.

## 已知限制
- This validates the deterministic OHLCV contract only; it does not add cleaning, imputation, source freshness, or real market adapters.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review after final validation passes.

## 2026-07-04 Closed-Loop Task 007 - Data Contract Smoke Pipeline

## 修改檔案
- `src/abc_quant/data/schema.py`: added required market columns, numeric columns, and dtype-intent constants.
- `src/abc_quant/data/sample.py`: added deterministic two-ticker OHLCV sample data for smoke checks.
- `src/abc_quant/pipeline/__init__.py`: added pipeline package marker.
- `src/abc_quant/pipeline/smoke.py`: added the deterministic validate -> feature -> label -> metrics smoke pipeline.
- `tests/test_data_schema.py`: added schema and sample fixture tests.
- `tests/test_pipeline_smoke.py`: added smoke pipeline summary, feature, label, metric, and multi-ticker isolation tests.
- `docs/data_pipeline.md`, `README.md`: documented the smoke fixture boundary and no-signal/no-performance-claim status.
- `INBOX.md`: reset the active Task 007 block to the commented empty template before PR handoff.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 007 progress.

## 實作摘要
- The schema contract defines `date`, `ticker`, `open`, `high`, `low`, `close`, and `volume`.
- The synthetic fixture returns two tickers with 12 deterministic rows each.
- The smoke pipeline validates the fixture, creates price/volume features, creates one 3-day forward-return label with next-period entry, computes basic metrics, and returns a summary dictionary.
- The pipeline remains local and deterministic only; it adds no data download, broker integration, strategy logic, model training, or full backtest engine.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 38 passed in 1.18s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- `python -m ruff check .`: unavailable in the current shell (`No module named ruff`); this was not part of Task 007 expected validation.

## 已知限制
- The sample fixture is synthetic and only proves local contracts and wiring.
- The metrics summary is smoke evidence only, not a trading signal, backtest result, or performance claim.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 Closed-Loop Task 006 - GitHub Actions CI

## 修改檔案
- `.github/workflows/ci.yml`: added minimal GitHub Actions CI for pull requests and pushes to `main`.
- `README.md`: documented CI quality gates and Python matrix.
- `docs/codex_closed_loop.md`: documented CI workflow behavior and boundaries.
- `INBOX.md`: reset the active Task 006 block to the commented empty template before PR handoff.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 006 governance progress.

## 實作摘要
- CI uses official `actions/checkout@v7` and `actions/setup-python@v6`.
- CI runs Python 3.11 and 3.12 because the project declares Python 3.11+ support.
- CI installs `.[dev]`, then runs `ruff check .`, `python -m pytest`, and `python -m compileall src tests`.
- No deployment, publishing, secrets, data acquisition, broker integration, model training, or trading signal changes were added.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`

## 測試結果
- `pytest`: 34 passed in 1.14s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `run_codex_closed_loop.ps1`: `status=no_task` after `INBOX.md` reset.
- `.github/workflows/ci.yml`: exists.

## 已知限制
- Local `ruff` is not required by the task validation command set; CI installs `ruff` through `.[dev]`.

## 下一步建議
- Open a draft PR for ChatGPT Tech Lead review.

## 2026-07-04 PR #3 Review Follow-up - INBOX Closeout

## 修改檔案
- `INBOX.md`: reset the active Task 005 YAML block back to the commented empty template.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`: recorded that Task 005 is complete and the inbox was cleared.

## 實作摘要
- Closed the loop after Task 005 so a merged PR does not leave an active task that returns `status=ready`.
- `scripts/run_codex_closed_loop.ps1` now returns `status=no_task`.
- No `.github/workflows/ci.yml` file was created.
- No trading, data, model, FinLab, broker API, data download, strategy, or backtest code changed.

## 測試方式
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_codex_closed_loop.ps1`
- `python -m pytest`
- `python -m compileall src tests`
- `git diff --check`

## 測試結果
- `run_codex_closed_loop.ps1`: `status=no_task`.
- `pytest`: 34 passed in 1.11s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.
- `.github/workflows/ci.yml`: absent.

## 已知限制
- This is a closeout-only commit for PR #3 review feedback.

## 下一步建議
- Re-run ChatGPT Tech Lead review on PR #3.

## 2026-07-04 Closed-Loop Task 005 - CI Target Root Preparation

## 修改檔案
- `configs/codex_closed_loop.yaml`: added `.github/` to `allowed_target_roots`.
- `tests/test_codex_loop_guard.py`: added tests proving `.github/workflows/ci.yml` is allowed while `.git/config` remains blocked.
- `docs/codex_closed_loop.md`: documented the CI target preparation boundary.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`, `TODO.md`: recorded Task 005 governance progress.

## 實作摘要
- Prepared the guard for a later reviewed CI workflow task without creating any workflow file.
- `.github/` is now an explicit allowed repository target root.
- `.git/` remains blocked through built-in blocked path defaults.
- Built-in blocked content/path defaults remain preserved when config adds custom blockers.
- No trading, data, model, broker, strategy, or backtest code changed.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`

## 測試結果
- `pytest`: 34 passed in 1.22s.
- `compileall`: passed for `src` and `tests`.
- `git diff --check`: passed.

## 已知限制
- This task only prepares the guard target root; CI workflow files are intentionally not created.

## 下一步建議
- Have ChatGPT Pro review this governance-only PR before any future task adds workflow files.

## 2026-07-04 Closed-Loop Task 004 - Final Review Audit and Guard Defaults

## 修改檔案
- `src/abc_quant/governance/codex_loop.py`: preserved built-in blocked content/path patterns when config adds custom patterns.
- `tests/test_codex_loop_guard.py`: added regression tests proving config cannot remove default `token` or `.git` blockers and cannot enable auto-merge.
- `scripts/build_review_package.py`: added two-pass final audit, output-file trailing-whitespace check, diff-check exclusion for the output file, and clearer SHA metadata.
- `reviews/review_package_002.md`: regenerated as the Task 004 review package after source changes were committed.
- `STATUS.md`, `OUTBOX.md`, `CHANGELOG.md`: recorded Task 004 governance results.

## 實作摘要
- `blocked_content_patterns` and `blocked_path_patterns` now merge config additions onto built-in defaults; config can no longer weaken the default guard.
- `allowed_risk_levels` still filters to `normal` only, and `allow_auto_merge` remains forced to `false`.
- Review package metadata now uses `source_head_sha_at_generation`, `review_package_output_file`, and `review_package_commit_sha: unavailable_self_reference`.
- Review package generation excludes `reviews/review_package_002.md` from repo-level diff checks to avoid self-reference, then separately audits the generated output file for trailing whitespace.

## 測試方式
- `python -m pytest`
- `python -m compileall src tests`
- `ruff check .`
- `git diff --check`
- `python scripts\build_review_package.py --output reviews\review_package_002.md --title "Codex Closed-Loop Task 004 Review Package" --pr-url "https://github.com/jongyawjong0514/abc-quant/pull/2" --run-validation --include-diff --include-file-contents --assert-clean`

## 測試結果
- `pytest`: 32 passed in 1.18s.
- `compileall`: passed for `src` and `tests`.
- `ruff`: unavailable in the current shell; no package was installed.
- `git diff --check`: passed before source commit; final check after package generation also passed.

## 已知限制
- `review_package_commit_sha` remains `unavailable_self_reference` because committing the review package changes the final commit SHA.
- The package excludes itself from repo-level diff sections to prevent recursive package growth, but it audits the output file directly for trailing whitespace.

## 下一步建議
- Ask ChatGPT Pro to re-review `reviews/review_package_002.md` on PR #2.
- Merge only after review approval; closed-loop policy still forbids auto-merge.

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
## 2026-07-09 Direct User Task - Zhu Walkline Shadow Scanner

## 修改檔案
- `CODEx_ZHU_WALKLINE_SHADOW_TASK.md`: 保存使用者提供的完整任務書。
- `config/zhu_walkline_shadow.yaml`, `config/concept_stock_map.yaml`: 新增 scanner 設定與人工維護概念股模板。
- `src/abc_quant/data/local_tw_loader.py`, `web_cache.py`, `web_research.py`: 新增本地 SQLite loader、官方事件 cache、官方重大訊息補充。
- `src/abc_quant/features/*walkline/chip/margin/market/news*`: 新增走圖、法人、大戶proxy、融資券、市場/類股/概念輪動與網路事件特徵。
- `src/abc_quant/signals/zhu_walkline_shadow.py`: 新增 shadow/advisory scoring、候選/風險分級與 evaluator-only forward metrics。
- `src/abc_quant/reports/zhu_walkline_report.py`: 新增 JSON/CSV/Markdown/parquet/JSONL 報告輸出。
- `scripts/run_zhu_walkline_shadow.py`: 新增 CLI 入口。
- `tests/test_zhu_walkline_features.py`, `tests/test_zhu_walkline_no_lookahead.py`, `tests/test_web_research_no_lookahead.py`: 新增 focused tests。
- `pyproject.toml`, `requirements.txt`: 新增 `pyarrow>=14.0` 以支援 parquet 輸出。

## 實作摘要
- 預設 `--no-web`；`--use-web` 僅讀本地官方 TWSE/TPEx 重大訊息 mirror 並寫入 `data/web_cache/`，不取代 OHLCV/法人/融資券。
- 所有輸出固定 `mode=shadow_advisory_only`、`formal_champion_changed=False`、`formal_trade_effect=False`。
- No-lookahead：價格、法人、融資、大戶、類股 snapshot 均以 `<= asof_date` 過濾；forward return 只在 `--evaluate-forward` evaluator 檔案輸出。

## 測試結果
- Ruff：`All checks passed!`
- Focused tests：`8 passed`。
- Full test suite：`421 passed`。
- Scanner smoke：`python scripts/run_zhu_walkline_shadow.py --asof latest --top-n 30 --no-web --verbose` 成功。
- 單檔 smoke：`--stock 6830` 成功。
- Web smoke：`--use-web --web-max-results 5` 成功。
- Forward evaluation smoke：`--asof 2026-07-01 --evaluate-forward --output-dir reports/zhu_walkline_shadow/eval_smoke` 成功。

## 資料狀態
- SQLite：找到 `C:/Users/User/Desktop/新增資料夾 (4)/state/tw_data_mirror.sqlite`。
- Price / 法人 / 融資券最新日期：`2026-07-08`。
- 大戶/TDCC 最新日期：`2026-06-26`。
- 正式大盤指數均線較股價資料舊，報告已降級使用全市場等權 proxy 並寫入 data quality warning。

## 2026-07-09 Direct User Task - Zhu Walkline Observation Points

## 修改檔案
- `src/abc_quant/signals/zhu_walkline_shadow.py`: 新增支撐壓力買賣觀察點欄位與規則。
- `src/abc_quant/reports/zhu_walkline_report.py`: 將觀察型態、trigger、目標壓力、賣點警示與失敗價輸出到 CSV、summary JSON、shadow log、Markdown。
- `tests/test_zhu_walkline_features.py`: 新增突破觀察與賣點警示欄位測試。
- `tests/test_zhu_walkline_no_lookahead.py`: 新增觀察欄位忽略未來價格列測試。
- `CHANGELOG.md`, `STATUS.md`: 記錄本輪 shadow-only 變更。

## 實作摘要
- 買點觀察型態：`SUPPORT_REBOUND`、`RESISTANCE_BREAKOUT`、`RESISTANCE_TURN_SUPPORT`、`FAILED_BREAKDOWN_RECLAIM`。
- 賣點警示型態：`RESISTANCE_REJECTION`、`SUPPORT_BREAKDOWN`、`ATTACK_K_FAILURE`、`FALSE_BREAKOUT`、`MA_SUPPORT_FAILURE`。
- 有效買點觀察必須同時具備收盤越過 trigger、量能大於 5 日或 20 日均量、收在相對高檔、非高檔長上影，且有明確 stop/invalidation reference。
- 本輪仍是 `shadow_observation_only`；不修改 formal champion，不產生正式交易指令。

## 目前驗證
- Focused tests：`tests/test_zhu_walkline_features.py tests/test_zhu_walkline_no_lookahead.py -q`，12 passed。
- Ruff focused：指定 signal/report/test 檔案，All checks passed。
- Ruff full：`ruff check .`，All checks passed。
- Full pytest：`427 passed`。
- Diff check：`git diff --check` 通過。
- Scanner smoke：`python scripts/run_zhu_walkline_shadow.py --asof latest --top-n 30 --no-web --verbose` 成功，寫出 `2026-07-09` 與 `latest` 報告。
- CSV header check：bullish watchlist 與 shadow log 包含 `buy_observation_type`、`buy_trigger_price`、`target_resistance_1`、`target_resistance_2`、`sell_warning_type`、`invalidation_price`；fall risk 包含 `sell_warning_type`、`invalidation_price`。

## 2026-07-09 Review Fix - Zhu Walkline Observation Points

## 修改檔案
- `src/abc_quant/signals/zhu_walkline_shadow.py`: hard-lock shadow mode, split main/detail observation fields, add trigger price role, strict retest logic, support-breakdown guard, target resistance filtering, and missing-value-safe price selection.
- `src/abc_quant/reports/zhu_walkline_report.py`: add `stop_reference`, detail fields, and trigger role to CSV/summary/shadow log; clean missing values; replace trade-command wording with observation wording.
- `tests/test_zhu_walkline_features.py`: add tests for mode lock, trigger role semantics, strict resistance-turn-support, support-breakdown overmarking, target resistance filtering, report wording, and missing-value output safety.
- `tests/test_zhu_walkline_no_lookahead.py`: add multi-stock future row, future high/low/volume, future chip/margin/holder, and future retest no-lookahead tests.
- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: record the review fix and formal-boundary guarantees.

## 實作摘要
- `ZhuWalklineResult.mode` is always `shadow_observation_only`; config attempts to set another mode are ignored with a run note.
- `buy_observation_type` and `sell_warning_type` are single highest-priority main fields; complete details are in `buy_observation_detail_types` and `sell_warning_detail_types`.
- `buy_trigger_price_role` clarifies `TRIGGERED_PRICE` versus `NEXT_CONFIRMATION_PRICE` versus `EMPTY`; Markdown states untriggered prices are confirmation observation prices, not buy prices.
- `RESISTANCE_TURN_SUPPORT` now requires an old resistance, prior close above it, current retest near it, current close above it, no same-candle first breakout, and no high-level upper-shadow supply pressure.
- `SUPPORT_BREAKDOWN` requires a clear broken support zone, support zone, or previous low breach; `price_down_volume_up` remains risk context but is not enough by itself.
- `target_resistance_1/2` only outputs resistance above current close; lower/equal fallback levels are blank.
- CSV/JSON/Markdown output avoids `nan`, `None`, and `<NA>` strings.
- Report language uses `續強觀察條件`, `風險升高觀察條件`, `訊號失效觀察條件`, and explicitly states: `不是買進名單，不是賣出指令，僅為支撐壓力觀察價與訊號失效價。`

## 硬邊界
- `mode=shadow_observation_only`
- `formal_champion_changed=False`
- `formal_trade_effect=False`
- no formal strategy modified
- no formal champion modified
- no formal trade effect
- 不產生交易指令
- 不輸出絕對買賣建議

## 目前驗證
- Ruff：project `.venv` `ruff check .`，All checks passed。
- Focused tests：`python -m pytest tests/test_zhu_walkline_features.py tests/test_zhu_walkline_no_lookahead.py -q`，25 passed。
- Full pytest：`python -m pytest -q`，440 passed。
- Diff check：`git diff --check` 通過。
- Scanner smoke：`python scripts/run_zhu_walkline_shadow.py --asof latest --top-n 30 --no-web --verbose` 成功，寫出 `2026-07-09` 與 `latest` 報告。
- Output audit：bullish watchlist、fall risk、shadow log、summary JSON 均含 required `stop_reference`/detail/role 欄位；CSV 未出現 `nan`、`None`、`<NA>` 字串；market/stock reports 含 required observation disclaimer。

## 2026-07-10 User Request - Backtest 2026-01 to 2026-05

## 修改檔案
- `scripts/backtest_zhu_walkline_shadow_range.py`: 新增區間回測 sidecar，逐交易日跑 Zhu walkline shadow scanner 與 evaluator-only forward outcomes，輸出 evaluations/daily metrics/summary。
- `src/abc_quant/features/market_rotation.py`: 歷史正式大盤資料缺 `volume` 時改用等權市場 proxy，避免 `_add_market_rolling` 在 Jan 2026 as-of 中斷。
- `tests/test_zhu_walkline_features.py`: 新增 official market history 缺 `volume` 時 fallback proxy 的 regression test。
- `CHANGELOG.md`, `STATUS.md`, `OUTBOX.md`: 記錄本輪回測與 hard boundary。

## 回測指令
```powershell
python scripts/backtest_zhu_walkline_shadow_range.py --start-date 2026-01-01 --end-date 2026-05-31 --top-n 30 --output-dir reports/zhu_walkline_shadow_backtest_2026_01_05 --verbose
```

## 產出檔案
- `reports/zhu_walkline_shadow_backtest_2026_01_05/zhu_walkline_range_evaluations.csv`
- `reports/zhu_walkline_shadow_backtest_2026_01_05/zhu_walkline_range_daily_metrics.csv`
- `reports/zhu_walkline_shadow_backtest_2026_01_05/zhu_walkline_range_summary.json`
- `reports/zhu_walkline_shadow_backtest_2026_01_05/zhu_walkline_range_summary.md`
- `reports/zhu_walkline_shadow_backtest_2026_01_05/run.log`
- `reports/zhu_walkline_shadow_backtest_2026_01_05/run.err.log`

## 回測摘要
- Requested range：`2026-01-01` ~ `2026-05-31`
- Resolved trading dates：`2026-01-02` ~ `2026-05-29`
- Trading days：95
- Evaluator rows：5,368
- `run.err.log`：empty
- Market states：`MARKET_STRONG_UPTREND` 55 days, `MARKET_PULLBACK_IN_UPTREND` 26 days, `MARKET_RANGE_BOUND` 14 days。

## 全段平均
- `rise_hit_rate_d1=0.522470`
- `rise_hit_rate_d3=0.508352`
- `rise_hit_rate_d5=0.529002`
- `rise_avg_forward_return_d5=0.028781`
- `rise_median_forward_return_d5=0.006783`
- `rise_tail_loss_rate_d5=0.344207`
- `fall_hit_rate_d5=0.506667`
- `fall_avg_forward_return_d5=0.004272`
- `fall_median_forward_return_d5=-0.002529`
- `fall_tail_loss_rate_d5=0.246612`

## 月度 D+5 摘要
| month | side | rows | hit_d5 | avg_d5 | median_d5 | tail_loss_d5 |
|---|---|---:|---:|---:|---:|---:|
| 2026-01 | rise | 628 | 0.466561 | 0.010097 | -0.005606 | 0.396497 |
| 2026-02 | rise | 287 | 0.550523 | 0.034863 | 0.009615 | 0.306620 |
| 2026-03 | rise | 461 | 0.416486 | 0.004483 | -0.013793 | 0.431670 |
| 2026-04 | rise | 551 | 0.626134 | 0.053481 | 0.036585 | 0.266788 |
| 2026-05 | rise | 591 | 0.582064 | 0.041292 | 0.021645 | 0.292724 |
| 2026-01 | fall | 630 | 0.504762 | 0.009032 | -0.001663 | 0.192063 |
| 2026-02 | fall | 360 | 0.486111 | 0.001511 | 0.000000 | 0.241667 |
| 2026-03 | fall | 660 | 0.587879 | -0.007461 | -0.010176 | 0.316667 |
| 2026-04 | fall | 600 | 0.510000 | 0.005521 | -0.005508 | 0.241667 |
| 2026-05 | fall | 600 | 0.428333 | 0.012966 | 0.002703 | 0.200000 |

## 硬邊界
- `mode=shadow_observation_only`
- `formal_champion_changed=False`
- `formal_trade_effect=False`
- no formal strategy modified
- no formal champion modified
- no formal trade effect
- 不產生交易指令
- 不輸出絕對買賣建議
- 本回測是 observation-only gross forward outcome，不是交易 PnL；未套用交易成本/滑價，因為沒有模擬成交、部位或持倉。
