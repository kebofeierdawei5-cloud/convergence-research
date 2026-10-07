# IIOS M1.2-FM04 Second Red-team Audit — 2026-10-07

Status: BLOCKED / REMEDIATION REQUIRED

Audit target: canonical main a4e9ac8cee7637b848a719b51695f169db97b385

Executive verdict

FM04 is not safe to promote to research-policy expansion until result integrity, empirical-evidence semantics, oracle independence and research-design sufficiency are remediated or explicitly adjudicated.

Positive boundaries remain strong: PIT, UNKNOWN, provenance, capability isolation, current-price separation and non-confirmatory posture.

Findings

RT-01 — RESULT_ARTIFACT_INTEGRITY_GAP — P0 BLOCKER
The independent FM04 audit does not recompute or validate conditional_performance. It validates selection evaluations but not conditional-group identity, sample membership, actual IDs, model-input IDs or reported conditional metrics. The result schema also permits a much weaker representation than the underlying research object.
Required: independently recompute the full conditional-performance matrix; bind each group to exact origins, state rows, actual records and model inputs; add full-result hash and run manifest; mutation-test every result section.

RT-02 — INPUT_BINDING_TAMPER_GAP — P0 BLOCKER
The result contains multiple upstream bindings, but the independent audit does not independently compare all declared hashes against the actual repository bytes. State snapshot binding is strong, while driver-history, research-plan, candidate-space, purity-boundary and outer-lock bindings are not all revalidated from the result.
Required: verify every declared input binding against exact bytes or exact Git object identity and bind the result to exact code revision and CI run.

RT-03 — ZERO_EMPIRICAL_OUTER_OBSERVATIONS — P0 RESEARCH BLOCKER
The accepted FM04 run has 79 conditional groups but zero empirical outer observations. Therefore there was no actual conditional model-error comparison and no OOS model-selection evaluation.
This is stronger than a generic N-insufficient finding. The current result demonstrates structural group construction plus fail-closed selection, not conditional forecast-performance evidence.
Required: separate group definition, empirical conditional performance and selection eligibility as distinct result objects.

RT-04 — AUDITOR_ORACLE_NON_INDEPENDENCE — P1 HIGH
The independent audit reimplements the same four forecast formulas and metric logic as the executor. Shared defects can therefore reproduce as PASS.
Required: independent known-answer fixtures, independently calculated reference cases, or a materially different reference implementation; add mutation tests that alter executor logic and require oracle rejection.

RT-05 — OVERCONDITIONED_SELECTION_DESIGN — P1 RESEARCH-DESIGN BLOCKER
The selection unit conditions on security, driver, horizon, state dimension, state value and outer origin. With one security and only 11 frozen origins, the design is extremely sparse. The observed zero-selection result is a direct warning that the current selection granularity is not supported by the sample.
Required: FM05 must freeze the estimand and sample unit before any threshold relaxation, pooling or state regrouping.

RT-06 — DATA_QUALITY_SEMANTIC_OVERLOAD — P1
DATA_QUALITY is treated as a Forecastability State dimension even though it primarily describes evidence availability and control eligibility rather than an economic regime.
Required: formally classify it as a research-control variable or explicitly define an economic interpretation. Do not silently alter it later.

RT-07 — MODEL_FAMILY_IDENTITY_SEAM — P1
FM00 freezes model families TREND_LOG_LINEAR and MEAN_REVERSION_YOY while FM04 uses parameterized instances TREND_LOG_LINEAR_8Q and MEAN_REVERSION_YOY_8. The candidate-space parameter section suggests this can be legitimate, but the identity relation is not explicit enough for strong governance.
Required: model_family + parameterization + model_instance_id, with instance-to-family resolution checked against the frozen candidate-space.

RT-08 — TEST_ASSERTION_SWALLOWING — P1
The FM04 unit test suite contains a blanket exception that can swallow its own assertion or unexpected runtime failure.
Required: remove blanket swallowing and catch only the explicitly expected unavailable-input condition.

RT-09 — RESULT_ARCHIVE_MISSING — P1
The accepted FM04 output is generated in CI temporary storage and is not itself preserved as a canonical exact research artifact.
Required: persist the exact result, run manifest, result SHA-256, input hashes, code SHA, CI run ID and environment.

RT-10 — CANONICAL_DOCUMENT_DRIFT — P1
The canonical state documentation contains inconsistent M1.2 sequencing, including residual FM03 endpoint language after FM04. STATUS also retains an outdated FM04 next-boundary statement.
Required: canonical sequence must be exactly FM00 → FM01 → FM02 → FM03 → FM04 → FM05.

Adjudication

OVERALL VERDICT: BLOCKED FOR FORWARD RESEARCH-POLICY EXPANSION

FM04 may remain canonical as limited PIT-safe conditional-backtest plumbing, but it must not be interpreted as evidence of State predictive validity, model superiority or model-routing readiness.

Correct path:
FM04 remediation
→ FM05 Scope / Estimand / Sufficiency Freeze
→ only then decide whether broader data research is justified.

Explicit no-go until remediation:
- do not lower N=3;
- do not merge state values from observed results;
- do not delete inconvenient states or origins;
- do not add model families;
- do not tune thresholds from FM04 outcomes;
- do not promote conditional groups to predictive evidence;
- do not build a production router.