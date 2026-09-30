# G2 Cross-module Bypass Red-team — Final v0.2

## Scope

This red-team was executed against a fresh extraction of the R1-R10 hardened candidate. It is deliberately separate from implementation-time unit tests and targets compositional trust-boundary failures.

## Attack families

| Family | Cases | Result |
|---|---:|---|
| G2 Intelligence Matrix | 10 | 10/10 DENY/PASS |
| Final Bypass Matrix | 6 | 6/6 DENY/PASS |
| Prior Cross-module R2 | 6 | 6/6 DENY/PASS |
| R9 Cross-module | 4 | 4/4 DENY/PASS |
| Legacy Bypass Red-team | 5 | 5/5 DENY/PASS |
| G2 Adversarial | 9 | 9/9 DENY/PASS |
| **Total** | **40** | **40/40 PASS** |

## Previously reproduced vulnerabilities and final state

- CM-01 ledger tail truncation masquerading as CLEAN: fixed by signed external head anchor and full-chain/head equality.
- CM-02 forged runtime attestation: fixed by signed bootstrap observation plus live PID/inode/start-time/UID/GID checks.
- CM-03 unsigned/attacker-observed runtime facts: rejected; attestation requires the trusted bootstrap observation channel.
- CM-04 self-issued Manifest/Capability authority: rejected by fixed system Trust Root.
- R10 authority laundering through caller-selected/in-memory Registry: eliminated across direct Manifest, Capability, Runtime Attestation, Ledger Head, Contamination Ledger and governance constructors.

No Critical/High reproducible bypass remained in the final clean-package execution.
