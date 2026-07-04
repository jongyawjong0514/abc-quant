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

## Train-Only Standardization Contract

`src/abc_quant/preprocessing/scaling.py` defines `fit_standard_scaler(...)`
and `transform_with_standard_scaler(...)` for leakage-safe numeric feature
standardization.

`fit_standard_scaler(feature_matrix, temporal_split, feature_columns=None)`
uses only `temporal_split.train_index` rows to compute per-feature means and
population standard deviations. Validation and test rows are never read during
fit, so extreme later-period values cannot change fitted parameters.

`transform_with_standard_scaler(feature_matrix, fitted_scaler, temporal_split)`
applies the fitted parameters to train, validation, and test rows and returns a
`StandardizedFeatureMatrix` with split DataFrames plus the `StandardScalerFit`.
The transformed split frames preserve split row counts, positional split
indices, and feature column order.

Safety rules:

- Feature columns default to `feature_matrix.feature_columns` or may be
  supplied explicitly.
- Unknown, duplicate, empty, or nonnumeric feature columns are rejected.
- Empty train splits are rejected.
- Missing training feature values are rejected.
- Zero-variance training features are rejected.
- A fitted scaler can only be transformed with the same train/validation/test
  split indices it was fitted with.
- The helper does not add dependencies, fit estimators, tune parameters, alter
  labels or metadata, create allocation logic, build performance curves, or run
  simulation engines.

## Preprocessing Smoke Diagnostics

`src/abc_quant/pipeline/preprocessing.py` defines
`run_preprocessing_smoke(...)`. It is a deterministic in-memory diagnostic path
for train-only scaling.

The pipeline wires together:

1. `build_smoke_frame(...)`
2. `build_feature_matrix(...)`
3. `build_temporal_split(...)`
4. `fit_standard_scaler(...)`
5. `transform_with_standard_scaler(...)`

The smoke fixture's rolling features naturally contain missing values in the
first rows for each ticker. The preprocessing smoke path therefore uses
feature-complete fixture rows before building the `FeatureMatrix`, while still
preserving missing labels for later diagnostics. It does not fill feature or
label values.

The returned plain dictionary is deterministic and JSON-serializable. It
contains:

- `row_count`
- `feature_columns`
- `split_counts`
- `fitted_means`
- `fitted_stds`
- `train_mean_after_scaling`
- `train_std_after_scaling`
- `split_shape`

`src/abc_quant/pipeline/contracts.py` centralizes the preprocessing smoke
summary contract with `PREPROCESSING_SMOKE_SUMMARY_KEYS`,
`PREPROCESSING_SMOKE_SPLITS`, and
`validate_preprocessing_smoke_summary(...)`. The smoke pipeline validates the
summary before returning it. The validator checks top-level keys,
`split_counts` split keys, `split_shape` split keys, and the per-split
`rows`/`columns` shape keys.

Safety rules:

- Fitted means and standard deviations come only from train rows.
- Train rows are expected to scale to approximately zero mean and unit
  population standard deviation.
- Validation and test rows are transformed with fixed train-fitted parameters.
- The helper stays separate from the modeling smoke CLI and modeling smoke
  summary contract.
- The helper does not train estimators, tune parameters, change modeling smoke
  outputs, define allocation logic, build performance curves, or run simulation
  engines.

## Preprocessing Smoke CLI

`src/abc_quant/cli/preprocessing_smoke.py` exposes the deterministic
preprocessing smoke diagnostic as module-executable JSON:

```powershell
python -m abc_quant.cli.preprocessing_smoke
```

When installed as a package, the same CLI is also exposed through the console
script:

```powershell
abc-quant-preprocessing-smoke
```

The CLI is a thin wrapper around `run_preprocessing_smoke(...)`. It accepts:

- `--train-end`
- `--validation-end`
- `--indent`

Successful runs write sorted deterministic JSON to stdout and return exit code
0. Invalid temporal boundaries return a non-zero exit code and write a concise
error message to stderr. The CLI does not write files, change preprocessing
calculations, alter the modeling smoke CLI, train estimators, tune parameters,
define allocation logic, build performance curves, or run simulation engines.

## Supervised Split Dataset Contract

