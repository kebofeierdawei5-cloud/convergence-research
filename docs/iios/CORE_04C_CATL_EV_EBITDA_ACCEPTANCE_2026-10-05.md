# CORE-04-C CATL EV/EBITDA Acceptance — 2026-10-05

Status: IMPLEMENTATION

This task converts the six previously captured historical market/company sources plus FY2024/FY2025 annual reports into three PIT historical EV/EBITDA observations.

Admission basis:

- market close is read from the official SZSE daily snapshot;
- balance-sheet inputs are read from the latest company report known by the market date;
- EBITDA is reconstructed from the latest completed fiscal-year annual report already public by the market date;
- enterprise value = market capitalization + net debt;
- net debt = short-term debt + current portion of non-current liabilities + long-term debt + bonds + lease liabilities + long-term payables - cash;
- shares use reported total share capital, explicitly recorded as the share-count basis.

The repeated SZSE XLSX responses have shown raw-byte drift across retrievals. This does not change the target row semantics, so this task records the exact hash of the actual captured bytes and separately records the difference from the prior capture. No previous hash is overwritten.

Expected reconstructed EBITDA:

- FY2024: 91,999,043,000 CNY.
- FY2025: 119,197,217,000 CNY.

These are reconstructed from the official annual-report income statement and cash-flow supplemental data. The FY2024 annual report was published 2025-03-15; the FY2025 annual report was published 2026-03-10. The latter is therefore PIT-valid for 2026-04-17 and 2026-07-27.

The three expected historical EV/EBITDA observations are approximately:

- 2025-10-22: 16.3855x
- 2026-04-17: 15.1303x
- 2026-07-27: 13.6687x

The output is historical market-observation evidence only. It does not itself assert that EV/EBITDA is the true current market model, and it does not unlock Expected Return or Decision Kernel.

## Acceptance

PASS requires the real source files to download, deterministic parsing to succeed, all PIT dates to be valid, and all three observations to be emitted as ADMITTED.

## Out of scope

Forward PE, MIE promotion, Expectation Gap, Expected Return, Decision Kernel, CSI800/A02, universe database and paid-data sources.
