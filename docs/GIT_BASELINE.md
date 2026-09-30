# M1.2-FM00 Git Baseline

Date: 2026-09-30

## Purpose

Establish the first durable Git engineering baseline so IIOS continuity is carried by versioned source, contracts, tests, hashes, and state indexes rather than chat history.

## Included

- AI/Agent Engineering Constitution (`AGENTS.md`)
- G2 R10 frozen-reference identity, current-state snapshot, freeze conclusion, final cross-module bypass report, and governance freeze gate
- FM-00 executable research-control package and tests
- FM-00 validation result and original artifact hash manifest
- Project status and continuity indexes

## Explicit non-claims

- The external G2 package `IIOS_M1_2_G2_R10_FINAL_v0.9.1.tar.gz` is referenced by its supplied SHA-256, but its exact package bytes were not present in this runtime during baseline creation and therefore are not claimed as Git-vendored or independently re-authenticated here.
- A Library materialization named `G2_NORMATIVE_0_9_RM7R_TR02B_F03FIX_CANDIDATE.json` hashes to `60bad875d5d09a2ed7bfe6161a6df05b14a2c2f252bfd8e15a744d789bdb85fe`; it is therefore retained as historical/unverified candidate material, not relabeled as the frozen `899f0b...` carrier.

## Acceptance gate

Before commit:

- FM-00 tests: 8/8 PASS
- FM-00 validator: PASS
- FM-00 original artifact hash manifest: exact 15-file match
- Python compile: PASS
- `git diff --check`: PASS
- No `__pycache__`, `.pyc`, logs, temporary files, or generated runtime debris tracked
