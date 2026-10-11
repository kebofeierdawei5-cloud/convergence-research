# Path A — Private deterministic scenario analysis runner v0.1

- Record class: implementation contract
- Scope: analysis-only local computation from the existing normalized operator price record
- Runtime: deterministic Python; no LLM, external provider, market quote API, paid API key, Ollama, or GitHub Actions data artifact is involved.

## 1. Purpose

The operator has already completed Path A local persistence. This module turns the existing normalized private record into a reproducible scenario analysis; it does not fetch or re-enter market prices.

    python -m iios_mvp.private_scenario_analysis_v01 \
      --prices "$HOME/.iios-private/analysis-inputs/operator-attested-prices-path-a-<run-id>.json" \
      --output-root "$HOME/.iios-private/scenario-analysis"

Replace <run-id> with the filename's actual suffix produced by the already-successful Path A run. The normalized private record is the input; do not provide the original raw intake JSON in its place.

The CLI prints a small receipt/status only, not numeric quote values. It saves each content-addressed run under a new directory and never overwrites existing output. Repeating the same exact input and profile returns the same run directory after verification; changing input bytes or the versioned profile creates a different run identity.

## 2. Outputs

Each private run directory contains four files, all mode 0600 within a mode 0700 directory on macOS/Linux:

- input.json: exact copy of the normalized private Path A record; contains prices and source claims and must stay private.
- analysis.json: scenario values, probabilities, weighted terminal wealth, total/annualized price return, 15% annualized target-entry ceiling, bear-loss price ceiling and the binding conditional entry ceiling.
- report.md: Chinese human-readable analysis with assumptions and caveats.
- receipt.json: exact-byte input/profile/analysis/report hashes, with quote values and source labels redacted.

Replay a saved bundle:

    python -m iios_mvp.private_scenario_analysis_v01 \
      --replay-run "$HOME/.iios-private/scenario-analysis/patha-scenario-<analysis-id>"

A successful replay means the stored outputs match deterministic recomputation from the stored private input. These hashes do not authenticate the external price source, market-data rights, independent-review signature, forecast validity or investment performance.

## 3. Versioned analysis assumptions

The first profile set is deliberately finite and explicit:

- RC-CN-A-002001-20261009: reuses the existing PILOT-02 normalized-EPS × P/E values and stated probabilities unchanged.
- RC-CN-A-605016-20261009: reproduces the prior analyst-only EPS × P/E scenario values (Bear 0.80 × 17, Base 1.10 × 22, Bull 1.30 × 25) and probabilities (0.25 / 0.50 / 0.25). These have not been accepted as an independent Forecast; probabilities are uncalibrated and the target multiples remain assumptions.

For each profile, the report names the profile version and assumption class. Scenario output is a sensitivity calculation, not an admitted Forecast or a formal IIOS valuation. Cash distributions are set to zero because the selected profiles do not contain an independently supported forward-distribution forecast.

The calculation keeps the v0.3 concepts distinct:
- expected terminal wealth and expected total return;
- expected annualized return over the profile horizon (default H=1Y);
- the price ceiling required for the 15% annualized target;
- a separately declared maximum-bear-loss constraint;
- the binding conditional entry-price ceiling from the two price constraints.

For the current initial profiles the horizon is H=1Y. Probabilities, EPS and multiples are explicit assumptions, not learned probabilities or market consensus.

## 4. Fail-closed and privacy contract

The runner rejects malformed or duplicate-key JSON, unsupported Case/profile combinations, mismatched symbol/exchange, non-CNY or adjusted prices, invalid/misaligned dates, a known-at timestamp at/after the overlay cutoff, false/changed scope, any authority flag that is not explicitly false, invalid probabilities, and unknown scenario assumptions.

It also rejects input/output/bundle paths under the public repository, symlink entrypoints, unsafe existing output directories, open output permissions, output tampering, and nondeterministic replay. An existing content-addressed run is never rewritten; if it no longer verifies, the runner returns BLOCKED.

Every result explicitly retains:
- OPERATOR_ATTESTED_MARKET_DATA;
- source origin, source vintage, source-use rights, canonical price admission, formal Evidence/PIT admission, formal Forecast/Valuation admission, formal Decision, Machine Publication, complete Run Receipt and execution authority as false;
- frozen base Case not mutated;
- company evidence not revalidated as one unified PIT case to the price-overlay cutoff.

No private numeric prices, source labels or raw source bytes belong in Git, PRs, CI logs or CI artifacts.

## 5. Acceptance

The dedicated CI workflow compiles the package and runs the scenario runner tests plus the existing Path A intake tests. Acceptance requires deterministic two-case calculations, exact probabilities summing to one, replay success, input/output tampering detection, private file modes, content-addressed new runs, no overwrite, and all formal authority flags remaining false.
