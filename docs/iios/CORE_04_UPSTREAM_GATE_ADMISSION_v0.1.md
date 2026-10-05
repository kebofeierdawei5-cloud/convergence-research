# CORE-04 Upstream Decision Gate Admission v0.1

Date: 2026-10-05
Status: IMPLEMENTED / CI PENDING / PR REVIEW

## Objective

Close the principal upstream gap exposed by the real 300750 CORE-04 decision E2E.

CORE-04 now requires an explicit, auditable upstream admission bundle before new capital can be considered:

Reality
-> Quality Gate
-> Value Driver
-> Primary Valuation
-> Independent Forecast
-> Thesis Admission
-> Return H
-> Risk
-> Portfolio
-> Optional MIE
-> Decision

## Quality Gate

Version: `IIOS-CORE-04-QUALITY-GATE-0.1`

Policy:

`ALL_CORE_DIMENSIONS_PASS_FOR_NEW_CAPITAL`

The six CORE-02 quality dimensions are evaluated explicitly:

1. competitive advantage
2. incremental return on capital
3. earnings quality
4. cash-flow conversion
5. balance-sheet resilience
6. reinvestment runway

Only six-of-six `PASS` yields a Quality Gate `PASS`.

Any `CONDITIONAL` or `UNKNOWN` produces `CONDITIONAL` and blocks new-capital admission.

Any `BLOCKED` produces `BLOCKED` and denies new capital.

This is a capital-admission gate, not a claim that a company with conditional evidence has no economic value.

## Thesis Admission

Version: `IIOS-CORE-04-THESIS-ADMISSION-0.1`

A Thesis Admission record must contain:

- explicit thesis statement;
- explicit economic mechanism;
- key value-driver IDs;
- falsifiers / thesis-break conditions;
- monitoring triggers;
- evidence IDs;
- PIT `known_at <= cutoff`;
- `prepared_without_current_price=true`.

The record is price-independent to prevent the thesis from being reverse-engineered from the current market price.

`admission_status=ADMITTED` means the thesis is structurally admitted and auditable. It does not itself imply BUY.

Thesis state remains separately classified as:

`INTACT / WATCH / BROKEN / UNKNOWN`

## Upstream Admission Bundle

Version: `IIOS-CORE-04-UPSTREAM-ADMISSION-0.1`

The bundle binds:

- Reality status;
- Quality Gate status;
- Value Driver status;
- Primary Valuation status;
- Independent Forecast status;
- Thesis state;
- Thesis Admission status;
- Quality Gate record;
- Thesis Admission record;
- evidence closure;
- deterministic `capital_admission_ready`.

`capital_admission_ready=true` requires:

- Reality = PASS;
- Quality Gate = PASS;
- Value Driver = PASS;
- Primary Valuation = PASS;
- Independent Forecast = PASS;
- Thesis Admission = ADMITTED;
- Thesis = INTACT.

Return/Risk/Portfolio/MIE remain downstream gates.

## Decision Kernel Integration

Decision Kernel version advances from:

`IIOS-CORE-04-DECISION-KERNEL-0.1`

to:

`IIOS-CORE-04-DECISION-KERNEL-0.2`

New-capital precedence now explicitly blocks or reviews non-admitted upstream states before MIE can influence the decision.

Existing-position protection is preserved:

- broken thesis still exits before Quality review;
- hard Quality failure can reduce an existing position;
- unresolved upstream admission routes to REVIEW_REQUIRED rather than automatic hold/add.

MIE remains:

`OPTIONAL_EXPLANATORY`

and does not become mandatory as a side effect of this gate integration.

## 300750 implication

The real 300750 case previously showed:

- current price = 291.11;
- 3Y explicit horizon override;
- expected annualized return ≈ 14.20%, below the 15% target;
- Risk = PASS;
- Quality = CONDITIONAL because incremental ROIC is UNKNOWN and several quality dimensions remain CONDITIONAL.

Under the new gate contract, that Quality state is explicitly propagated into CORE-04 rather than hidden inside Reality or omitted from the Decision Kernel.

Therefore the case remains:

`NO NEW CAPITAL / REVIEW_REQUIRED`

without any need to fabricate an MIE.

## Safety boundary

This batch does not:

- add a valuation model;
- make Quality an automatic permanent economic veto;
- infer thesis status from price;
- auto-trade;
- relax PIT;
- promote MIE to a mandatory gate;
- replace human approval.

The principal objective is to eliminate silent omission of upstream company-quality and thesis states from the canonical investment decision.


## Verification checkpoint

Acceptance head:
`a6e1a0cd307139d1e4c41d7987d1716ca30dcd58`

CI evidence:
- IIOS Investment Core CI #465 — **PASS**
- CORE-00 Scope Reconciliation #202 — **PASS**
- Full pytest suite: **378 passed**
- Compileall includes the new Quality/Thesis/upstream admission modules and real 300750 upstream-gate E2E.
- JSON schema parsing includes all three new CORE-04 schemas.

Real 300750 upstream-gate E2E:
- Reality admission = PASS
- Quality Gate = **CONDITIONAL**
- Value Driver admission = PASS
- Primary Valuation admission = PASS
- Independent Forecast admission = PASS
- Thesis Admission = **ADMITTED**
- Thesis state = **INTACT**
- Trust strict case = **REVALIDATION**
- MIE = **OPTIONAL_EXPLANATORY**

With Trust normalized to PASS only for diagnostic isolation, the production kernel returns:

`REVIEW_REQUIRED / QUALITY_GATE_UNRESOLVED / capital=false`

Strict Trust state remains higher precedence:

`REVIEW_REQUIRED / TRUST_NOT_PASS_REQUIRES_REVIEW / capital=false`

The 300750 Quality Gate is conditional because the current Core-02 evidence set still contains unresolved incremental ROIC and other conditional quality dimensions. This is now an explicit machine gate rather than a hidden omission.

PR #72 remains OPEN / NOT MERGED; merge remains owner-controlled.
