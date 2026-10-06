# B00 Acceptance — Post-C8 Baseline Recovery + Authority Threat Reproduction

Date: 2026-10-06

## Status

**B00 = PASS / MERGED / CANONICAL**

Canonical main after B00: `e97d6292678175448b905eded6f221631b81`

B00 was executed as two independent PR tracks:

```
B00-A  Restore Global Investment Core CI GREEN
B00-B  Reproduce Second-Red-Team Attacks
```

## B00-A — Baseline Recovery

B00-A was diagnostic first, then corrective. No Investment Decision semantic rule was changed.

### Root-cause sequence

1. The historical Global Investment Core RED on head `0b44427b18c8a7f9b3dd773d967a7cdcb5ef4c3b` was reproduced from the then-current canonical code.
2. Four pytest failures were traced to stale 300750 Risk fixtures missing the current Risk/Portfolio contract fields `thesis_breaks` and `evidence_ids`.
3. After those fixture repairs, all 407 Investment Core pytest tests passed; the remaining failure was the legacy CLI demo.
4. The demo failure was traced first to missing explicit `market` in the legacy demo case, then to lifecycle `decision.action` extraction of the actual engine Decision wrapper.
5. The lifecycle fix was kept strict: direct `action` is accepted; nested `decision.action` is accepted; scalar legacy `decision` values remain rejected.

### B00-A PRs

- PR #117 — baseline probe only; no semantic change.
- PR #118 — real 300750 Risk fixture contract alignment.
- PR #119 — legacy demo explicit market identity.
- PR #120 — lifecycle engine-wrapper compatibility fix.
- PR #121 — lifecycle regression-test fixture correction.

### CI evidence

- Global Investment Core CI run `37487233225` = **SUCCESS** on `cffc71aa9944489c23c7aaffa84d73973a247a46`; the full 407-test Investment Core suite passed.
- DR-02 run `37487233216` = **SUCCESS**.
- C6 run `37487379909` = **SUCCESS**.
- DR-01 run `37487379916` = **SUCCESS**.
- C8 Auth Remediation run `37487379923` = **SUCCESS**.
- C8 re-executed the lifecycle regression suite and C7 full-lifecycle harness successfully, providing cross-check coverage after the lifecycle fix.

The final B00-A state is therefore GREEN without weakening C8 authority boundaries.

## B00-B — Authority Threat Reproduction

B00-B contained no remediation. It was designed to distinguish red-team claims from reproducible production behavior.

Dedicated CI:

- workflow: **IIOS B00-B — Authority Threat Reproduction**
- run `37487757790` = **SUCCESS**
- head: `bdcf468ab85d6d43733e9e3807e0bb88e35c1814`

### Findings

**P0-01 — CONFIRMED**

A v0.3 case with caller-declared `reality_status=PASS`, `value_driver_status=PASS`, `valuation_status=PASS`, and `forecast_status=PASS`, while lacking domain-owned canonical admission references for those states, can pass validation and reach:

```
action = BUY
new_capital_allowed = true
```

This is a real upstream Investment-State authority bypass, not merely a documentation improvement.

**P0-02 — CONFIRMED**

A structurally valid case can supply a Return Gate whose terminal-value path is economically inconsistent with the supplied Forecast and Valuation, while the Return Gate independently passes the 15% annualized hurdle and the decision still reaches:

```
action = BUY
new_capital_allowed = true
```

This confirms a missing hard Forecast → Valuation → Return lineage boundary.

**P0-03 — RECLASSIFIED P1**

C6 can record an execution receipt whose `approved_action` is `HOLD` while the receipt records a positive executed position. The receipt remains explicitly:

```
auto_execution = false
policy_effect = POST_APPROVAL_RECORD_ONLY_NO_DECISION_MUTATION
```

Therefore the reproduction establishes execution-evidence inconsistency, not an internal execution-authority bypass. It should be treated as P1 evidence-integrity hardening unless the execution boundary is later brought inside IIOS.

## B00 Conclusion

The second red-team's strongest two concerns are empirically confirmed:

```
P0-01  caller-declared upstream authority       CONFIRMED
P0-02  Forecast/Valuation/Return lineage gap     CONFIRMED
P0-03  execution scope                           P1 / evidence integrity
```

B00 deliberately does **not** remediate these findings.

## Next Development Boundary

Next work is restricted to closing the confirmed investment-authority gaps:

1. **B02 — Canonical Investment Input / Admission Contract**
   Define domain-owned, provenance-bound admission references for every decision-critical upstream state, without forcing unrelated domains into a single monolithic object.

2. **B03 — Upstream Authority Integration**
   Replace caller-declared decision-critical status authority with canonical resolver-backed admission, fail-closed behavior, and adversarial regression coverage.

B04+ Forecast/Valuation/Return lineage work follows only after B02/B03 contract boundaries are frozen.

No scheduler, alerts, automatic execution, universe expansion, optimizer/Kelly logic, or new valuation/forecast model families are authorized by B00.
