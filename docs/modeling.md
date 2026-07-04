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
