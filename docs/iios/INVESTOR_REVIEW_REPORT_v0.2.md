# IIOS Investor Review Report v0.2

Date: 2026-10-08
Status: DESIGN / IMPLEMENTATION CANDIDATE — NOT CANONICAL

## Purpose

v0.2 is the target investor-review surface for the new IIOS decision semantics. It is projection-only and cannot become a second Decision Source.

Pipeline:

Machine Publication → Machine Investor Surface → Human Investor Review Surface → deterministic QA

## Required decision chain

The human report MUST expose, in this order:

Candidate → Trust → Quality → Reality → Thesis → Value Drivers → Independent Forecast → Valuation → Market Implied Expectation → Expectation Gap → Risk → Market / Positioning → Decision → Position → Monitoring → Validation

No module may disappear because its upstream data is absent.

## Fail-closed module status

Supported display states are PASS, FAIL, CONDITIONAL, UNKNOWN, NOT_PROVIDED, NOT_RUN, NOT_IDENTIFIABLE, BLOCKED, N/A and REVIEW_REQUIRED.

NOT_PROVIDED means that the canonical publication did not provide the module. It is not a negative investment conclusion and never becomes PASS.

NOT_IDENTIFIABLE must come from an explicit upstream semantic declaration. The renderer MUST NOT infer NOT_IDENTIFIABLE merely from a missing field.

## Dual-surface rule

The write path produces:

1. envelope JSON binding the outputs;
2. separate machine JSON normalized for machine consumption;
3. Chinese Markdown as the primary human-review surface;
4. deterministic QA receipt.

The machine JSON is not rendered as the human report. The Markdown is not a machine source of truth.

## Human-review readiness

The machine surface exposes human_review_readiness.

READY means all required core semantic modules have structured upstream representations.

HUMAN_REVIEW_NOT_READY means one or more required modules is NOT_PROVIDED.

This is a report-readiness signal only. It cannot mutate Decision, approval, position or execution state.

## Evidence and PIT provenance

Human review should expose evidence rows with evidence_id, claim_type, source, period, known_at and purpose where available. Hashes remain integrity controls and do not substitute for readable evidence.

## B2 boundary

v0.2 does not claim that Natural Language → LLM Semantic Reasoning → Semantic Admission → Canonical Decision has been proven.

The missing LLM semantic-orchestration capability remains a separate B2 boundary.

## Promotion rule

Passing tests does not make v0.2 canonical. Promotion requires dedicated CI, independent red-team review, exact-head evidence, explicit governance acceptance and a Project State Index update.

Until promotion, the existing canonical v0.1 report remains authoritative.
