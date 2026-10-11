# Operator-Entered Price — Decision Input Contract (2026-10-11)

- Record class: governance/implementation contract proposal
- Baseline: canonical `main@a60e62cd6c39492b404fee1cbfc0511717726ee3`
- Status: **MP-1 + MP-2 + REPORT ASSURANCE PASS / PRs #366/#368/#370; MP-3 CROSS-LAYER / EVIDENCE-PIT / SNAPSHOT / PROVENANCE / NO-PUBLICATION SLICES PASS / PRs #372/#375/#377/#378/#379; LOCAL RECEIPT REVIEW + REMAINING MP-3 OPEN**
- Scope: initial A/H-share current-price entry is supplied manually by the operator; IIOS does not automatically fetch market quotes for this path.

## 1. Decision

For the initial local-single-user workflow, use **MANUAL_OPERATOR_INPUT** for the price value used by a valuation/decision run. Do not make automated SSE/SZSE quote retrieval, a paid quote API, or a provider key a prerequisite for entering the price.

This changes the acquisition path, not the truth class of the value. A manually entered quote is recorded as `OPERATOR_ATTESTED_MARKET_DATA` and must never be relabelled as official-source captured, source-vintage verified, licensed-vendor data, or formally admitted exchange market data merely because it passes a schema or hash check.

## 2. Separate three kinds of records

1. **Company Evidence/PIT:** official filing bytes and facts, exact hashes, source-vintage/known-at bounds, permitted use, and required authorized signatures. Manual price entry does not waive these gates.
2. **Operator-entered price input:** a separate typed input attached to one run. It records what the operator entered and when the local tool received it. It is not a company-filing fact and must not masquerade as the `market_price` Evidence/PIT group.
3. **Decision output:** may use the operator-entered price only through an explicit resolver/contract that preserves the price class and its lower source assurance. A formal Decision may be produced only if the new decision-input contract, all company Evidence/PIT requirements, Forecast/Valuation/Risk/Portfolio gates, and existing human-approval boundary pass. Until implementation and independent adversarial acceptance are complete, current analysis-only restrictions remain in force.

The implementation must not weaken the existing Core/PIT validator by silently treating an operator-entered price as admitted exchange evidence. If the canonical schema currently requires a market-price evidence group, implement a separately typed operator-price alternative at the relevant admission boundary and test the original evidence path unchanged.

## 3. Required fields and time semantics

The local input contract must bind at least:

- Case/version id, market, symbol, exchange, currency and price units;
- positive finite price and explicit adjustment semantics (v0 should support only unadjusted close);
- observation/quote date and, where actually known, quote timestamp;
- the local tool's generated `entered_at` timestamp (not an operator-provided timestamp);
- the run's explicit as-of/cutoff timestamp and the rule for how long that quote remains usable;
- explicit operator confirmation and an input content hash;
- a private, content-addressed receipt that redacts the quote value and any private source label.

The tool must distinguish `observation_date`, `entered_at`, and `decision_cutoff`; they are not interchangeable. The quote may not be backfilled into a frozen Case whose PIT cutoff precedes the observed/entered information. A date-only cutoff retains the existing Shanghai start-of-day semantics. If a manually entered value arrives after that cutoff, create a new run/case revision or use the explicitly non-canonical scenario overlay; never mutate the frozen case or pretend the old cutoff covers the new input.

A quote freshness/expiry rule must be explicit and verifiable for each run. Do not invent an exchange timestamp, assume a quote is current, or silently extend validity. If required time information is absent or inconsistent, return `BLOCKED` or remain in analysis-only mode.

## 4. Provenance and authority invariants

Every operator-entered price record and downstream output must preserve:

- `record_class = OPERATOR_ATTESTED_MARKET_DATA`;
- `source_origin_verified = false`;
- `source_vintage_verified = false`;
- `source_use_rights_verified = false` unless a distinct applicable permission instrument is independently verified;
- `raw_source_bytes_captured = false`;
- `canonical_exchange_price_admission = false`;
- `operator_confirmation = true` only after an explicit user action;
- `public_upload_allowed = false` for private price values, input files, and full receipts.

A local hash proves byte integrity, not that the entered price is true, current, licensed, or from the claimed source. Do not put actual quote values, private input files, source labels, secrets, or full private manifests in GitHub commits, issues, PRs, CI logs, or artifacts.

The operator can manually enter a value without naming a source. If a source is named, preserve it as an unverified operator claim; do not promote that label into source evidence.

## 5. C1/C2 implications

- **C1 / 605016:** do not rerun or overwrite the existing source-vintage candidate. Its historical market-price admission remains blocked as exchange-sourced evidence. A fresh analysis/decision run may instead carry a separately entered operator price if all applicable time and company-evidence gates pass. The manual path does not resolve or falsify the SSE market-data-rights question for the old candidate.
- **C2 / 002001:** manually entering price removes the need for this initial workflow to fetch/retain a market quote. It does not complete the independent review/sign-off of the thirteen official-filing fact locators, nor permit a user-attested quote to be used as corroborating source evidence.
- **Current case cutoffs:** neither existing frozen cutoff nor any pinned raw filing/manifest is rewritten. The system must use a new run/case revision where the manual price is later than the frozen cutoff.
- **No source/legal conclusion:** this contract defines provenance and engineering behavior. It is not a legal conclusion that manual transcription overrides a data provider's terms.

## 6. Implementation batches and acceptance

