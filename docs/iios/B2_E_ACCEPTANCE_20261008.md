# B2-E — Natural-Language → Semantic → Decision E2E Acceptance

Date: 2026-10-08

Status: **PASS / MERGED / CANONICAL**

## Canonical promotion

- canonical base: `999bf17080f0ac73736d8a44d98a7202c1dad147`
- PR: #223
- merge commit: `bb297c212f3deb153549cab013000904ebd982dd`

## Closed boundary

B2-E establishes the canonical control-plane path:

```
Natural Language
  ↓
B2-B Request Admission
  ↓
Research Case identity
  ↓
Evidence Admission
  ↓
B2-A Semantic Admission
  ↓
Forecast / Valuation stages
  ↓
Decision Admission
  ↓
AI_PROPOSED Decision Revision
```

The semantic producer remains non-authoritative. B2-E explicitly rejects semantic output that attempts to write Decision-authoritative fields.

The final Decision is freshly re-executed by the canonical Investment Core v0.3 Decision Kernel and then admitted by the existing Decision Admission contract.

The lifecycle artifact remains:

- `decision_status = AI_PROPOSED`
- `human_approval_required = true`
- `auto_execution = false`

## Evidence and lineage

The E2E binding receipt records:

- raw natural-language request SHA-256;
- B2-B Research Case hash;
- expanded Investment Core case hash;
- semantic artifact hash;
- semantic admission hash;
- Decision Admission hash;
- Decision Revision hash.

Research Case and expanded Investment Core case are intentionally bound by exact identity fields rather than by structural hash equality because they are different contract layers.

## Verification

- dedicated B2-E workflow #3: **SUCCESS**
- B2-E E2E tests: **3 / 3 PASS**
- independent B2-E red-team: **4 / 4 PASS**
- B2 Semantic Producer workflow #27: **SUCCESS**
- Investment Core CI #999: **SUCCESS**
- MVP Pilot #137: **SUCCESS**
- Post-B04 independent red-team #126: **SUCCESS**
- B2 Data Evidence PIT #94: **SUCCESS**

## Evidence classification

This is a **control-plane / authority-conformance PASS**.

The conformance run uses fixture request interpretation, fixture semantic production and the existing canonical 300750 case/resolvers. It does not prove live production LLM reasoning or economic validity.

## Production gate

B2-D3 remains independently gated:

```
B2-D3 real provider runtime
        ↓
LIVE_RESPONSE_CAPTURED
        ↓
B2-D1 INDEPENDENT_VERIFIED
        ↓
production semantic producer
        ↓
B2-E production-backed E2E
```

Until that gate is satisfied, B2-E must not be labeled as production-Live or used as proof of provider/model quality.

## Non-claims

- no semantic producer Decision authority;
- no Human Approval;
- no automatic execution;
- no change to Investment Core economics;
- no claim of LLM model quality;
- no claim of forecast validity.
