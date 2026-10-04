# IIOS CORE-01 Acceptance — 2026-10-04

Status: CANDIDATE — pending CI evidence

| Gate | Required condition | Status |
|---|---|---|
| Minimal-input construction | 300750 + as-of + position creates deterministic case | PENDING |
| Identity honesty | Company identity remains unresolved until primary evidence exists | PENDING |
| PIT | known_at <= cutoff embedded and validated | PENDING |
| Historical protection | Current-state substitution forbidden | PENDING |
| Position | Current position normalized and bounded [0,100] | PENDING |
| Evidence plan | Company-specific P0/P1 evidence plan generated | PENDING |
| Free-first | No paid/commercial source mandatory | PENDING |
| Auditability | Deterministic case ID + input/plan SHA-256 | PENDING |
| Schema | JSON Schema validates generated case | PENDING |
| CLI | One command produces the case envelope | PENDING |

## Non-claims

CORE-01 does not claim automatic live-web evidence retrieval or production decision readiness.

## Exit

CORE-01 PASS requires green CORE-01 CI and Investment Core CI, with no A02/CSI universe dependency introduced.
