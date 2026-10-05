# CORE-04-C Final Acceptance — 300750 Historical EV/EBITDA PIT

Date: 2026-10-05

## Result

**PASS / ADMITTED**

CORE-04-C is now a completed Investment Core data gate for the 300750.SZ case. The historical EV/EBITDA observations were captured from exact source bytes, parsed deterministically, checked for PIT ordering, passed the existing typed market-observation admission function, and survived JSON/integrity verification in CI.

## Execution

- Repository: `kebofeierdawei5-cloud/convergence-research`
- PR: #55
- Branch: `core04c/300750-ev-ebitda-pit-20261005`
- CI run: `37261504704`
- CI job: `111609522344`
- CI result: **PASS**
- Unit tests: **8 passed**
- Live capture / parse / admission: **PASS**
- JSON re-verification: **PASS**
- Artifact: `11324627858`
- Artifact ZIP SHA-256: `00ca7f00bcf98153d31cbd4be036cb23626c52d3d3d9138d01e83d1f66109037`

## Admitted Observations

| Date | Price | EBITDA basis | EBITDA | Net debt | EV | EV/EBITDA |
|---|---:|---|---:|---:|---:|---:|
| 2026-07-27 | 400.00 | TTM H1 2026 | 139.451bn | -291.183bn | 1,559.478bn | 11.18295x |
| 2026-04-17 | 444.20 | FY2025 latest PIT | 119.197bn | -285.866bn | 1,741.491bn | 14.61017x |
| 2025-10-22 | 372.86 | FY2024 latest PIT | 91.999bn | -238.640bn | 1,462.665bn | 15.89870x |

### Basis decision

Only 2026-07-27 is a deterministic PIT TTM observation because the H1 2026 filing contains both current and comparative supplemental depreciation/amortization inputs needed for the bridge.

For 2026-04-17 and 2025-10-22, the quarterly filings do not provide the complete supplemental depreciation/amortization detail required for a robust synthetic TTM EBITDA calculation. The implementation therefore **does not invent a TTM**. It uses the latest fully disclosed FY EBITDA known on the observation date and labels the basis explicitly.

## PIT / Evidence Checks

1. Eight external source files were captured as exact bytes and SHA-256 recorded.
2. Every financial source used by an observation satisfies `known_at <= observation_date` in executable code.
3. The market price is taken from the exact-date SZSE EOD snapshot.
4. Derived EBITDA and net debt are bound to the immutable derivation artifact hash.
5. All three observations passed the existing `VerifiedMarketEvidence → admit_market_valuation_observation` typed admission path.
6. EV bridge and EV/EBITDA arithmetic were independently re-verified from the final artifact.
7. The final CI artifact retains raw source bytes plus derivation/admission receipts for replay/audit.

## Permanent Receipt

Canonical compact receipt:

`research/core04c_ev_ebitda_admission_receipt_v0.1.json`

Detailed implementation:

`tools/core04c_ev_ebitda.py`

Execution contract:

`docs/iios/CORE_04C_EV_EBITDA_PIT_ADMISSION_v0.1.md`

## Boundary

CORE-04-C does **not** introduce Market Implied Expectation, Expectation Gap, Expected Return, decision-state changes, position sizing, CSI universe work, or automatic execution.

The next consumer is the existing P3/P4 ratio-family market-model path, now with actual admitted 300750 EV/EBITDA observations available rather than a placeholder or retrospective vendor multiple.
