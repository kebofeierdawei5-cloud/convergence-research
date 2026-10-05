# CORE-04-C — 300750 Historical EV/EBITDA PIT Observation Admission v0.1

Date: 2026-10-05
Status: IMPLEMENTATION / LIVE CI VERIFICATION PENDING

## Objective

Admit a minimum three-point historical EV/EBITDA observation set for CATL (300750.SZ) using exact-date SZSE market snapshots plus PIT-known financial report vintages.

## User Value

CORE-04-C turns the captured public/free source set into actual model-observation evidence that P3 can consume. The result is a deterministic, replayable TTM EV/EBITDA series rather than a retrospective vendor multiple.

## Product Surface

`tools/core04c_ev_ebitda.py` performs:

- exact-byte capture of 3 SZSE EOD snapshots and 5 CNINFO report vintages;
- XLSX parsing for the 300750 close;
- PDF parsing for profit, interest expense, depreciation/amortization and balance-sheet bridge inputs;
- PIT TTM EBITDA construction;
- standard interest-bearing net-debt bridge;
- enterprise value and EV/EBITDA calculation;
- exact-byte SHA-256 re-verification before success;
- JSON derivation and admission receipts.

## PIT Construction

For each market date:

`TTM EBITDA = current period EBITDA + prior fiscal-year EBITDA - prior-year comparable period EBITDA`

This is constructed only from report vintages whose `known_at` is on or before the market observation date.

The three target dates are:

- 2026-07-27: H1 2026 + FY2025 - H1 2025.
- 2026-04-17: Q1 2026 + FY2025 - Q1 2025.
- 2025-10-22: 9M 2025 + FY2024 - 9M 2024.

EBITDA is derived consistently as:

`profit total + interest expense + depreciation/amortization`

Net debt is:

`short-term borrowings + current portion of non-current liabilities + long-term borrowings + bonds + lease liabilities - cash - trading financial assets`

## Evidence Boundary

The market price comes only from the exact-date SZSE snapshot. Current retrospective provider pages are not used.

Derived EBITDA and net debt are treated as deterministic derivations with a dedicated derivation artifact containing the component source hashes and formula. They are not presented as direct issuer-disclosed EBITDA.

## Test / Acceptance

PASS requires:

- unit tests green;
- all declared source captures succeed with non-zero exact bytes and SHA-256;
- the 300750 row is parsed from each exact-date SZSE snapshot;
- all required financial rows are parsed from each PIT financial report;
- every financial source used for a market observation has `known_at <= observation_date`;
- all three EV and EBITDA values are strictly positive;
- the generated admission receipt is JSON-valid;
- exact source-byte hashes re-verify after parsing;
- raw source bytes and derived receipts are retained in the CI artifact for audit/replay.

## Out of Scope

No MIE promotion, Expectation Gap, Expected Return, decision-state change, position sizing, CSI800/industry universe work, or automatic execution is introduced.
