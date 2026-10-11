# Operator-Entered Price — Decision Input Contract (2026-10-11)

- Record class: governance/implementation contract proposal
- Baseline: canonical `main@70d146f3e5589829d334e18d0198692eed4fcd81`
- Status: **MP-1 PASS / MERGED at `c0eeb8c7543aec8939de7b29d84ac35b62044fdf`; MP-2/MP-3 OPEN**
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

### Batch MP-2 — decision-chain integration
- Integrate the typed price into the current-price resolver as an explicitly lower-assurance input class.
- Bind the input receipt/hash to the Run Envelope, stage receipts, valuation/return/risk outputs and full Run Receipt.
- Ensure report and machine publication expose the operator-attested class and limitations; do not claim formal exchange-price admission.
- Keep Human Approval required and automatic execution disabled.

### Batch MP-3 — adversarial and end-to-end acceptance
- Test missing/false operator confirmation, wrong symbol/exchange/currency, invalid or adjusted price, duplicated records, stale/ambiguous timestamps, date-only cutoff violation, post-cutoff backfill, changed bytes, path traversal/symlinks, unsafe permissions, replay/tamper, and attempts to flip provenance flags.
- Prove ordinary company Evidence/PIT admission still rejects an absent or invalid company-evidence group; operator price cannot fill it by type confusion.
- Run exact-head CI with real jobs, then independent red-team review and one locally executed sanitized receipt/replay.
- Until all applicable gates pass, existing output stays explicitly analysis-only and no formal Decision is claimed.

## 7. Non-goals

No automatic quote retrieval, broker integration, price scraping, provider API, broad price archive, change to frozen historic cases, no-source proof, legal interpretation, relaxation of C1/C2 source-fact review, or order execution.
