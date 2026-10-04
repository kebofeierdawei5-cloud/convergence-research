# IIOS B1 — Decision Semantics Red-Team v0.3

Date: 2026-10-04
Status: REVIEW OF PROPOSED SEMANTICS

1. UNKNOWN -> HOLD: FAIL. Must route to REVIEW_REQUIRED unless a definitive negative policy applies.
2. REVIEW_REQUIRED permits capital: FAIL. It permits no new capital and requires Human review.
3. Trust FAIL automatically sells: FAIL. EXIT requires an explicit hard-exit rule.
4. Strong valuation ignores portfolio limits: FAIL. Portfolio BLOCKED has permission priority.
5. Portfolio policy changes intrinsic value: FAIL. It only controls allocation/position.
6. Missing MIE blocks every BUY: FAIL in v0.3. MIE is non-mandatory.
7. Ambiguous MIE becomes market truth: FAIL. It may only inform or trigger review under an explicit materiality rule.
8. BUY with only 15% entry cushion: FAIL. Annualized target and RR conditions remain separate.
9. BUY with 15% annualized target but no entry cushion: FAIL.
10. RR added to either 15%: FAIL.
11. Cost basis rescues weak current opportunity: FAIL.
12. WATCH has no re-evaluation trigger: FAIL.
13. HOLD used for missing material evidence: FAIL.
14. Human override erases AI proposal: FAIL.
15. BUY/ADD without complete position package: FAIL.

Conclusion: the proposed decision semantics block the known Unknown/Trust/Investability/Portfolio/MIE/return-gate failure modes. Implementation remains unauthorized until owner approval.