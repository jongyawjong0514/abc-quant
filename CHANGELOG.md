# CHANGELOG

## Unreleased

- 完成 ChatGPT Review 001，確認第一輪 scaffold 可接受並記錄下一輪修正 prompt。
- 固定 pytest 本地暫存目錄並停用 cache provider，避免 Windows 受限暫存/cache 目錄造成驗收失敗或警告。
- 新增 `.gitignore`，排除 venv、cache、egg-info、打包 zip、解壓副本與本機 Codex context capsule。

## 0.0.1 - Project bootstrap

- 建立 ABC Quant AI Research Platform 專案骨架。
- 建立 `PROJECT_RULES.md` 作為 Codex 與 ChatGPT 協作規範。
- 建立初始文件、Prompt、程式碼目錄與測試目錄。

## 0.0.2 - First executable research scaffold

- 建立 YAML 設定載入、OHLCV 資料驗證、價量 rolling 特徵、forward return label 與基礎績效指標。
- 新增資料驗證、防未來資料洩漏、label shift 與績效指標測試。
