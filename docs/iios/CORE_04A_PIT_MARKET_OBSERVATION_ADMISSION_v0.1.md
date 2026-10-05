# CORE-04-A — PIT Market Valuation Observation Admission v0.1

Date: 2026-10-05
Status: CANDIDATE

## Objective

Create the smallest executable admission boundary for the historical market-valuation observations required by P3/P4, while preserving the single-company Investment Core scope.

The contract admits only evidence that is:

- exact-byte verified;
- explicitly sourced;
- PIT-safe under `known_at <= cutoff`;
- tied to one observation date;
- backed by explicit units and economic basis;
- temporally classified as source-vintage or contemporaneous publication.

## User Value

The system can now distinguish a real historical market observation from a value that merely looks historical because a current data provider recomputed it later.

This is critical for a personal-investor workflow using free/public sources: retrospective web pages are not silently converted into PIT evidence.

## Contract

A market-valuation observation is constructed from four verified evidence records:

1. `market_price`;
2. `shares_outstanding`;
3. one model economic variable such as `forward_eps`, `revenue`, `book_equity`, `ebitda`, `fcf`, `dividend`, `segment_value` or `pipeline_value`;
4. `net_debt`.

All four records must:

- have unique evidence IDs;
- be ADMITTED;
- carry exact bytes and a lowercase SHA-256;
- have observation dates equal to the same market observation date;
- satisfy `observation_date <= cutoff` and `known_at <= cutoff`;
- carry timezone-aware `known_at`;
- use explicit source location and economic basis.

`RETROSPECTIVE_RECOMPUTED` and `UNKNOWN` temporal provenance are hard-blocked.

The resulting typed object is the existing `MarketValuationObservation` consumed by the P3 model-identification layer.

## Fail-closed examples

- Current retrospective provider statistics: BLOCKED.
- A value with no exact raw bytes: BLOCKED.
- A record published after cutoff: BLOCKED.
- Mixed observation dates: BLOCKED.
- Missing/invalid units or economic variable: BLOCKED.
- Any duplicated evidence ID: BLOCKED.

## Important boundary

This batch does **not** claim that CATL historical market-model data has been acquired.

It only creates the admission boundary needed to safely admit such data.

The next data task remains acquisition of the minimum per-company PIT observation set, using free/public sources where defensible and retaining exact raw evidence.

## Test / Acceptance

PASS requires:

- deterministic typed admission of valid evidence;
- fail-closed PIT validation;
- fail-closed temporal-provenance validation;
- fail-closed exact-byte/hash validation;
- date/unit/variable consistency checks;
- regression tests covering negative controls;
- compileall and dedicated CORE-04 CI green.

## Out of Scope

No CSI800, CSI Industry, universe database, paid-data dependency, MIE promotion, Expected Return change, or automatic execution is introduced.
