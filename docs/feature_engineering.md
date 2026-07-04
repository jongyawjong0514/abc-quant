# Feature Engineering

## 初始特徵

第一階段只建立容易驗證的特徵：

- momentum：過去 N 日報酬。
- volatility：過去 N 日報酬標準差。
- volume average：過去 N 日平均成交量。
- SMA：過去 N 日收盤價簡單移動平均。
- EMA：過去 N 日收盤價指數移動平均。
- RSI：過去 N 日漲跌幅簡化相對強弱指標。

## 時間安全原則

若在第 `t` 日收盤後產生訊號，則：

- 特徵可以使用第 `t` 日收盤以前的資料。
- 進場價格不應假設為第 `t` 日收盤，除非策略明確可於收盤前決策。
- 預設應使用第 `t+1` 日之後的價格作為交易價格基礎。

## Feature Matrix Assembly

`src/abc_quant/features/matrix.py` defines `build_feature_matrix(...)` for safe
research dataset assembly after features and labels already exist.

- Inputs are sorted deterministically by `ticker` then `date`.
- `metadata` contains only `date` and `ticker`, preserving one row per input row.
- `X` contains only feature columns.
- `y` contains the explicit evaluator target column.
- Inferred features exclude `date`, `ticker`, raw OHLCV columns, and every
  column whose name starts with `label_`.
- Explicit `feature_columns` preserve caller-provided order but reject metadata,
  raw OHLCV, and label columns.
- Missing labels are preserved; the builder does not drop, fill, scale, impute,
  or split the data.

## 後續特徵池

後續可加入：

- KD, MACD, William %R。
- 均線排列。
- 波動收斂。
- 突破前高。
- 法人買賣超。
- 主力籌碼集中度。
- 月營收成長。
- 毛利率、營益率。
- 市場寬度。
