# IIOS B2 — Source Registry v0.1

Status: FROZEN / FREE-FIRST FOUNDATION
Date: 2026-10-04

## Registry policy

The normative production architecture MUST work with zero paid commercial financial-data subscriptions.
Paid providers may be used only as optional external cross-checks. They cannot be mandatory for acquisition, PIT validation, replay, admission or production execution.
Source agreement is for divergence detection, not majority voting.

## Current registry

| source_ref | provider | primary role | access | authority | PIT capability | production mandatory |
|---|---|---|---|---|---|---|
| CSIINDEX:000906:OFFICIAL_CONSTITUENT_FILE | China Securities Index Co. | CSI800 constituent source / terminal control | FREE_PUBLIC | PRIMARY_OFFICIAL | SOURCE_VINTAGE | No until exact bytes admitted |
| CSIINDEX:OFFICIAL_ADJUSTMENT_NOTICE | China Securities Index Co. | historical index changes | FREE_PUBLIC | PRIMARY_OFFICIAL | EVENT_PUBLICATION | No single source snapshot is sufficient |
| SSE:COMPANY_ANNOUNCEMENT | Shanghai Stock Exchange | issuer disclosure | FREE_PUBLIC | PRIMARY_ISSUER | EVENT_PUBLICATION | Yes for applicable SSE primary evidence |
| SZSE:COMPANY_ANNOUNCEMENT | Shenzhen Stock Exchange | issuer disclosure | FREE_PUBLIC | PRIMARY_ISSUER | EVENT_PUBLICATION | Yes for applicable SZSE primary evidence |
| CNINFO:DISCLOSURE | CNINFO | public disclosure mirror/search | FREE_PUBLIC | SECONDARY_VALIDATION | EVENT_PUBLICATION | No |
| TUSHARE:PUBLIC_API | Tushare | structured secondary data / cross-check | FREE_WITH_LIMITS | SECONDARY_VALIDATION | EXPLICIT_PIT_QUERY only when endpoint and archive support it | No |
| JOINQUANT:HISTORICAL_EXPORT | JoinQuant | optional historical cross-check | PAID_OPTIONAL | SECONDARY_VALIDATION | EXPLICIT_PIT_QUERY only when licensed export preserves request/response provenance | No |
| IFIND:HISTORICAL_QUERY | iFinD | optional security-master cross-check | PAID_OPTIONAL | SECONDARY_VALIDATION | EXPLICIT_PIT_QUERY only when evidence envelope is preserved | No |
| QLIB:COLLECTOR_CACHE | Qlib | reconstruction methodology / independent implementation cross-check | FREE_PUBLIC | METHODOLOGY_ONLY | UNKNOWN unless source bytes are preserved | No |
| WESTOCK:CSI800_CURRENT | westock | terminal/current control only | FREE_PUBLIC | SECONDARY_VALIDATION | CURRENT_ONLY | No |

## CSI official control target

The previously identified terminal control target is:

```text
000906cons.xls
expected size: 169984 bytes
expected SHA256:
f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984
```

This is a validation target only. It does not prove that the bytes have been delivered or admitted.

Historical CSI800 membership cannot be established by the terminal snapshot alone. Historical adjustment notices or other admissible historical source-vintage evidence are required for earlier origins.

## Source role rules

### CSI official
Official CSI source material is the normative authority for index identity and index membership evidence. A declared filename, size or hash is not evidence of delivered bytes.

### Exchange / issuer disclosure
SSE and SZSE public disclosure are preferred for issuer facts and publication timing. CNINFO is a public mirror/search layer; a mirror does not automatically outrank originating evidence.

### Structured public APIs
Tushare and similar APIs may reduce acquisition cost and enable structured cross-checking. Endpoint permissions, update policy and historical-vintage semantics must be demonstrated separately. A historical in_date/out_date interval is not by itself proof of known_at.

### Paid providers
JoinQuant, iFinD and other commercial providers may accelerate validation but cannot become hidden production dependencies.

## Forbidden source practices

- current-only source substituted for historical PIT;
- declared SHA treated as local byte verification;
- retrieved_at substituted for known_at;
- vendor effective dates treated as publication timestamps;
- majority vote used to resolve conflicts;
- unknown licensing silently treated as distributable;
- a paid credential treated as mandatory.

## Admission principle

Source Registry qualification does not admit any individual artifact. Artifact admission remains evidence-record + exact-byte + temporal + provenance dependent.