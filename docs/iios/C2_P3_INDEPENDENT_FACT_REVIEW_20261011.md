# C2-P3 — Separate-method fact/PIT review

Date: 2026-10-11  
Case: RC-CN-A-002001-20261009  
Review class: **independent local method review; not external third-party sign-off**

## Method

This review has a separately authored 13-item matrix and directly extracts physical PDF pages from the immutable Run #8 ZIP using pypdf. It does not import the candidate builder's FACT_SPECS, call route_a_c2_adjudicate.py, or accept the previous 13/13 result as input. The archive SHA-256 is pinned to 0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1.

The review records only fact ID, PDF member/page, raw PDF hash, locator status, official HTTPS source binding, URL date vs intake publication-date match and conservative known_at upper bound. It excludes all value-bearing market-price artifacts and does not re-search the market price.

## Findings

- 13/13 page-term locator checks pass against the original PDF bytes.
- The three reviewed PDF members' SHA-256 hashes match the immutable Run #8 archive content.
- The claimed publication date matches the date in the official SZSE PDF URL path for each cited source.
- The conservative upper bound published-date 23:59:59 +08:00 is before the case cutoff 2026-10-09T00:00:00+08:00 for all 13 fact records.
- The 2026-10-09 buyback-progress notice is excluded because its end-of-publication-day bound is later than the date-only midnight cutoff.
- All intake entries declare PUBLIC_ACCESS_REUSE_UNKNOWN; no source declares permission for retained reuse. **This remains a blocking formal-admission issue.**

## Boundary

This is a fresh, separate-method local review, not an external reviewer or legal opinion. A truly separate reviewer still must resolve the official-filing claims and permitted private fact-level use/retention boundary. Factual and PIT checks do not promote the evidence to formal signed admission. No formal admission, production Host acceptance, Decision, Publication, complete IIOS_RUN_RECEIPT or execution authority is created.
