# B2-F — Full Independent Red-team Acceptance Record

Date: 2026-10-08

Status: **BLOCKED / FINDINGS REPRODUCED**

The audit independently reviewed B2-E from a clean-room perspective and reproduced four findings.

## P0 — F-001: Semantic → Economic causal edge missing

B2-E accepts a semantic artifact, but the Decision Kernel is invoked against a separately supplied expanded Investment Core case. The admitted semantic output is not transformed into the economic inputs used by Forecast, Valuation, Risk, Expectation Gap or Decision.

This is the principal blocker for any production claim that the LLM actually drives the canonical investment reasoning chain.

## P1 — F-002: Forecast / Valuation stage admission

B2-E marks Forecast and Valuation stages admitted after extracting mappings from the supplied case and hashing them. Dedicated canonical admission validation is not performed at those stage transitions.

## P1 — F-003: Nested authority-field escape

The semantic guard checks only top-level keys. A nested payload such as output.decision.action is not matched by the current guard.

This does not directly grant Decision authority because the Decision Kernel ignores semantic output, but it leaves the semantic contract weaker than the intended closed authority boundary.

## P1 — F-004: Decision Series identity

The lifecycle contract accepts a caller-supplied decision_series_id; the lifecycle record itself does not structurally carry market, symbol and company into the series identity. Cross-series correctness therefore depends on caller discipline.

## Overall disposition

B2-F is **not PASS**.

The correct next development batch is a dedicated repair batch, followed by a fresh independent B2-F rerun from the new canonical main. No P0/P1 finding should be silently waived.

B2-D3 remains a separate live-provider evidence gate.
