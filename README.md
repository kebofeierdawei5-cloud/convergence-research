# IIOS — Intelligent Investment Operating System

## M1.2 Forecast Validation Engineering Baseline

This repository is the primary engineering continuity source for IIOS. Chat history is not authoritative.

Version: `0.1.0`

Current canonical state (2026-10-04):

```text
G2 R10 Reference Governance Runtime = FROZEN
        ↓
M1.2 Forecast Validation = FM-00 PASS / FM-01 foundation PASS
        ↓
Investment Decision Core
        ↓
Batch 1-B Company Value Core = MERGED
        ↓
Human-authoritative Valuation Model Selection = MERGED
        ↓
Batch 2 v0.1 = OPEN / RED-TEAM BLOCKED
        ↓
Next: Investment Core Contract v0.2
```

Return hurdle: **positive expected return >15%**. No fixed 1–3 year holding period and no annualized-return core gate.

Canonical reconciliation: `docs/iios/STATE_RECONCILIATION_2026-10-04.md`

### Repository boundaries

- `governance/` — frozen/reference governance identity and audit evidence
- `research/fm00/` — executable M1.2 research-control baseline
- `AGENTS.md` — engineering constitution
- `IIOS_LONG_TERM_MEMORY_2026-09-30.md` — compact project continuity record
- `STATUS.md` — current machine-facing project status

### FM-00 validation

```bash
python -m pytest -q research/fm00/tests/test_fm00.py
python research/fm00/fm00_validator.py \
  --epoch research/fm00/RE-EXPLORATORY-CATL-20260930.json \
  --plan research/fm00/RP-M12-FM00-EXP-001.json \
  --candidate-space research/fm00/CS-M12-FM00-CATL-001.json \
  --outer-universe research/fm00/OU-M12-FM00-CATL-001.json \
  --purity-boundary research/fm00/EPB-M12-FM00-EXP-001.json
```
