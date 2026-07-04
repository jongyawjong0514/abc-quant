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

## Phase 3：模型

- [x] 建立 temporal split contract。
- [x] Baseline 模型。
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
