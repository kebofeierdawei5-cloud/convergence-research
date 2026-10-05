# P5-A — Semantic Expectation Gap v0.1

Status: CANDIDATE

## Objective

Create the smallest independent expectation-gap contract after P4-F.

## Rule

Expectation Gap may be calculated only when:

1. Market Implied Expectation is `UNIQUE_MODEL`.
2. MIE qualification is `DECISION_GRADE`.
3. Independent and market expectations use the same:
   - variable;
   - unit;
   - basis;
   - horizon.
4. Comparison direction is explicit.

Otherwise the result is BLOCKED, AMBIGUOUS, or INCOMPATIBLE and no scalar gap is produced.

## Output

For a compatible pair:

```
gap_absolute
gap_relative = gap_absolute / abs(market_required_value)
```

No forced conversion between economically different variables is permitted.

This module does not implement the 15% return gate or BUY/ADD decision semantics. Those remain separate.

## Out of scope

No changes to Trust, Portfolio Constraint, decision state machine, A02/CSI800, or historical data acquisition.
