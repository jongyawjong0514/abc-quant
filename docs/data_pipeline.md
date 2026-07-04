# Data Pipeline

## 資料來源

初始階段可支援：

1. CSV 本地檔案。
2. Parquet 本地檔案。
3. 日後再加入 FinLab 或其他資料庫介面。

## 標準市場資料格式

必要欄位：

```text
date
ticker
open
high
low
close
volume
```

`src/abc_quant/data/schema.py` 定義第一版 deterministic market data contract：

- `MARKET_REQUIRED_COLUMNS`: `date`, `ticker`, `open`, `high`, `low`, `close`, `volume`
- `MARKET_NUMERIC_COLUMNS`: `open`, `high`, `low`, `close`, `volume`
- `MARKET_DTYPE_INTENT`: 每個欄位的預期 dtype 意圖

## Deterministic Smoke Fixture

`src/abc_quant/data/sample.py` 提供 `sample_market_data()`，只用於本地 smoke checks。

此 fixture 是合成資料，不是實際市場資料，不是交易訊號，也不是績效主張。它的用途是讓資料驗證、價量特徵、forward-return label 與 basic metrics 可以用固定輸入做端到端檢查。

`src/abc_quant/pipeline/smoke.py` 提供：

- `build_smoke_frame()`: validate sample -> add price/volume features -> add one forward-return label
- `run_smoke_pipeline()`: 回傳 row count、ticker count、feature columns、label column、metric keys 與 basic metrics summary

## 資料品質檢查

必須檢查：

- 必要欄位是否存在。
- `date` 是否可解析，並在驗證後轉為 datetime。
- `ticker` 是否存在，並在驗證後轉為 string。
- 同一 `date` + `ticker` 是否重複。
- OHLCV 欄位是否為 numeric。
- OHLCV 欄位是否缺值。
- high 是否大於等於 low。
- volume 是否非負。
- open 是否落在 high-low range 內。
- close 是否落在 high-low range 內。

## 資料版本

正式研究應記錄：

- 資料來源。
- 匯入時間。
- 股票池定義。
- 是否包含下市股票。
- 欄位定義。
