# FM-01 Exact CATL M1.1 Source Admission — Acceptance v0.2

Status: DATA_READY / EXACT-SOURCE-ADMITTED

## Objective

Resolve the FM-01 data-ingress blocker without reconstructing or fabricating the CATL historical series.

## Exact source identity

M1.1 source package:

- `IIOS_M1_1_QUARTERLY_REALITY_ROLLING_BACKTEST_v1.1.0.zip`
- SHA-256: `34c16dca266a2f35bc2895739b3e847a6c20ea0d66e0acbbc57274a96e22804b`
- persistent Library path: `/iios/PROJECT/IIOS_M1_1_QUARTERLY_REALITY_ROLLING_BACKTEST_v1.1.0.zip`

Matching Git bundle:

- SHA-256: `0f3dd5d5058722ce8f63a6a24d8c7aafa8b28c20ae0374c3bb0a94e9fa2609e1`
- M1.1 commit: `9b612cc79cd8c16ed8aea1529a6ea93e9eb8b993`
- tag: `v1.1.0`
- tag object: `a9516728aa1429cd033b474414ed5398c939eabb`

Runtime verification independently recomputed both raw-file SHA-256 values. The extracted quarterly case and frozen driver-series files were byte-equal between the ZIP and Git bundle.

## Data admitted

CATL `300750.SZ`:

- 22 quarters;
- 2021Q1–2026Q2;
- 2 drivers: REVENUE, NET_PROFIT;
- 44 admitted DriverSeries records.

Quarter types:

- 12 direct periodic observations;
- 10 derived quarterly observations.

Derived records are explicitly labeled and retain source-parent references:

```
Q2 = H1 cumulative - Q1
Q4 = Annual cumulative - Q1 - Q2 - Q3
```

## Source-vintage

Twenty-two source evidence records were admitted from the exact M1.1 snapshot.

Each has:

- source evidence reference;
- publication timestamp;
- source URL;
- source class;
- authority classification.

The admission preserves the M1.1 source-vintage as evidence lineage. It does not claim that all historical URLs were re-fetched today.

## PIT admission

The normative rule remains:

```
known_at <= origin quarter-end cutoff
```

Independent replay covers the M1.1 rolling-origin boundary:

- 3M: 11 origins;
- 6M: 10 origins;
- 12M: 8 origins.

For every origin/horizon pair:

- all admitted training records satisfy `known_at <= cutoff`;
- the target actual is not available to the training side;
- target records with later `known_at` remain excluded;
- missing/conflicting data fail closed.

## Independent replay

Replay implementation:

`research/fm01/fm01_source_admission_replay.py`

The replay is intentionally independent of the M1.1 backtest implementation. It reconstructs PIT visibility and coverage from the admitted source-vintage + DriverSeries records, then compares the observed origin counts to the accepted M1.1 counts.

## Acceptance

Data gate transition:

```
BLOCKED_DATA_INGRESS
        ↓
exact source hash PASS
        ↓
source-vintage PASS
        ↓
44/44 record validation PASS
        ↓
22/22 quarter coverage PASS
        ↓
PIT replay PASS
        ↓
DATA_READY
```

FM-02 remains outside this acceptance gate.
