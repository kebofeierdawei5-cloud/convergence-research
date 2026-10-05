# CORE-04-B Acceptance — 2026-10-05

Status: PASS / LIVE CAPTURE VERIFIED

## Evidence

PR #50
Successful live capture workflow: 37258457522
Capture commit: fc247c9b53abcd2150e11e56f343328533e6a1c9
Receipt artifact ID: 11323138280
Receipt artifact digest: sha256:c61e268eaf5aa4f7efb2ff8d3220313f1897bc1fd7df3b948eb09b72b3749a45
Receipt file SHA-256: 291a45c54351e1992dda05fa3770e9137b0ab4279d40c883cf3a6409507a643a

## Live capture result

All six declared official public/free sources returned HTTP 200 and produced non-empty exact-byte captures.

1. SZSE-MKT-2026-07-27 — 229,584 bytes — ab420679237525a7e6846ffa49a3ef8115e4d64d6bc97f63319f5ee9c333e568
2. CNINFO-H1-2026 — 1,374,568 bytes — aa40daf911df40f56900dc506d7debe05a4fea43cd533474039a408e3b5aabcc
3. SZSE-MKT-2026-04-17 — 231,968 bytes — bd5875b4294e3acdcca6aeddf42dd65d8284a15e5a29d6290308c65973b49a0d
4. CNINFO-Q1-2026 — 537,170 bytes — 32e4936e6dd68a89741a8167b4c4ae3f8b4bc7ef61d70f35b294e1cb0e46fbe8
5. SZSE-MKT-2025-10-22 — 230,180 bytes — dfe49f5fade60087e5118f17446bbf55161c4cd7d765dd81155edb10ccdd6ba9
6. CNINFO-Q3-2025 — 351,045 bytes — d099bc0054f4bf8624d34fffa2c82399b7d8e31cce8f84aab909955da9d84f50

## What this proves

The public/free source layer is operationally reachable from the CI environment, and the exact bytes fetched in the successful run have verifiable fingerprints.

## What this does NOT prove

These captures are not yet PIT evidence admissions.

Market snapshots have no asserted known_at in this batch. Financial-report publication timing is recorded only as a candidate PIT anchor. Semantic extraction, private raw-vault retention, and evidence-manifest admission remain pending.

Current provider multiples, retrospective consensus estimates, and recomputed historical values are not promoted to PIT market observations.

## Next gate

CORE-04-C: parse and admit the minimum historical EV/EBITDA observation set from the captured price snapshots plus PIT financial-report vintages.

Forward PE remains separately blocked until a defensible point-in-time forward-estimate source is obtained.
