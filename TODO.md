# TODO

## Phase 0：專案基礎

- [x] 建立專案目錄。
- [x] 建立 PROJECT_RULES.md。
- [x] 建立 Codex 主控 Prompt。
- [x] 建立 Review Prompt。
- [x] 建立文件骨架。
- [x] 由 Codex 完成第一版可測試程式骨架。
- [x] 由 ChatGPT 審查 Codex 第一輪產出。

## Phase 1：資料層

- [x] 定義資料格式。
- [x] 建立資料驗證。
- [x] 強化 OHLCV validation contract。
- [ ] 建立資料清洗流程。
- [ ] 建立資料版本管理規範。
- [ ] 加入 FinLab 或本地資料來源介面。

## Phase 2：特徵工程

- [x] 價量特徵。
- [x] 技術指標特徵。
- [x] 建立 feature matrix 組裝契約。
- [ ] 籌碼特徵。
- [ ] 基本面特徵。
- [ ] 市場狀態特徵。
- [x] 特徵洩漏測試。
- [x] 建立主力／無上影／量比／融資變化四項等權影子強度分數與 holdout 驗證。
- [x] 建立指定日期 scanner KD 確認事件的每日四項 shadow 排名輸出。
- [x] 將四項 shadow strength 串入每日 scanner 並設為日期型報告預設主要排序。
- [x] 以 2026H1 完整標籤、時間切分與未見樣本最佳化 T-5／T-3／T-1 提早起漲影子參數；結果未支持早於 T-1 的硬篩選。
- [x] 建立 D-10～D 逐日技術／四項影子軌跡，補上 label-maturity purge 與提醒日到同一 D+5 endpoint 評估。
- [x] 以單一凍結 D-4 規則重播 2026H1 TWSE/TPEX point-in-time 全市場；結果 precision lift 0.83x、balanced accuracy 49.91%，拒絕加入 early hard filter。
- [x] 深挖 D-10～D 的 61 項技術與 48 項落後法人量因子，完成共同市場 D+1→D+5、成本、冷卻、公司行動、機率校準與 5 日區塊 bootstrap 比較。
- [x] 建立 PIT 產業分層與 beta-binomial 部分池化報告；確認產業診斷有用，但樣本不足以按產業調參。
- [x] 建立共同市場交易日曆的 D-5／D-3／D-1 提早低點日報；量比與月線為核心，小實體與下影只作不影響入池的 5 分加分。
- [x] 建立四個互斥 D+5 結果、單調機率、PIT lineage、空市場狀態覆蓋與 fail-closed 排序狀態。
- [ ] 以 2026-07-14 後全新 forward shadow 資料驗證提早低點池；不得用已查看的 2026H1／07-13 結果調高下影、小實體或 probability-edge 權重。
- [ ] 補做純技術高信心門檻的每日容量上限、holdout 起點 cooldown reset／連續暖機及 2026-07-14 後前向影子複驗。
- [ ] 從 2026-07-09 起累積 point-in-time 概念股多標籤快照；資料成熟前不得回填 2026H1 或用於 promotion。
- [ ] 建立 point-in-time 自由流通市值／流動性分層；普通股股本只作 historical-vintage-unverified sensitivity。
- [ ] 自 2026-07-14 後前向累積新的全市場 shadow candidates，再以 expanding walk-forward 複驗；不得用已查看的 Jan-Jun 或 May-Jun 重調固定規則。

## Phase 3：模型

- [x] 建立 temporal split contract。
- [x] Baseline 模型。
- [x] 模型預測誤差評估。
- [x] Baseline modeling smoke pipeline。
- [x] Baseline modeling smoke CLI diagnostics。
- [x] Modeling smoke summary contract validator。
- [x] Modeling smoke constant-baseline method selector。
- [x] Modeling smoke packaged console-script alias。
- [x] Split prediction bundle diagnostics contract。
- [x] Constant-baseline prediction bundle adapter。
- [x] Split prediction bundle evaluator。
- [x] Wire bundle evaluation into modeling smoke pipeline。
- [x] Train-only feature standardization contract。
- [x] Deterministic preprocessing smoke diagnostics。
- [x] Preprocessing smoke summary contract validator。
- [x] Preprocessing smoke CLI diagnostics。
- [x] Preprocessing smoke packaged console-script alias。
- [x] Supervised split dataset contract。
- [x] Deterministic supervised dataset smoke diagnostics。
- [x] Supervised dataset smoke summary contract validator。
- [x] Supervised dataset smoke CLI diagnostics。
- [x] Supervised dataset smoke packaged console-script alias。
- [x] Train-only ordinary least-squares regression contract。
- [x] Deterministic train-only OLS smoke diagnostics。
- [x] Linear regression smoke summary contract validator。
- [x] OLS smoke CLI diagnostics。
- [x] OLS smoke packaged console-script alias。
- [x] Prediction evaluation comparison contract。
- [x] Deterministic baseline versus OLS comparison smoke diagnostics。
- [x] Model comparison smoke summary contract validator。
- [x] Model comparison smoke CLI diagnostics。
- [x] Model comparison smoke packaged console-script alias。
- [x] LightGBM optional dependency guard and parameter contract。
- [x] LightGBM train-only fitting contract。
- [x] LightGBM dependency smoke diagnostics。
- [x] LightGBM dependency smoke CLI diagnostics。
- [x] LightGBM dependency smoke packaged command alias。
- [x] LightGBM dependency smoke summary contract validator。
- [x] LightGBM dependency smoke summary contract package exports。
- [x] LightGBM optional evaluation smoke diagnostics。
- [x] Walk-forward split contract。
- [x] Walk-forward supervised dataset smoke diagnostics。
- [x] Walk-forward constant-baseline evaluation smoke diagnostics。
- [ ] LightGBM。
- [ ] Walk-forward validation。
- [ ] 模型解釋。
- [ ] Ablation study。

## Phase 4：回測

- [ ] 交易成本。
- [ ] 滑價。
- [ ] 部位限制。
- [ ] 換手率。
- [ ] 停損停利。
- [ ] 報告產生。

## Phase 5：研究治理

- [ ] 每次實驗寫入 `research/experiments.md`。
- [ ] 每次 Codex 變更後寫入 `CHANGELOG.md`。
- [x] 每輪 ChatGPT Review 寫入 `reviews/`。
- [x] 建立 Codex/ChatGPT Pro 檔案式閉環守門器。
- [x] 準備 `.github/` 作為未來 CI workflow 的 closed-loop target root。
- [x] 建立最小 GitHub Actions CI quality gates。
- [ ] 審查第一輪自動化閉環輸出並調整 cadence。
