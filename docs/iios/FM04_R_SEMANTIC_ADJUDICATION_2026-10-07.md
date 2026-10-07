# FM04-R Semantic Adjudication — 2026-10-07

Status: **FROZEN FOR FM04-R / RESEARCH-ONLY**

This remediation record resolves two semantic seams identified by the second independent red-team without changing the FM04 candidate universe, state construction, sample threshold, or selection outcome.

## 1. DATA_QUALITY interpretation

DATA_QUALITY is classified as a **research-control dimension**, not an economic regime dimension.

Economic interpretation remains reserved for:

- DIRECTION
- MOMENTUM
- VOLATILITY
- SEASONALITY
- MEAN_REVERSION_PRESSURE
- STRUCTURAL_STABILITY

FM04 may continue to materialize DATA_QUALITY-conditioned diagnostic groups under its already-frozen research implementation. Those groups must not be interpreted as evidence that data availability/quality is an economic state, and DATA_QUALITY must not acquire economic meaning through result-driven reinterpretation.

Any change to its role in the research estimand requires a separately frozen amendment/new research epoch.

## 2. Model identity

Every FM04 model instance is interpreted as:

model_family -> parameterization -> model_instance_id

Frozen mappings:

| model_family | parameterization | model_instance_id |
| --- | --- | --- |
| SEASONAL_NAIVE | seasonal period = 4 quarters | SEASONAL_NAIVE |
| PERSISTENCE_YOY | growth lag = 4 quarters | PERSISTENCE_YOY |
| TREND_LOG_LINEAR | rolling window = 8 quarters | TREND_LOG_LINEAR_8Q |
| MEAN_REVERSION_YOY | rolling window = 8 quarters; PIT rolling mean | MEAN_REVERSION_YOY_8 |

The mapping does not add a model family or parameterization. It only makes the already-admitted FM00 family/parameter space relationship explicit.

## 3. Oracle boundary

research/fm04/tests/test_fm04_known_answer_oracle.py contains frozen synthetic known-answer fixtures. These are deliberately independent expected values rather than executor-generated expectations.

This closes the semantic minimum for FM04-R. A materially different oracle / mutation harness remains a required control for future promotion beyond the current research plumbing.
