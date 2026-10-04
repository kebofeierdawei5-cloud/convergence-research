# IIOS CORE-01 Acceptance — 2026-10-04

Status: PASS — branch acceptance; pending canonical merge

| Gate | Required condition | Status |
|---|---|---|
| Minimal-input construction | 300750 + as-of + position creates deterministic case | PASS |
| Identity honesty | Company identity remains unresolved until primary evidence exists | PASS |
| PIT | known_at <= cutoff embedded and validated | PASS |
| Historical protection | Current-state substitution forbidden | PASS |
| Position | Current position normalized and bounded [0,100] | PASS |
| Evidence plan | Company-specific P0/P1 evidence plan generated | PASS |
| Free-first | No paid/commercial source mandatory | PASS |
| Auditability | Deterministic case ID + input/plan SHA-256 | PASS |
| Schema | JSON Schema validates generated case | PASS |
| CLI | One command produces the case envelope | PASS |

## Non-claims

CORE-01 does not claim automatic live-web evidence retrieval or production decision readiness.

## Evidence

- CORE-01 CI run 37208574586 — SUCCESS.
- Investment Core CI run 37208574616 — SUCCESS.
- CORE-00 isolation regression run 37208574588 — SUCCESS.
- CORE-01 tests: 9 passed.
- CLI generation completed for 300750 / 2026-10-04 / position 0.
- Generated envelope remains EVIDENCE_PENDING and decision_ready=false, with no fabricated company or price fields.
- No A02 / CSI800 / CSI Industry dependency is introduced.

## Exit

CORE-01 is **PASS for the branch implementation**. The branch is ready for merge to canonical main.
