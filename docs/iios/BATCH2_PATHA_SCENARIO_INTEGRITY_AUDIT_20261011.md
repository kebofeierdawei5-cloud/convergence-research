# Batch 2 — Path A Scenario Integrity Audit (2026-10-11)

## Status

**IN PROGRESS — initial audit slice merged; operator bundle/receipt review pending.**

The operator reports that the fixed macOS one-click launcher completed normally. The actual private bundle, report and receipt have not been attached to this repository or independently inspected in this session. State classification is therefore **operator-reported successful execution; bundle-level acceptance not independently evidenced here**. Private prices and source labels must not be uploaded to public GitHub.

## Scope

Batch 2 builds on Batch 1's deterministic runner and its existing replay contract. It does not alter live valuation assumptions or create formal Forecast/Valuation/Decision admission.

New tests independently check:

1. **Fixed case assumptions:** exact profile constants for 002001 and 605016 (EPS, multiples and probabilities) against separately authored expected constants, not by importing the implementation profile as its own oracle.
2. **Arithmetic:** scenario values, probability-weighted terminal wealth, expected total/annualized price return, 15% annualized hurdle entry ceiling, 25% Bear-loss ceiling, binding minimum and headroom.
3. **Human report consistency:** the Chinese Markdown report reflects the machine JSON values, identifies the profile and assumption class, states that probabilities are uncalibrated, and preserves analysis-only / non-decision caveats.
4. **Exact-byte hashes:** SHA-256 of the stored private input, analysis JSON and report; the canonical analysis-body digest is independently recomputed from the file bytes' parsed content.
5. **Authority boundary:** source origin/use rights, formal Decision and execution remain false.

Existing tests continue to cover same-input repeat reuse, content-addressed non-overwrite for changed input, tamper detection, file permissions and fail-closed profile/probability validation.

## Independently expected model arithmetic

All output must match independently calculated values to the runner's declared rounding precision. H is currently 1 year for both profiles, so expected annualized price return equals expected total price return.

- 002001: scenarios 19.95 / 32.20 / 45.50 with probabilities 0.30 / 0.50 / 0.20; probability-weighted wealth ¥31.185. Return-hurdle ceiling is about ¥27.11739130; Bear-loss ceiling is ¥26.60000000; binding conditional ceiling is ¥26.60000000.
- 605016: scenarios 13.60 / 24.20 / 32.50 with probabilities 0.25 / 0.50 / 0.25; probability-weighted wealth ¥23.625. Return-hurdle ceiling is about ¥20.54347826; Bear-loss ceiling is about ¥18.13333333; binding conditional ceiling is about ¥18.13333333.

These are deterministic re-calculations of declared scenario assumptions, not proof that EPS, multiples, probabilities, source rights or expected returns are externally valid. The 25% Bear-loss limit for 605016 remains provisional and analysis-only.

## Acceptance gates

- [x] Exact-head CI including the Batch 2 tests passes: 13/13 checks; dedicated workflow 43 passed.
- [x] Independent arithmetic/report/hash tests pass.
- [x] Batch 2 test/document changes merged to canonical main at `0d257fe243d0a2e921023504c2a3b2128fdd285a`.
- [ ] A sanitized local receipt summary (status, analysis ID, replay status and hash-check outcomes only) is reviewed before claiming operator-bundle validation. Do not request or upload private price values, original source labels or input.json.
- [ ] No status is elevated to formal Evidence/PIT, Forecast, Valuation, Decision, Publication or execution authority.

## Out of scope

- No re-fetch of market prices.
- No source-rights assumptions or signer self-registration.
- No LLM/Ollama/API dependency.
- No changing scenario assumptions during the audit.
- No public upload of private inputs or full private analysis bundle.
