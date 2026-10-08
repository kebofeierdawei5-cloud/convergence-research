# IIOS Dual Report Surface — Human Review + Machine Archive — 2026-10-08

Status: IMPLEMENTED ON VALIDATION BRANCH / NOT YET CANONICAL

## Decision

IIOS now defines two distinct report surfaces derived from the same canonical Machine Publication:

1. Investor Review Report
   - language: zh-CN;
   - audience: human investor/operator;
   - purpose: practical investment review and human usability acceptance;
   - contains causal explanation, authorization semantics, assumptions, valuation, return/risk, position package, thesis breaks, monitoring and the human decision boundary;
   - cannot create or mutate investment authority.

2. Canonical Machine/Archive Summary
   - existing iios_mvp.human_report output;
   - remains the compact structured/English summary used for machine validation, deterministic rendering, CI evidence and archival lookup;
   - it is not the primary human usability surface.

## Shared Authority Rule

Both report surfaces are one-way projections from the exact same canonical Machine Publication:

Machine Publication
→ report surface

No report is allowed to recalculate company economics, rewrite the Decision, create new evidence, or authorize trading.

The Investor Review Report carries exact publication/decision binding and its own deterministic hash/QA record. The existing machine/archive report remains independently versioned and validated.

## Human Acceptance Rule

The Human Acceptance Gate must be performed against the Investor Review Report, not inferred from CI and not inferred from the machine/archive summary.

The operator is reviewing:

- whether the current action is obvious;
- whether capital authorization is unambiguous;
- whether facts, assumptions, thresholds and authorizations are distinguishable;
- whether the causal chain from Trust → Forecast → Valuation → Return/Risk → Portfolio → Decision is understandable;
- whether review/revision triggers are actionable.

The operator is not being asked to approve a trade merely by accepting report usability.

## Compatibility

The existing report CLI remains available for the compact machine/archive surface.

The new investor-report CLI generates:

- <hash>.investor-review.json
- <hash>.investor-review.md
- <qa-hash>.investor-review-qa.json

The new surface is additive and does not mutate historical reports or Decision semantics.

## Next Boundary

After this report-surface split passes CI, the actual human usability gate can be performed against the Chinese report. Final MVP closure remains subject to B0 P0-LLM-004 and the later B2 natural-language-to-canonical conformance gate.