`src/abc_quant/models/dataset.py` defines
`build_supervised_split_dataset(...)`. It combines a `FeatureMatrix` and a
`StandardizedFeatureMatrix` into aligned train/validation/test supervised
inputs for future estimators.

The builder uses the split indices stored in `standardized_features.fitted` to
align `FeatureMatrix.y` with already-standardized split feature frames. By
default, missing labels are dropped independently per split and recorded in
`dropped_label_counts`. When `drop_missing_labels=False`, any missing label is
rejected with a `ValueError`.

The returned `SupervisedSplitDataset` records:

- `feature_columns`
- `label_column`
- `train_X` / `train_y`
- `validation_X` / `validation_y`
- `test_X` / `test_y`
- `dropped_label_counts`

Safety rules:

- Input types must be `FeatureMatrix` and `StandardizedFeatureMatrix`.
- Split feature indices must match the fitted scaler split indices.
- Split feature columns must match fitted `feature_columns`.
- Empty train data after label filtering is rejected.
- Feature frames and label Series are copied before returning.
- The helper does not train estimators, tune parameters, change smoke outputs,
  alter CLI behavior, define allocation logic, build performance curves, or run
  simulation engines.

## Supervised Dataset Smoke Diagnostics

`src/abc_quant/pipeline/supervised.py` defines
`run_supervised_dataset_smoke(...)`. It is a deterministic in-memory diagnostic
path for the supervised dataset contract.

The pipeline wires together:

1. `build_smoke_frame(...)`
2. `build_feature_matrix(...)`
3. `build_temporal_split(...)`
4. `fit_standard_scaler(...)`
5. `transform_with_standard_scaler(...)`
6. `build_supervised_split_dataset(...)`

The smoke path uses the same feature-complete deterministic fixture rows as the
preprocessing smoke diagnostics, then applies the supervised dataset label-drop
contract with `drop_missing_labels=True`.

The returned plain dictionary is deterministic and JSON-serializable. It
contains:

- `row_count`
- `feature_columns`
- `label_column`
- `split_counts_before_label_drop`
- `split_counts_after_label_drop`
- `dropped_label_counts`
- `split_shape`

`src/abc_quant/pipeline/contracts.py` centralizes the supervised dataset smoke
summary contract with `SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS`,
`SUPERVISED_DATASET_SMOKE_SPLITS`,
`SUPERVISED_DATASET_SMOKE_SPLIT_SHAPE_KEYS`, and
`validate_supervised_dataset_smoke_summary(...)`. The smoke pipeline validates
the summary before returning it. The validator checks top-level keys,
pre-label-drop split counts, post-label-drop split counts, dropped label count
splits, split shape splits, and the per-split `rows`/`columns` shape keys.

Safety rules:

- Split counts before label drop are derived from the standardized split
  feature frames.
- Split counts after label drop and `dropped_label_counts` are derived from
  `SupervisedSplitDataset`.
- Train data must remain non-empty after label filtering.
- The helper does not train estimators, change existing smoke outputs, alter CLI
  behavior, define allocation logic, build performance curves, or run simulation
  engines.

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

`src/abc_quant/models/evaluation.py` defines `evaluate_predictions(...)`,
`evaluate_prediction_bundle(...)`, and `evaluate_constant_baseline(...)` for
model-output diagnostics.

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

`evaluate_prediction_bundle(feature_matrix, prediction_bundle)` evaluates any
validated `SplitPredictionBundle` against `feature_matrix.y`, preserves the
bundle `model_name` and `method`, and returns train/validation/test
`PredictionEvaluationResult` objects.

Safety rules:

- Empty split names are rejected.
- Empty prediction Series are rejected.
- Prediction indices outside the actual-label index are rejected.
- Splits with no non-missing actual labels are rejected.
- Missing actual labels never contribute to `mae`, `rmse`, or `mean_error`.
- Bundle evaluation reads only `feature_matrix.y` and the prediction Series
  already stored in the bundle.
- The helpers do not train models, fit scalers, tune hyperparameters, create
  trading signals, define strategies, create positions, build equity curves, or
  run backtests.

## Split Prediction Bundle Contract

`src/abc_quant/models/predictions.py` defines `SplitPredictionBundle`,
`build_split_prediction_bundle(...)`, and
`build_constant_baseline_prediction_bundle(...)` for in-memory diagnostic
prediction outputs. The bundle fixes the shape used by train, validation, and
test prediction Series before those outputs are passed to later diagnostics.

