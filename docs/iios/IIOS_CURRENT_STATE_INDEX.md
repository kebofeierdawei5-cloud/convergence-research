# IIOS Current-State Index

Snapshot: 2026-10-03

## Current canonical engineering state

```
R0 Governance = PASS
        ↓
Canonical Git root established
        ↓
FM-00 exact Git baseline = 536e883...
        ↓
FM-01 exact implementation baseline = d5b2fb3...
        ↓
Canonical root + CI carrier = 1285506...
        ↓
FM-00 GitHub Actions = PASS
        ↓
M1.2-DATA-00 / A02 = BLOCKED_PENDING_EXACT_RAW_DATA
```

## Exact canonical refs

- `main` = `1285506b47fa89802c6e85a1bd066b54f088e3b0`
- `m1.2-fm00-v0.1.0` = `aac0cccf596ee2703caedffc08f434be9e2dffed`
- `m1.2-fm01-foundation-v0.1.0` = `36c8da2070e91be41c0574e6c9db54947080d478`

## CI closure

- Workflow: `IIOS FM00 Baseline`
- Workflow run: `37124212188`
- Head commit: `1285506b47fa89802c6e85a1bd066b54f088e3b0`
- Event: `push`
- Conclusion: `success`
- Job: `verify-fm00`
- Job ID: `111206141430`
- FM00 unit tests: 8/8 PASS
- FM00 validator: PASS, findings=[]
- compileall: PASS
- git diff --check: PASS

## Research boundary

FM00 remains exploratory and contaminated by prior exposed results. It does not establish forecast model validity or production-router eligibility.

FM01 code-contract implementation is complete, while CATL population remains blocked until its exact M1.1 source snapshot is materialized and admitted under PIT controls.

Model selection remains unauthorized until the required data and evaluation gates are satisfied.

## Next gate

Proceed to M1.2-DATA-00 / A02 exact raw-data admission. Do not infer or fabricate missing PIT source bytes.

## Authority precedence

1. Frozen governance artifacts and accepted evidence chains.
2. Canonical repository artifacts and exact Git history.
3. Independent execution/verification receipts.
4. Chat context only.
