# IIOS CORE-04 Decision Semantics Reconciliation v0.1

Date: 2026-10-05
Status: FROZEN FOR CORE-04 IMPLEMENTATION

## 1. Problem reconciled

The repository contained two conflicting decision interpretations:

- B1 v0.3: MIE is explanatory/non-mandatory for BUY/ADD;
- legacy Decision State Machine: unresolved/non-positive expectation gap could block new capital.

This was semantic drift, not merely documentation drift.

## 2. Canonical v0.3 rule

Investment Core v0.3 uses:

MIE_POLICY = OPTIONAL_EXPLANATORY

Therefore:

- missing MIE does not block BUY/ADD;
- UNKNOWN MIE does not block BUY/ADD;
- BLOCKED MIE does not block BUY/ADD;
- AMBIGUOUS MIE does not block BUY/ADD;
- a non-positive but otherwise valid advisory gap does not automatically veto BUY/ADD.

MIE can still inform the proposal and may affect capital admission only through an explicit, versioned material-contradiction policy.

No hidden contradiction threshold is introduced in CORE-04 v0.1.

## 3. What remains mandatory

The company-side BUY/ADD return package remains conjunctive:

- Entry Return Cushion >= 15%;
- Expected Annualized Return_H >= 15%;
- Expected Annualized Return_H >= Required Return;
- Risk gate passes;
- Trust/PIT/forecast/valuation gates pass;
- Portfolio constraint permits allocation;
- BUY/ADD position package is complete.

MIE is not an alternative to these gates.

## 4. Price-entry semantics

Return/risk-derived target entry price is valid without an MIE.

When a qualified MIE exists, the existing P2 price-dependent MIE refinement may additionally constrain the target-entry price. Absence of MIE does not create a fake requirement for gap revalidation.

## 5. Legacy compatibility boundary

decision_state_machine_v01.py retains explicit MANDATORY behavior for compatibility tests and older callers.

CORE-04 v0.3 never relies on that default; it passes OPTIONAL_EXPLANATORY explicitly through decision_kernel_v03.py.

## 6. Production kernel

iios_mvp/decision_kernel_v03.py is the canonical CORE-04 orchestration boundary. It consumes deterministic validation, Trust, Thesis, Risk, Portfolio, Return and optional MIE state and returns one auditable decision state plus policy/version metadata.

It does not authorize execution.

## 7. Negative safety invariant

An unresolved or advisory MIE state cannot be upgraded into a positive capital decision by omission of validation. A missing/ambiguous MIE can permit a BUY only when all independent company-side gates pass; it never creates a BUY by itself.

Likewise, a verified MIE contradiction cannot become a veto unless an explicit versioned policy turns that contradiction into a decision rule.


## 8. Acceptance checkpoint

- PR #69: MERGED into canonical `main` as `da6964ee6dd5a50b8696a46132448c205c463726`.
- PR #70: refreshed on top of that canonical main; post-refresh CI verification is the remaining acceptance step.
- Pre-refresh acceptance review on PR #70: review `5414885493`.
- Merge of PR #70 remains an owner-controlled action.
