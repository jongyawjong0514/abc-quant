from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from abc_quant.validation.expected_return_model import (
    evaluate_expected_return,
    fit_expected_return_model,
    predict_expected_return,
)


def _frame(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"momentum": values, "volume_ratio": values[::-1]})


def test_expected_return_model_uses_split_specific_contract() -> None:
    discovery = _frame([-2, -1, 0, 1, 2, 3])
    validation = _frame([-1.5, -0.5, 0.5, 1.5])
    calibration = _frame([-1.25, -0.25, 0.75, 1.75])
    model = fit_expected_return_model(
        discovery,
        np.array([-4, -2, 0, 2, 4, 6], dtype=float),
        validation,
        np.array([-3, -1, 1, 3], dtype=float),
        calibration,
        np.array([-2.5, -0.5, 1.5, 3.5], dtype=float),
        feature_names=["momentum", "volume_ratio"],
        l2_grid=[0.1, 1.0],
    )
    prediction = predict_expected_return(model, validation)
    assert prediction.shape == (4,)
    assert np.isfinite(prediction).all()
    metrics = evaluate_expected_return(
        np.array([-3, -1, 1, 3], dtype=float), prediction
    )
    assert metrics["rows"] == 4
    assert metrics["mae"] >= 0


def test_expected_return_model_rejects_outcome_feature() -> None:
    frame = pd.DataFrame({"net_return_pct": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError, match="outcome-like"):
        fit_expected_return_model(
            frame,
            [1.0, 2.0, 3.0],
            frame,
            [1.0, 2.0, 3.0],
            frame,
            [1.0, 2.0, 3.0],
            feature_names=["net_return_pct"],
        )


def test_expected_return_transform_does_not_refit_on_holdout() -> None:
    discovery = _frame([-2, -1, 0, 1, 2, 3])
    model = fit_expected_return_model(
        discovery,
        [-4, -2, 0, 2, 4, 6],
        _frame([-1.5, -0.5, 0.5, 1.5]),
        [-3, -1, 1, 3],
        _frame([-1.25, -0.25, 0.75, 1.75]),
        [-2.5, -0.5, 1.5, 3.5],
        feature_names=["momentum", "volume_ratio"],
    )
    base = _frame([10.0, 11.0])
    mutated = base.copy()
    mutated.loc[1, "momentum"] = 10_000.0
    base_prediction = predict_expected_return(model, base.iloc[[0]])
    mutated_prediction = predict_expected_return(model, mutated.iloc[[0]])
    assert base_prediction == pytest.approx(mutated_prediction)
