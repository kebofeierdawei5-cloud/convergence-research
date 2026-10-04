# IIOS CORE-01 — Single Company Research Intake v0.1

Date: 2026-10-04
Status: CANDIDATE FOR ACCEPTANCE

## Goal

Turn the minimum user intent:

Market + Symbol + As-of + Current Position

into one deterministic, auditable Single Company Research Case.

Example: 300750 + As-of 2026-10-04 + Position 0%.

## What CORE-01 does

It automatically creates:
- deterministic case identity;
- normalized market/symbol;
- venue routing hint where mechanically derivable;
- current/historical temporal mode;
- mandatory PIT rule;
- current position context;
- company-specific evidence acquisition plan;
- free-first source policy boundary;
- explicit admission blockers;
- reproducibility/audit hashes.

## What CORE-01 does not do

It does not invent or silently resolve company name, issuer identity, current price, financial statements, business facts, forecasts, valuation or investment decision.

A venue hint is routing metadata, never evidence.

## PIT boundary

PIT remains mandatory for every case. The rule is known_at <= cutoff.

Historical cases additionally prohibit current-state substitution.

## Admission boundary

The generated case starts as EVIDENCE_PENDING and decision_ready=false.

Only after required evidence is resolved can a later layer admit the case into the Investment Core decision pipeline.

## CLI

PYTHONPATH=. python -m iios_mvp.cli intake 300750 --as-of 2026-10-04 --position 0

Use --out PATH to persist the machine-readable case.

## Next

CORE-02 consumes admitted company-specific evidence and constructs Reality / Trust / Quality / Value Core.
