# IIOS B2-A Scope Repair — 2026-10-05

Status: CANDIDATE FOR ACCEPTANCE

## Finding

B2 had accidentally reintroduced A02/CSI800 into its implementation surface:

- A02 admission code was under `research/b2/`.
- B2 CI executed an A02 fail-closed check.
- Canonical state documents mixed the B2 single-company path with historical CORE-03/A02 context.

This violated the established CORE-00 rule that A02/CSI800 is Research Track only and is not an Investment Core dependency.

## Repair

- Moved A02 admission validator to `research/a02/`.
- Removed A02 admission artifacts from `research/b2/`.
- Removed A02 execution from `.github/workflows/iios_b2.yml`.
- Added automated B2 namespace/workflow isolation tests.
- Updated B2 acceptance matrix and B2-A documentation to make the separation explicit.
- Marked older CORE-02/CORE-03 sections in STATUS as historical references rather than current execution state.
- Current next step is CATL existing-evidence migration/admission; no new universe or historical-market platform is required.

## Acceptance invariant

A future B2 change fails CI if it reintroduces A02, CSI800, CSI Industry, A02 universe IDs, or A02 execution into the B2 namespace/workflow.

A02 remains independently runnable under Research Track paths.
