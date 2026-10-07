# PILOT-02 — Fresh Candidate: 浙江新和成股份有限公司

Status: **TECHNICAL PASS / HUMAN OBSERVATION PENDING**
Date: 2026-10-07

## Scope

This pilot uses the user-selected fresh candidate:

- Company: 浙江新和成股份有限公司
- Symbol: 002001.SZ
- Market: CN-A
- Cutoff / as-of: 2026-10-07
- Security classification: NON_FINANCIAL
- Research weighting: cyclical 70% + growth 30%

The 70% / 30% weighting is an explicit user research input. It is not evidence supplied by the market or issuer.

PILOT-02 was started at the user's explicit direction before completion of the previously planned PILOT-01 human-observation gate. This is recorded as an owner-directed sequencing override, not a silent governance change.

## Market-date handling

2026-10-07 is a non-trading day. The pilot therefore uses 2026-09-30 as the latest tradable close rather than fabricating a 2026-10-07 market price.

Observed close:

`CNY 25.95/share`

Exact primary evidence captured in the accepted run:

- CNINFO H1 2026 report SHA-256: `ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e`
- Tencent historical K-line raw SHA-256: `637bd885980763b1eea5ce63e7b255746e4a4c6ade4ec8981dabbad75635405b`
- ChinaClear holiday-page raw SHA-256: `756241e1e86515b5a9bbfafdede05055344c9ac9cf7dcba38a75141ed2096fa7`
- all three were admitted as exact bytes in the pilot receipt.

## Company evidence anchors

The 2026 H1 primary report provides the following anchors used by the pilot:

- Revenue: CNY 13.1293bn
- Net profit attributable to parent: CNY 4.0107bn
- Adjusted net profit: CNY 3.9189bn
- Operating cash flow: CNY 3.6401bn
- R&D: CNY 0.6057bn
- Nutrition products: 67.07% of revenue
- Overseas sales: 58.43%
- H1 report states methionine demand and price increased materially, with both volume and price rising.

These are evidence anchors only. They do not by themselves establish long-term economic moat or investment attractiveness.

## Research thesis used in the pilot

The pilot treats Xinhecheng as a mixed cyclical-growth case:

- Cyclical 70%: the main short-to-medium term earnings elasticity is attributed to nutrition/vitamin-related product pricing and supply-demand conditions.
- Growth 30%: product expansion, overseas penetration, new materials and R&D/capacity expansion are treated as the structural-growth component.

Primary falsifiers:

- core nutrition-product economics mean-revert rapidly and the normalized earnings center falls materially;
- core-product gross margin deteriorates without sufficient volume offset;
- operating cash flow persistently diverges from earnings without an adequate working-capital explanation;
- new capital projects fail to earn an acceptable return;
- material governance / minority-shareholder risk worsens.

## Valuation test assumptions

The pilot uses a normalized-earnings scenario model. These are explicit model assumptions, not market consensus:

| Scenario | Normalized EPS | Multiple | Value/share | Probability |
|---|---:|---:|---:|---:|
| Bear | CNY 2.10 | 9.5x | CNY 19.95 | 30% |
| Base | CNY 2.80 | 11.5x | CNY 32.20 | 50% |
| Bull | CNY 3.50 | 13.0x | CNY 45.50 | 20% |

The first attempted bear case was CNY 19.00/share. At the observed CNY 25.95 entry price this implied a 26.78% loss, exceeding the 25% declared maximum-loss boundary, and the canonical risk gate correctly rejected the run.

The corrected bear case of CNY 19.95/share produces a bear loss of about 23.12%, bringing the scenario set within the declared risk boundary. This was a test-fixture correction; no Investment Core risk semantics were changed.

## Canonical test result

Accepted GitHub Actions run:

- Workflow run: `37627712090`
- Run number: #23
- Accepted head: `80aa3b6489963d51e65b8ea34c3c2325614ea42e`
- Overall conclusion: **SUCCESS**
- Evidence capture: **PASS**
- Investment Core E2E: **PASS**
- Acceptance assertions: **PASS**
- Artifact: `iios-pilot02-xinhecheng-20261007`
- Artifact ID: `11484414188`
- Artifact ZIP SHA-256: `dc27e134749d0689cab1afe01533e6cf8dcc36dbfe4c7e52c3f16620e5b685fc`

Decision output:

- Quality: **CONDITIONAL**
- Trust: **REVALIDATION**
- Action: **REVIEW_REQUIRED**
- Decision status: **REVIEW_REQUIRED**
- New capital allowed: **FALSE**
- Human approval required: **TRUE**
- Automatic execution: **FALSE**

Return / risk gates:

- Entry return cushion: 24.08%
- Margin of safety vs. CNY 32.20 reference: 19.41%
- Expected total return: 20.17%
- Expected annualized return: 20.17% (1Y pilot horizon)
- Fundamental 15% target: **PASS**
- Required return 10%: **PASS**
- Risk / max-loss 25%: **PASS**
- Canonical target entry price from return/risk thresholds: CNY 26.60

Lifecycle:

- Decision revision: r001
- Decision replay: **PASS**
- Monitoring evaluation: **VALID**
- Validation: **PASS**
- Machine Publication QA: **PASS**
- Human Report QA: **PASS**
- Human report deterministic replay: **TRUE**

## Interpretation

This is a **technical pipeline pass, not an investment approval**.

The strongest result is the separation of economic attractiveness from Trust and evidence gates:

`20.17% expected return + PASS return/risk gates`

did **not** convert into a buy permission because:

`Trust = REVALIDATION`

Therefore the canonical decision remains:

`REVIEW_REQUIRED / new capital FALSE / human approval TRUE`

The human-readable report also correctly keeps Investability UNKNOWN and the evidence/PIT/forecast/valuation readiness fields unavailable where the canonical trust boundary does not admit them.

## Remaining human boundary

CI can prove deterministic execution and governance behavior, but it cannot establish whether the report is practically useful to an actual investor.

The remaining PILOT-02 human-observation task is to review the generated artifact and note:

- confusing or missing decision-critical information;
- information that had to be reconstructed manually;
- operationally cumbersome steps;
- whether the report/decision is directly usable for an actual investment decision.

Those observations are PILOT-03 candidates only and cannot silently alter normative semantics.

## Downstream

A02 / CSI800 remains non-blocking.

The next engineering phase remains PILOT-03, but only for actual observed pilot friction or defects. No new investment semantics should be added merely because this candidate was different.