The frozen dataclass contains:

- `model_name`
- `method`
- `train_predictions`
- `validation_predictions`
- `test_predictions`

Safety rules:

- `model_name` and optional `method` strings are normalized and must be
  non-empty when present.
- Each prediction input must be a pandas Series.
- Train and test prediction Series must be non-empty.
- Validation prediction Series may be empty for train/test-only diagnostics.
- Series indices must be unique.
- Missing prediction values are rejected.
- Split indices must not overlap across train, validation, and test.
- Returned Series are copied so later caller mutation cannot change the bundle.
- `build_constant_baseline_prediction_bundle(...)` accepts only a
  `ConstantBaselineResult`, uses its existing prediction Series and `method`,
  and delegates to `build_split_prediction_bundle(...)` so the same validation
  and copy-isolation rules apply.
- The helper does not implement estimators, alter baseline fitting, change CLI
  behavior, change summary keys, fit preprocessing, tune parameters, define
  allocation logic, build performance curves, or run simulation engines.

## Baseline Modeling Smoke Pipeline

`src/abc_quant/pipeline/modeling.py` defines
`run_baseline_modeling_smoke(...)`. It is a deterministic in-memory smoke check
that wires the existing modeling contracts together:

1. `build_smoke_frame(...)`
2. `build_feature_matrix(...)`
3. `build_temporal_split(...)`
4. `fit_constant_baseline(...)`
5. `build_constant_baseline_prediction_bundle(...)`
6. `evaluate_prediction_bundle(...)`

The returned plain dictionary contains diagnostic evidence only:

- row counts and rows per ticker
- `feature_columns`
- `label_column`
- label missing/non-missing counts
- train/validation/test split counts
- `baseline_method`
- baseline `fitted_value`
- `training_label_count`
- train/validation/test prediction evaluation metrics

The smoke pipeline accepts `method="mean"` or `method="median"` and passes that
selection through to the existing constant-baseline contract. The selected
method is recorded as `baseline_method` in the diagnostic summary.

After fitting the constant baseline, the pipeline evaluates predictions through
the generic split prediction bundle contract. This keeps the public summary
shape unchanged while sharing the same bundle validation and evaluation path as
future diagnostic model outputs.

The smoke pipeline is deterministic and uses synthetic fixture data. It does
not access outside data, train new model types, fit scalers, tune
hyperparameters, create market-action outputs, define allocation logic, build
performance curves, or run simulation engines.

## Modeling Smoke Summary Contract

`src/abc_quant/pipeline/contracts.py` defines the diagnostic summary shape:

- `MODELING_SMOKE_SUMMARY_KEYS`
- `EVALUATION_METRIC_KEYS`
- `validate_modeling_smoke_summary(summary)`

The validator accepts only the documented top-level summary keys, the
`train`/`validation`/`test` evaluation split names, and the documented
evaluation metric keys for each split. It also validates that
`baseline_method` is either `mean` or `median`. It returns the original summary
object unchanged when valid and raises deterministic `ValueError` messages for
missing or unknown keys. `run_baseline_modeling_smoke(...)` validates the
summary before returning it, so the pipeline and CLI share the same summary
contract.

## Modeling Smoke CLI

`src/abc_quant/cli/modeling_smoke.py` exposes the deterministic smoke pipeline
as a module entry point:

```powershell
python -m abc_quant.cli.modeling_smoke
```

When installed as a package, the same CLI is also exposed through the console
script declared in `pyproject.toml`:

```powershell
abc-quant-modeling-smoke
```

The command writes deterministic JSON to stdout with sorted keys. It supports:

- `--train-end`: overrides the last train date boundary.
- `--validation-end`: overrides the last validation date boundary.
- `--method`: selects the existing constant-baseline method, `mean` or `median`.
- `--indent`: optionally formats the JSON output.

Invalid date boundaries return a non-zero exit code and write a concise error
message to stderr. The CLI is diagnostic-only: it does not write files, access
outside data, connect to live accounts, add model types, fit scalers, tune
hyperparameters, define allocation logic, build performance curves, or run
simulation engines.
