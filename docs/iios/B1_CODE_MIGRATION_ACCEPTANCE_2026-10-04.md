# IIOS B1 — Code Migration Acceptance 2026-10-04

Status: PASS — IMPLEMENTATION SLICE ACCEPTED
Semantic parent: cf43ccd59ff92198c01bd1568c96fa147e0e2e37
Runtime head tested: cd4f510301a8a03d0884fe5d816384aef386921e
Branch: repair/b1-code-migration-v0.3-clean-20261004
PR: #20

## Evidence

GitHub Actions Investment Core CI run for the exact tested head:
- compileall: PASS
- pytest: 190 passed
- v0.3 JSON schema syntax: PASS
- CLI run: PASS
- snapshot replay: PASS
- replay_status: PASS
- same_decision: true
- integrity_status: PASS

## Implemented

- versioned v0.3 return contract/runtime;
- separate 15% BUY Entry Return Cushion and 15% 1–3Y Fundamental Target Annualized Return;
- explicit horizon and terminal wealth;
- Expected Total Return and Expected Annualized Return;
- independent Required Return comparator;
- BUY/ADD/HOLD/REDUCE/EXIT/NO-BUY/WATCH/REVIEW_REQUIRED;
- Trust / Portfolio / Unknown behavior;
- optional/non-mandatory MIE;
- current-price opportunity semantics distinct from historical cost basis;
- deterministic snapshot/replay routing;
- full BUY/ADD position package validation.

## Non-claims

This acceptance does not establish:
- completeness of the company Reality / Quality / Value Core chain;
- correctness of Entry Value Reference construction;
- correctness of Required Return methodology;
- decision-grade MIE necessity;
- production investment capability;
- predictive validity of forecast assumptions.

## Next

Merge the accepted runtime into the B0 repair line, then proceed to B2 Data/Evidence/PIT Foundation and B3 Reality/Quality/Value Core. Do not resume P5 feature expansion.