# IIOS Agent Engineering Constitution

## Mission
Build the smallest working product that makes personal investment analysis more repeatable, auditable, point-in-time reproducible, and resistant to LLM failure modes.

## Non-negotiable rules

1. Do not fabricate missing data.
2. UNKNOWN, missing, stale, conflicting, or unverifiable evidence must close only the affected permission; never silently become PASS/HOLD.
3. Trust, Thesis, Valuation, and Investment Attractiveness are separate states.
4. A Trust FAIL must not permit a new BUY or ADD.
5. Historical decisions and events are append-only; never overwrite prior records.
6. AI Decision and Human Decision are separate records.
7. Deterministic calculations, state transitions, permissions, dates, hashes, and persistence must not be delegated to an LLM.
8. The system never places an order automatically.
9. Never modify tests solely to make a failing implementation pass.
10. Never expand task scope without an explicit task-level reason and an updated test/acceptance statement.

## Task contract
Every task must state:

- Objective
- User Value
- Product Surface
- Test / Acceptance
- Out of Scope

## Change discipline

- Prefer one narrow PR per task.
- Business-semantic changes require tests in the same PR, but tests must not be weakened to obtain PASS.
- Changes to invariant/property-test definitions require explicit review.
- Use conventional Semantic Versioning for releases.
- Use repository files, ADRs, and CHANGELOG for continuity; do not depend on chat history.

## Architecture boundaries

- `domain/`: business state and value objects.
- `runtime/`: transitions, permissions, invalidation, replay.
- `store/`: durable event persistence.
- `analyst/`: future LLM-facing analysis adapters.
- `calc/`: future deterministic calculations.

## Prohibited patterns

- self-referential verification
- verifier consuming its own previous result as proof of PASS
- a mutation test that only checks that a file changed
- hidden current-price leakage into blind-forecast inputs
- silent evidence substitution
- direct LLM writes to authoritative state
