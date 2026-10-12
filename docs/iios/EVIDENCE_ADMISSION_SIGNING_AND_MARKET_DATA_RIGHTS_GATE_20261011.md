# IIOS formal Evidence/PIT signature and market-data rights gate

- Date: 2026-10-11
- Type: implementation contract and actionable licensing workflow
- State: IMPLEMENTATION CONTRACT; NO SIGNER TRUSTED; NO EXCHANGE PRICE RIGHTS GRANTED; NO CASE FORMALLY ADMITTED
- Runtime constraint: **No local LLM, Ollama, model installation, provider endpoint, or model API is required for this workstream.** Admission is deterministic code plus an explicitly authorized human signer.

## 1. Decision

Treat cryptographic sign-off and source-use rights as two independent gates:

1. A trusted signer approves a particular immutable candidate and rights decision.
2. The rights record cites an applicable license/permission instrument whose exact bytes are hashed. A valid signature does not itself create permission.
3. A price record from an exchange is not formally admitted merely because it can be fetched from an official HTTPS URL, is publicly visible, or has a SHA-256.
4. A manual/operator-attested price may remain available as a clearly labelled non-canonical working input, but it cannot be promoted by this gate to source-vintage-verified admission.
5. Missing rights evidence or an unregistered signer produces a fail-closed result. Do not hand-edit booleans or treat a self-hash as a signature.

## 2. Cryptographic signing contract

The implementation is in `iios_mvp/canonical_signed_evidence_admission_v01.py`. It reuses the established Core Evidence/PIT validator and Ed25519 primitive but **must not reuse the provider/runtime key**.

### Signed payload binds

- Case id, exchange/market, symbol and cutoff;
- SHA-256 of the exact manifest file bytes;
- SHA-256 of the exact source-use-rights adjudication file bytes;
- SHA-256 of the exact permission instrument bytes (for an ADMIT decision);
- source class, rights status, allowed use scope and required signer roles;
- decision (`ADMIT` or `BLOCK`) and the payload creation timestamp.

The signature is Ed25519 over a canonical JSON representation of payload + signer key id + signing timestamp. Verification rechecks the exact files, the Core/PIT manifest and raw artifacts for ADMIT, permission scope, signer role/scope/validity/revocation, and the signatures. Multiple signatures are supported.

### Trust enrollment and key custody

The canonical trust registry is `evidence/authority/IIOS_EVIDENCE_ADMISSION_SIGNER_REGISTRY_v01.json`. It is intentionally empty at first release. An arbitrary public key inside a candidate cannot trust itself.

- Generate a dedicated Evidence Admission keypair using the CLI in the module. This is ordinary cryptographic key management, **not** a local-LLM setup step.
- The private key must remain outside the repository in an owner-controlled directory with mode 0600. Never commit it, paste it into chat, place it in GitHub Actions artifacts, or reuse a Provider key.
- Only the public key may be submitted for explicit review and merged into the trust registry, with signer id, roles, case scope, validity interval and revocation status.
- A key can sign only within its registered role and case scope. A role name self-written into the case record is not authorization.
- Independent fact/use review must use a separate trusted signer key id with the `INDEPENDENT_REVIEWER` role. One key holding both roles cannot substitute for two distinct signers.
- A signature on a `BLOCK` decision is a formal, auditable refusal; it is not an admitted Evidence/PIT record.

### CLI skeleton

Run from a canonical checkout with the Python project dependencies already installed. No LLM/model is involved.

```bash
python -m iios_mvp.canonical_signed_evidence_admission_v01 generate-keypair \
  --private-key-out "$HOME/.iios-private/keys/evidence-admission-ed25519.key" \
  --public-key-out "$HOME/.iios-private/keys/evidence-admission-ed25519.public.json"
```

The key-generation command refuses to overwrite existing files and refuses a private-key path inside the repository. Register only the public key after an explicit human authorization step. The empty registry means no signature is trusted until that step occurs.

Before any key is added to the trusted registry, prepare a private enrollment proposal for review. Generate the public/private keypair in a private local folder, then run the proposal command (replace role, scope, label and dates with the explicitly approved values):

```bash
python -m iios_mvp.canonical_signed_evidence_admission_v01 prepare-enrollment-request \
  --public-key "$HOME/.iios-private/keys/evidence-admission-ed25519.public.json" \
  --signer-key-id "OWNER-C1-20261012" \
  --display-label "owner-admission-signer" \
  --role EVIDENCE_ADMISSION_SIGNER \
  --case-scope "RC-CN-A-605016-20261009" \
  --valid-from "2026-10-13T00:00:00+08:00" \
  --authorization-note "Owner-approved identity/scope; complete only after explicit review" \
  --out "$HOME/.iios-private/keys/owner-admission-enrollment-request.json"
```

