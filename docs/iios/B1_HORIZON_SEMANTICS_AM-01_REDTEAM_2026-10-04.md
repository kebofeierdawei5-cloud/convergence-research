# IIOS B1 Horizon Semantics Amendment AM-01 Red-Team

Date: 2026-10-04
Status: REVIEW TARGET — PENDING CI

## Primary finding

The previous B1 runtime only enforced 1 <= H <= 3. It did not enforce the new policy that H=1 is the default and H=3 requires an explicit exception.

Therefore a caller could supply H=3 without recording why the 3Y horizon was selected. That is a framework-level semantic bypass.

## Required attacks

1. H=1 with override=false and empty basis must PASS.
2. H=3 with override=true and a qualifying basis must PASS.
3. H=3 with override=false must BLOCK.
4. H=3 with override=true and unsupported basis must BLOCK.
5. H=2 with override=true must BLOCK.
6. Missing horizon metadata must not be silently defaulted by the validator.
7. CORE-03 must not silently default its forecast horizon to 3.
8. CATL 2027–2029 must carry an explicit 3Y override and rationale.
9. Entry Return Cushion must remain non-annualized.
10. A DCF explicit forecast length must not be interpreted as Decision H.

## Expected result

The shared horizon validator, schema and cross-module tests must enforce one identical rule:
1Y default, 3Y explicit exception, 1–3Y actual holding cycle.
