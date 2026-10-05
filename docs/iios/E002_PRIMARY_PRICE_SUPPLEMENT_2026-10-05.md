# E002 Primary-Source Supplement — 2026-10-05

Status: PASS / PRIMARY CAPTURED — PRIVATE RAW

## Objective

Close the CATL E002 material primary-price source gap without publishing SZSE trading-information bytes into the public repository.

## Evidence

- Case: `RC-CN-A-300750-20261004`
- Legacy evidence retained: `E002` (secondary Stockstar observation)
- Primary supplement: `E011`
- Field: `market_price.close.2026-09-30`
- Observation date: `2026-09-30`
- Known-at: `2026-09-30`
- Value: `291.11 CNY/share`
- Source: `SZSE:MARKET_DATA`
- Raw filename: `E002_SZSE_primary_2026-09-30.xlsx`
- Raw size: `231394` bytes
- Raw SHA-256: `349b422f6f9c95d5ea8787aa664e8cd913f9aac3b056914e68f3826567cd6ea2`
- Manifest SHA-256: `662804bd3f882b2d0b8ce17a73195f2d75a84e668442dbd00348072d624d28a0`
- License status: `UNKNOWN`

## Storage boundary

The raw SZSE trading-information bytes are retained outside the public repository. Public repository state contains only the evidence record, provenance, expected size/hash, and verification contract.

The exact-byte verification boundary is:

```
private raw vault
      ↓
size + SHA-256 recomputation
      ↓
E011 evidence record
      ↓
PIT / source-role validation
```

A public CI run that does not have the private raw vault MUST remain BLOCKED for exact-byte verification.

## CORE-03 binding

CORE-03 now receives a dedicated `price_evidence` object. The valuation `price_evidence_id` must match that evidence object, and `price_cny` must equal the admitted evidence value.

This removes the prior hard-coded dependency on legacy E002 while preserving E002 as append-only historical evidence.

## Out of scope

No CSI800, CSI Industry, universe database, PIT security master, paid data dependency, or general historical market-data platform is introduced.