The output is a mode-0600, local-only request with status \`PROPOSED_NOT_TRUSTED\`. It includes only the public key and proposed role/scope—not the private key—and explicitly records that no trust-registry mutation occurred. It rejects wildcard case scopes and combined admission/reviewer roles. The request is not an authorization: the owner must separately approve the identity, scope and validity, and the canonical registry remains unchanged until that approval is intentionally applied. Prepare a separate request and a separate key for \`INDEPENDENT_REVIEWER\`; that signer must not be the same key id as the admission signer.

### Prepare a rights adjudication draft (always UNKNOWN by default)

For a specific Case and source class, the CLI can now create a private rights-record draft. This helper deliberately does not infer permission from public access, a URL, a downloaded file or a matching hash. Even when an exact candidate instrument is supplied, it only computes a candidate byte hash and leaves the canonical permission fields unset.

~~~bash
python -m iios_mvp.canonical_signed_evidence_admission_v01 prepare-rights-draft \
  --case-id "RC-CN-A-605016-20261009" \
  --source-class EXCHANGE_MARKET_DATA \
  --request-note "Written permission for private storage, local computation and internal display is still pending." \
  --out "$HOME/.iios-private/rights/RC-CN-A-605016-20261009-rights-draft.json"
~~~

For a PUBLIC_COMPANY_DISCLOSURE case such as C2, the helper adds INDEPENDENT_REVIEWER to the required signer roles. If a candidate permission/terms file already exists outside the repository, pass --candidate-permission-evidence with its local path; the file stays local and only its SHA-256 is recorded as a candidate hash.

The draft output is mode 0600 and contains status UNKNOWN, basis_kind UNKNOWN, no allowed uses, no admitted permission instrument and formal_admission_authorized false. Human review must establish whether the instrument is authentic/applicable and exactly which uses and retention scope it grants; source-use authorization and trusted signer enrollment remain independent gates.

After the relevant rights record and exact permission bytes exist, create/add a signature:

```bash
python -m iios_mvp.canonical_signed_evidence_admission_v01 sign \
  --manifest "$PRIVATE_CASE/manifest.json" \
  --raw-root "$PRIVATE_CASE/raw" \
  --rights-record "$PRIVATE_CASE/rights-adjudication.json" \
  --permission-evidence "$PRIVATE_CASE/rights-instrument.pdf" \
  --registry "evidence/authority/IIOS_EVIDENCE_ADMISSION_SIGNER_REGISTRY_v01.json" \
  --signer-key-id "REPLACE_WITH_REGISTERED_KEY_ID" \
  --private-key "$HOME/.iios-private/keys/evidence-admission-ed25519.key" \
  --signed-at "YYYY-MM-DDTHH:MM:SS+08:00" \
  --decision ADMIT \
  --out "$PRIVATE_CASE/signed-admission.json"
