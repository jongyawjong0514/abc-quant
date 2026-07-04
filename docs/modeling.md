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

## Prediction Evaluation Contract

`src/abc_quant/models/evaluation.py` defines `evaluate_predictions(...)` and
`evaluate_constant_baseline(...)` for model-output diagnostics.

`evaluate_predictions(actual, prediction, split_name)` treats the prediction
Series index as the evaluated split positions and aligns it against the actual
label Series. Prediction indices must already be present in the actual labels.
Missing actual labels are counted but excluded from error metrics.

Metrics returned for each split:

- `row_count`
- `non_missing_count`
- `missing_actual_count`
- `mae`
- `rmse`
- `mean_error`
- `prediction_mean`

`evaluate_constant_baseline(feature_matrix, baseline_result)` evaluates the
train, validation, and test prediction Series returned by
`fit_constant_baseline(...)` against `feature_matrix.y`.

Safety rules:

- Empty split names are rejected.
- Empty prediction Series are rejected.
- Prediction indices outside the actual-label index are rejected.
- Splits with no non-missing actual labels are rejected.
- Missing actual labels never contribute to `mae`, `rmse`, or `mean_error`.
- The helpers do not train models, fit scalers, tune hyperparameters, create
  trading signals, define strategies, create positions, build equity curves, or
  run backtests.

## Baseline Modeling Smoke Pipeline

`src/abc_quant/pipeline/modeling.py` defines
`run_baseline_modeling_smoke(...)`. It is a deterministic in-memory smoke check
that wires the existing modeling contracts together:

1. `build_smoke_frame(...)`
2. `build_feature_matrix(...)`
3. `build_temporal_split(...)`
4. `fit_constant_baseline(...)`
5. `evaluate_constant_baseline(...)`

The returned plain dictionary contains diagnostic evidence only:

- row counts and rows per ticker
- `feature_columns`
- `label_column`
- label missing/non-missing counts
- train/validation/test split counts
- baseline `fitted_value`
- `training_label_count`
- train/validation/test prediction evaluation metrics

The smoke pipeline is deterministic and uses synthetic fixture data. It does
not access outside data, train new model types, fit scalers, tune
hyperparameters, create market-action outputs, define allocation logic, build
performance curves, or run simulation engines.

## Modeling Smoke CLI

`src/abc_quant/cli/modeling_smoke.py` exposes the deterministic smoke pipeline
as a module entry point:

```powershell
python -m abc_quant.cli.modeling_smoke
```

The command writes deterministic JSON to stdout with sorted keys. It supports:

- `--train-end`: overrides the last train date boundary.
- `--validation-end`: overrides the last validation date boundary.
- `--indent`: optionally formats the JSON output.

Invalid date boundaries return a non-zero exit code and write a concise error
message to stderr. The CLI is diagnostic-only: it does not write files, access
outside data, connect to live accounts, add model types, fit scalers, tune
hyperparameters, define allocation logic, build performance curves, or run
simulation engines.
