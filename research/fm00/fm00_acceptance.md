# FM-00 Acceptance Gate v0.1

## Decision

`PASS` means only that the FM-00 contract package is internally consistent and the negative controls reject the defined leakage / purity violations. It is **not** evidence that any forecast model is predictive.

## Required controls

| Control | Acceptance |
|---|---|
| Epoch / Plan / Candidate Space / Outer Lock / Purity Boundary bindings | PASS |
| Exploratory contamination cannot become confirmatory | PASS |
| Current OOS result visibility | MUST DENY |
| Result-driven tuning in same epoch | MUST DENY |
| Silent origin exclusion | MUST DENY |
| Future actuals in feature engineering | MUST DENY |
| PIT-only feature construction | MUST PASS |
| Pairwise same-origin comparison | MUST PASS |
| Rolling-origin iid assumption | MUST NOT be assumed |
| Statistical insufficiency | MUST permit `NO_SELECTION` |
| Production router from FM-00 exploratory epoch | MUST DENY |
| Independent deterministic validator | PASS |

## Out of scope

- Forecast model implementation
- State classification thresholds
- Statistical significance claims
- Global router selection
- Prospective validation
- Production deployment