```

For an additional independent signature, pass the existing envelope with `--existing-envelope`, use the independent reviewer's registered key id and key, and write a new output path. Run the `verify` subcommand after all required signers have signed. These are illustrative commands: the current empty trust registry intentionally makes them fail closed until a public key is formally registered.

## 3. Rights evidence policy (must be data-class-specific)

The code accepts only the following bases for an `ADMIT`:

| Source class | Allowed rights basis | Not sufficient by itself |
|---|---|---|
| `EXCHANGE_MARKET_DATA` | `EXPLICIT_WRITTEN_PERMISSION` or `LICENSED_VENDOR_CONTRACT` | Public HTTPS access, a 200 response, hash match, website terms that do not expressly scope market data use |
| `VENDOR_MARKET_DATA` | `LICENSED_VENDOR_CONTRACT` or `EXPLICIT_WRITTEN_PERMISSION` | User recollection, broker screen capture, or an unverifiable quote |
| `PUBLIC_COMPANY_DISCLOSURE` | `OFFICIAL_TERMS_REVIEWED` or `EXPLICIT_WRITTEN_PERMISSION` | The fact that the PDF can be downloaded, without retaining its exact terms and documenting the use scope |
| `OPERATOR_ATTESTED_MARKET_DATA` | **No source admission basis in this implementation** | Attestation cannot be upgraded to source-vintage verification |

An `ALLOWED` rights record must have a hashed permission instrument, a non-empty instrument id, and explicit scope including `PRIVATE_STORAGE`, `LOCAL_COMPUTATION`, and `INTERNAL_DISPLAY`. If rights are limited to viewing, or prohibit retention/computation, those uses are not inferred.

The license/permission is scoped to: single-user non-commercial personal investment research; manually selected A/H companies; private local storage; local calculations and internal display; no public market-data display, third-party access, publication of raw data, redistribution, resale, shared service, or onward licensing. If the rights holder permits less, the rights record must be narrower. The policy must be revisited for a materially different use.

## 4. Verified external terms and permission request

### Shanghai Stock Exchange (SSE) — historical close for 605016

The current SSE Trading Rules (2026 revision), effective 2026-07-06, §5.1.3 says transaction information generated by SSE belongs to SSE and may not be used or disseminated without permission. It separately says even permitted recipients may not redistribute it without SSE consent. Official rule: https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20260424_10816482.shtml

SSE's website legal statement permits non-commercial browsing/downloading subject to the statement, but that broad clause is not treated as a specific grant overriding the transaction-information rule for local historical-price retention and computation. The statement expressly gives this written-permission route: Shanghai Pudong South Road 528, Securities Building, Shanghai Stock Exchange Information Network Co., Ltd. (上证所信息网络有限公司), postal code 200120; fax 021-68792027. Official page: https://www.sse.com.cn/home/legal/

**Decision for current 605016 close:** rights remain UNKNOWN/BLOCKED pending an explicit written response/license that covers the operations above, or a documented licensed-vendor agreement. Do not admit the close row based only on the previous source-vintage upper bound.

### Shenzhen Stock Exchange (SZSE) — prices and 002001 case

SZSE's website statement allows non-commercial browsing/downloading of site content, but does not specifically settle the requested market-data retention, reuse and calculation scope. SZSE's official data-services page describes end-of-day closing price as a market-data service and states Shenzhen Securities Information Co., Ltd. (深圳证券信息有限公司, SSIC) is exclusively authorized to manage and distribute SZSE securities information: https://investor.szse.cn/English/services/dataServices/index.html

Ask SSIC / SZSE for a written determination and license path for individual, non-commercial, single-user usage. A public filing PDF and an exchange closing-price observation are different data classes; do not copy a corporate-disclosure rights conclusion onto prices. Current 002001 operator-attested price remains unverified.

### Copy-ready request letters

The proposed requests are in `docs/iios/EXCHANGE_MARKET_DATA_RIGHTS_REQUESTS_20261011.md`. Sending the letter and receiving a response are external actions; no request has been represented as sent and no permission has been represented as granted.

## 5. Current case disposition

- **C1 / 605016:** candidate Core/PIT PASS may remain as a private candidate. Formal price admission is blocked until (a) market-data rights evidence is suitable, (b) the candidate is signed by a registered authorized signer, and (c) signature verification passes. Current source-vintage bound does not prove the exact original first-public timestamp or license.
- **C2 / 002001:** company-filing facts may be considered separately under reviewed official website terms; the existing thirteen-fact independent review/sign-off has not been completed. The operator-attested price stays explicitly unverified, cannot become source-vintage verified and cannot enter a fully admitted formal case on this basis.
- **Signer registry:** empty and deliberately fail-closed. No private key has been generated by this branch, no signer identity has been fabricated, and no formal signed Admission has been claimed.
- **Local model / Host:** not a dependency for either signature or rights review. D1 Host/model work is a separate deployment track and must not hold this workstream hostage.

## 6. Closure acceptance criteria

A case may change to formal admitted only when all applicable conditions hold:

1. Candidate manifest and every raw artifact pass the canonical Core/PIT validator on exact bytes.
2. The rights adjudication records source class, exact allowed operations, applicable instrument id, exact instrument-byte hash, and validity window.
3. For SSE/SZSE market-price data, rights have explicit scope for private retention and local computation; general public accessibility is not substituted for the instrument.
4. The signer public key is already enrolled in the canonical trusted registry with appropriate role and case scope; the private key remains outside Git.
5. All required trusted signatures validate and required distinct reviewer roles are met.
6. Independent replay produces `FORMALLY_ADMITTED`; otherwise return `BLOCKED`, `SIGNATURES_PENDING`, or an explicit validation error.

This implementation does not assert a legal conclusion that only the exchange or its authorized data distributor can grant. It stores the actual received instrument and its exact bytes, and fails closed until the written scope is clear.
