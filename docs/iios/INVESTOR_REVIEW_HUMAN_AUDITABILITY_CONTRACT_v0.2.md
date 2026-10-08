# IIOS Investor Review v0.2 — Human Auditability Contract

Date: 2026-10-08
Status: DEVELOPMENT / NORMATIVE FOR v0.2 — NOT CANONICAL

## Purpose

The Human Auditability Contract is the normative boundary between a value existing in the canonical Decision Publication and that value being independently understandable and auditable by the investor.
It does not change Decision Kernel semantics, Decision Precedence, Risk/Portfolio policy, or Human Approval policy.

## HA-01 — Required Return

required_return_pass = true is insufficient for human auditability when numeric required_return is absent.
- numeric value present → AUDITABLE
- pass flag true + numeric value absent → INCOMPLETE
- no numeric value and no positive pass flag → NOT_PROVIDED
The renderer must not infer a numeric Required Return from historical documents, chat context, or test assumptions.

## HA-02 — Expected Return / Scenario Probability

An expected annualized return is independently reconstructable only when the published scenario probabilities needed for the scenario set are present.
- expected return + Bear/Base/Bull probabilities complete → AUDITABLE
- expected return present + one or more probabilities missing → INCOMPLETE
- expected return absent → NOT_PROVIDED
The renderer must not reconstruct omitted probabilities from an older fixture, report, or external context.

## HA-03 — Actionable Entry vs Threshold

A price derived from return/risk mathematics is not automatically an executable entry price.
- canonical actionable target entry + non-skipped entry evaluation → ACTIONABLE
- threshold exists but no actionable target is admitted → THRESHOLD_ONLY
- neither exists → UNAVAILABLE
The report must explicitly distinguish Actionable Target Entry Price from Return/Risk Threshold.
For the Xinhecheng pilot, 26.60 is threshold-only and is not an execution authorization.

## HA-04 — Portfolio Permission Precedence

portfolio.can_add is package-level reference data. It cannot override canonical Decision capital authorization.
When package.can_add = true and Decision.new_capital_allowed = false, the effective Human Auditability state must be OVERRIDDEN_BY_DECISION.
The human report must show both source values and their effective resolution.

## HA-05 — MIE / Expectation Gap Absence vs Identifiability

Absence is not identifiability failure.
- MIE mapping absent → NOT_PROVIDED
- explicit upstream status = NOT_IDENTIFIABLE → preserve NOT_IDENTIFIABLE
- expectation-gap mapping absent → preserve any explicit gate status such as UNKNOWN, but do not invent structured gap semantics
- no source field may be upgraded from absence to NOT_IDENTIFIABLE
The renderer must preserve the distinction among NOT_PROVIDED, UNKNOWN, and NOT_IDENTIFIABLE.

## Human Auditability Overall State

The overall auditability state is INCOMPLETE whenever HA-01 through HA-04 is incomplete, or when MIE / Expectation Gap data are absent in a way that prevents the requested investor review chain from being independently reconstructed.
This overall state does not mutate the canonical Decision.

## QA

The v0.2 QA must verify:
- contract object exists and carries this version;
- HA-01 through HA-05 are represented in the machine surface;
- the human report explicitly shows their resolution;
- absence never silently becomes PASS or NOT_IDENTIFIABLE;
- package permissions never silently override Decision permissions.

A QA PASS means the Human Auditability Contract was applied correctly. It does not mean that the underlying investment case is complete or investable.

## Promotion

This contract remains development-only until exact-head CI passes, independent red-team passes, human investor review accepts the real-company surface, governance explicitly promotes v0.2, and PROJECT_STATE_INDEX.md is updated on canonical main.