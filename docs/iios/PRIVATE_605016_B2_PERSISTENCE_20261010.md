# 605016 — Local Private B2/PIT Persistence — 2026-10-10

**Scope:** persist the real official-HTTPS B2 candidate and exact raw bytes in a user-controlled local private data root.  
**Status:** operator-reported local private persistence PASS on 2026-10-11; a read-only offline replay after atomic promotion is the remaining storage-integrity confirmation. GitHub-hosted CI cannot inspect the user's private filesystem.

## One-launcher operation

On macOS, download the file **tools/Launch_IIOS_Private_605016_B2_Ingest.command** from canonical main and open it in Terminal. The launcher:

1. checks for git, Python 3.12+, GitHub CLI (gh) and an authenticated GitHub CLI session;
2. obtains canonical main source into a temporary working directory;
3. downloads the genuine Attempt 10 artifact (run 38026139364, artifact iios-company-evidence-38026139364) into a temporary directory;
4. re-runs the established official HTTPS dividend/price adjudicator and then the Investment Core-owned Evidence/PIT validator. If the SSE bulletin-listing API is blocked by the local network, it reuses the already adjudicated canonical listing/fact record, directly re-fetches the fixed official Big5 PDF URL over HTTPS, and requires the exact previously recorded PDF size/SHA-256 before continuing; the receipt explicitly says the original listing bytes were not re-fetched in that run;
5. if both validators pass, atomically persists the manifest and only the raw files referenced by that manifest under:
   ~/Library/Application Support/IIOS/private-data/cases/RC-CN-A-605016-20261009/<candidate-fingerprint>/
6. removes the temporary clone, raw download and full temporary adjudication workspace.

No market data, manifest containing numeric quote values, private receipt, request bundle, or local filesystem contents are uploaded or committed by this launcher. Source acquisition is free-first and does not use a paid market-data API, LLM provider endpoint or provider API key. The GitHub CLI login is used only to download the genuine source artifact.

If gh is absent, install GitHub CLI and run gh auth login once. The program does not ask for a provider API key. A failed authentication, missing artifact, byte mismatch, validator error or unsafe filesystem path fails closed and must not produce a passing persistence receipt.

## Persistent layout

- company_evidence_manifest.json: exact B2 candidate manifest including its audit digest.
- evidence_root/raw/...: only raw files referenced by the manifest's raw_artifacts list; each file is size/hash checked before and after copying.
- PRIVATE_B2_PERSISTENCE_RECEIPT.json: a content-hashed local receipt with status, manifest hash, source-byte hash, verification status and explicit non-claims. It contains no numeric quote value.

The private root is created with restrictive directory permissions; raw files and JSON files are mode 0600, directories are mode 0700, and writes are immutable/content-addressed. Re-running the same evidence candidate re-verifies it and returns the existing candidate rather than overwriting it. The tool refuses to write anywhere inside the public Git repository.

A single original raw source file may support multiple distinct evidence records, so the manifest may contain multiple declarations with the same relative path. The ingester verifies every declaration independently, permits a shared path only when all declarations agree on expected size and SHA-256, and writes that path once. Conflicting size/hash contracts for the same path fail closed before the private staging destination is created. The offline verifier applies the same rule and separately validates every declaration through the unchanged Core/PIT validator.

## Acceptance boundary

A successful local run means:

- the official HTTPS source response and its exact byte hash passed the existing adjudicator;
- the unchanged research B2/PIT manifest builder returned PASS;
- the Investment Core-owned iios_mvp.canonical_evidence_admission_v01.validate_company_evidence_manifest validator independently passed against the persisted bytes;
- the persisted manifest and raw files are private, durable and hash-bound.

It does not mean that:

- a cryptographically signed admission record was created (no trusted signing authority is configured for this path);
- the official endpoint exposed an exact historical first-public timestamp (the known-at basis remains the market-session closing event time and this limitation is explicitly recorded);
- a production Host/runtime has been deployed or accepted;
- a canonical request bundle exists;
- a semantic/Forecast/Valuation/Decision/Publication/Run Receipt was created; or
- any trade is authorized.

