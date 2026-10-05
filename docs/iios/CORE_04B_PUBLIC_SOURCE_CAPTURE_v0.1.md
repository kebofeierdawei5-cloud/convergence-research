# CORE-04-B — Public/Free Source Capture Receipt v0.1

Date: 2026-10-05
Status: IMPLEMENTATION CANDIDATE

## Objective

Prove that the minimum single-company historical source set can be fetched from public/free endpoints without silently promoting fetched bytes to PIT evidence.

The selected sources pair company-report vintages with subsequent SZSE market snapshots:

- 2026 H1 report → 2026-07-27 market snapshot.
- 2026 Q1 report → 2026-04-17 market snapshot.
- 2025 Q3 report → 2025-10-22 market snapshot.

This is deliberately a narrow CATL-only data-readiness step.

## Capture contract

The workflow computes, for each source:

- source URL;
- observation date;
- known_at where publication timing is explicitly established;
- retrieval timestamp;
- HTTP status;
- exact byte count;
- SHA-256 of the fetched bytes.

The raw bytes exist only in the runner's temporary workspace and are removed when the job exits. The workflow publishes the receipt, not the raw corporate/trading files.

## Critical semantic boundary

A successful capture is **not** an evidence admission.

The receipt field `admission_status` therefore remains `NOT_ADMITTED`.

PIT admission still requires the CORE-04-A contract: exact raw bytes retained in a controlled vault, defensible known_at, source-vintage classification, semantic mapping, and evidence manifest closure.

Retrospective provider pages, current consensus screens and recomputed historical multiples are not admitted merely because they display a historical date.

## User constraint

No paid broker/commercial data source is required for this capture batch.

## Acceptance

- All six declared public/free endpoints are fetchable in CI.
- Every fetched object has a non-empty byte count and SHA-256.
- The receipt is deterministic in structure and preserves source identity.
- No fetched object is automatically promoted to ADMITTED evidence.

## Out of scope

No market-model identification, MIE qualification, Expectation Gap, Expected Return, Decision Kernel, CSI800, CSI Industry or universe database work is included.
