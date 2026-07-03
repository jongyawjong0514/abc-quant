# RUN_CODEX_NEXT.md

請把以下內容完整貼給 Codex，作為第一輪任務。

---

## Codex 任務：初始化 ABC Quant AI Research Platform

你是本專案的 Implementation Engineer。請先閱讀並遵守：

1. `PROJECT_RULES.md`
2. `README.md`
3. `docs/architecture.md`
4. `prompts/codex_master.md`

### 任務目標

請完成第一版可執行的專案骨架，重點不是建立完整交易策略，而是建立乾淨、可測試、可擴充的量化研究平台基礎。

### 修改範圍

允許修改：

- `src/abc_quant/**`
- `tests/**`
- `configs/**`
- `scripts/**`
- `pyproject.toml`
- `requirements.txt`

除非必要，不要修改：

- `PROJECT_RULES.md`
- `prompts/**`
- `docs/**`

### 具體要求

1. 建立設定載入模組。
   - 支援 YAML 設定檔。
   - 不得硬編碼本機絕對路徑。
   - 提供清楚的錯誤訊息。

2. 建立資料結構驗證模組。
   - 檢查 market data 必須包含 `date`, `ticker`, `open`, `high`, `low`, `close`, `volume`。
   - 檢查 `date` 可排序。
   - 檢查同一 `date` + `ticker` 不重複。

3. 建立基礎特徵工程模組。
   - 實作 rolling momentum。
   - 實作 rolling volatility。
   - 實作 rolling volume average。
   - 所有 rolling 特徵必須只使用過去資料，避免 look-ahead。

4. 建立標籤產生模組。
   - 實作 forward return label。
   - 預設使用下一期進場假設，避免同日收盤決策又同日收盤成交。
   - 清楚註解 label 的時間定義。

5. 建立基礎回測績效指標。
   - total return
   - CAGR
   - annual volatility
   - Sharpe ratio
   - max drawdown

6. 建立測試。
   - 測試資料驗證。
   - 測試 rolling 特徵沒有使用未來資料。
   - 測試 forward return label 的 shift 是否正確。
   - 測試績效指標在簡單序列上的結果。

### 禁止事項

- 不要下載資料。
- 不要串接券商 API。
- 不要建立複雜模型。
- 不要使用未來資料。
- 不要建立大型單檔架構。
- 不要把所有邏輯寫進 `main.py`。

### 驗收標準

執行以下指令應通過：

```bash
pytest
```

若尚未安裝專案，可使用：

```bash
pip install -e .
pytest
```

### Codex 完成後必須回報

請用以下格式回報：

```text
## 修改檔案
- ...

## 實作摘要
- ...

## 測試方式
- ...

## 測試結果
- ...

## 已知限制
- ...

## 下一步建議
- ...
```
