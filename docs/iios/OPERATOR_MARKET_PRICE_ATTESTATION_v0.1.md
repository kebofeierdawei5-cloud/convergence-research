# IIOS Operator-Attested Market Price v0.1

Status: Implementation candidate under review. This is a narrow manual-input policy, not a claim that a publisher's original data has been independently verified.

## Operator instruction

When a required market-price observation is missing, ask the operator directly for the security, observation date, and price. After the operator supplies the value, do not perform a second web search or source-page audit unless the operator explicitly requests it.

## Evidence class and limits

The resulting evidence uses OPERATOR_ATTESTED_MARKET_DATA and must be restricted to market_price.* fields. It requires an explicit operator attestation that the value was available by a declared known_at no later than the case cutoff, and the observation date must bind to the security and case. The value is recorded in a private JSON artifact whose exact bytes are SHA-256 hashed.

The hash verifies only the operator-attestation artifact. It does not verify the publisher's source bytes, prove the publisher's exact publication time, or convert the evidence class into SOURCE_VINTAGE_VERIFIED. The evidence must retain:
- operator_confirmed=true;
- secondary_web_audit_performed=false;
- original_vendor_bytes_received=false;
- the exact case, market, symbol, company, observation date, close, currency, source locator, known-at basis and attestation time.

This path is an explicit, operator-approved provenance class. It is not available for financial statement facts, corporate events, or other evidence types.

## Private local workflow

    python tools/iios_operator_market_price_attestation_v01.py \
      --case-id RC-CN-A-002001-20261009 \
      --market CN-A \
      --symbol 002001 \
      --company '浙江新和成股份有限公司' \
      --cutoff-date 2026-10-09 \
      --observation-date 2026-10-08 \
      --close-price "$OPERATOR_SUPPLIED_CLOSE" \
      --currency CNY \
      --source-ref 'OPERATOR-PROVIDED:<source locator>' \
      --out-dir "$PRIVATE_IIOS_ROOT/c2-market-price-attestation" \
      --confirm-operator-attestation \
      --confirm-known-by-cutoff

The tool does not access the network. It writes the value-bearing attestation, evidence record, and raw-artifact declaration into a private directory with restrictive local permissions. Never commit this directory or upload it as a public GitHub Actions artifact.

Then rerun C2 locally against the pinned Run #8 source archive and the private bundle:

    python tools/route_a_c2_adjudicate.py \
      --archive-dir "$PRIVATE_RUN8_ARTIFACT_DIR" \
      --out-dir "$PRIVATE_IIOS_ROOT/c2-successor-run" \
      --operator-market-price-attestation-dir "$PRIVATE_IIOS_ROOT/c2-market-price-attestation"

The Core/PIT validator remains unchanged. Only the provenance classification is extended; the operator attestation can cover the required price group if its case/date/cutoff bindings and exact attestation bytes pass. The C2 source review for the 13 official filing facts is an independent gate.

## Blockers and non-claims

- This class must not be used to claim original vendor bytes or independent source-vintage verification.
- If observation date, known-at, security binding or exact artifact hash fails, keep the case blocked.
- A Core/PIT pass does not create formal signed Evidence admission, production Host acceptance, Decision, Publication, complete Run Receipt, or execution authority.
- The current GitHub Actions workflow deliberately does not accept the real quote as an input; its only price fixtures are synthetic tests. The real value is used only through the private local workflow.
