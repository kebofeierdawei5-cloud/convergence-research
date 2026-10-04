# IIOS CORE-00 Acceptance — 2026-10-04

Status: CANDIDATE — pending CI evidence
Branch: `core-00-scope-reconciliation-2026-10-04`
Base main: `f911b1a9673ec266780834e53f19858841ced1fa`

## Scope

CORE-00 establishes the Investment Core / Research Track boundary without changing P3/P4 algorithms or frozen B2 v0.1 semantics.

## Acceptance matrix

| Gate | Required condition | Status |
|---|---|---|
| Scope contract | CORE-00 scope reconciliation document present | PENDING |
| Core source isolation | `iios_mvp/` has no `research.*` import dependency | PENDING |
| Core CI isolation | Investment Core workflow has no A02 / CSI800 / CSI Industry research dependency | PENDING |
| PIT retention | Historical single-company case still requires defensible `known_at` semantics | PENDING |
| MIE role | B1 v0.3 non-mandatory MIE boundary retained | PENDING |
| Frozen B2 preservation | B2 v0.1 artifacts unchanged | PENDING |
| State reconciliation | Status/index point to CORE-00 as current gate | PENDING |

## Explicit non-claims

CORE-00 does not claim that A02 is complete, that historical single-company PIT is universally recoverable, or that Investment Core is production-capable.

## Exit

CORE-00 is PASS only when the automated isolation CI and the existing Investment Core CI are green and the canonical status/index are reconciled.
