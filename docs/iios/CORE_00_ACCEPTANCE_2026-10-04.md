# IIOS CORE-00 Acceptance — 2026-10-04

Status: PASS — branch acceptance; pending merge to canonical main
Branch: `core-00-scope-reconciliation-2026-10-04`
PR: #25
Base main: `f911b1a9673ec266780834e53f19858841ced1fa`

## Scope

CORE-00 establishes the Investment Core / Research Track boundary without changing P3/P4 algorithms or frozen B2 v0.1 semantics.

## Acceptance matrix

| Gate | Required condition | Status |
|---|---|---|
| Scope contract | CORE-00 scope reconciliation document present | PASS |
| Core source isolation | `iios_mvp/` has no `research.*` import dependency | PASS |
| Core CI isolation | Investment Core workflow has no A02 / CSI800 / CSI Industry research dependency | PASS |
| PIT retention | Historical single-company case still requires defensible `known_at` semantics | PASS |
| MIE role | B1 v0.3 non-mandatory MIE boundary retained | PASS |
| Frozen B2 preservation | B2 v0.1 semantic artifacts unchanged by this branch | PASS |
| State reconciliation | Status/index point to CORE-00 as current gate | PASS |

## Explicit non-claims

CORE-00 does not claim that A02 is complete, that historical single-company PIT is universally recoverable, or that Investment Core is production-capable.

## Evidence

- CORE-00 Scope CI: run `37208107654` — SUCCESS.
- Investment Core CI: run `37208107544` — SUCCESS.
- The same head `0fa6da1874befc09b3699dd91d5f915e2235075f` also passed the Research Track FM00/B2 workflows triggered by changed research-control files; these are not Investment Core acceptance gates.
- Compare against pre-CORE-00 main confirms no modification to the frozen B2 Evidence Contract or PIT Temporal Semantics files.
- CORE-00 additionally removed the broad `docs/iios/**` / `manifests/iios/**` FM00 trigger, preventing routine core documentation changes from scheduling FM00.

## Exit

CORE-00 is **PASS for the branch implementation**. Merge to canonical `main` remains the only outstanding integration step. No CORE-01 implementation should begin from an unmerged main state unless the owner deliberately chooses branch continuation.
