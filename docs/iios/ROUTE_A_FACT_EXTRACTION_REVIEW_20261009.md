# Route A Fact Extraction Review — 新和成 002001.SZ

**Date:** 2026-10-09  
**Record class:** diagnostic / page-located candidate facts; **not B2 Evidence/PIT admission**  
**Case:** `RC-CN-A-002001-20261009`  
**Cutoff:** `2026-10-09`  
**Source:** Route A Run #8 / GitHub Actions run `37938129274`  
**Raw artifact ZIP SHA-256:** `0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1`  
**Intake manifest SHA-256:** `c6ec425f3c2ef5404bbdd1868e57434c64da90e255bcde5eae24586dba1227e3`

## Result

- Reverified all **8/8** captured raw objects against the intake receipt’s exact byte count and SHA-256. The fact extractor independently repeats this check for each PDF it cites, then confirms its exact search terms appear on the stated PDF physical page after whitespace-only normalization.
- Extracted **11 page-located fact candidates** from three retained official-exchange PDF objects.
- Every emitted fact remains `known_at = null`, `provenance_class = UNKNOWN`, `status = UNKNOWN`, `admission_status = NOT_ADMITTED`.
- B2 remains `BLOCKED_NOT_ADMITTED`; admitted field groups remain empty. Page-level PDF text match plus raw-byte integrity does not prove official source origin, first-public time, license/reuse rights, or field-level PIT admission.
- No PDF/raw-source bytes are committed to Git. The new tool accepts the externally retained Route A run directory and emits a local JSON review record.

## Source objects cited

| Source object | Size | SHA-256 | Candidate publication date |
|---|---:|---|---|
| `raw/SZSE-2026-H1-SUMMARY.pdf` | 144,809 bytes | `bbd0f336ee1fd4bb5ec606d20939b06a245b7c79ac4facdad602233507db25c3` | 2026-08-20; candidate only |
| `raw/SZSE-2026-H1-FULL.pdf` | 980,820 bytes | `ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e` | 2026-08-20; candidate only |
| `raw/SZSE-2026-BUYBACK-PROGRESS-SEP.pdf` | 84,057 bytes | `af6ad44d49b10b0f23306e0812fa64200880b29883bcaa71fecaf6b54a8ac6ed` | 2026-10-09; candidate only |

The corresponding public HTTPS locators are preserved in the Run #8 capture manifest; they are not restated here as verified source-origin assertions.

## Extracted facts — all NOT_ADMITTED

| Fact ID | Group / locator | Text-matched claim candidate |
|---|---|---|
| `XHC-FACT-SECURITY-001` | `security_identity`; H1 summary, physical PDF p.2, “公司简介” | 股票简称新和成、代码 002001、上市交易所深圳证券交易所 |
| `XHC-FACT-FIN-REVENUE-H1-001` | `financial_reality`; H1 summary, p.2, “主要会计数据和财务指标” | H1 revenue RMB 13,129,300,260.89; +18.28% YoY |
| `XHC-FACT-FIN-NET-PROFIT-H1-001` | `financial_reality`; H1 summary, p.2 | H1 attributable net profit RMB 4,010,733,454.55; +11.31% YoY |
| `XHC-FACT-FIN-ADJ-PROFIT-H1-001` | `financial_reality`; H1 summary, p.2 | H1 adjusted attributable net profit RMB 3,918,936,563.72; +6.53% YoY |
| `XHC-FACT-FIN-OCF-H1-001` | `financial_reality`; H1 summary, p.2 | H1 net operating cash flow RMB 3,640,144,282.94; +12.26% YoY |
| `XHC-FACT-BUSINESS-METHIONINE-H1-001` | `business_reality`; H1 full report, physical p.9 / printed p.8, “主营业务分析” | Management text attributes methionine volume-and-price increase to stronger demand and prices |
| `XHC-FACT-BUSINESS-PROJECTS-H1-001` | `business_reality`; H1 full report, physical p.9 / printed p.8 | Management text says Tianjin nylon-chain equipment was arriving for installation; PPS phase IV construction and HA phase II civil works had started |
| `XHC-FACT-FIN-RD-H1-001` | `financial_reality`; H1 full report, physical p.10 / printed p.9 | H1 R&D input RMB 605,728,077.64; +15.88% YoY |
| `XHC-FACT-FIN-SEGMENTS-H1-001` | `financial_reality`; H1 full report, physical p.11 / printed p.10, “营业收入构成 / 分产品” | Nutrition sales RMB 8.806bn (+22.30%); flavors/fragrances RMB 2.022bn (-3.91%); new materials RMB 1.166bn (+12.31%) |
| `XHC-FACT-FIN-ASSETS-H1-001` | `capital_structure`; H1 full report, physical p.12 / printed p.11, “资产构成重大变动情况” | Fixed assets RMB 19.538bn; construction-in-progress RMB 1.007bn; monetary funds RMB 7.458bn |
| `XHC-FACT-TRUST-BUYBACK-PROGRESS-001` | `trust_governance_events`; buyback progress announcement, p.1 | Through 2026-09-30 buyback 7,136,014 shares (0.2322%); amount RMB 199,490,835.70 excluding fees; high/low RMB 29.97/25.24 per share |

## Still blocked

1. **Source-origin and source-vintage:** the URL path / document heading / public listings give candidate publication dates, but an independent adjudication record must prove the source identity and when the exact document first became public. Candidate dates have not been promoted to `known_at`.
2. **License and reuse:** the capture receipt declares `PUBLIC_ACCESS_REUSE_UNKNOWN`; that status remains unchanged.
3. **Market price:** the exact historical-price endpoint failed on Run #8 and produced no bytes/hash. Quote/history pages were captured but have no admitted fact-level date and price. Conflicting public search results must be reconciled; no close has been selected.
4. **B2/PIT:** none of the 11 records can cover a required field group while status/provenance remain UNKNOWN. This record is extraction progress, not permission for company-level valuation or investment decision.

## Reproduction

With the Run #8 ZIP safely extracted into `/path/to/route-a-run8`:

```bash
python tools/route_a_fact_review.py \
  --input-run-dir /path/to/route-a-run8 \
  --out /tmp/ROUTE_A_FACT_EXTRACTION_REVIEW_20261009.json
```

The tool has no network, Provider endpoint, API key or paid search dependency. It refuses source-byte hash/size mismatches and PDF page-text locator mismatches; it never writes ADMITTED/PASS evidence records.