The tool therefore reports PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED and retains source_vintage_review_required=true. A formal production run must wait for the independent source-vintage adjudication and real Host acceptance. No empty admission root or placeholder request bundle is created.

## Offline persisted-copy verification after restart

After an ingest invocation returns `PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED` or `ALREADY_PERSISTED_CORE_VALIDATED_NOT_PRODUCTION_ACCEPTED`, the private candidate is kept under the local private root. To verify that stored copy again after quitting Terminal or restarting the Mac, run the same launcher from Terminal with `--verify-existing`:

```bash
bash /path/to/Launch_IIOS_Private_605016_B2_Ingest.command --verify-existing
```

This mode does not download the Attempt 10 artifact and does not request the official source endpoints. It obtains the verifier code from public canonical `main`, then locally checks the stored case/cutoff, candidate fingerprint, receipt semantics/hash, restrictive filesystem modes, exact manifest-listed raw-file set, exact raw bytes and the unchanged Investment Core Evidence/PIT validator. It reports only hashes, counts and statuses; it does not print company facts or numeric quote values.

Expected successful status: `VERIFIED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED`.

Missing files, loose permissions, symlinks, unlisted files, altered bytes, altered receipt claims, or a failed Core/PIT validator must remain `BLOCKED`. This mode is a durable-copy integrity/replay check, not a fresh source-origin check, formal signed admission, production Host acceptance, or a Decision.

## Verification

tests/test_iios_private_605016_b2_ingest_v01.py covers exact referenced-byte persistence, private permissions, idempotence, core-validator fail-closed behavior, repository-root rejection, path traversal, official price-hash mismatch, source-free post-persistence replay, modified bytes/receipt, unlisted files and loose permissions. The workflow compiles the Python code, validates launcher shell syntax, and runs contract tests; it does not access the user's private machine or run the real intake.


## Attempt 10 artifact download recovery — 2026-10-11

An actual operator run returned `BLOCKED / ATTEMPT10_ARTIFACT_DOWNLOAD_FAILED_CHECK_GITHUB_ACTIONS_ACCESS` before any private write. Follow-up metadata inspection confirmed that workflow run `38026139364` completed successfully and artifact `11660285551` (`iios-company-evidence-38026139364`) existed, was not expired at inspection time, and had the pinned ZIP digest `19916fee166b45a04430e4d2bb3131be2f0beab3140df4820793099d7d413f5c` and size 8,526,921 bytes. This points to the old local `gh run download` transport/access path, not evidence adjudication failure. It does not prove the operator's local token scopes or network are valid.

The follow-up downloader uses the official GitHub Actions artifact ZIP endpoint for the pinned artifact ID. It obtains a short-lived redirect without following it, then fetches the HTTPS redirect without forwarding the GitHub bearer token to the redirect host. Before extracting anything, it requires the exact artifact ZIP byte count and SHA-256. Extraction rejects ZIP-slip paths, symlinks/special files, duplicate paths, excess files and oversized expansion; extracted files use private modes. Failures now differentiate unavailable/expired artifacts, token/action-read access denial, API transport, digest mismatch and unsafe archive structure. No raw evidence is committed by this recovery change.

## Network-failure recovery added after operator report

A network `BLOCKED` result from the SSE query API no longer creates an uncaught traceback or immediately abandons the run. The adjudicator may use the canonical `DIVIDEND_IMPLEMENTATION_ADJUDICATION_20261010.json` for the previously reviewed listing identity, but it must directly retrieve the official PDF again over HTTPS and match the pinned 146,499-byte SHA-256 before proceeding. It does not represent the historical listing body as re-downloaded: `listing_bytes_reverified_in_current_run=false` is included in the report. If direct PDF retrieval, TLS origin, hash or PDF structure validation fails, the run remains `BLOCKED` and no private persistent candidate is written. The local command now emits a sanitized `BLOCKED` JSON reason instead of exposing a traceback.
