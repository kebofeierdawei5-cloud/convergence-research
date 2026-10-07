# M1.2 A02 — Runtime Acquisition Audit & Development Plan

Date: 2026-10-07
Status: DIAGNOSTIC / CANONICAL STATE EVIDENCE
Universe: OU-M12-A02-CSI800-NONFIN-PIT-001

## 1. Actual execution evidence

- Workflow: A02 Exact Raw Materialization
- Run: 37588901115
- Job: 112684403959
- Run head: cd0db18cb33b06c462b79c1313b5112d2efae847
- Acquisition step: SUCCESS
- Deterministic hash manifest: SUCCESS
- Immutable artifact upload: SUCCESS
- Final admission gate: FAILURE
- Run conclusion: failure by the final fail-closed gate

Artifact:
- Artifact ID: 11468022181
- Name: A02-exact-raw-37588901115
- Size: 199685 bytes
- GitHub artifact digest: b385d27e24b5765aca9c62e50bd01617c6553a1985f44f6be040e20ec47ab180
- Independently recomputed ZIP SHA-256: b385d27e24b5765aca9c62e50bd01617c6553a1985f44f6be040e20ec47ab180
- Artifact integrity: PASS

The artifact and independent verification record are also retained in the persistent Library under /iios/A02/.

## 2. A-side result

The runner retrieved the official current CSI800 constituent carrier:

- exact bytes present: YES
- size: 169984 bytes
- observed SHA-256: b3338f5f6fdfd04a72fb42f5444539507b50ee4805c83dabb04ec26e54c3b5fb
- frozen historical validation target: f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984
- size match: TRUE
- SHA-256 match: FALSE
- role: CURRENT_SNAPSHOT_NOT_HISTORICAL_TARGET

Therefore A is not historically admitted.

Archive recovery in this run did not produce exact historical bytes. Wayback CDX had service-unavailable/zero-capture responses; Wayback Availability returned no snapshot for the tested target timestamp; Memento DNS resolution failed; Arquivo.pt did not return a usable JSON CDX response; Common Crawl target probes returned service errors/timeouts.

## 3. B-side result

The free-first runner did not materialize the PIT Security Eligibility / Master raw bundle.

- B raw bundle: NOT PRESENT
- pit_admission: BLOCKED_FREE_FIRST_ROUTE_NOT_MATERIALIZED
- Tushare token: NOT CONFIGURED

No B evidence may be inferred from current/static security-master data.

## 4. Required A02 state transition

RAW_CAPTURED = PASS
CAPTURE_VERIFIED = BLOCKED
PIT_RECONSTRUCTION_READY = BLOCKED
INDEPENDENT_REPLAY_PASS = BLOCKED
A02_ADMISSION_PASS = BLOCKED

## 5. Requirements / principle audit

### Alignment — PASS

1. A02 remains a Research Track prerequisite, outside the Investment Core.
2. Current data has not been back-applied to historical origins.
3. Exact bytes are distinguished from declared hashes.
4. SHA-256 is recomputed from actual bytes.
5. Acquisition failure is fail-closed.
6. known_at is not inferred from retrieval time.
7. FM02/FM03/A02-FM04/FM05/FM06/model-selection remain locked.
8. The current M1.2 research epoch remains closed; no result-driven redesign was introduced.
9. No paid data dependency was introduced.
10. The runtime artifact pointer is explicitly diagnostic, not admission evidence.

### Process deviations / risks — FIX NEEDED

1. The workflow can write a diagnostic runtime pointer back to canonical main. It must remain non-authoritative and must never become a data-admission input.
2. Archive-probe code has accumulated multiple recovery routes. Further generic archive fan-out now has lower priority than obtaining a real historical source carrier.
3. The B execution path does not currently materialize a complete free-first PIT evidence bundle. The next development batch must make B acquisition explicit and bounded.
4. The frozen target SHA remains only a validation target until the exact historical bytes are independently recovered.
5. The state index did not previously record the actual 2026-10-07 runtime outcome; this audit records it.

## 6. Next development plan

### A02-A — Evidence Supply Gate

Priority is actual evidence acquisition, not more generic recovery code.

A required:
- exact historical 000906cons.xls matching 169984 bytes and SHA-256 f8e4aa8d...b2b984, OR
- an immutable historical source bundle that contains equivalent exact bytes plus source-vintage evidence sufficient for deterministic reconstruction.

B required:
- identity
- listing/delisting
- common-equity eligibility
- ST history
- CSI industry history
- source-vintage/publication evidence

No admission work proceeds until A and B raw evidence are physically present.

### A02-B — Independent Raw Verification

Use a verifier separate from the collector:

artifact integrity
-> per-file SHA-256
-> exact A target comparison
-> B manifest completeness
-> receipt consistency

The collector's own receipt is not sufficient.

### A02-C — PIT Reconstruction

After raw evidence exists:

source-vintage/publication basis
-> effective interval reconstruction
-> known_at <= origin_cutoff
-> 11/11 origins
-> unresolved conflict = UNKNOWN / exclusion

### A02-D — Independent Replay

Re-run A02 from a clean environment using only admitted raw evidence and compare canonical output against an independent verifier.

### A02-E — Admission

Only after A02-C and A02-D pass:
A02_ADMISSION_PASS

This unlocks only the explicitly downstream cross-sectional research path. Model selection remains separately locked.

## 7. Explicit non-goals

Do not:
- modify FM04/FM05 semantics to accommodate current data;
- reopen the closed M1.2 epoch;
- start model selection;
- substitute 申万 for CSI industry as the primary exclusion taxonomy;
- infer known_at from effective dates or retrieval time;
- treat current 000906 as historical PIT evidence;
- declare A02 PASS from metadata, checksum declarations, or self-authored receipts.

## 8. Current verdict

A02 = BLOCKED

Reason: historical A exact bytes and the complete B PIT raw evidence bundle are both absent.
