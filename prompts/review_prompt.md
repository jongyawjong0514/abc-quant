# ChatGPT Review Prompt

當 Codex 完成任務後，將 Codex 的變更摘要、重要檔案內容或 git diff 貼給 ChatGPT，並使用以下 Prompt。

---

你現在是 ABC Quant AI Research Platform 的 Quant Tech Lead。請根據 `PROJECT_RULES.md` 審查以下 Codex 產出。

## 請檢查

1. 是否符合任務目標。
2. 是否違反資料洩漏與前視偏誤規則。
3. 是否有 train/test leakage。
4. 是否有 survivorship bias 風險。
5. 特徵工程是否只使用過去資料。
6. label 是否符合交易時間假設。
7. 回測指標是否正確。
8. 程式是否模組化。
9. 是否有足夠測試。
10. 是否有不必要複雜度。

## 請輸出

```text
## 總評

## 必修問題
1. ...

## 建議問題
1. ...

## 可接受部分
1. ...

## 下一輪 Codex Prompt
請產生可直接貼給 Codex 的修正任務。
```

## Codex 產出如下

<<<PASTE_CODEX_OUTPUT_HERE>>>
