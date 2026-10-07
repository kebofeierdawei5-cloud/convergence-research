# IIOS B1-LCE — Semantic Artifact Contract Design v0.1

Date: 2026-10-07
Status: SUCCESSOR DESIGN / B2 IMPLEMENTATION INPUT

## 1. Purpose

Define the minimum typed boundary required to distinguish evidence provenance from semantic provenance.

This contract does not make the LLM authoritative over capital. It makes semantic reasoning auditable and admissible by code.

## 2. Semantic artifact classes

Required decision-relevant artifact classes:

```text
REALITY_INTERPRETATION
TRUST_ASSESSMENT
QUALITY_ASSESSMENT
THESIS_ASSESSMENT
VALUE_DRIVER_ASSESSMENT
INDEPENDENT_FORECAST_REASONING
VALUATION_PROPOSAL
MIE_INTERPRETATION
RISK_ASSESSMENT
POSITIONING_ASSESSMENT
```

Each class has a domain schema in B2. This B1 contract defines the common envelope only.

## 3. Common artifact envelope

Required fields:

```text
artifact_id
artifact_type
schema_version
case_id
market
symbol
company
cutoff_date
producer_type
producer_id
producer_version
policy_version
input_refs
input_hashes
output
facts
inferences
assumptions
uncertainties
decision_relevance
created_at
artifact_hash
```

## 4. Producer authenticity

Allowed `producer_type` values for canonical semantic artifacts:

```text
LLM_SEMANTIC_PRODUCER
HUMAN_EXPERT_ADJUDICATION
```

`EXTERNAL_JSON`, `USER_SUPPLIED_JSON`, and `LEGACY_FIXTURE` are not valid producer types for canonical semantic admission.

A producer declaration is admissible only when backed by an orchestrator stage receipt issued by the runtime.

## 5. Evidence binding

Every material semantic claim must reference one or more admitted evidence IDs.

The artifact must preserve:

```text
known_at <= cutoff_date
```

for every evidence item used by the reasoning path.

Evidence IDs alone are insufficient. The runtime must resolve them against the admitted evidence manifest before admission.

## 6. Reasoning vs fact

The semantic artifact must keep separate fields for:

- `facts`
- `inferences`
- `assumptions`
- `uncertainties`
- `decision_relevance`

No single free-text paragraph may be the only representation of a material economic claim.

## 7. UNKNOWN / ambiguity

A producer must be able to emit:

```text
UNKNOWN
AMBIGUOUS
CONDITIONAL
PASS
FAIL
```

The runtime must not reinterpret `UNKNOWN` or `AMBIGUOUS` as PASS merely because a downstream calculator accepts a numeric field.

## 8. Forecast-specific boundary

Independent Forecast Reasoning must explicitly attest:

```text
current_price_used = false
```

and must identify the admitted company/economic inputs used to generate the forecast.

A canonical Forecast Admission remains the deterministic admission authority; the LLM remains the reasoning producer.

## 9. Valuation-specific boundary

`VALUATION_PROPOSAL` must state:

- proposed primary model;
- economic rationale;
- candidate alternatives;
- material assumptions;
- model incompatibilities;
- evidence references;
- unresolved uncertainties.

The proposal does not itself authorize the model. B4 later defines the corrected LLM proposal -> code suitability -> human override role.

## 10. Hashing / replay

The runtime hashes the exact canonical JSON representation of the artifact envelope.

The hash is an integrity binding only. It is not proof that the reasoning is economically correct.

Replay must verify both:

```text
artifact bytes / hashes
+
producer / input / cutoff lineage
```

## 11. Acceptance boundary

B1 design PASS requires that the contract can distinguish:

```text
same evidence + different reasoning
```

from:

```text
same reasoning artifact + different evidence lineage
```

and must reject both silent substitutions.
