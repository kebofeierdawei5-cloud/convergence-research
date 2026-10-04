# IIOS B1 — Code Migration Red-Team v0.3

Date: 2026-10-04
Status: REVIEW COMPLETE — NO CRITICAL BYPASS OBSERVED
Runtime commit: cd4f510301a8a03d0884fe5d816384aef386921e
Semantic base: cf43ccd59ff92198c01bd1568c96fa147e0e2e37

## 1. Critical semantic bypass attacks

1. Dual 15% aliasing: v0.3 exposes separate entry-cushion and fundamental-target fields. PASS.
2. Additive hurdle injection: return_gate_pass uses conjunction, never 15% + RR. PASS.
3. Missing H: validator requires horizon and enforces 1 <= H <= 3. PASS.
4. Annualization of point intrinsic value: v0.3 requires horizon terminal wealth. PASS.
5. Probability-weighted annualized returns: primary calculation annualizes expected terminal wealth. PASS.
6. Unknown -> HOLD: UNKNOWN Trust/Portfolio/Risk/Thesis routes to REVIEW_REQUIRED. PASS.
7. Trust FAIL -> automatic EXIT: existing positions route to REVIEW_REQUIRED absent explicit hard-exit policy. PASS.
8. Portfolio constraint bypass: BLOCKED portfolio constraint prevents new capital and can REDUCE existing exposure. PASS.
9. MIE becomes mandatory: MIE is optional and the BUY gate records mie_required_for_buy_add=false. PASS.
10. Cost-basis anchoring: v0.3 return math uses current entry price; no cost-basis field enters return gate. PASS.
11. Incomplete BUY/ADD package: runtime and schema require entry zone, position limits, thesis-break triggers and monitoring triggers. PASS.
12. Decimal serialization/replay divergence: metrics are serialized as exact strings before snapshot hashing; replay passed. PASS.
13. PIT price leakage: observed_at and known_at are checked against cutoff. PASS.
14. Future contract confusion: v0.2 remains legacy path; v0.4 remains explicitly rejected. PASS.
15. Auto-execution path: every v0.3 decision reports human_approval_required=true and auto_execution=false. PASS.

## 2. Known limitations — not hidden

- Entry Value Reference construction is a supplied input; economic independence is not yet proven by this migration slice.
- Required Return construction methodology is a supplied policy input; methodology is not yet frozen.
- Full company Reality / Quality / Value Core economic chain remains incomplete.
- MIE remains explanatory and is intentionally not a decision gate.
- Position-sizing formula remains policy work beyond the migration slice.
- LLM direct-state-write protection is not demonstrated by this deterministic-only runtime test suite.

## 3. Conclusion

The migration implements the accepted B1 semantic target for the tested runtime slice without observed critical bypass.
It does not establish production investment capability or economic validity of the supplied valuation/forecast inputs.