### Batch MP-1 — typed local input (PASS / MERGED; exact-head CI + red-team passed)
- Added `iios_mvp/operator_entered_price_decision_input_v01.py`: interactive local entry for CN-A/HK, locally generated `entered_at` / decision-cutoff timestamps, explicit operator confirmation, quote timestamp and explicit `valid_until`.
- Added private content-addressed `price-input.json` + value/source-claim-redacted `receipt.json`, mode-restricted non-overwrite, ownership/path checks and deterministic replay/provenance-flag validation.
- Added `tests/test_operator_entered_price_decision_input_v01.py` with 23 guardrail cases, including provenance escalation, timestamp, unsupported A-share prefixes, private-path redaction, tilde-expanded symlink, and storage boundaries and wired it into `.github/workflows/iios_private_scenario_analysis.yml`.
- This is only typed input and replay integrity. It deliberately leaves `decision_chain_bound=false`, `formal_evidence_pit_admission=false`, and `formal_decision_authority=false`. Exact-head CI/review must pass before MP-1 is accepted.

### Batch MP-2 — decision-chain integration (CORE PASS / MERGED PR #368)
- Added a separate trusted local resolver for the operator price bundle; canonical admitted-market-price resolver behavior is unchanged.
- Validated private price-input and receipt bytes/hashes, case/instrument/currency identity and date-level cutoff; manual values remain `OPERATOR_ATTESTED_MARKET_DATA`, with source-origin/vintage/rights and formal Evidence/PIT flags false.
- Kept the P4-F MIE baseline price source-qualified and separate from the operator current price used for entry/return evaluation.
- Bound the input and receipt as two distinct hashes/references in `DECISION_PENDING`; Run Authority validates pair format, hash format, equality with the snapshot reference, price synchronization and non-escalated provenance flags.
- Decision Admission preserves the input class and assurance; Human Approval remains required and automatic execution disabled.
- Exact-head PR #368 passed 30/30 triggered workflow checks, including B2-E persisted integration, legacy Run Envelope replay and B2-F/Post-B04 independent red-team.
- **Report assurance completed in PR #370** (`d6fe4855276a7e5425950fa89efbc6d20242646b`): 6/6 exact-head checks passed, including dedicated investor-review QA and Post-B04 independent red-team. The machine surface records the price input class, assurance label and limitation codes; the Chinese report discloses non-verification/source-rights limits, and private bundle IDs/hashes are deliberately omitted. No private price value/source label/bundle is stored in Git.
- **Still open:** independently review one actual local private bundle/receipt/Run Receipt replay using sanitized status and hash outcomes, then finish MP-3 cross-layer adversarial acceptance.

### Batch MP-3 — adversarial and end-to-end acceptance (MULTIPLE SLICES PASS / REMAINDER OPEN)
- **PR #372 cross-layer slice PASS:** both exact-head workflows passed (B2-E 14/14, B2-E red-team 7/7, B2 semantic admission 14/14, semantic red-team 15/15). It rejects a missing trusted resolver, conflicting top-level-vs-Case references, forged receipt SHA blocking a persisted run before Decision stage, and malformed Run Authority record/receipt pairs.
- **PR #375 Evidence/PIT + snapshot-tamper slice PASS** at `642867f216c7eac94c6c65e233dbb1190afc2108`: both exact-head workflows passed (B2-E 17/17, B2-E red-team 7/7, B2 semantic admission 14/14, semantic red-team 15/15). With a valid private manual-price receipt, B2-E still blocks when the company Evidence/PIT manifest is missing or a required evidence group is incomplete. After a Decision is admitted, changing current price, expectation-gap price/ID or return-gate entry price causes Decision Revision authorization to fail; changing linked values together and recomputing the snapshot hash still cannot rebind to the existing Decision Admission.
- **PR #377 stale-reference/currency/provenance boundary slice PASS:** the exact-head B2-E workflow exercises stale record SHA with a bundle-ID prefix preserved, wrong Case ID, Case-side currency tampering, a source-origin assurance flag set to true, and unknown price class; every persisted run is BLOCKED before Decision.
- **PR #378 full provenance flag and exchange identity closure PASS:** 9/9 exact-head checks passed, including `test-mvp` 412/412 and `pilot-02`. All eight flags are explicitly false on the operator input observation and rejected if escalated: source claim/origin/vintage/use rights, raw bytes captured, canonical exchange admission, canonical price admission, and formal Evidence/PIT admission. Exchange metadata on the current-price observation must match the private record.
- **PR #379 blocked-run downstream artifact boundary PASS:** both exact-head B2-E and semantic-admission workflows passed; counts were B2-E 24/24, B2-E red-team 8/8, B2 semantic admission 14/14 and semantic red-team 15/15. A forged receipt hash causes a persisted run to be BLOCKED, with no Decision Admission; machine publication and complete Run Receipt creation are also rejected.
- **Remaining cross-layer negatives:** deeper stage-bypass and replay-record tampering, additional instrument/exchange/currency/reference corruption permutations, and complete downstream publication/report authorization bypass coverage. Failures must remain fail-closed with no Decision Admission/Publication/Run Receipt from a blocked run.
- **Local acceptance still OPEN:** independently review one actual local private bundle/receipt and complete Run Receipt/replay using only sanitized status, analysis ID and hash-check outcomes. Never upload prices, source labels, raw source bytes, local manifests or private receipts.
- Until the remaining gates pass, Path A remains analysis-only and software tests are not formal investment acceptance.

## 7. Non-goals

No automatic quote retrieval, broker integration, price scraping, provider API, broad price archive, change to frozen historic cases, no-source proof, legal interpretation, relaxation of C1/C2 source-fact review, or order execution.
