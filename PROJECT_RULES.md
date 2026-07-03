# PROJECT_RULES.md

此文件是 ABC Quant AI Research Platform 的最高優先規則。Codex、ChatGPT 與任何自動化工具在修改專案前都必須先遵守本文件。

---

## 1. 專案總目標

本專案目標是建立一套針對台股市場的 AI 量化研究平台，用於：

1. 資料整理與清洗。
2. 技術面、籌碼面、基本面與行為金融特徵工程。
3. 機器學習與深度學習模型訓練。
4. 回測、風控、交易成本與滑價模擬。
5. 策略評估、報告產生與長期迭代。

本專案不是一次性 notebook，不接受不可重現、不可測試、不可維護的實作。

---

## 2. 角色分工

### 2.1 使用者

使用者負責定義高層目標，例如：

- 想研究的交易邏輯。
- 偏好的交易週期。
- 可接受風險。
- 是否偏重勝率、報酬率、回撤控制或穩定性。

使用者不需要負責提出具體程式修改建議。

### 2.2 ChatGPT：Quant Tech Lead

ChatGPT 負責：

- 將需求拆解為具體任務。
- 撰寫 PRD、技術規格與 Codex 任務。
- 審查 Codex 產出。
- 主動檢查資料洩漏、前視偏誤、過度擬合與工程風險。
- 產生下一輪 Codex Prompt。

### 2.3 Codex：Implementation Engineer

Codex 負責：

- 按照規格實作。
- 重構現有程式。
- 撰寫測試。
- 修復錯誤。
- 不得自行改變研究目標與交易假設。

---

## 3. 嚴格禁止事項

以下問題一律視為重大缺陷：

1. 使用未來資料建立特徵。
2. 在訓練資料中包含測試期資訊。
3. 以全期間資料標準化後再切分 train/test。
4. 使用回測結果反覆調參，卻未設 out-of-sample 驗證。
5. 忽略交易成本、手續費、交易稅與滑價。
6. 使用 survivorship-biased 股票池。
7. 把缺失資料任意補零而未記錄原因。
8. 在策略績效中只報酬年化報酬率，不報最大回撤、Sharpe、Sortino、換手率與交易次數。
9. 在模型中只有 accuracy，沒有 precision、recall、AUC、profit factor 或交易層面的評估。
10. 把 notebook 當正式系統主體。
11. 建立大型單一檔案，導致無法測試與維護。
12. 任務完成後沒有更新 CHANGELOG 或 TODO。

---

## 4. 資料處理規範

### 4.1 時間索引

所有市場資料必須明確包含：

- `date`
- `ticker`
- 原始欄位
- 計算後欄位

不得使用模糊命名，例如 `time`, `code`, `x1`, `data1`。

### 4.2 資料延遲

基本面與財報資料不得假設在財報期間結束當天即可取得。必須考慮公告日或至少設定保守延遲。

範例：

- 月營收：使用公告日或保守延遲。
- 季報：使用公告日或保守延遲。
- 法人籌碼：確認資料實際可取得時間。

### 4.3 缺失值

缺失值處理必須記錄：

- 缺失原因。
- 補值方式。
- 是否新增 missing indicator。
- 是否會造成偏誤。

---

## 5. 特徵工程規範

### 5.1 特徵分類

特徵至少分成以下類別：

1. 價量特徵。
2. 趨勢特徵。
3. 波動特徵。
4. 籌碼特徵。
5. 基本面特徵。
6. 行為金融特徵。
7. 市場狀態特徵。

### 5.2 特徵計算原則

每個特徵必須符合：

- 僅使用當下或過去資料。
- rolling window 不得穿越未來。
- rank / z-score 必須在當期橫截面或過去時間窗計算。
- train/test 切分前不得使用全樣本 fit scaler。

### 5.3 特徵命名

建議格式：

```text
{domain}_{concept}_{window}_{transform}
```

範例：

```text
price_momentum_20d_rank
volume_turnover_10d_zscore
chip_foreign_buy_5d_sum
fundamental_revenue_yoy_rank
```

---

## 6. 模型訓練規範

### 6.1 Baseline 優先

任何複雜模型前必須先建立 baseline：

1. Buy-and-hold benchmark。
2. Market-cap 或 equal-weight universe benchmark。
3. Simple rule-based strategy。
4. Logistic Regression 或 LightGBM baseline。

