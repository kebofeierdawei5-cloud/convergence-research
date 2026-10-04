# IIOS Human Valuation Model Selection v1.0

## Decision

At the current stage, IIOS does not attempt to automatically determine a single "most appropriate" company valuation model.

The system boundary is:

Company Value Core Scan
→ Economic Profile
→ Candidate Valuation Models
→ Human Primary Model Selection
→ IIOS Model Consistency Gate
→ Primary / Secondary / Cross-check
→ Independent Forecast
→ Intrinsic Valuation

## Authority

### IIOS owns
- deterministic value-core schema validation
- economic-profile classification
- candidate model generation
- model suitability ranking as an advisory prior
- supported-model validation
- model/profile consistency checks
- override enforcement
- valuation calculations
- scenario calculations
- replay and audit persistence

### Human owns
- final Primary Model
- rationale for Primary Model
- Secondary / Cross-check selection when material
- explicit override decision when selecting outside the candidate set
- final investment approval

The router is advisory and must never silently replace the human-selected Primary Model.

## Required human selection record

`valuation.model_selection` must contain:

- `selection_method = HUMAN`
- `economic_profile`
- `primary_model`
- `rationale`

Optional:
- `secondary_models`
- `cross_check_models`
- `alternatives`
- `override_reason`

If Primary Model is outside IIOS candidate models, `override_reason` is mandatory.

## Fail-closed

Block valuation when:
- HUMAN selection is missing
- Primary Model is unsupported
- economic profile is missing or conflicts with Company Value Core Scan
- rationale is missing
- outside-candidate selection lacks override reason
- model inputs are incomplete or invalid

## Why

The final company valuation model is an investment judgment, not always a uniquely identifiable classification target. IIOS should automate repeatable evidence and calculation work while preserving the human judgment that cannot be reliably inferred from current data.

## Development consequence

Do not spend the next milestone trying to make the company-side Model Router more intelligent.

Instead:
1. make Human Model Selection deterministic and auditable;
2. strengthen the Model Consistency Gate;
3. make secondary/cross-check models useful without averaging them into the primary value by default;
4. move automation effort to the market side:
   Current Price → Market Model Hypotheses → Reverse Valuation → Feasible Solution Set → Identifiability → Stability → Market Implied Expectation;
5. only later revisit automatic company-model recommendation after sufficient historical validation data exists.

## Boundary with Market Model Identification

Company model selection answers:

> How should IIOS value the company independently?

Market model identification answers:

> What valuation logic and operating expectations are currently embedded in the market price?

They must remain separate to preserve a genuine expectation-gap calculation.
