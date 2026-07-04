# Modeling Contracts

This project does not train models until the input contracts are explicit and
locally testable.

## Temporal Split Contract

`src/abc_quant/validation/temporal.py` defines `build_temporal_split(...)`.
It accepts in-memory metadata, such as the `date`/`ticker` metadata returned by
`build_feature_matrix(...)`, and returns a `TemporalSplit` object with
deterministic positional indices:

- `train_index`
- `validation_index`
- `test_index`

Rows are sorted by `date` and then `ticker` when a ticker column is present.
The indices are therefore stable for shuffled input and can be applied to
already-sorted feature matrices with `.iloc`.

Supported modes:

- train/test: set `train_end`.
- train/validation/test: set `train_end` and `validation_end`.
- optional `test_end`: sets the last allowed test date; rows after that date are
  rejected instead of silently dropped.

Safety rules:

- Training dates must be strictly earlier than validation and test dates.
- Boundaries must be increasing.
- Missing or unsortable date columns are rejected.
- Empty train, validation, or test splits are rejected when that split is part of
  the requested contract.
- The function does not drop rows, fill missing labels, fit scalers, train
  models, generate trading signals, or run backtests.

This contract is a pre-modeling guard only. Model baselines, walk-forward
validation, scalers, feature importance, ablation studies, strategies, and
backtests remain future tasks.

## Constant Baseline Contract

`src/abc_quant/models/baseline.py` defines `fit_constant_baseline(...)`.
It accepts a `FeatureMatrix`, a `TemporalSplit`, and a method of `mean` or
`median`.

The fitted constant uses only non-missing labels at `train_index`. Validation
and test labels are never read to compute `fitted_value`, so changing
validation/test labels cannot leak into the baseline. Predictions are returned
as pandas Series for the train, validation, and test split positions.

Safety rules:

- Empty train splits are rejected.
- All-missing training labels are rejected.
- Unsupported baseline methods are rejected.
- Missing validation/test labels are allowed because evaluator targets remain
  separate from prediction generation.
- The helper does not fit scalers, tune hyperparameters, train complex models,
  create trading signals, define strategies, or run backtests.

This is a minimal baseline contract for future model validation. It is not a
production model, trading rule, or performance claim.
