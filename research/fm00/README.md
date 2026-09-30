# IIOS M1.2-FM-00 — Exploratory Research Epoch + Research Plan + Candidate Space Registry v0.1

Purpose: establish the machine-readable research-control layer immediately before Forecastability Feature / State / Conditional Backtest implementation.

This package is deliberately independent of the frozen G2 carrier. It does not modify or re-freeze any G2 artifact.

## Scope

- `RESEARCH_EPOCH`: lifecycle, contamination lineage, research cleanliness, and result-exposure status.
- `RESEARCH_PLAN`: pre-registration of target, horizon, metric, method, feature/state scope, selection policy, exclusion/stopping rules.
- `CANDIDATE_SPACE_REGISTRY`: immutable candidate universe for drivers, features, models, state dimensions, targets, horizons, metrics, and parameterizations.
- `OUTER_UNIVERSE_LOCK`: fixed origin universe and eligibility schedule.
- `EVALUATION_PURITY_BOUNDARY`: explicit rule for what is visible during development/evaluation and what is prohibited from influencing the same epoch.
- `FM00_VALIDATOR`: deterministic structural, cross-reference, semantic, and hash validation.

## Current epoch posture

The included example is intentionally `EXPLORATORY` and explicitly contaminated by prior M1.0/M1.1 development observations. It is allowed to generate descriptive/development evidence, but it cannot emit `RESEARCH_CLEAN_CONFIRMATORY` evidence.

## Design constraints

1. PIT visibility remains mandatory; this package does not relax the existing M1.1 PIT rules.
2. Rolling-origin observations are not iid by default.
3. Excluded / unavailable origins must be retained with explicit reasons.
4. Candidate-space changes, feature/state/metric/threshold changes, or result-driven tuning in the same epoch are prohibited after freeze.
5. A frozen exploratory result cannot be relabeled as clean confirmatory evidence.
6. The validator is independent of the plan's own declared PASS/FAIL field; it recomputes acceptance from object content.
