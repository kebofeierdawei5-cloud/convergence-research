# Route A — Free-First Company Evidence Intake v0.1

Status: **PASS / CANONICAL for raw-intake infrastructure; evidence admission remains separate**

## Task contract

- **Objective:** collect exact public HTTPS source bytes or operator-supplied original files for one user-selected A-share/HK company case without requiring any paid data service or LLM provider credential.
- **User value:** one repeatable input boundary for source downloads and manually supplied PDFs/CSV/XLSX/HTML or other original artifacts, including SHA-256, source identity, retrieval time, declared publication/known-at basis and PIT/UNKNOWN evaluation.
- **Product surface:** `tools/company_evidence_intake.py`, `tools/verify_company_evidence_intake.py`, `schemas/company_evidence_intake_manifest_v0.1.schema.json`, and `manifests/company_evidence_intake_template_v0.1.json`.
- **Acceptance:** raw bytes are retained outside Git; the collector emits a manifest-bound receipt; a separate verifier recomputes hashes and rejects tampering/path traversal/forged admission; missing or future `known_at` never becomes PASS; no API key or paid data source is required.
- **Out of scope:** automated broad-market screening, CSI800/CSI Industry, paid vendor integration, automatic semantic reasoning, evidence admission, forecast/valuation decisions, LLM provider calls or order execution.

## Use it

Copy the manifest template and replace the sample case identity, source and local path. The `case_id` must exactly match the IIOS research case identity for `market + symbol + cutoff_date`.

For manually supplied original files, keep those files under an input directory and use relative `local_path` values:

```bash
python tools/company_evidence_intake.py \
  --manifest ./my-case-manifest.json \
  --input-root ./incoming-originals \
  --out ./iios-evidence-runs/RC-CN-A-300750-20261009
python tools/verify_company_evidence_intake.py \
  --root ./iios-evidence-runs/RC-CN-A-300750-20261009
```

For a public official source, replace `local_path` with a publicly accessible `https://` `url`. URLs with embedded credentials/signed-token query parameters are rejected. HTTPS redirects are allowed only if they remain HTTPS. Each object is capped at 50 MiB; use a new, empty output directory for every run. The intake refuses to overwrite prior artifacts.

For checked-in case manifests under `manifests/company_cases/`, `.github/workflows/iios_company_evidence_capture.yml` can download public HTTPS sources and upload raw files, receipt and independent verification as a 14-day artifact. It requires no secrets and never fetches sources on pull-request events. Manual capture of operator-supplied local files remains a local CLI operation using `--input-root`.

The `raw/` directory retains exact bytes. The receipt retains the exact intake manifest copy and SHA-256 for each byte object. Never put API keys, private URLs, raw company documents, or generated evidence runs into Git. Run data locally or in a controlled evidence store.

## Trust and PIT contract

- A raw SHA-256 proves byte identity against the captured artifact, **not** source authenticity or content truth.
- `source_class` is a declared claim. `source_registry_status` shows whether the `source_ref` exists in the current source registry; neither field independently authenticates the issuer.
- `retrieved_at` is acquisition time and never substitutes for `known_at`.
- If `known_at` or `known_at_basis` is absent, the source PIT status remains `UNKNOWN`.
- If `known_at` is after the requested cutoff, the source is `BLOCKED_KNOWN_AFTER_CUTOFF`.
- Even when the declared basis puts `known_at` before the cutoff, the result is only `PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW`.
- Every source record and the whole run retain `admission_status = NOT_ADMITTED`. The separate verifier outputs `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION`; it does not certify publication dates, licenses, issuer authenticity or evidence admission.
- Seven field groups are reported as capture coverage only. A non-empty group does not mean its evidence is sufficient for a company decision.

## CI boundary

The dedicated contract workflow validates schemas and runs deterministic tests/red-team attacks without network fetches. The separate capture workflow is manual-only or triggered by an explicit push to a dedicated `route-a-capture/**` branch with a capture-request file; it captures only public HTTPS sources, needs no secrets, and uploads a short-retention artifact. Capture plus independent byte integrity verification still does not admit evidence or certify source authenticity, PIT eligibility or completeness.
