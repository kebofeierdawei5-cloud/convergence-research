# IIOS C5 — Positioning / Sizing Production Integration v0.1

Date: 2026-10-06
Status: IMPLEMENTATION CANDIDATE — pending dedicated CI and canonical acceptance

## 1. Objective

C5 completes the positioning / sizing layer of the IIOS architecture while keeping fundamental investment semantics authoritative.

Canonical hierarchy:

Market Regime
→ Industry Sentiment
→ Stock Structure
→ Holder / Capital Structure
→ Crowding / Supply Pressure
→ timing bias / sizing permission

The C5 surface is a projection only. It cannot rewrite Quality, Thesis, Intrinsic Value, Return, Required Return, Trust, Risk, or the canonical Decision action.

## 2. Production input contract

A positioning observation must bind:

- observation identity;
- observation as-of date;
- known-at timestamp;
- source identity;
- source bundle SHA-256;
- evidence IDs;
- the five positioning dimensions.

PIT rule:

- observation_as_of_date <= case cutoff;
- known_at date <= case cutoff.

Unknown or ambiguous dimensions fail closed for sizing.

## 3. Explicit policy

Policy version: `IIOS-C5-POSITIONING-POLICY-0.1`.

Each dimension contributes one transparent score:

- favorable state = +1;
- neutral state = 0;
- unfavorable state = -1.

Composite score range is [-5, +5].

Sizing surface:

- score >= +2 → FAVORABLE / TARGET band / allow up to target position;
- score 0..+1 → NEUTRAL / INITIAL band / allow up to initial position;
- score < 0 → UNFAVORABLE / CURRENT band / hold current position and do not add.

The policy never auto-reduces an existing position. An unfavorable positioning state may set `reduce_consideration = true`, leaving the actual Decision action unchanged.

The sizing output is capped by the existing portfolio package and never exceeds declared maximum position.

## 4. Fail-closed behavior

Missing positioning input:
- explicit BLOCKED record;
- `NO_SIZING_PERMISSION`;
- no composite score;
- no permitted position.

Unknown / ambiguous dimension:
- BLOCKED;
- no sizing permission.

Stale PIT evidence:
- BLOCKED;
- no sizing permission.

Missing portfolio BUY/ADD package:
- positioning cannot authorize sizing;
- C5 returns BLOCKED sizing permission;
- fundamental Decision action remains unchanged.

## 5. Authority boundary

C5 policy effect:

`TIMING_AND_SIZING_ONLY_NO_FUNDAMENTAL_DECISION_MUTATION`

Therefore:

- BUY remains BUY even when positioning says defer sizing;
- HOLD / REVIEW_REQUIRED are not promoted by positioning;
- positioning cannot bypass Trust, Quality, Return, Required Return, Risk, or portfolio constraints;
- positioning cannot create new capital authorization outside the existing Decision Kernel;
- no Kelly / optimizer / portfolio optimization is introduced.

## 6. Canonical persistence / replay

Each accepted C5 evaluation is content-addressed with SHA-256 and deterministic replay.

The record is embedded into the canonical v0.3 Decision projection so it flows through the existing Publication / Human Report / Monitoring / Validation lifecycle.

The C5 record does not mutate the Decision revision; it is an auditable sizing/timing projection attached to the Decision.

## 7. Explicit non-goals

C5 does not add:

- new P3/P4/MIE model families;
- market-wide screening;
- automatic portfolio optimization;
- Kelly sizing;
- scheduler or alerts;
- automatic execution / order placement;
- Human Execution Receipt;
- lifecycle changes;
- Forecast Research productionization.

## 8. Acceptance target

Dedicated C5 CI must prove:

1. favorable positioning yields TARGET sizing band deterministically;
2. neutral positioning yields INITIAL sizing band;
3. unfavorable positioning yields CURRENT / NO-ADD sizing permission;
4. missing / ambiguous positioning fails closed;
5. stale known-at positioning fails closed;
6. missing portfolio package fails closed for sizing;
7. the fundamental Decision action is unchanged by positioning;
8. tamper detection and replay are deterministic;
9. standalone schema validation passes;
10. C4 Expectation Gap, semantic expectation-gap, and Investment Core tests remain green for this path; the separately tracked Risk Portfolio schema-test regression remains outside C5 acceptance.
