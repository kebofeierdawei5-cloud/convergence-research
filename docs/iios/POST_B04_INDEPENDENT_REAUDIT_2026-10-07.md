# Post-B04 Independent Authority Re-audit — 2026-10-07

Status: **PASS / GOVERNANCE-ADJUDICATED**

## Audit target

The audit was required to start from the actual canonical `main`, not from a stale B04-B branch.

At audit initialization:

```
canonical main = 268852d754ab2385d9a96a10309a782978eb25af
```

This is later than the previously recorded governance-sync point `c6c3e02a0c28fcd6331389ca86f76fa416b8ab22`.

The intervening main-line change was PR #131, **Post-B04-B: Authority Regression Hardening**, containing test-only hardening:
- B03-B engine propagation is asserted through a resolver spy;
- B00-B P0-02 explicitly forges the canonical Valuation admission hash.

No production decision semantics were changed by PR #131.

## Independent audit method

A fresh diagnostic suite was constructed without reusing the B04-B attack assertions as the audit verdict.

The audit directly exercised canonical runtime resolvers and production Decision / replay entry points against the current main implementation.

Audit workflow:

- workflow: **IIOS Post-B04 Independent Red-team**
- run #4
- audit head: `a080caebe3e6fa08d3716511128db674a6e8d7f1`
- result: **SUCCESS**
- 7 audit tests passed
- compileall: PASS
- git diff --check: PASS

The audit suite contains no production implementation changes.

## Threat matrix

### A-01 — Valid alternate Forecast substitution

Attack:
- create a second, valid canonical Forecast admission for the same instrument;
- replace `return_gate.canonical_forecast_ref` with the alternate reference;
- leave the originally admitted canonical Valuation unchanged.

Expected security property:

```
alternate Forecast
    !=
Valuation.forecast_ref
    ⇒ BLOCKED
```

Observed: **BLOCKED**.

The runtime rejected the substitution because canonical Valuation remains bound to the original Forecast reference.

### A-02 — Valid alternate Valuation substitution

Attack:
- create a second, valid canonical Valuation admission;
- substitute its canonical Valuation reference into Return Gate;
- retain the original Return Gate economics.

Expected security property:

```
Return Gate economics
    !=
selected canonical Valuation
    ⇒ BLOCKED
```

Observed: **BLOCKED**.

The runtime rejected the substitution through the canonical valuation binding.

### A-03 — Cross-domain Canonical Upstream Reference

Attack:
- move a valid canonical REALITY admission reference into the VALUATION slot;
- preserve the reference's valid admission hash.

Expected security property:

```
canonical ref domain != required domain
    ⇒ BLOCKED
```

Observed: **BLOCKED**.

The upstream authority boundary rejects the reference as invalid for the expected domain.

### A-04 — Missing Valuation Resolver at direct Decision runtime

Attack:
- submit an otherwise valid v0.3 case;
- omit `valuation_output_resolver`.

Expected security property:

```
missing mandatory resolver
    ⇒ validation BLOCKED
    ⇒ no BUY
    ⇒ new capital forbidden
```

Observed: **PASS**.

The runtime returned validation BLOCKED, action != BUY, and `new_capital_allowed = false`.

### A-05 — Missing Valuation Resolver at replay

Attack:
- create a valid v0.3 snapshot using all canonical resolvers;
- replay it while omitting `valuation_output_resolver`.

Expected security property:

```
re-execution cannot silently reconstruct the decision
    ⇒ replay FAIL
```

Observed: **PASS**.

Replay returned:

```
replay_status     = FAIL
same_decision     = false
integrity_status  = PASS
```

The separation is correct: the persisted snapshot remains internally hash-intact, while canonical re-execution fails closed because a mandatory authority resolver is absent.

### A-06 — Same-ID conflicting Forecast bytes

Attack:
- admit a canonical Forecast;
- attempt to admit a second Forecast with the same `forecast_id` but different economics.

Expected security property:

```
same canonical ID + different bytes
    ⇒ reject
```

Observed: **REJECTED**.

The registry preserves immutable canonical admission bytes.

## Runtime boundary inspection

Independent source inspection of the canonical main confirms:

```
engine.validate_case()
        ↓
validate_case_v03()
        ↓
canonical Forecast resolver
canonical Valuation resolver
canonical Upstream resolver
        ↓
Decision

engine.decide()
        ↓
same resolver set
        ↓
Decision

engine.run_case()
        ↓
same resolver set
        ↓
snapshot

engine.replay()
        ↓
same resolver set
        ↓
deterministic re-execution
```

Canonical Decision Admission also re-validates the v0.3 case and re-executes the canonical Decision Kernel with the resolver set, rather than trusting a caller-supplied Decision projection.

Decision Lifecycle persistence requires a Decision Admission receipt for v0.3 revisions.

## Governance findings

### Finding G-01

**No authority bypass was reproduced in the tested post-B04 chain.**

The tested authority boundaries fail closed under:
- valid-but-wrong Forecast reference;
- valid-but-wrong Valuation reference;
- cross-domain upstream reference;
- missing mandatory Valuation resolver;
- replay without mandatory resolver;
- immutable-admission collision.

### Finding G-02

**The previously identified B00-B P0-02 path is materially closed on the enforced Decision path.**

The current chain does not rely only on caller-supplied Return Gate economics; it requires resolver-backed canonical Forecast → Valuation lineage and checks Return Gate equality against that canonical output.

### Finding G-03

The audit does not constitute a formal proof of absence of all possible authority vulnerabilities. Its conclusion is bounded to the tested interfaces, current production call graph inspected above, and canonical main target SHA.

### Finding G-04

The baseline case constructor used by the audit comes from the existing canonical v0.3 test fixture. The attack logic itself is fresh and does not call the B04-B `bind_return_lineage` helper to perform the security assertions. This is a limitation of fixture independence, not a production runtime dependency.

## Adjudication

**VERDICT: PASS**

The post-B04 authority chain is adjudicated **sufficient for the current governance boundary**.

The following may now be treated as canonical:

```
B02 Canonical Admission
        ↓
B03-B Mandatory Upstream Authority
        ↓
B04-B Mandatory Forecast → Valuation → Return Lineage
        ↓
Post-B04 Independent Authority Re-audit
        ↓
PASS
```

This PASS does **not** authorize:
- FM-02;
- a new forecast model family;
- automated execution;
- scheduler / alerts;
- universe expansion;
- portfolio optimizer / Kelly logic.

## Next canonical development boundary

Proceed to the next explicitly governed engineering step:

**M1.2-FM00 Git Baseline / Frozen Reference Establishment**

followed by the constrained **FM-01 exact CATL source snapshot** work.

FM-02 Forecast Model Selection / research-model productionization remains gated by its own M1.2 governance and data-partition requirements.
