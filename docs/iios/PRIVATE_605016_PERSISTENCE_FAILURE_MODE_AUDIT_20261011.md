# 605016 Private B2 Persistence — Closure and Failure-Mode Audit

**Audit date:** 2026-10-11  
**Case:** `RC-CN-A-605016-20261009`  
**Audit type:** operator-result reconciliation, incident root-cause review, and defensive persistence-path hardening  
**Data handling:** metadata/status/hash only. No numeric market quote, private filesystem path, or raw source bytes are recorded here.

## 1. Current outcome

The operator supplied a successful local launcher result after PRs #321–#324:

- adjudicator: `PASS_EPHEMERAL_B2`;
- candidate manifest: `PASS`;
- required field groups admitted: 7; missing required groups: 0;
- exact official price raw SHA-256 matched the pinned value;
- local persistence: `PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED`;
- evidence records: 11; Core validator: `PASS`;
- candidate fingerprint: `c6b78f0185e27ddb089af723f1811ec00185775ca3dbbd679a933a887c566350`;
- private manifest SHA-256: `034a4b5de2693d725422d9fb740ba4d5364a63b6b080531ee15a9b1bfff1a7da`;
- `exact_first_public_timestamp_verified=false`; `source_vintage_review_required=true`;
- no formal signed admission, production Host acceptance, bundle, decision, or automatic execution.

This closes the repeated **ingest/write failure** sequence based on the actual operator result. GitHub CI cannot inspect the Mac's private filesystem, so the independent read-only `--verify-existing` replay remains the final confirmation of the post-promotion stored copy.

## 2. Incident sequence and permanent controls

| Failure observed | Root cause | Permanent correction / regression gate |
|---|---|---|
| `ATTEMPT10_ARTIFACT_API_TRANSPORT_FAILED` | API metadata download depended on one Python HTTPS transport. | PR #317: bounded `curl` fallback; TLS and sanitized diagnostics retained. |
| `ATTEMPT10_ARTIFACT_DOWNLOAD_TRANSPORT_FAILED` | Signed artifact ZIP body depended on Python HTTPS only. | PR #318: HTTPS-only `curl` fallback without forwarding GitHub bearer token; exact archive size/hash before extraction. |
| `UNEXPECTED_PRIVATE_INGEST_FAILURE` / `NameError` | Prior-dividend recovery path referenced an unbound final URL. | PR #319: derive the URL from the validated dividend capture and enforce official-host HTTPS allowlisting. |
| `OFFICIAL_SSE_HTTPS_PRICE_FETCH_BLOCKED` | Price acquisition lacked bounded fallback transport and the pinned alternate official TLS port. | PR #320: Python HTTPS, bounded HTTPS `curl`, then fixed official alternate port; unchanged exact-byte/date-row gate. |
| `EPHEMERAL_B2_MANIFEST_STATUS_NOT_PASS` | The final in-memory manifest was not written to the workspace path consumed by the private ingester; adjacent report transport semantics were inconsistent. | PR #321: materialize the final manifest after adding price evidence; separate normalized TLS verification from the concrete transport method; producer/consumer regression test. |
| `RAW_ARTIFACT_PATH_DUPLICATED` | Evidence-centric manifests may bind multiple facts to the same original PDF/HTML bytes, but private storage assumed paths must be globally unique per declaration. | PR #323: permit repeated path only when every declaration agrees on size and SHA-256; validate each evidence declaration; write one shared raw file; offline replay uses the same path-contract rule. |

The underlying process defect was **missing integration coverage across component boundaries**, not a need to relax the evidence gate. Earlier unit tests validated individual helpers but did not prove that the successful producer output was exactly what the private consumer later read and persisted.

Canonical traceability is recorded in State Index:
- PR #321 — final-manifest handoff and TLS report contract;
- PR #322 — state synchronization;
- PR #323 — shared raw-source path semantics;
- PR #324 — state synchronization after that fix.

## 3. Deep-audit result and added defensive hardening

Merged hardening PR #325 (merge commit `819a4080992a09e02e01a169a1c5be2951667976`; 13/13 exact-head checks passed) strengthens the local copy boundary beyond the failures already fixed:

1. Validate all declarations and shared-path size/hash contracts before writing.
2. Reject symlinked path components in the ephemeral raw-source tree rather than calling `is_symlink()` only after `resolve()` (which would have lost evidence that the original path was a symlink).
3. Read and hash every unique source byte object and compare each evidence declaration before creating the raw-output directory.
4. Copy the already-verified byte sequence only after the complete declared set passes, preserving shared-path de-duplication.
5. Keep the existing persisted-copy Core/PIT replay and receipt hash/semantics checks.
6. Make the sanitized result distinguish `raw_artifact_declaration_count` from `unique_raw_file_count`. For backward compatibility, the existing `raw_artifact_count` field remains an alias for declaration count; the local receipt schema is not rewritten.

New regression tests cover:
- a later bad hash does not leave an earlier good artifact copied into a destination;
- a symlinked raw source is blocked before destination creation;
- two distinct evidence records share one exact raw source and pass persist + offline replay;
- a shared path with conflicting byte contracts fails closed;
- the real Core-validator fixture permits consistent shared-path declarations.

This hardening does not change the contents, fingerprint, manifest SHA-256, or receipt schema of the candidate already persisted on the operator Mac.

## 4. Controls deliberately not relaxed

- Pinned Attempt 10 ZIP exact size/SHA-256 and safe archive extraction.
- Official source host/TLS checks; no HTTP downgrade.
- Exact official price raw-byte hash, observation date and single-row match.
- Candidate manifest `PASS`, empty validation errors, seven required field groups and unchanged Core/PIT validation.
- Raw files are restricted to manifest-referenced paths; shared source paths require identical size/hash contracts.
- Private-root path, owner and permission controls; immutable content-addressed candidate; staged validation before promotion.
- No raw source bytes or numerical quotes are uploaded as GitHub artifacts by the local ingester workflow.
- No automatic promotion to signed admission, production Host acceptance, request bundle, decision, publication, or trade execution.

## 5. Next step and remaining gates

**Do not rerun ingest again merely to check storage.** The hardening PR is already merged into canonical `main`. Perform one read-only verification using the already existing candidate:

```bash
bash "$HOME/Downloads/Launch_IIOS_Private_605016_B2_Ingest.command" --verify-existing
```

Expected status: `VERIFIED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED`. This mode must not re-download the Attempt 10 artifact or request the official price/dividend source endpoints; it validates the already persisted copy.

That read-only replay is a storage-integrity check only. It does not resolve the explicit source-vintage limitation: the official historical price endpoint does not establish its exact first-public timestamp. Source-vintage adjudication and genuine production Host acceptance remain separate gates before formal investment decisions or reports are authorized.
