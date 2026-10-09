# IIOS Public Web Discovery — Free-First / No LLM Provider v0.1

Status: **IMPLEMENTATION CANDIDATE until exact-head CI passes; discovery records are never evidence admission**

## Why this exists

The company-level Investment Core MVP must not require a commercial LLM endpoint/API key or a paid web-search API in order to find public sources. B2-D external LLM live invocation is a separate optional integration track. Source discovery and source evidence are different capabilities.

This adapter uses the open-source `ddgs` metasearch library to query publicly accessible web-search engines without a configured LLM provider endpoint or provider API key. It is best-effort only: public search engines can rate-limit/block automated traffic or change their behavior, and results are not guaranteed or authoritative. If it fails, the user can use ChatGPT/web-browser search or provide official URLs; the source capture/B2 path does not wait for an LLM provider.

## Run locally

```bash
python -m pip install ddgs
python tools/public_web_discovery.py \
  --query 'site:disc.static.szse.cn 002001 新和成 2026 半年度报告' \
  --region cn-zh \
  --backend auto \
  --max-results 10 \
  --out ./iios-evidence-runs/public-discovery.json
```

The tool emits a hash-bound discovery receipt containing the query, search region/backend, timestamp, candidate URLs, titles/snippets, rejected candidate count and result-record SHA-256. It rejects unsafe URL schemes, credential-bearing URLs, localhost and non-public IP literals. Use one new output path per run; existing output files are not overwritten.

## GitHub Actions

The manual-only workflow `.github/workflows/iios_public_web_discovery.yml` accepts a query, region and result limit. It needs no repository secrets, has read-only contents permissions, and uploads the candidate receipt for 14 days. It doesn't fetch source URLs. Search failures produce a diagnostic receipt when possible and keep the workflow failed instead of pretending discovery succeeded.

## Trust and evidence boundary

- Search result title/snippet/date/rank are **untrusted discovery hints**, not source evidence.
- Public search can locate a primary official source, but the original source URL and exact response bytes must still be captured through Route A.
- Search results never auto-write a company manifest or auto-admit facts.
- Route A still hashes exact bytes; existing B2 evidence contracts still decide `known_at`, PIT, source authority, field semantics and admission status.
- If `known_at` is missing or cannot be independently established, it remains UNKNOWN. A reported search publication date is not enough.
- The no-key adapter is not a promise of uninterrupted search availability. It is an additional discovery route, not a single provider dependency.

## Scope

User-selected single company only. No CSI800, no cross-company screening, no paid data dependence, no automatic investment decision and no execution authority.
