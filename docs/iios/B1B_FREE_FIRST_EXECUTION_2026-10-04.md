# B1-B Free-First PIT Raw Evidence — Execution Record

Date: 2026-10-04

## Current state

`B1B_FIELD_ADMISSION = BLOCKED` by design.

Official public captures are being preserved byte-for-byte. BaoStock is used only as a free secondary reconciliation/PIT candidate. Its historical daily interface exposes `isST`, but the returned rows do not establish source-side publication/known_at provenance, so IIOS does not promote them to normative evidence.

## B1-B2 ST pilot

`research/a02_b1b/st_history_pilot.py` deterministically seeds the current CSI800 800-code population, captures the current 000906 workbook, and queries historical daily `date,code,tradestatus,isST` from 2023-01-01 through 2026-03-31 for a bounded pilot sample.

Pilot results remain `CONDITIONAL` until field-level `known_at` evidence is established.

## Authority boundary

- SSE/SZSE/CSI official sources = normative source candidates.
- BaoStock = free secondary reconciliation/PIT candidate.
- Current source state never substitutes for historical PIT.
- Effective date never substitutes for known_at.
- `retrieved_at` never substitutes for known_at.

## Next

After the pilot, expand historical ST only if response quality and reproducibility are adequate; in parallel close security-level CSI Industry history using a free public source with reproducible source-vintage metadata.
