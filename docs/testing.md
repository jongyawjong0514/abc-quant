# Testing

## 測試目標

測試不只是檢查程式不報錯，更要檢查研究邏輯是否安全。

## 必要測試類型

1. Schema validation tests。
2. Look-ahead prevention tests。
3. Label alignment tests。
4. Metric calculation tests。
5. Edge case tests。

## Look-ahead 測試概念

對 rolling feature，測試方式：

1. 建立一組簡單時間序列。
2. 手算某一天應該使用的歷史資料。
3. 確認 feature 不受未來值改變影響。

## Label alignment 測試概念

若 `entry_lag=1` 且 `horizon=20`，則第 `t` 日 label 應與 `t+1` 到 `t+20` 或明確定義的未來區間一致。不可混淆同日決策與同日成交。
