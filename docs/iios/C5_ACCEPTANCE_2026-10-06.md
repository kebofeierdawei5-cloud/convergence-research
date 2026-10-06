# C5 Acceptance — Positioning / Sizing Production Integration

Date: 2026-10-06
Status: PASS / MERGED / CANONICAL

## Scope

C5 completes the IIOS positioning / sizing layer as a bounded production projection over:

Market Regime
→ Industry Sentiment
→ Stock Structure
→ Holder / Capital Structure
→ Crowding / Supply Pressure

It is explicitly limited to timing and sizing. It does not mutate fundamental Decision semantics.

## Implementation

- PR #108
- implementation merge: `cdf998cd21776363914f178e648f03ec0c1539f8`
- canonical main after implementation merge: `cdf998cd21776363914f178e648f03ec0c1539f8`

## Exact-head acceptance evidence

Dedicated workflow:

- Workflow: IIOS C5 — Positioning / Sizing Production Integration
- Run #7
- Exact head: `f9758beb683b3ba044fc9a153018050fa4ff09d9`
- Result: SUCCESS

Verified:

- compileall: PASS
- C5 + C4 + semantic Expectation Gap + Investment Core tests: **86 passed**
- executable C5 acceptance harness: **9 / 9 PASS**
- git diff --check: PASS

## Acceptance conclusions

### 1. Five-layer positioning hierarchy is productionized

The production record binds the five required positioning dimensions with explicit source, observation date, known-at timestamp, evidence IDs and source-bundle hash.

### 2. PIT and evidence failures are fail-closed

Positioning evidence that is stale, missing, malformed, unknown or ambiguous produces `BLOCKED` sizing state and `NO_SIZING_PERMISSION`.

### 3. Sizing policy is deterministic

Factor scores are +1 / 0 / -1.

- score >= +2 → FAVORABLE / TARGET / allow up to target position;
- score 0..+1 → NEUTRAL / INITIAL / allow up to initial position;
- score < 0 → UNFAVORABLE / CURRENT / hold current and do not add.

The permitted position never exceeds the declared maximum position.

### 4. Full sizing surface is explicit

C5 emits / binds:

- entry zone;
- add zone when explicitly evidenced;
- reduce zone when explicitly evidenced;
- initial position;
- target position;
- maximum position;
- hard exposure limit.

C5 never fabricates missing add/reduce price zones; absent evidence remains explicit null.

### 5. Fundamental Decision authority is unchanged

C5 policy effect is:

`TIMING_AND_SIZING_ONLY_NO_FUNDAMENTAL_DECISION_MUTATION`

Positioning cannot rewrite Trust, Quality, Thesis, intrinsic value, Expected Return / Required Return, Risk, or the canonical Decision action.

An unfavorable positioning state can block additional sizing and surface `reduce_consideration`, but it does not auto-reduce a position.

### 6. Deterministic persistence and replay

The C5 record is content-addressed with SHA-256, validates against a standalone schema, and replays deterministically.

The record is projected into the v0.3 Decision surface without changing Decision precedence.

## Known independent regression

The broader Investment Core / Risk Portfolio workflows continue to contain the separately tracked `test_schema_accepts_record` failure caused by an existing test using `json.load(str)`. This is not C5 logic and is not used as C5 acceptance evidence.

## Explicitly unchanged

C5 does not add:

- Kelly or optimizer sizing;
- portfolio optimization;
- new P3/P4/MIE model families;
- scheduler / alerts;
- automatic execution / order placement;
- Human Execution Receipt;
- Forecast Research productionization.

## Next canonical boundary

**C6 — Human Execution Receipt**

C5 is therefore closed as a canonical Stage C productization boundary.
