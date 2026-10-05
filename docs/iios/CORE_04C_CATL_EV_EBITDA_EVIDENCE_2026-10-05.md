# CORE-04-C — CATL 300750 Historical EV/EBITDA Evidence

Date: 2026-10-05
Case: RC-CN-A-300750-20261004
Status: FINAL CANDIDATE — awaiting CI merge gate

## Admission result

All three historical observations were constructed from exact raw bytes fetched in the CI run and passed the CORE-04-A admission engine.

Each observation contains four admitted evidence records:

- market_price
- shares_outstanding
- net_debt
- EBITDA

The admission engine returned:

`ADMITTED`, with zero blockers.

## Calculation basis

EV = historical close × reported total share capital + interest-bearing debt − cash.

EV/EBITDA = EV / latest known completed fiscal-year EBITDA.

This is deliberately **not TTM** in this batch. The denominator is the latest completed fiscal-year EBITDA that was publicly knowable by the market observation date.

## Historical observations

| Date | Close | Shares | Net debt | EBITDA | EV/EBITDA |
|---|---:|---:|---:|---:|---:|
| 2025-10-22 | 372.86 | 4,562,854,000 | -193,859,897,000 | 91,999,043,000 | 16.3854513730104779459499377618525879665943916394869455326834x |
| 2026-04-17 | 444.20 | 4,564,063,000 | -223,867,376,000 | 119,197,217,000 | 15.1302979548591306456425069051738011634952852968035319146755x |
| 2026-07-27 | 400.00 | 4,626,654,919 | -221,391,911,000 | 119,197,217,000 | 13.6686920853194080865159796474107277185842350664948830139214x |

## Source evidence

### 2025-10-22

Market source:
- SZSE daily snapshot.
- Current captured size: 230,182 bytes.
- Current captured SHA-256: `359aa844467b5aaae9c0ef719f8191650c4fca0f0c85ce508d26ea6dc4f10d30`
- Parsed row: 300750 / 宁德时代 / close 372.86.

Financial source:
- CATL 2025 Q3 report, published 2025-10-21.
- SHA-256: `d099bc0054f4bf8624d34fffa2c82399b7d8e31cce8f84aab909955da9d84f50`.
- Balance-sheet basis: interest-bearing debt less cash.
- Share-count basis: reported total share capital.

EBITDA source:
- CATL 2024 annual report, published 2025-03-15.
- SHA-256: `b4f1713d7b821eb076c102711d177fe942ccc2bc8dd171ae5d7a95799a65b0ad`.
- EBITDA: 91,999,043,000 CNY.

### 2026-04-17

Market source:
- SZSE daily snapshot.
- Current captured size: 231,970 bytes.
- Current captured SHA-256: `f83bf14d5f10a4cc74484693c5cb3baa38bd3c747e63486ad7fd38eecbce34d9`.
- Parsed close: 444.20 CNY/share.

Financial source:
- CATL 2026 Q1 report, published 2026-04-16.
- SHA-256: `32e4936e6dd68a89741a8167b4c4ae3f8b4bc7ef61d70f35b294e1cb0e46fbe8`.

EBITDA source:
- CATL 2025 annual report, published 2026-03-10.
- SHA-256: `c15272977147dee7e6935a38ea0e4fd6855370aabb106f54cfe20f7cf6048ec9`.
- EBITDA: 119,197,217,000 CNY.

### 2026-07-27

Market source:
- SZSE daily snapshot.
- Current captured size: 229,586 bytes.
- Current captured SHA-256: `9ac5fe3b92b7490a048579830d15cd1979c194c22c4bf73c3716bec4ba3dc3a3`.
- Parsed close: 400.00 CNY/share.

Financial source:
- CATL 2026 H1 report, published 2026-07-24.
- SHA-256: `aa40daf911df40f56900dc506d7debe05a4fea43cd533474039a408e3b5aabcc`.
- Exact reported total share count: 4,626,654,919 shares.

EBITDA source:
- CATL 2025 annual report, published 2026-03-10.
- SHA-256: `c15272977147dee7e6935a38ea0e4fd6855370aabb106f54cfe20f7cf6048ec9`.

## PIT checks

For every observation:

`known_at <= observation_date <= 2026-10-04 cutoff`.

No later report is used for the corresponding historical observation.

## Source-byte drift

Repeated SZSE downloads can differ by a small number of wrapper bytes. CORE-04-C therefore records the **exact SHA-256 of the bytes used in the admitted observation**, rather than asserting that the public endpoint is byte-stable across retrievals.

Historical capture hashes from CORE-04-B remain append-only and are not overwritten.

## Boundary

This evidence establishes historical market observations for the EV/EBITDA family. It does not establish that EV/EBITDA is the unique true market model, does not promote MIE, and does not unlock Expected Return or Decision Kernel.
