# IIOS B0 — LLM Canonical Execution Governance Boundary Freeze

Date: 2026-10-07
Status: **GOVERNANCE BOUNDARY FROZEN / READY FOR B1**
Scope: IIOS Investment Core / natural-language research execution
Repository: `kebofeierdawei5-cloud/convergence-research`
Canonical baseline: `0839dfe972f2e1451a9cc8a8ce3f909020b8b784`

## 1. Purpose

B0 converts the 2026-10-07 P0 LLM red-team findings into a canonical governance boundary. It does **not** change Investment Core economic formulas, decision semantics, or production calculation logic.

The boundary being frozen is the separation between:

```text
explicit / deterministic standard
        -> Code / Script

ambiguous / semantic / deep reasoning
        -> LLM / expert reasoning

LLM semantic output
        -> typed artifact + provenance
        -> deterministic admission
        -> canonical state
```

Authority is therefore separated as:

```text
LLM       = Reasoning Authority
Code      = Rule / Permission Authority
Human     = Capital / Approval Authority
```

No layer may silently assume another layer's authority.

## 2. P0 findings converted into governance requirements

### P0-LLM-001 — Canonical Investment Execution Path Bypass

**CONFIRMED.** A natural-language investment request can currently obtain free-form analysis without being forced through one complete canonical research session.

**Frozen rule:** a user request intended to produce an IIOS investment decision MUST enter the Canonical Research Orchestrator. A response produced outside that path is never a canonical IIOS investment decision.

### P0-LLM-002 — Missing Semantic Producer Boundary

**CONFIRMED.** Current schemas/admissions validate structured semantic objects, but the production path does not force deep-reasoning outputs through an authorized LLM semantic producer boundary.

**Frozen rule:** the following objects require an explicit semantic producer boundary before canonical admission:

- Reality interpretation
- Trust
- Quality
- Thesis
- Value Drivers
- Independent Forecast reasoning
- Valuation model proposal / rationale
- Market Implied Expectation interpretation
- Risk interpretation
- Positioning interpretation

### P0-LLM-003 — Admission Producer Authenticity Gap

**CONFIRMED.** Evidence provenance is not the same thing as semantic provenance.

**Frozen rule:** a semantic artifact is not canonically admissible merely because its evidence IDs, schema, hash, cutoff and identity are valid. The admission contract MUST also bind the authorized semantic producer, producer type/version, research-stage identity and the relevant input/output lineage. Self-declared external JSON is not canonical semantic evidence.

### P0-LLM-004 — Pilot Acceptance Category Error

**CONFIRMED.** PILOT-01~04 primarily prove deterministic lifecycle behavior from preconstructed semantic inputs. They do not prove natural-language request → LLM reasoning → semantic admission → canonical decision.

**Frozen rule:** prior pilot PASS results MUST NOT be interpreted as proof that the real LLM research path is canonical. Future pilot acceptance must include a real natural-language entry test.

## 3. Canonical execution boundary

The canonical product path is frozen as:

```text
User Natural-Language Request
        ↓
Canonical Research Orchestrator
        ↓
Research Case / Run Envelope
        ↓
Evidence Acquisition + Evidence Admission
        ↓
LLM Semantic Workbench
        ↓
Typed Semantic Artifacts + provenance
        ↓
Deterministic Admission / consistency checks
        ↓
Canonical State
        ↓
Decision Kernel
        ↓
Decision Admission
        ↓
Human Approval
        ↓
Machine Publication
        ↓
Human Report
        ↓
Monitoring / Validation / Replay
```

No stage may be bypassed by a convenience CLI, direct function call, ad-hoc notebook, or free-form assistant response when the declared output is a canonical investment decision.

## 4. Run Receipt boundary

A canonical run MUST eventually be represented by an `IIOS_RUN_RECEIPT` binding, at minimum:

```text
run_id
case_id
market
symbol
cutoff / as_of
engine_version
research_case_hash
evidence_manifest_hash
semantic artifact hashes
forecast admission hash
valuation admission hash
return / risk / portfolio hashes
decision admission hash
decision revision
publication hash
report hash
```

A missing or invalid complete run receipt means:

```text
NON-CANONICAL ANALYSIS / BLOCKED
```

It MUST NOT be upgraded to canonical merely because a report is readable or a downstream deterministic calculator passes.

## 5. Evidence vs semantic provenance

The governance distinction is explicit:

```text
Evidence provenance
  proves where an input came from and when it was knowable.

Semantic provenance
  proves who/what reasoning producer created the interpretation,
  under which policy/version, from which admitted inputs,
  and with which exact output bytes.
```

