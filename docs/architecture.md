# Architecture

## 目標架構

ABC Quant 採用分層架構：

```text
Data Source
  ↓
Data Validation
  ↓
Data Cleaning
  ↓
Feature Engineering
  ↓
Label Generation
  ↓
Model Training / Ranking
  ↓
Portfolio Construction
  ↓
Backtesting
  ↓
Metrics / Reports
```

## 模組責任

### `config/`

讀取 YAML 設定與環境設定。

### `data/`

處理資料載入、欄位驗證、索引檢查、資料品質檢查。

### `features/`

特徵工程。所有特徵必須只使用當下或過去資料。

### `labels/`

產生 supervised learning label。label 必須明確定義交易假設。

### `models/`

模型訓練與推論。不得在模型模組內做資料下載或回測。

### `validation/`

時間序列切分、walk-forward、out-of-sample 驗證。

### `backtesting/`

根據模型訊號或規則訊號模擬交易。

### `metrics/`

績效指標與風險指標。

### `reports/`

輸出 markdown、html 或圖表報告。

## 設計原則

1. 資料與模型分離。
2. 模型與回測分離。
3. 回測與報告分離。
4. 每層可單獨測試。
5. 每個函式只做一件事。
