# B72 — Operating feasibility exception register and remediation loop

Date: 2026-10-31

**Status: BRANCH PROPOSAL ONLY / NOT MERGED / NOT TESTED**

## 1. Objective

B69 identifies price-implied operating requirements that are not yet demonstrably executable. B70 links product/scenario/period-specific operating claims to primary-class source references and compares their values with B69 requirements. B71 records claim-specific human source-content review.

B72 consolidates these outputs into an auditable, per-scenario / per-requirement-lens / per-product exception register. For each requirement it preserves:
- the B70 numerical comparison result;
- the separately recorded B71 semantic-review result;
- the precise B70 evidence record IDs and source references;
- whether the requirement is still unknown, numerically short, contradicted by human review, conditionally supported or blocked; and
- an explicit remediation owner role, next action and evidence required for closure.

B72 is a read-only reporting / remediation layer. It does not change the operating assumptions that generated the requirement.

## 2. Placement and interface

New module:

iios_mvp/operating_feasibility_exception_register_v01.py

Output schema:

IIOS-OPERATING-FEASIBILITY-EXCEPTION-REGISTER-0.1

Nested result:

assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.operating_feasibility_exception_register

Local pilot integration:
- invokes B72 immediately after B69/B70/B71;
- publishes the derived exception register in analysis.json; and
- renders a Chinese report section B72 — 经营可行性例外清单与整改闭环.

B72 introduces no new operator input field. It does not require a new Replay input binding; the output is deterministically derived from the already-bound B69/B70/B71 inputs.

## 3. Two independent evidence axes

B72 deliberately avoids treating a numerical match as proof of source truth.

### Numerical / linkage axis

The B70 comparison is retained with its original value and status. B72 distinguishes:
- linked value numerically covers the requirement;
- linked value misses a sales / ASP / unit-cost requirement;
- linked funding amount is insufficient;
- capacity is available after the forecast period;
- evidence is missing;
- evidence linkage is not eligible;
- analyst assumption only;
- duplicate / ambiguous claims; and
- required or evidence values remain unidentified.

A numerical requirement gap is not the same as a false source claim. It means the linked value, if accepted, does not reach the price-implied threshold.

### Human semantic-review axis

B71 is independently retained as:
- conditionally supported by a complete human review with a separate reviewer and declared no-known-conflict status;
- partial;
- unable to verify;
- contradicted / not supported;
- independence unresolved;
- blocked / incomplete; or
- not provided.

A B71 conditional support cannot override a B70 numerical shortfall. Conversely, a B70 numerical match without the required semantic review is only NUMERICAL_LINKAGE_ONLY_REVIEW_PENDING.

The strongest B72 row status is CONDITIONALLY_SUPPORTED_NOT_FORMALLY_ADMITTED. It is not a formal Evidence/PIT admission, Forecast admission, Valuation admission or an operational execution approval.

## 4. Requirement rows and exception taxonomy

For each Bear / Base / Bull scenario, and separately for each B61 / B63 lens, B72 retains the product-level B70 comparison rows:
- supported sales volume;
- supported net ASP;
- supported unit variable cost;
- effective capacity available;
- capacity availability date;
- incremental capex requirement / funding; and
- incremental working-capital requirement / funding.

It also keeps the B69 nameplate-capacity arithmetic as a separate row:
- NAMEPLATE_CAPACITY_CONSTRAINT;
- CONDITIONAL_NAMEPLATE_FIT_ONLY;
- CAPACITY_NOT_IDENTIFIABLE; or
- INVALID_NEGATIVE_REQUIRED_PRODUCTION.

A conditional nameplate fit is not described as operational feasibility.

B72 separately retains B69 dimensions that B70's narrow one-driver numerical comparisons do not prove in full:
- customer-demand sustainability and demand elasticity;
- price elasticity and competitive response; and
- the cost curve and execution of savings.

These remain NOT_IDENTIFIABLE_UNCOVERED_DIMENSION, even where a narrower volume / price / cost claim numerically meets its threshold. This prevents a single-variable threshold from being misrepresented as a complete operating plan.

## 5. Remediation contract

Each requirement row carries:
- deterministic requirement_id and action_id;
- exception_status;
- owner_role;
- next_action;
- closure_evidence_required;
- status = OPEN_REMEDIATION_REQUIRED; and
- automatically_closed = false.

Actions differ by failure class. Examples:
- numerical gap: rebuild the operating driver plan against the original price-implied threshold;
- incremental funding shortfall: prove incremental, unrestricted funds and timing without double counting B4;
- late expansion: verify commissioning, ramp and first qualified-product date;
- analyst assumption: replace it with cutoff-compatible primary evidence, otherwise retain UNKNOWN;
- semantic contradiction: suspend the claim, resolve the conflict and re-review;
- incomplete reviewer independence: obtain a separate reviewer with a no-known-conflict declaration; and
- nameplate capacity constraint: independently rebuild the capacity / inventory / expansion plan for the applicable lens.

B72 generates the closure criteria but does not mark tasks closed. Closure requires new evidence / corrected inputs and a fresh B69/B70/B71/B72 run. It is not a workflow ticketing engine and does not independently verify that an operator completed an action.

## 6. Non-additivity and governance boundary

- B61 B61_SINGLE_SEGMENT_THRESHOLD and B63 B63_FULL_B4_VECTOR_THRESHOLD remain alternative threshold lenses. B72 displays them separately and performs no sum, average, shared score or probability weighting across them.
- Sales, ASP, unit-cost and capacity evidence rows retain their separate economic meaning. They are not combined into a single operating forecast.
- Missing evidence or review is a coverage gap / UNKNOWN, never a negative observation.
- No composite feasibility score, probability, expected value, or financial materiality estimate is generated.
- overall_operational_feasibility_status remains NOT_IDENTIFIABLE_PENDING_COMPLETE_OPERATING_COVERAGE_AND_FORMAL_ADMISSION.
- No formal Evidence/PIT, Forecast or Valuation admission is created.
- No change to B4/B42/B43/B55/B61–B71, selected SOTP, external MIE, expectation gap, the 15% annualized return hurdle, target entry price, portfolio constraints, Decision or execution authority.

## 7. Regression coverage and acceptance

Twenty regression cases are authored in:

tests/test_operating_feasibility_exception_register_v01.py

Coverage includes schema blockers, numerical-vs-semantic separation, conditional support, human contradiction, quantified threshold gaps, missing evidence vs analyst assumptions, duplicate claim handling, reviewer independence, funding shortfall, late capacity, B69 nameplate constraints, unmodeled dimensions, B61/B63 non-additivity, governance boundaries, remediation closure criteria and input immutability.

Tests have **not** been executed. Replay, CI, unified tests and real macOS acceptance have **not** been run or verified. No PASS is claimed.
