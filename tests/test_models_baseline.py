import pandas as pd
import pytest

from abc_quant.features.matrix import FeatureMatrix, build_feature_matrix
from abc_quant.models.baseline import ConstantBaselineResult, fit_constant_baseline
from abc_quant.validation.temporal import TemporalSplit, build_temporal_split


LABEL_COLUMN = "label_forward_return_3d_entry_lag_1d"


def _model_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    labels = {
        ("2026-01-01", "2317"): 1.0,
        ("2026-01-01", "2330"): 3.0,
        ("2026-01-02", "2317"): pd.NA,
        ("2026-01-02", "2330"): 7.0,
        ("2026-01-03", "2317"): 100.0,
        ("2026-01-03", "2330"): 200.0,
        ("2026-01-04", "2317"): 300.0,
        ("2026-01-04", "2330"): 400.0,
        ("2026-01-05", "2317"): pd.NA,
        ("2026-01-05", "2330"): 600.0,
    }
    for ticker in ("2330", "2317"):
        for date in pd.date_range("2026-01-01", periods=5, freq="D"):
            label = labels[(date.strftime("%Y-%m-%d"), ticker)]
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.0,
                    "close": 10.5,
                    "volume": 1000,
                    "feature_alpha": len(rows) + 0.5,
                    LABEL_COLUMN: label,
                }
            )
    return pd.DataFrame(rows)


def _matrix_and_split() -> tuple[FeatureMatrix, TemporalSplit]:
    matrix = build_feature_matrix(_model_frame(), LABEL_COLUMN)
    split = build_temporal_split(
        matrix.metadata,
        train_end="2026-01-02",
        validation_end="2026-01-03",
    )
    return matrix, split


def test_fit_constant_baseline_mean_uses_only_non_missing_training_labels() -> None:
    matrix, split = _matrix_and_split()

    result = fit_constant_baseline(matrix, split, method="mean")

    assert isinstance(result, ConstantBaselineResult)
    assert result.method == "mean"
    assert result.fitted_value == pytest.approx((1.0 + 3.0 + 7.0) / 3.0)
    assert result.training_label_count == 3
    assert tuple(result.train_predictions.index) == split.train_index
    assert tuple(result.validation_predictions.index) == split.validation_index
    assert tuple(result.test_predictions.index) == split.test_index
    assert (result.train_predictions == result.fitted_value).all()
    assert (result.validation_predictions == result.fitted_value).all()
    assert (result.test_predictions == result.fitted_value).all()


def test_fit_constant_baseline_median_uses_only_training_labels() -> None:
    matrix, split = _matrix_and_split()

    result = fit_constant_baseline(matrix, split, method="median")

    assert result.method == "median"
    assert result.fitted_value == pytest.approx(3.0)
    assert result.training_label_count == 3


def test_validation_and_test_label_changes_do_not_change_fitted_value() -> None:
    matrix, split = _matrix_and_split()
    changed_frame = _model_frame()
    changed_frame.loc[changed_frame["date"] >= pd.Timestamp("2026-01-03"), LABEL_COLUMN] = [
        -9999.0,
        8888.0,
        -7777.0,
        6666.0,
        -5555.0,
        4444.0,
    ]
    changed_matrix = build_feature_matrix(changed_frame, LABEL_COLUMN)

    baseline = fit_constant_baseline(matrix, split)
    changed = fit_constant_baseline(changed_matrix, split)

    assert changed.fitted_value == baseline.fitted_value
    assert changed.training_label_count == baseline.training_label_count


def test_missing_validation_and_test_labels_do_not_block_predictions() -> None:
    frame = _model_frame()
    frame.loc[frame["date"] >= pd.Timestamp("2026-01-03"), LABEL_COLUMN] = pd.NA
    matrix = build_feature_matrix(frame, LABEL_COLUMN)
    split = build_temporal_split(
        matrix.metadata,
        train_end="2026-01-02",
        validation_end="2026-01-03",
    )

    result = fit_constant_baseline(matrix, split)

    assert matrix.y.iloc[list(split.validation_index)].isna().all()
    assert matrix.y.iloc[list(split.test_index)].isna().all()
    assert len(result.validation_predictions) == len(split.validation_index)
    assert len(result.test_predictions) == len(split.test_index)


def test_fit_constant_baseline_rejects_invalid_methods_and_empty_training_labels() -> None:
    matrix, split = _matrix_and_split()

    with pytest.raises(ValueError, match="method must be one of"):
        fit_constant_baseline(matrix, split, method="mode")  # type: ignore[arg-type]

    all_missing_train = matrix.y.copy()
    all_missing_train.iloc[list(split.train_index)] = pd.NA
    missing_matrix = FeatureMatrix(
        X=matrix.X,
        y=all_missing_train,
        metadata=matrix.metadata,
        feature_columns=matrix.feature_columns,
        label_column=matrix.label_column,
    )

    with pytest.raises(ValueError, match="non-missing training label"):
        fit_constant_baseline(missing_matrix, split)

    empty_train_split = TemporalSplit(
        train_index=(),
        validation_index=split.validation_index,
        test_index=split.test_index,
        date_column=split.date_column,
        train_end=split.train_end,
        validation_end=split.validation_end,
        test_end=split.test_end,
        train_start_date=split.train_start_date,
        train_end_date=split.train_end_date,
        validation_start_date=split.validation_start_date,
        validation_end_date=split.validation_end_date,
        test_start_date=split.test_start_date,
        test_end_date=split.test_end_date,
    )

    with pytest.raises(ValueError, match="non-empty train split"):
        fit_constant_baseline(matrix, empty_train_split)
