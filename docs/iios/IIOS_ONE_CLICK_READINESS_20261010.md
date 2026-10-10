# IIOS one-click readiness — 2026-10-10

## How to use it

Open the GitHub Actions workflow **IIOS — One-click case readiness (read-only)**, read the authorization description, tick the checkbox, and click **Run workflow**. When it finishes, read the job summary. The JSON and Chinese-readable Markdown are also attached as a downloadable artifact.

This replaces the previous confusing file-picker request. You do not need to find a local request-bundle file or admission-root directory to obtain a diagnostic report.

## Scope and safety

This is deliberately a read-only preflight. It checks the canonical repo, searches for a full-shape request bundle while excluding examples/tests/templates, inspects the committed B2 record, and checks for a formally provisioned admission root visible to the runner. It does not read local Mac folders, create admissions, call ChatGPT, run canonical-run, issue a Decision, publish a formal report/Run Receipt, or authorize trades.

A green GitHub Actions status means the diagnostic report was generated. It does not mean the case passed its gates. The report's own status is authoritative.

As of the committed 605016 B2 ledger, market_price remains UNKNOWN/unadmitted, evidence_admission=false and pit_admission=false. The hosted runner cannot see your Mac's local store. Do not upload private admission records to GitHub or create placeholders to make the preflight green.

## What remains before a true investment run

1. Admit a cutoff-correct and permitted market-price source under the unchanged B2/PIT contract.
2. Stage a real canonical request bundle against the actual admitted evidence manifest and raw evidence bytes.
3. Provision the durable case-matching admission store in the intended execution host.
4. Complete the free ChatGPT web handoff manually for the two supported LLM callbacks; keep provider_origin_verified=false.
5. Run the formal canonical entry, verify all output/receipt lineage, and obtain independent review. The one-click preflight does none of these steps.
