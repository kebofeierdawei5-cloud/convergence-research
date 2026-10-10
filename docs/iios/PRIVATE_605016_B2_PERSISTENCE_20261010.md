# 605016 — Local Private B2/PIT Persistence — 2026-10-10

**Scope:** persist the real official-HTTPS B2 candidate and exact raw bytes in a user-controlled local private data root.  
**Status:** implementation candidate; exact-head contract tests required; no private host can be reached from GitHub-hosted CI.

## One-launcher operation

On macOS, download the file **tools/Launch_IIOS_Private_605016_B2_Ingest.command** from canonical main and open it in Terminal. The launcher:

1. checks for git, Python 3.12+, GitHub CLI (gh) and an authenticated GitHub CLI session;
2. obtains canonical main source into a temporary working directory;
3. downloads the genuine Attempt 10 artifact (run 38026139364, artifact iios-company-evidence-38026139364) into a temporary directory;
4. re-runs the established official HTTPS dividend/price adjudicator and then the Investment Core-owned Evidence/PIT validator;
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

## Verification

tests/test_iios_private_605016_b2_ingest_v01.py covers exact referenced-byte persistence, private permissions, idempotence, core-validator fail-closed behavior, repository-root rejection, path traversal and official price-hash mismatch. The dedicated workflow is contract-only; it does not access the user's private machine or run the real intake.
