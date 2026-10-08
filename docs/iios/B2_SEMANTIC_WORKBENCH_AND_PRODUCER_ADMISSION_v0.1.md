# IIOS B2-A — LLM Semantic Workbench + Semantic Producer Admission v0.1

Date: 2026-10-08
Status: DEVELOPMENT / FIRST IMPLEMENTATION BATCH

## Purpose

B2-A closes the production boundary identified by B0 P0-LLM-002 and P0-LLM-003:

admitted evidence
    ↓
LLM Semantic Workbench
    ↓
typed semantic artifact
    ↓
producer receipt / semantic provenance
    ↓
deterministic admission
    ↓
Canonical Research Orchestrator → SEMANTIC_ADMITTED

## B2-A implemented boundary

### 1. Typed semantic artifact
The existing IIOS-LLM-SEMANTIC-ARTIFACT-0.1 envelope is now consumed through a deterministic admission kernel binding case identity, market/symbol/company, cutoff, artifact type, exact input lineage, producer identity/version/policy, and exact artifact hash.

### 2. Producer registry
Canonical semantic admission requires an active registry entry for producer_id, producer_type, producer_version and policy_version. Only LLM_SEMANTIC_PRODUCER and HUMAN_EXPERT_ADJUDICATION are authorized.

### 3. Producer receipt
The receipt binds artifact identity/type, research-stage identity, case identity, cutoff, producer identity/version/policy, exact input lineage, artifact hash, output hash and receipt hash.

Evidence provenance remains separate from semantic provenance.

### 4. Workbench boundary
LLMSemanticWorkbench only runs when the canonical orchestrator is already at SEMANTIC_PENDING. Producer output is untrusted until deterministic admission succeeds. Success advances only SEMANTIC_PENDING → SEMANTIC_ADMITTED; no decision or execution transition is performed by B2-A.

## Fail-closed cases

Reject unregistered or inactive producers, identity/version/policy mismatch, case/market/symbol/company/cutoff mismatch, exact input-lineage mismatch, forged artifact/receipt hashes, output-hash mismatch, orchestrator bypass, and non-mapping producer output.

## Explicit non-claim

A fixture producer in the regression suite is not a real external LLM provider. Therefore B2-A PASS is not evidence that Natural Language → real LLM → semantic admission → canonical Decision is proven.

The next B2 boundary is B2-B: Natural-Language Semantic Conformance + Independent Red Team.

## Acceptance

Acceptance requires dedicated tests, schema validation, compileall, orchestrator-bound workbench execution, registry-bound producer identity/version/policy, deterministic artifact/receipt hashing, exact input lineage enforcement, and no Investment Core economic semantic changes.
