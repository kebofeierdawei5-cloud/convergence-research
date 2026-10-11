# Execution-first pivot: Local Single-User MVP

- Date: 2026-10-11
- Decision class: product execution priority, not a change to frozen investment semantics
- Authority: owner direction in the current conversation; recorded into `docs/PROJECT_STATE_INDEX.md` and the active batch plan
- Baseline: canonical main at `c857dc5f8097a12317c07ab9ef56fae5f3bb39fc`
- Status: **ACTIVE DEVELOPMENT PRIORITY**

## Decision

IIOS development now prioritizes finishing and actually running one complete local, single-user investment-research workflow. The recent implementation sequence over-weighted additional adversarial/integrity cases and infrastructure diagnostic work while the user still lacked a complete everyday run from candidate input through a useful report.

The immediate goal is not to prove the most hostile imaginable tampering scenario. The goal is to let the owner select one A/H-listed company and run the core research decision workflow locally, inspect the result, discover real defects and iterate from observed use.

## Keep these minimum safeguards

The pilot must preserve the following because they protect the investment result itself:

- Explicit candidate, market, symbol, as-of/cutoff, position context and manually entered current price.
- Source references and known-at/observation dates when available; raw source bytes and hashes when available without unsafe collection or use.
- Explicit distinction between source-verified data and operator-attested/manual inputs.
- UNKNOWN / missing / conflict / stale states remain visible; no invented values or silent completion.
- Deterministic calculations, schema validation and basic input-to-output binding.
- Human-readable Chinese report plus machine-readable output; expected return / entry range, risk, thesis-break conditions and review triggers.
- Human approval remains separate from the AI proposal; automatic trading stays disabled.
- A simple private run record and replay or recomputation check appropriate to the pilot.

These controls are the floor. They are not an invitation to create more governance subsystems before the user can run the product.

## Explicitly stop expanding these items before the first complete run

- Do not add more MP-3 tamper permutations, signature escalations or stage-bypass red-team cases unless a demonstrated defect directly blocks the pilot or can silently produce a misleading investment result.
- Do not treat the P0 GitHub Actions zero-job incident as a dependency of local use. Keep the issue open as a diagnostic backlog item; it is not a reason to hold the local pilot.
- Do not require GitHub Actions, a remote production Host, paid data services, a paid LLM API key, local-model installation, multi-user services or deployment infrastructure for the pilot.
- Do not duplicate the core, create a second decision engine/store/report pipeline, or turn a local workflow into a security-platform rewrite.

## Two assurance levels — do not conflate them

### Level 1: local pilot run — build this first

The local path may use operator-supplied source files, manually entered current price, and an explicitly identified free/manual AI handoff. Such AI output is labelled `PILOT_NON_CANONICAL` / provisional, not source-authenticated and not a formal semantic admission. This permits a real workflow and report to be exercised without claiming provenance assurance that was not established.

A pilot report should still calculate with the existing deterministic core where applicable and plainly disclose missing inputs / limited evidence. It must not label a provisional proposal as a formal canonical Decision, claim a complete canonical Run Receipt where none exists, or enable trading.

### Level 2: formal canonical decision — hardening follows the pilot

Formal Evidence/PIT admission, unresolved source-use rights, independently authorized signatures, trusted producer identity/model lineage, canonical Decision Admission and a formally complete Run Receipt remain required for their existing claims. They remain blockers **to the formal/canonical status**, not to developing and exercising a clearly segregated provisional research workflow.

No existing guard is to be bypassed or relabelled. If the only available route is analysis-only, the output must say so clearly and still be useful for testing the product.

## Next execution sequence

1. **Freeze scope now.** Pause residual MP-3 hardening and P0 workflow diagnosis; preserve their current issues and existing tests.
2. **Map the existing runnable path once.** Reuse the current intake, evidence/PIT, company-economic-core, valuation/MIE/expectation-gap, risk/positioning, report and local persistence components. Record the actual missing joins, not hypothetical threat cases.
3. **Implement the smallest complete local entry.** One launch/command should accept candidate, cutoff, current price, position constraints, official source files / source references and structured AI-analysis input. No paid API key or local LLM requirement.
4. **Complete the provisional vertical slice.** Run available company facts through Reality / Quality / Thesis / Value Drivers / Forecast assumptions / Valuation / MIE and expectation gap / Risk and Positioning / decision proposal. Missing components stay UNKNOWN and must constrain the recommendation.
5. **Produce and review the output.** Generate a Chinese human report, a machine-readable record, and a private pilot run receipt; replay/recompute once. Keep all private prices and raw evidence outside Git.
6. **Run it on the user's Mac with one real company and inspect the actual result.** The actual local bundle is evidence of usability; record operator-run facts separately from independently verified CI facts. Fix only blockers exposed by the run.
7. **After the run, iterate.** Prioritize correctness, missing evidence, report usability, startup friction and repeatability based on observed use. Resume formal admission and deeper adversarial expansion when they solve a demonstrated risk or are needed to promote the provisional path to canonical status.

## Acceptance criteria for the first complete local run

- Starts from a user-selected A/H company rather than only one of two hard-coded scenario profiles.
- Requires no paid market-data API, paid LLM key, GitHub Actions runtime or local-model installation.
- Uses the existing IIOS investment semantics and deterministic components rather than a parallel hand-built calculator.
- Outputs the actual core modules, action/provisional action, target entry zone, expected annualized return versus the 15% hurdle, key assumptions, risk, thesis breaks, and reassessment triggers; displays UNKNOWN and evidence gaps.
- Makes manual price/source assurances and the provisional/canonical boundary unmistakable.
- Persists privately and reproduces its own output or reports the precise reason reproducibility failed.
- Never places orders; capital execution and any formal human approval remain out of scope for the first pilot unless a later explicit decision authorizes them.

**Priority rule:** a real end-to-end user run and the defects it reveals outrank additional speculative hardening. Preserve current minimum safety semantics; defer the rest until after the pilot.
