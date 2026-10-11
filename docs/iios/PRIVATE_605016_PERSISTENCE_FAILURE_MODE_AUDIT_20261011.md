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


## 6. Follow-up incident: read-only verifier import environment — 2026-10-11

The operator's `--verify-existing` run returned `BLOCKED / UNEXPECTED_PRIVATE_INGEST_FAILURE` with `error_type=ModuleNotFoundError`. Its receipt explicitly reports `private_store_written=false`; no admission, Host acceptance, bundle or decision was created.

**Root cause identified in the current entry-point path:** the default Core validator is imported by `_validate_core()`. The ingest path happened to add the repository root to `sys.path` while importing the official HTTPS adjudicator; the read-only verifier deliberately skips adjudication and never performed that setup. Therefore the verifier could fail to import `iios_mvp.canonical_evidence_admission_v01` before it inspected the persisted candidate. This is a Python import-environment defect, not evidence that the local candidate bytes or receipt are corrupt.

**Corrective change under review:** make `_validate_core()` establish the import root explicitly from the effective `repository_root` argument and propagate that argument through persist-time and offline replay call sites. A regression test constructs an isolated temporary canonical-runtime package, removes that path and cached package modules from the test process, and proves the default validator import succeeds only after the function bootstraps the repository path.

**Operator action:** do not rerun ingestion, do not fetch Attempt 10, and do not contact official source endpoints. After the fix is merged, repeat only the existing-candidate read-only verification once. A PASS verifies local storage integrity only; source-vintage review and production Host acceptance remain separate gates.


## 7. Final replay outcome after PR #327 — PASS — 2026-10-11

The operator supplied the output of the read-only `--verify-existing` run after PR #327 had been merged.

- Status: `VERIFIED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED`.
- Candidate count: 1.
- Candidate fingerprint: `c6b78f0185e27ddb089af723f1811ec00185775ca3dbbd679a933a887c566350`.
- Private manifest SHA-256: `034a4b5de2693d725422d9fb740ba4d5364a63b6b080531ee15a9b1bfff1a7da`.
- Evidence records: 11; artifact declarations: 11; unique physical raw files: 8; Core/PIT validator: PASS.
- `official_source_refetched=false`; signed admission, production Host acceptance, request bundle and Decision remain false; Human Approval remains required; auto execution remains false.

This closes the outstanding **local storage-integrity confirmation**. PR #327's import-path fix is no longer merely under review: it is merged to canonical `main`, and its exact-head private persistence contract completed 48/48 tests, with State Hygiene, independent red-team and the related workflow set passing.

The record must not be over-interpreted. The replay does not establish the exact first-public timestamp of the 2026-10-08 historical quote. `exact_first_public_timestamp_verified=false` and `source_vintage_review_required=true` therefore remain in force. The next engineering task is a separate source-vintage/PIT policy adjudication; do not rerun ingestion or this already-passing storage verifier as a substitute for that work.


## 8. C1 source-vintage/PIT bounded adjudication — 2026-10-11

The local storage gate was closed by the operator's read-only replay (Section 7). PR [#329](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/329) now implements a separate bounded-public-availability adjudication:

- Official source: SSE `上海证券交易所交易规则（2026年修订）`, document `上证发〔2026〕41号`, published 2026-04-24, effective 2026-07-06; URL: https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20260424_10816482.shtml.
- Rules §§3.7.2, 3.7.9 and 5.1.1 are used to justify `2026-10-08T15:30:00+08:00` as a conservative upper bound on public availability of the prior session's close. It is an upper bound for PIT ordering, not a claimed exact historical endpoint publication time.
- The source-vintage receipt binds the previous event-time value, price evidence ID, original raw-byte SHA-256, policy/rule identity and strict cutoff comparison. It validates the exact stored raw price file again and re-runs the unchanged Core/PIT validator.
- The original private candidate (fingerprint and manifest hash already recorded above) is never modified. Migration writes a new immutable content-addressed successor, validates it before atomic promotion, and retains the original for comparison/rollback. Re-running the migration is idempotent.
- Exact endpoint first-public timestamp remains unknown by design: `exact_first_public_timestamp_verified=false`. The official rule page bytes were not materialized/hashes in this run; the policy records `raw_rule_bytes_materialized=false` and `raw_rule_bytes_sha256=null`.
- Code CI on head `ddce63396904c9ab696ddfe784e8a3b94ab55b82`: private persistence contract **53/53 PASS**; B2 Evidence/PIT **31/31 PASS**; company Evidence/PIT **23/23 PASS**; B2 scope **3/3 PASS**; compile/shell/schema/diff checks pass. These are code tests, not a statement that the operator's private successor migration has executed.
- At the time this section was first written, the local successor migration had not yet been reported; **superseded by Section 9 below**. The operator subsequently ran the offline mode after PR #329 merged, with Core/PIT PASS. No further C1 migration is required.
- The new bound clears this specific cutoff-ordering issue only. It does not create formal signed admission, Production Host acceptance, a bundle, or a Decision and does not establish an exact endpoint first-public timestamp.

## 9. Operator confirmation — C1 successor migration PASS — 2026-10-11

The operator subsequently ran the merged launcher's offline source-vintage mode. Reported result:

- Status: `SOURCE_VINTAGE_ADJUDICATED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED`.
- Successor fingerprint: `9a4a1f2e22c982e12f09fc7858eba2ee06768cac59659734ab35ea450579bd3c`.
- Manifest SHA-256: `90b1b4b77b28a0e8df36fb7737c7ade5a7ede85948246bcde0439cfc7bd1f72a`.
- Source-vintage adjudication SHA-256: `e06240acec667926aaa453a7558f76d9f1763488fe5630f5916b180157c75535`.
- Evidence records: 11; manifest raw-artifact declarations: 11; unique physical raw files: 8; Core validator: PASS.
- `source_vintage_status=BOUNDED_PUBLIC_AVAILABILITY_ACCEPTED_FOR_PIT`; `source_vintage_review_required=false`; `public_availability_upper_bound=2026-10-08T15:30:00+08:00`.
- `exact_first_public_timestamp_verified=false`; `official_source_refetched=false`; `attempt10_downloaded=false`; `previous_candidate_retained=true`.
- Signed admission, production Host acceptance, bundle and Decision remain false; Human Approval remains required; auto execution remains false.

This closes C1's local source-vintage successor migration. The limit remains explicit: the upper bound is rule-derived, not exact endpoint upload telemetry; the rule page bytes were not materialized/hashed in this run. No follow-up C1 ingest or price-source request is required.

## 10. C2 / 新和成 next boundary — preserved Run #8 re-audit

The Run #8 archive SHA-256 `0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1` independently matches the preserved archive, and all 8 captured raw objects match the intake receipt's sizes/SHA-256 values. This is a raw-integrity PASS only.

The Run #8 B2 manifest uses `cutoff_date=2026-10-09T23:59:59+08:00`, inconsistent with the canonical date-only cutoff rule (start of 2026-10-09). Its old preflight remains diagnostic; do not patch the cutoff in place or re-use the old manifest digest/fingerprint. The 2026-10-09 buyback-progress notice and any same-day close stay excluded unless pre-cutoff availability is independently proven. See `docs/iios/ROUTE_A_C2_SOURCE_ADJUDICATION_AUDIT_20261011.md`.

Next step is C2 fact-level source adjudication under unchanged Core/PIT and conservative source-reuse conditions. C1 storage/source-vintage work is closed; production Host acceptance remains a separate gate.