不得直接從深度學習模型開始。

### 6.2 驗證方法

至少支援：

- Time-series split。
- Walk-forward validation。
- Out-of-sample test。

在進階階段可加入：

- Purged K-Fold。
- Embargo period。
- Regime-based validation。
- Bootstrap / Monte Carlo robustness test。

### 6.3 標籤設計

標籤必須清楚定義：

- 預測期間。
- 報酬計算方式。
- 是否扣除交易成本。
- 是否使用分類、回歸或排序目標。
- 是否有 class imbalance。

範例：

```text
label_20d_forward_return = close[t+20] / close[t+1] - 1
```

注意：若在收盤後決策，買進價應從下一交易日開始計算，不得用同日收盤價假設成交，除非明確定義。

---

## 7. 回測規範

回測引擎必須顯式處理：

1. 進出場價格。
2. 交易成本。
3. 交易稅。
4. 滑價。
5. 資金配置。
6. 持倉上限。
7. 單股權重上限。
8. 停損與停利。
9. 再平衡頻率。
10. 可交易性限制。

### 7.1 最低績效報告要求

每次回測至少輸出：

- Total return。
- CAGR。
- Annual volatility。
- Sharpe ratio。
- Sortino ratio。
- Max drawdown。
- Calmar ratio。
- Win rate。
- Profit factor。
- Turnover。
- Average holding period。
- Number of trades。

---

## 8. 程式設計規範

### 8.1 Python 版本

預設使用 Python 3.11 以上。

### 8.2 程式風格

- 使用 type hints。
- 使用 dataclass 或 pydantic 管理設定。
- 模組保持單一職責。
- 不得在函式中硬編碼絕對路徑。
- 不得在核心邏輯中直接 print，應使用 logging。
- IO、計算、模型、回測必須分層。

### 8.3 測試

每次新增核心邏輯必須新增測試。測試至少包含：

- 正常案例。
- 邊界案例。
- 缺失資料案例。
- 防資料洩漏案例。

---

## 9. 檔案與模組規劃

建議架構：

```text
src/abc_quant/
├── config/
├── data/
├── features/
├── labels/
├── models/
├── validation/
├── backtesting/
├── metrics/
├── reports/
└── utils/
```

### 9.1 不接受的架構

```text
main.py              # 裝下所有邏輯
strategy.py          # 混合資料、模型、回測、報告
notebook.ipynb       # 作為正式系統
```

---

## 10. Codex 每次任務必須遵守的輸出格式

Codex 完成任務後必須提供：

1. 修改檔案清單。
2. 每個檔案修改摘要。
3. 如何執行測試。
4. 測試結果。
5. 已知限制。
6. 下一步建議。

若 Codex 無法執行測試，必須說明原因，不得假裝測試通過。

---

## 11. ChatGPT Review Checklist

ChatGPT 審查 Codex 產物時，必須檢查：

### 11.1 研究面

- 假設是否清楚。
- 是否有 baseline。
- 是否有 out-of-sample。
- 是否過度依賴單一期間。

### 11.2 資料面

- 是否有資料洩漏。
- 是否有前視偏誤。
- 是否考慮公告延遲。
- 是否處理缺失值。

### 11.3 模型面

- 特徵是否合理。
- 標籤是否合理。
- 是否有過度擬合風險。
- 是否有特徵重要度與 ablation 計畫。

### 11.4 回測面

- 是否扣除成本。
- 是否處理滑價。
- 是否有持倉限制。
- 是否有換手率。
- 是否只挑好看的區間。

### 11.5 工程面

- 是否模組化。
- 是否有 type hints。
- 是否有 logging。
- 是否有 tests。
- 是否容易擴充。

---

## 12. 每輪任務流程

每輪固定流程：

```text
ChatGPT 產生任務規格
↓
Codex 實作
↓
Codex 提交變更摘要
↓
ChatGPT 審查
↓
ChatGPT 產生修正任務
↓
Codex 修正
```

使用者只需負責把 Codex 輸出貼回 ChatGPT，不需要自己想技術建議。

---

## 13. 優先順序

若規則衝突，依下列順序：

1. 避免資料洩漏與前視偏誤。
2. 研究可重現性。
3. 測試完整性。
4. 系統可維護性。
5. 模型複雜度。
6. 短期績效。

短期績效永遠不得凌駕於資料正確性與可重現性。
