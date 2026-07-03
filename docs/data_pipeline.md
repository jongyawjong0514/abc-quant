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

## 資料品質檢查

必須檢查：

- 必要欄位是否存在。
- `date` 是否可解析。
- 同一 `date` + `ticker` 是否重複。
- 價格是否為正。
- high 是否大於等於 low。
- volume 是否非負。

## 資料版本

正式研究應記錄：

- 資料來源。
- 匯入時間。
- 股票池定義。
- 是否包含下市股票。
- 欄位定義。
