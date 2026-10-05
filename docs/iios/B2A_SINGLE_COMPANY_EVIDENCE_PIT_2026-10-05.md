# IIOS B2-A — Single Company Evidence / PIT Foundation

Date: 2026-10-05
Status: IMPLEMENTATION TARGET

## Scope

B2-A is the Investment Core Evidence/PIT foundation for one user-selected company.

It has no dependency on CSI800 historical membership, CSI Industry history, cross-company universe construction, A02 Object A/B or paid commercial data. A02 code and artifacts are outside the `research/b2/` namespace and are not executed by B2 CI.

## Vertical slice

User-selected company -> Evidence Record -> Raw Artifact Declaration -> exact-byte verification -> PIT validation -> required field-group coverage -> immutable manifest hash -> admission/replay.

## Minimum company evidence envelope

- security_identity
- market_price
- corporate_disclosures
- business_reality
- financial_reality
- capital_structure
- trust_governance_events

The default envelope contains the minimum material evidence groups needed before a real-company Investment Core case can proceed.

## Exact bytes

content_sha256 identifies the expected evidence content, but the hash string alone is not physical verification.

B2-A therefore has an independent raw-artifact verifier that recomputes file size and SHA-256 from actual local bytes.

No raw bytes means no exact-byte admission.

## PIT

Canonical rule: known_at <= cutoff.

retrieved_at never substitutes for known_at.

Historical evidence retrieved after the cutoff can still qualify only when the source vintage or publication basis independently proves that the fact was already knowable.

## Fail closed

B2-A blocks when material evidence is:
- missing;
- future-known relative to cutoff;
- hash-mismatched;
- absent from required field-group coverage;
- missing exact raw verification;
- internally invalid under the Evidence Contract.

## Research Track boundary

A02/CSI800 continues as a separate Research Track consumer of the same generic Evidence/PIT primitives. Its code lives outside `research/b2/`, and B2 CI must not invoke or validate A02 execution.

It is not required for the Investment Core single-company path.

## Exit criterion

B2-A is PASS when the contract, validator, exact-byte verifier and adversarial tests are green in CI.

It does not claim CATL or any other real company is already fully admitted; that is B2-B.
