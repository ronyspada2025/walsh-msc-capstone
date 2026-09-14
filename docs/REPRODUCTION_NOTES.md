# Analysis protocol and interpretation

## Estimation and validation

- The preserved municipal CSV is identified by SHA-256. Cleaning restores one row
  per municipality, sums SLP counts, and keeps the first non-null stable values.
- Random forests use 300/600 trees, depth None/8/14, minimum leaf size 1/5, and
  balanced class weights. Count and per-capita targets are tuned separately within
  the seed-42 development training partition.
- Repeated stratified five-fold CV uses five repeats. These evaluations and the
  seed-2026 repartition use selected configurations. They are sensitivity analyses,
  not nested or untouched assessments of model selection.
- Held-out intervals use 1,000 row resamples, restarting NumPy RandomState(42) for
  each statistic and holding the fitted model fixed. They do not capture all spatial
  or model-selection uncertainty.
- Ridge uses StandardScaler followed by RidgeCV over 30 penalties and five folds.
  Scaling is fitted before RidgeCV's inner splits. Full-frame raw/log intensity and
  log intensity among NR-present municipalities are separate estimation targets.
- The truncated negative-binomial model uses positive counts, a log-population
  offset, centered log population, and standardized structural predictors. The
  unconditional model includes zeros. Coefficients describe associations.
- State-pairs bootstrap draws 27 states with replacement 999 times, using seed 42,
  fixed transformations, and full-fit starting values. Rank-deficient, nonconverged,
  and nonfinite fits are excluded and recorded. At least 80% must be usable.
- The population exponent applies to the underlying NB count mean. The expectation
  conditional on a positive count also requires the truncation adjustment. Region
  coefficients are per standard deviation of their indicators.
- SLP thresholds are computed on the cleaned municipal frame before selecting model
  rows. Alternative aggregation rules and P70/P80 targets follow the same sequence.

## Use of results

The full-frame ridge intervals include zero, supporting the report's conclusion of
limited national-frame intensity prediction. The NR-present log-intensity analysis
has R² .114 with a 95% interval [.068, .153], indicating modest predictive value under
the stated evaluation. Complete model-specific results remain in Table 11 and the
RQ2 technical results.

There are 3,377 recorded zero NR counts and two unknown counts. The descriptive
speed-stage group of 3,379 includes both. State-grouped validation is weaker for SLP.
Held-out municipal predictions are evaluation outputs; full-population scoring,
probability calibration, and deployment decisions require further validation.

## Computational evidence

The pipeline records input and source hashes, software versions, split membership,
bootstrap diagnostics, and output hashes. The final-report numerical reference is
checked after fitting. `scripts/verify_project.py` requires complete valid outputs,
matching documents, and agreement at the report's displayed precision.

Historical raw snapshots and the original SLP registry grain remain unverified.
Dataset source links do not authenticate unavailable acquisition bytes. Reproduction
uses the preserved municipal input and does not replace it with a new download.
