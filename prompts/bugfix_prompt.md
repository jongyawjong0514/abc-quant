# Bugfix Prompt

用於交給 Codex 修復錯誤。

---

你是 ABC Quant AI Research Platform 的 Implementation Engineer。請修復以下錯誤，並遵守 `PROJECT_RULES.md`。

## 錯誤描述

<<<PASTE_ERROR_DESCRIPTION_HERE>>>

## 相關輸出

```text
<<<PASTE_TRACEBACK_OR_TEST_OUTPUT_HERE>>>
```

## 限制

1. 不要重寫無關模組。
2. 不要移除測試來讓測試通過。
3. 不要降低資料驗證標準。
4. 不要引入資料洩漏。

## 完成後請回報

```text
## 根因分析

## 修改檔案

## 測試方式

## 測試結果

## 是否有殘留風險
```