Therefore:

```text
valid evidence provenance
≠
valid semantic provenance
```

Both are required where the output is decision-relevant.

## 6. Required fail-closed behaviors

The repaired system MUST block or downgrade to non-canonical analysis when any of the following holds:

- natural-language request bypasses the Canonical Research Orchestrator;
- required semantic artifact has no authorized producer receipt;
- semantic artifact has unresolved evidence / cutoff / identity conflicts;
- independent forecast uses current market price as a hidden input;
- material business segments are missing or cannot support reliable SOTP mapping;
- order / backlog / revenue overlap is materially unknown but is treated as certain;
- unit or currency errors are detected or cannot be resolved;
- Market Implied Expectation is not identifiable/stable enough to support the claimed inference and the model nevertheless forces a single point;
- report/publication has no complete canonical upstream lineage or run receipt;
- external structured output declares itself safe/canonical without an authorized producer boundary.

## 7. Authority and approval boundary

The following responsibilities are frozen:

| Layer | Authority | May decide / produce | May not do alone |
|---|---|---|---|
| LLM | Reasoning | Interpret evidence; propose semantic states; forecast; propose valuation; explain uncertainty | Grant canonical decision authority; authorize capital execution |
| Code | Rules / Permission | Validate schema, provenance, consistency, thresholds, state transitions, permissions, receipts | Infer business meaning that requires deep semantic judgment |
| Human | Capital / Approval | Final approval, portfolio constraints, override, execution choice | Turn non-canonical analysis into canonical evidence without explicit adjudication |

The human remains the final capital authority. Automatic ordering remains disabled.

## 8. Governance effect on existing components

The following existing components are treated as supporting infrastructure, not as proof that the missing semantic producer boundary already exists:

- existing semantic schemas / admissions;
- canonical Independent Forecast validation;
- deterministic Value Core / valuation calculators;
- Risk / Portfolio contracts;
- Decision Admission;
- Machine Publication;
- Human Report;
- PILOT-01~04 acceptance evidence.

C2 Human Report is not the root cause of the Haomai incident. It is a downstream projection/QA boundary and cannot independently validate upstream economic reasoning.

Existing MIE capability remains reference/optional infrastructure until its role is explicitly adjudicated in later batches. The valuation role correction is reserved for B4 and MUST NOT be silently implemented in B0.

## 9. B0 prohibited changes

B0 MUST NOT:

- alter investment formulas or return/risk semantics;
- redefine existing normative economic concepts without a versioned semantic adjudication;
- make MIE a new universal BUY gate;
- claim current pilot evidence proves real LLM research conformance;
- enable automatic trading/order placement;
- treat a human-authored or externally supplied JSON object as canonical semantic state without producer provenance;
- merge B1/B2/B3 implementation work under a B0 documentation change.

## 10. B1 unlock criteria

B1 may start from this frozen boundary and must produce a versioned successor design. B1 acceptance requires explicit decisions for:

1. the Canonical Research Orchestrator interface and stage machine;
2. the typed Semantic Artifact contract and required evidence/provenance fields;
3. authorized LLM semantic producer identity/versioning;
4. semantic admission and producer-authenticity rules;
5. `IIOS_RUN_RECEIPT` minimum schema and canonicality test;
6. the exact boundary between semantic reasoning, deterministic validation and human override;
7. a natural-language-to-canonical conformance test plan using the Haomai failure mode as a regression case.

B1 MUST be versioned as a successor governance/design artifact; this B0 record is not rewritten to retroactively claim B1 semantics.

## 11. Acceptance

B0 is considered complete when:

- exact canonical baseline is recorded;
- P0 findings are explicitly tied to normative governance rules;
- canonical research execution path is frozen;
- semantic producer boundary is frozen as a mandatory architectural requirement;
- evidence provenance and semantic provenance are explicitly separated;
- run-receipt canonicality rule is recorded;
- authority boundaries are explicit;
- B0 changes no production investment semantics;
- B1 is the only next semantic implementation gate.

## 12. Result

**B0 Governance Boundary Freeze = PASS**

Canonical baseline: `0839dfe972f2e1451a9cc8a8ce3f909020b8b784`

P0 audit source artifact:
`IIOS_P0_LLM_CANONICAL_EXECUTION_AUDIT_20261007.md`

P0 audit SHA-256:
`b70d83e9920e4ef9b2b879e727fa427d057b2ffa96cf6c53ddd73329a1705ea1`

Next development gate:

```text
B1 — Canonical Research Orchestrator + Semantic Contract Design
```

B1 may proceed only on a successor branch/commit from the canonical B0 result.