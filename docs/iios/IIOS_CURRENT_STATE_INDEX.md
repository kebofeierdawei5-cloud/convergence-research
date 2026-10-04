# IIOS Current-State Index

Snapshot: 2026-10-04

## Canonical State

Current canonical `main` HEAD:

`93fefe0dcd513fd466d2319205c67f783cb54020`

Canonical reconciliation:

`docs/iios/STATE_RECONCILIATION_2026-10-04.md`

## Current Investment-Core State

```
Initial MVP Decision Vertical Slice = MERGED
        ↓
Batch 1-B Company Value Core = MERGED
        ↓
Human-authoritative Valuation Model Selection = MERGED
        ↓
Batch 2 v0.1 = OPEN / RED-TEAM BLOCKED
        ↓
Next: Investment Core Contract v0.2
```

### Company-side valuation authority

`Company Value Core → Candidate Models → HUMAN Primary Model → Consistency Gate → Intrinsic Value`

Router is advisory only.

### Market-side target

`Market Observable Evidence → Candidate Models → Historical/Current Fit → Feasible Solution Set → Identifiability → Stability → Reverse Valuation → Market Implied Expectation`

The current Batch 2 v0.1 implementation does not satisfy this contract and is not current capability.

## Return Target

**Positive expected return >15%.**

No fixed 1–3 year holding period and no annualized-return requirement are part of the current core gate.

## Forecast Research

- FM-00 = PASS
- FM-01 implementation foundation = PASS
- FM-01 CATL data ingress = BLOCKED pending exact source snapshot
- FM-02 waits for exact source admission

## Authority Precedence

1. Frozen governance artifacts and accepted evidence chains.
2. Current canonical Git repository state.
3. Independent CI / execution evidence.
4. Historical audit records as point-in-time records.
5. Chat context.

## Reconciliation Rule

Historical state documents may remain as historical evidence, but must not be interpreted as the current state when they conflict with this index or the reconciliation artifact.
