# A02 DATA-01-B Run #2 — Independent Adjudication

Workflow run 37593042893; head 6e8fc8ef9639c486daae33aa74bb64b86366c4dc; artifact 11469004605.

## Integrity

GitHub artifact digest: sha256:dabc25996524f03e8c533e33bd7921ed5c03e85a4b72edbf1b3a15589c4b17ec

Independent ZIP SHA-256: dabc25996524f03e8c533e33bd7921ed5c03e85a4b72edbf1b3a15589c4b17ec

Result: PASS.

The artifact contains 9 files. Its independent raw-byte manifest contains 8 entries; all 8 hashes recomputed exactly with zero mismatches.

## PIT sufficiency

- Identity: BLOCKED — current exchange snapshots only; historical source-vintage / known_at not closed.
- Listing / delisting: BLOCKED_FOR_PIT — current listing dates exist, but source-side publication / known_at is not established.
- Common equity: BLOCKED_FOR_PIT — current instrument metadata exists, but historical authority / known_at is not established.
- ST status: BLOCKED — current risk-plate snapshot only.
- CSI taxonomy definition: PASS_FOR_STANDARD_DEFINITION.
- CSI security-level industry history: BLOCKED — no historical assignment carrier with reproducible known_at.
- Baostock: BLOCKED at login (10002007 网络接收错误), therefore not admitted.

Overall B sufficiency: BLOCKED.

## Governance finding

The emitted admission matrix contained a stale provenance reason claiming that free secondary effective dates had been materialized, while the artifact contains only a blocked Baostock receipt and no secondary data files.

The canonical materializer logic is corrected in the accompanying commit. The correction does not relax any admission condition.

Confirmatory model selection and the cross-security successor epoch remain locked.
