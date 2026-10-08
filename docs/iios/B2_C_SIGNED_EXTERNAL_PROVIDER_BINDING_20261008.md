# IIOS B2-C — Signed External Semantic Provider Binding v0.1

Date: 2026-10-08
Status: DEVELOPMENT / SIGNED-PROVIDER RECEIPT BOUNDARY

## Purpose

B2-C closes the signed external-provider receipt path permitted by the canonical B2 governance boundary:

Natural Language request
→ Research Case
→ admitted Evidence
→ SEMANTIC_PENDING
→ external signed semantic receipt
→ cryptographic provider authentication
→ B2-A deterministic semantic admission
→ SEMANTIC_ADMITTED.

## Cryptographic boundary

The external receipt is verified using Ed25519 against an allow-listed public key.

The signed payload binds:

- request_id / run_id;
- raw natural-language request SHA-256;
- case_id / cutoff;
- producer identity / version / policy;
- exact semantic artifact hash;
- exact input reference / hash lineage.

A valid JSON shape is insufficient. The external receipt must be signed by a trusted public key and match the active provider registration.

## Authority boundary

B2-C only authenticates and admits semantic output. It does not grant:

- Decision authority;
- capital permission;
- Human Approval;
- publication;
- order execution.

## Explicit non-claim

The repository conformance suite uses a deterministic fixture signing key. It proves the signed receipt protocol and end-to-end canonical lineage, but it does not claim that a production external LLM provider has been connected.

A real provider connection can satisfy this boundary by emitting a receipt under an actively registered public key.

## Next boundary

B2-D — Real Provider Adapter / Live Model Invocation + Independent Provider Replay.

