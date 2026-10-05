# A1-02 — Capital Allocation + Trust/Governance Evidence Closure v0.1

Date: 2026-10-05
Status: IMPLEMENTATION TARGET

## Objective

Close the next company-side evidence gap after A1-01:

    shareholder return / repurchase
    → strategic capital commitments
    → related-party exposure
    → governance safeguards
    → Trust revalidation input

This slice is evidence closure, not a new investment model.

## Normative boundary

A1-02 does not alter:

- Decision Kernel semantics;
- BUY / ADD permissions;
- Quality Gate precedence;
- MIE semantics;
- portfolio constraints;
- automatic execution.

The output is explicitly:

    decision_effect = NO_DIRECT_GATE_EFFECT

Trust and capital-allocation statuses are evidence states for downstream revalidation.

## Deterministic calculations

### Annual payout

    2025 payout ratio =
        declared 2025 cash dividend total
        / 2025 attributable net income

The 2025 annual report states a proposed cash distribution equal to 50% of attributable net profit, with total cash distribution including the already-paid 2025 interim dividend.

### 2026 H1 payout

    H1 2026 interim payout ratio =
        H1 2026 interim cash dividend
        / H1 2026 attributable net income

The 2026 H1 report states the interim distribution is 15% of H1 attributable net profit.

### Repurchase share ratio

    repurchase share ratio =
        H1 2026 repurchase-account shares
        / H1 2026 total shares

This is a diagnostic measure of treasury-share scale, not a claim about economic value creation.

### Related-party guarantee exposure

    guarantee / project commitment ratio =
        related-party guarantee cap
        / Indonesia project planned-investment cap

This ratio contextualizes exposure only. It does not imply the full project amount or guarantee amount has been spent or drawn.

## Trust / Governance semantics

A related-party transaction is an observed governance-risk fact, not an automatic Trust FAIL.

The current A1-02 evidence shows:

- related-party guarantee exposure for the Indonesia project;
- related-party procurement commitment;
- independent-director special-meeting review;
- recusal by the related director;
- unanimous recorded vote by eight non-related directors.

Accordingly:

    governance_integrity = CONDITIONAL
    trust_revalidation = CONDITIONAL

The reason is deliberate: procedural controls reduce governance risk but do not eliminate the need to assess economic terms, arm's-length fairness, recurring exposure, and shareholder impact.

Shareholder treatment is recorded as PASS at this evidence layer because the disclosed 2025 and 2026 H1 cash-return actions are explicit and material. This PASS is not an aggregate Trust PASS.

## CATL 300750 evidence

### E014_A1 — 2025 annual capital allocation

The official 2025 annual report states that the 2025 distribution proposal uses 50% of attributable net profit, and that no bonus shares or capital-reserve capitalization is proposed. The report also identifies 31,982,306 shares in the repurchase account at the relevant distribution-plan date.

Source:
https://static.cninfo.com.cn/finalpage/2026-03-10/1225002214.PDF

### E015_A1 — 2026 H1 capital allocation

The official 2026 H1 report states an interim cash dividend of CNY 6,492.6 million, equal to 15% of H1 attributable net profit, with 28,319,044 shares in the repurchase account at H1 end.

Source:
https://static.cninfo.com.cn/finalpage/2026-07-25/1225441586.PDF

### E016_A1 — related-party guarantee

The 2026-09-30 board resolution / 2026-10-01 announcement records a related-party guarantee for financing of the Indonesia battery industry-chain project. The historic project investment cap is USD 5.968 billion; the related-party guarantee cap is USD 130 million. The announcement records independent-director review, related-director recusal, and 8-0-0 voting by non-related directors.

Source:
https://static.cninfo.com.cn/finalpage/2026-10-01/1225592063.PDF

### E017_A1 — related-party procurement

The 2026-09-30 board meeting / 2026-10-01 announcement records a related-party procurement arrangement for cathode copper for 2027-2028 with a total cap of USD 320 million. The disclosed related-party relationship includes indirect 29.4% ownership by the actual controller and a non-independent director role.

Source:
https://static.cninfo.com.cn/finalpage/2026-10-01/1225592062.PDF

## Expected 300750 result

| Metric | Result |
| --- | ---: |
| 2025 annual payout ratio | 50.00% |
| 2026 H1 interim payout ratio | 15.00% |
| H1 2026 repurchase-account share ratio | ~0.612% |
| Indonesia guarantee / project-cap ratio | ~2.178% |
| Capital allocation status | CONDITIONAL |
| Governance integrity | CONDITIONAL |
| Trust revalidation | CONDITIONAL |
| Shareholder treatment evidence | PASS |
| Decision effect | NO_DIRECT_GATE_EFFECT |

## Acceptance

A1-02 is accepted only when:

1. E014_A1 through E017_A1 exact-byte size/SHA checks pass;
2. all four evidence records are bound to the exact case and cutoff;
3. unadmitted evidence references fail closed;
4. post-cutoff observations fail closed;
5. governance-control facts are validated deterministically;
6. payout and repurchase ratios are deterministic;
7. schema validation passes;
8. tamper/hash detection passes;
9. Investment Core CI passes with no existing regression;
10. no P3/P4/MIE model is added or modified.

## Deliberate non-claims

A1-02 does not conclude that:

- the related-party terms are economically fair;
- the Indonesia project will earn an adequate ROIC;
- the copper procurement is arm's-length;
- Trust should be upgraded to PASS;
- Quality should be upgraded to PASS.

Those questions require the next evidence-linked validation layer.

## Next slice

A1-03 should integrate the now-closed economic bridge plus capital-allocation/trust evidence into the existing Quality dimensions with explicit conditional semantics and regression tests, without introducing new valuation or MIE logic.
