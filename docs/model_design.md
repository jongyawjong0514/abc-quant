# Model Design

## 初始模型順序

模型複雜度必須循序增加：

1. Rule-based baseline。
2. Logistic Regression / Linear Model。
3. LightGBM / XGBoost 類模型。
4. Ranking model。
5. 深度學習或序列模型。

## 模型任務形式

可選任務：

- Classification：預測未來 N 日是否進入 top quantile。
- Regression：預測未來 N 日報酬。
- Ranking：預測橫截面相對排名。

## 評估方式

不得只使用 ML 指標。必須同時評估：

- IC / Rank IC。
- Top quantile return。
- Long-only portfolio return。
- Drawdown。
- Turnover。
- Cost-adjusted return。
