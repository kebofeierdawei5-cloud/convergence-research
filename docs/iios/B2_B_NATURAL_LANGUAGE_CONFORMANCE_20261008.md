# IIOS B2-B — Natural-Language Semantic Conformance v0.1

Date: 2026-10-08
Status: DEVELOPMENT / FIRST CONFORMANCE BATCH

## Purpose

B2-B closes the canonical entry portion of P0-LLM-001:

`User Natural Language → Request Interpreter → Request Admission Receipt → Canonical Research Orchestrator → Research Case`.

The interpreter may be an LLM or a human adjudicator, but its output is untrusted until registry and identity checks pass.

## Contract

The raw request is bound by SHA-256 before interpretation. The normalized request is hashed separately. The resulting Research Case is built and validated by the existing deterministic research-intake contract, and the case hash is bound into both the run envelope and request-admission receipt.

The canonical run cannot be advanced to CASE_CREATED by this entry without first recording REQUEST_ADMITTED.

## Conformance boundary

The batch proves:

- natural-language input must enter a versioned admission boundary;
- interpreter identity/type/version/policy is registered;
- request type is explicitly INVESTMENT_DECISION;
- the resulting case preserves PIT and current-state-substitution-forbidden semantics from Research Case v0.1;
- raw request hash, normalized request hash and case hash provide reproducible lineage;
- this entry layer has no Decision, capital or execution authority.

## Explicit non-claim

The conformance fixture is not a live external LLM. B2-B therefore does not prove provider-specific model quality or end-to-end production LLM economic reasoning.

The next requirement is to connect an actual authorized semantic producer to admitted Evidence and run the conformance case through the full canonical semantic-to-decision path, with independent red-team review.

## Next boundary

B2-C — Live Semantic Producer Binding + Natural-Language-to-Semantic-to-Decision Conformance.
