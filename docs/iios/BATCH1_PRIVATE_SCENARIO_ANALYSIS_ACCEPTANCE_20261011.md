# Batch 1 — Private Path A scenario analysis acceptance and local handoff

- Status on canonical main after PR #356: IMPLEMENTED / EXACT-HEAD CI PASS / ANALYSIS-ONLY
- Merge commit: 4ccb8cf89084d7299dfa8d0774cce97009eb5b54
- Dedicated exact-head test run: 38143577446
- Dedicated post-merge workflow: 38143646589
- User-host runtime status: NOT YET OBSERVED; operator-local run remains the next product-acceptance action.

## Delivered

The existing normalized private Path A file can now be consumed by a single deterministic local command, without reacquiring quotes. The versioned profile set covers the existing cases RC-CN-A-002001-20261009 and RC-CN-A-605016-20261009.

Each content-addressed private bundle contains input.json, analysis.json, report.md, and receipt.json. Repeating the exact input reuses the bundle after replay verification; changing input bytes creates a new ID. Private price values and claimed source labels are absent from receipt.json but remain in the private input, analysis and report.

## Observed CI evidence

- The dedicated workflow compiled the package and ran 40 tests across the scenario runner and the existing Path A intake suite; all passed.
- The 17 checks visible on the exact PR head were all SUCCESS.
- The post-merge dedicated workflow on main is SUCCESS.
- Tests cover two-case output, weighted terminal wealth, the separate 15% entry ceiling and bear-loss ceiling, replay, tamper rejection, permissions, exact probabilities, cutoff semantics, case/profile binding, and non-escalation of formal authority.

These prove the deterministic code path and its CI contract. They do not prove that the operator's Mac has run/replayed this scenario bundle.

## Expected analysis semantics from current profile versions

These are scenario calculations only, not canonical forecasts or formal decisions.

- 新和成 (002001): expected terminal wealth ¥31.185/share; 15% target-entry ceiling about ¥27.12; existing profile's 25% bear-loss ceiling ¥26.60; binding conditional entry ceiling ¥26.60; operator-attested price ¥26.58, only ¥0.02 below that ceiling.
- 百龙创园 (605016): expected terminal wealth ¥23.625/share; 15% target-entry ceiling about ¥20.54; provisional 25% bear-loss ceiling about ¥18.13; binding conditional entry ceiling about ¥18.13; operator-attested price ¥20.28 is about ¥2.15 above that ceiling.

The probabilities are not calibrated. The 605016 EPS/P-E profile is an analyst scenario, not an admitted Independent Forecast. The 002001 profile reuses existing PILOT-02 assumptions without change. Neither result is a BUY/ADD/NO-BUY Decision.

## Operator run instructions

The one-click package is a separately generated local launcher: it asks the operator to choose an existing normalized record from ~/.iios-private/analysis-inputs, downloads the two canonical Python modules from the exact merged commit, verifies their Git blob SHA-1 values, then runs the analysis into ~/.iios-private/scenario-analysis. It does not upload private data or create a formal Decision.

For repository checkout users, the equivalent command is:

    python -m iios_mvp.private_scenario_analysis_v01 \
      --prices "$HOME/.iios-private/analysis-inputs/operator-attested-prices-path-a-<run-id>.json" \
      --output-root "$HOME/.iios-private/scenario-analysis"

After the first run, use the returned analysis ID and directory path to replay:

    python -m iios_mvp.private_scenario_analysis_v01 \
      --replay-run "$HOME/.iios-private/scenario-analysis/patha-scenario-<analysis-id>"

Do not copy input.json into chat or GitHub. It contains private prices and claimed source labels.

## Governance boundary

All source-origin, source-vintage, data-use-rights, canonical price admission, formal Evidence/PIT, formal Forecast/Valuation Admission, Decision, Publication, complete Run Receipt and execution flags remain false. The overlay does not mutate frozen Cases or prove full company evidence PIT at the price-only overlay cutoff.

The C1/605016 signer + SSE market-data rights gate and C2/002001 independent fact/use signature are not closed by this batch and continue in parallel.

The separate P0 incident workflow anomaly remains OPEN: runs 38143107853 and 38143645878 ended failure with zero jobs. No test assertions were executed in those runs. This is not evidence of a failed application test, and not evidence of PASS.
