# PILOT-00 — MVP Investment Core Test Protocol

Status: FROZEN FOR PILOT
Date: 2026-10-07

## Purpose

Freeze the exact accepted Investment Core baseline used to start real-user testing.

## Baseline

Canonical main at freeze:
f9ab3590425c0df87881ce2b7a2ce1aee11749d5

Baseline receipt:
evidence/mvp_pilot/PILOT-00_BASELINE_20261007.json

## Controlled test cases

- CATL / 300750
- 科伦药业 / 002422

These cases are not performance evidence. They are controlled operator-workflow acceptance cases.

## Pilot assertions

1. Company-level research can run without CSI800 / A02.
2. Evidence, Trust, Reality, Quality, Value, Forecast, Valuation, Return, Required Return, Risk, Position and Decision remain distinct.
3. Human approval remains separate from AI proposal.
4. Publication and report remain projections.
5. Monitoring and validation do not mutate historical decision state.
6. Changed decisions require new run/revision.
7. Current-to-historical substitution remains forbidden.
8. Automatic ordering remains absent.

## Pilot gate

PASS requires the dedicated MVP Pilot CI to pass on the exact baseline and controlled cases.

A P0 authority, PIT, provenance, semantic-bypass or replay failure blocks pilot continuation.

## Next step

After PILOT-00 PASS, execute PILOT-01 controlled operator testing, then PILOT-02 with a fresh user-selected candidate.

A02 / CSI800 research remains outside the MVP Investment Core launch gate.
