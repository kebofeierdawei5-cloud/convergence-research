# CORE-04-C — 300750 Historical EV/EBITDA PIT Observation Admission v0.1

Date: 2026-10-05
Status: FINAL ACCEPTED / LIVE CI PASS

## Objective

Admit a minimum three-point historical EV/EBITDA observation set for CATL (300750.SZ) using exact-date SZSE market snapshots plus PIT-known CNINFO financial report vintages.

## User Value

CORE-04-C converts CORE-04-B public-source captures into actual deterministic valuation observations that can be consumed by model-identification work. It must never replace missing historical inputs with a current retrospective provider multiple.

## Product Surface

`tools/core04c_ev_ebitda.py` performs:

- exact-byte capture of the declared SZSE EOD snapshots and CNINFO report vintages;
- XLSX parsing for the 300750 close;
- PDF parsing for consolidated profit, interest expense, depreciation/amortization and balance-sheet bridge inputs;
- PIT validation of source `known_at` against each market observation date;
- deterministic EBITDA selection:
  - TTM where the report vintage supplies all required comparable-period components;
  - otherwise the latest fully disclosed fiscal-year EBITDA known by the observation date;
- enterprise value and EV/EBITDA calculation;
- SHA-256 re-verification of every exact source byte before success;
- JSON derivation and admission receipts.

## PIT Construction

The three observations deliberately use different EBITDA bases because the quarterly CNINFO reports available at the older dates do not provide a complete depreciation/amortization supplement needed to construct a robust quarterly TTM EBITDA bridge.

### 2026-07-27

Use deterministic TTM EBITDA:

`TTM EBITDA = H1 2026 EBITDA + FY2025 EBITDA - H1 2025 comparable EBITDA`

The H1 2026 report contains both current and prior-period supplemental depreciation/amortization inputs, so the TTM bridge can be completed without look-ahead.

### 2026-04-17

Use **FY2025 EBITDA — latest fully disclosed fiscal-year EBITDA known at the observation date**.

The 2025 annual report was published before this market date. The Q1 2026 report does not expose the required cash-flow supplementary depreciation/amortization detail, so a synthetic Q1 TTM is not admitted.

### 2025-10-22

Use **FY2024 EBITDA — latest fully disclosed fiscal-year EBITDA known at the observation date**.

The 2024 annual report was published before this market date. The Q3 2025 report does not expose the required cash-flow supplementary depreciation/amortization detail, so a synthetic Q3 TTM is not admitted.

## Valuation Bridge

`EV = price * shares_outstanding + net_debt`

`EV / EBITDA = EV / EBITDA_basis`

Net debt:

`short-term borrowings + current portion of non-current liabilities + long-term borrowings + bonds + lease liabilities - cash - trading financial assets`

Share count:

`share capital (CNY thousand) * 1000`

The bridge is a deterministic valuation construction, not a claim that the issuer reports the exact derived EBITDA or EV figure.

## Evidence Boundary

The market price is taken from the exact-date SZSE EOD snapshot.

Financial inputs are taken from the report vintage that was knowable at the observation date. Current retrospective provider pages, current consensus screens, or a later restatement of historical valuation multiples are not used.

The admission receipt distinguishes:

- direct market evidence;
- source-vintage financial evidence;
- deterministic derived EBITDA/net-debt evidence.

Derived evidence hashes the immutable derivation artifact rather than presenting the derived number as a direct issuer observation.

## Final Live Verification

- CI run: `37261504704`
- CI job: `111609522344`
- CI result: **PASS**
- Unit tests: **8 passed**
- Live capture / parse / admission: **PASS**
- JSON re-verification: **PASS**
- Raw-source + receipts artifact: `11324627858`
- Artifact ZIP SHA-256: `00ca7f00bcf98153d31cbd4be036cb23626c52d3d3d9138d01e83d1f66109037`
- Derivation receipt SHA-256: `ed476c7f2613c80ac67ab4e6a996c0737bb4ef15b4caf89f42f72ba9edb88e6e`
- Admission receipt SHA-256: `743d999cca969170210df1c03fedc10cce3c1cc829795d59b798715f2ba6762b`

| Observation date | Price | EBITDA basis | EBITDA (CNY) | Net debt (CNY) | EV/EBITDA |
|---|---:|---|---:|---:|---:|
| 2026-07-27 | 400.00 | TTM H1 2026 | 139,451,341,000 | -291,182,555,000 | 11.182953x |
| 2026-04-17 | 444.20 | FY2025 latest PIT | 119,197,217,000 | -285,865,524,000 | 14.610167x |
| 2025-10-22 | 372.86 | FY2024 latest PIT | 91,999,043,000 | -238,640,390,000 | 15.898702x |

The older two observations are deliberately **not** synthetic TTM values: the corresponding Q1/Q3 reports do not expose the complete depreciation/amortization supplement required for a robust PIT TTM bridge, so the implementation uses the latest fully disclosed FY EBITDA known by each observation date.

## Test / Acceptance

PASS requires all of the following:

- unit tests green;
- all declared source captures succeed with non-zero exact bytes and SHA-256;
- the 300750 row is parsed from each exact-date SZSE snapshot;
- required balance-sheet and financial-report fields are parsed from each selected CNINFO vintage;
- every financial source used by an observation satisfies `known_at <= observation_date` in executable code;
- TTM is constructed only when all required PIT comparable-period inputs are available;
- otherwise the latest fully disclosed FY EBITDA is used and explicitly labeled;
- EV and EBITDA are strictly positive;
- generated derivation/admission JSON is valid;
- exact source-byte hashes re-verify after parsing;
- the CI artifact retains the raw captured source bytes and generated receipts for replay/audit.

## Out of Scope

No Market Implied Expectation promotion, Expectation Gap, Expected Return, decision-state change, position sizing, CSI800/industry universe work, or automatic execution is introduced.
