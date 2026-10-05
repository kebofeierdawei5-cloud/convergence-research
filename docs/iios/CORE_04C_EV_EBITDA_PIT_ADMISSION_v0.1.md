# CORE-04-C — PIT EV/EBITDA Observation Admission v0.1

Status: IMPLEMENTATION

## Objective

Materialize the exact public/free source bytes previously captured by CORE-04-B, verify every byte against the historical Receipt, then parse enough company and market data to create auditable PIT EV/EBITDA observations for 300750.

## Source pairing

- 2026-07-27 market snapshot + 2026 H1 report.
- 2026-04-17 market snapshot + 2026 Q1 report.
- 2025-10-22 market snapshot + 2025 Q3 report.

## Hard gate

CORE-04-C may not consume a source unless its current size and SHA-256 exactly match the CORE-04-B Receipt.

This prevents a current re-issued PDF/XLSX from silently replacing the bytes used in the earlier capture run.

## EV/EBITDA definition

For each historical date:

EV = market capitalization + net debt

EV/EBITDA = EV / EBITDA

where market capitalization = historical close × shares outstanding.

Net debt and EBITDA must come from the latest company disclosure known by that historical market date; later filings must not be used.

## Important PIT rule

A company report's period end is not its known_at.

Only the publication/availability date may anchor PIT admissibility. A Q2/H1 report published on 2026-07-24 can support a 2026-07-27 observation; a report published after 2026-07-27 cannot.

## Current expected gate

Forward PE remains blocked.

Historical EV/EBITDA may become admissible only if:

- exact raw bytes match the Receipt;
- 300750 is identified in the market snapshot;
- close and share count are extracted deterministically;
- EBITDA, net debt and their publication vintages are extracted from the company report;
- all required variables are available by the corresponding market date;
- the constructed observation passes CORE-04-A.

## Out of scope

No MIE promotion, Expectation Gap, Expected Return, Decision Kernel, CSI800/A02 or universe database changes are made in this task.
