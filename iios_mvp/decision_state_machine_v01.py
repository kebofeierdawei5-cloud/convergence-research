from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Mapping, Sequence

DECISION_PRECEDENCE_VERSION = "IIOS-DECISION-PRECEDENCE-0.1"

PositionState = str  # NONE | EXISTING

@dataclass(frozen=True)
class DecisionRule:
    rule_id: str
    rank: int
    scope: str
    trigger: str
    action: str
    reason: str
    capital_effect: str
    description: str


# Canonical, auditable precedence table. Rank is evaluated ascending within
# each scope. Scope separation is intentional: portfolio constraints govern
# NEW CAPITAL admission, while EXISTING_POSITION protection must still be able
# to escalate BROKEN thesis / failed risk to EXIT/REDUCE.
CANONICAL_DECISION_PRECEDENCE: tuple[DecisionRule, ...] = (
    DecisionRule("V00_VALIDATION_UNRESOLVED", 0, "UNIVERSAL", "validation_pass == false", "REVIEW_REQUIRED", "RETURN_OR_CASE_VALIDATION_UNRESOLVED", "REVIEW", "Contract/evidence/runtime validation is a prerequisite to all semantic decisions."),
    DecisionRule("T00_TRUST_NOT_PASS", 10, "UNIVERSAL", "trust_status != PASS", "REVIEW_REQUIRED", "TRUST_NOT_PASS_REQUIRES_REVIEW", "REVIEW", "Trust Gate has precedence over all investment actions; non-PASS never auto-allocates or auto-disposes capital."),
    DecisionRule("U20_RETURN_METRICS_UNRESOLVED", 20, "UNIVERSAL", "return_metrics_ready == false", "REVIEW_REQUIRED", "RETURN_OR_CASE_VALIDATION_UNRESOLVED", "REVIEW", "Deterministic return/risk metrics are required before semantic action selection."),
    DecisionRule("EP10_THESIS_BROKEN", 20, "EXISTING_POSITION", "position > 0 and thesis_status == BROKEN", "EXIT", "THESIS_BROKEN", "DECREASE", "A broken investment thesis exits an existing position."),
    DecisionRule("EP11_THESIS_UNKNOWN", 21, "EXISTING_POSITION", "position > 0 and thesis_status == UNKNOWN", "REVIEW_REQUIRED", "THESIS_UNKNOWN", "REVIEW", "An unresolved thesis cannot be silently converted into HOLD."),
    DecisionRule("EP15_RISK_UNKNOWN", 25, "EXISTING_POSITION", "position > 0 and risk_status == UNKNOWN", "REVIEW_REQUIRED", "RISK_UNKNOWN", "REVIEW", "Risk state is unresolved; no automatic holding/reduction decision is permitted."),
    DecisionRule("EP20_RISK_HARD_FAIL", 30, "EXISTING_POSITION", "position > 0 and hard_risk_failure", "REDUCE", "RISK_GATE_FAILED", "DECREASE", "Hard risk failure reduces an existing position."),
    DecisionRule("EP30_PORTFOLIO_UNKNOWN", 35, "EXISTING_POSITION", "position > 0 and portfolio_status == UNKNOWN", "REVIEW_REQUIRED", "PORTFOLIO_CONSTRAINT_UNKNOWN", "REVIEW", "An unresolved portfolio constraint cannot be converted into a deterministic sizing action."),
    DecisionRule("EP31_PORTFOLIO_BLOCKED", 40, "EXISTING_POSITION", "position > 0 and portfolio_status == BLOCKED", "REDUCE", "PORTFOLIO_CONSTRAINT_BLOCKED", "DECREASE", "Portfolio constraint violation reduces an existing position; it cannot suppress a higher-protection thesis exit."),
    DecisionRule("EP40_EXPECTED_RETURN_NEGATIVE", 50, "EXISTING_POSITION", "position > 0 and expected_annualized_return < 0", "REDUCE", "NO_POSITIVE_LONG_TERM_RETURN", "DECREASE", "Negative expected return is a hard long-term value failure for capital already at risk."),
    DecisionRule("NP10_PORTFOLIO_UNKNOWN", 10, "NEW_CAPITAL", "position == 0 and portfolio_status == UNKNOWN", "REVIEW_REQUIRED", "PORTFOLIO_CONSTRAINT_UNKNOWN", "REVIEW", "Portfolio capacity is unresolved; new capital cannot be deterministically admitted or denied."),
    DecisionRule("NP11_PORTFOLIO_BLOCKED", 15, "NEW_CAPITAL", "position == 0 and portfolio_status == BLOCKED", "NO-BUY", "PORTFOLIO_CONSTRAINT_BLOCKED", "UNCHANGED", "Portfolio Constraint blocks new capital before long-term value or expectation-gap admission."),
    DecisionRule("NP20_THESIS_BROKEN", 20, "NEW_CAPITAL", "position == 0 and thesis_status == BROKEN", "NO-BUY", "THESIS_BROKEN", "UNCHANGED", "A broken thesis cannot admit new capital."),
    DecisionRule("NP21_THESIS_UNKNOWN", 25, "NEW_CAPITAL", "position == 0 and thesis_status == UNKNOWN", "REVIEW_REQUIRED", "THESIS_UNKNOWN", "REVIEW", "An unresolved thesis cannot admit new capital."),
    DecisionRule("NP30_RISK_UNKNOWN", 30, "NEW_CAPITAL", "position == 0 and risk_status == UNKNOWN", "REVIEW_REQUIRED", "RISK_UNKNOWN", "REVIEW", "An unresolved risk state cannot admit new capital."),
    DecisionRule("NP31_RISK_HARD_FAIL", 35, "NEW_CAPITAL", "position == 0 and hard_risk_failure", "NO-BUY", "RISK_GATE_FAILED", "UNCHANGED", "Hard risk failure blocks new capital."),
    DecisionRule("NP40_EXPECTED_RETURN_NEGATIVE", 40, "NEW_CAPITAL", "position == 0 and expected_annualized_return < 0", "NO-BUY", "NEGATIVE_EXPECTED_RETURN", "UNCHANGED", "Negative expected return is a hard long-term value failure."),
    DecisionRule("G00_GAP_UNRESOLVED_NEW", 50, "NEW_CAPITAL", "position == 0 and gap_status in {UNKNOWN,BLOCKED,INCOMPATIBLE,AMBIGUOUS}", "REVIEW_REQUIRED", "POSITIVE_EXPECTATION_GAP_UNRESOLVED", "REVIEW", "Canonical expectation gap is mandatory for BUY; unresolved evidence fails closed."),
    DecisionRule("G10_GAP_NONPOSITIVE_NEW", 60, "NEW_CAPITAL", "position == 0 and gap_status == PASS and not gap_positive", "NO-BUY", "NO_POSITIVE_EXPECTATION_GAP", "UNCHANGED", "No positive expectation gap means no new-capital admission."),
    DecisionRule("R00_RETURN_QUALIFIED_NEW_PACKAGE_MISSING", 70, "NEW_CAPITAL", "position == 0 and gap_positive and return_gate_pass and not package_complete", "REVIEW_REQUIRED", "BUY_ADD_POSITION_PACKAGE_INCOMPLETE", "REVIEW", "A BUY package must be complete before a BUY proposal can be READY."),
    DecisionRule("R10_RETURN_QUALIFIED_NEW", 80, "NEW_CAPITAL", "position == 0 and gap_positive and return_gate_pass", "BUY", "POSITIVE_EXPECTATION_GAP_AND_RETURN_PRICE_GATES_PASS", "INCREASE", "Positive expectation gap plus all long-term/price gates admit BUY."),
    DecisionRule("R20_RETURN_NOT_QUALIFIED_NEW", 90, "NEW_CAPITAL", "position == 0 and gap_positive and not return_gate_pass", "WATCH", "CURRENT_PRICE_ABOVE_TARGET_ENTRY_PRICE", "UNCHANGED", "The company may remain investable at a better price; no new capital at the current price."),
    DecisionRule("EP50_GAP_UNRESOLVED", 100, "EXISTING_POSITION", "position > 0 and gap_status in {UNKNOWN,BLOCKED,INCOMPATIBLE,AMBIGUOUS}", "HOLD", "EXPECTATION_GAP_UNRESOLVED_FOR_ADD_ONLY", "UNCHANGED", "Unresolved expectation gap blocks ADD only; it does not force disposal of an otherwise unbroken position."),
    DecisionRule("EP60_GAP_NONPOSITIVE_NEG_RETURN", 110, "EXISTING_POSITION", "position > 0 and gap_status == PASS and not gap_positive and expected_annualized_return < 0", "REDUCE", "NO_POSITIVE_EXPECTATION_GAP_AND_NEGATIVE_EXPECTED_RETURN", "DECREASE", "Negative long-term return plus no positive gap warrants reduction."),
    DecisionRule("EP70_GAP_NONPOSITIVE", 120, "EXISTING_POSITION", "position > 0 and gap_status == PASS and not gap_positive", "HOLD", "NO_POSITIVE_EXPECTATION_GAP_FOR_ADD", "UNCHANGED", "No positive gap blocks ADD but does not by itself force a sale."),
    DecisionRule("R30_RETURN_QUALIFIED_EXISTING_PACKAGE_MISSING", 130, "EXISTING_POSITION", "position > 0 and gap_positive and return_gate_pass and can_add and not package_complete", "REVIEW_REQUIRED", "BUY_ADD_POSITION_PACKAGE_INCOMPLETE", "REVIEW", "An ADD package must be complete before increasing an existing position."),
    DecisionRule("R40_RETURN_QUALIFIED_EXISTING_ADD", 140, "EXISTING_POSITION", "position > 0 and gap_positive and return_gate_pass and can_add", "ADD", "POSITIVE_EXPECTATION_GAP_AND_RETURN_PRICE_GATES_PASS", "INCREASE", "Positive expectation gap plus all long-term/price gates admit ADD."),
    DecisionRule("R50_RETURN_NOT_QUALIFIED_EXISTING", 150, "EXISTING_POSITION", "position > 0 and gap_positive and not return_gate_pass", "HOLD", "CURRENT_OPPORTUNITY_DOES_NOT_JUSTIFY_NEW_CAPITAL", "UNCHANGED", "Existing capital may be held while current price fails the new-capital return/price gates."),
    DecisionRule("R60_EXISTING_DEFAULT_HOLD", 160, "EXISTING_POSITION", "position > 0", "HOLD", "CURRENT_OPPORTUNITY_DOES_NOT_JUSTIFY_NEW_CAPITAL", "UNCHANGED", "Deterministic conservative fallback for an existing position."),
    DecisionRule("R70_NEW_DEFAULT_NO_BUY", 170, "NEW_CAPITAL", "position == 0", "NO-BUY", "FUNDAMENTAL_RETURN_OR_REQUIRED_RETURN_GATE_FAILED", "UNCHANGED", "Deterministic conservative fallback for a new candidate."),
)

def decision_precedence_table() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": rule.rule_id,
            "rank": rule.rank,
            "scope": rule.scope,
            "trigger": rule.trigger,
            "action": rule.action,
            "reason": rule.reason,
            "capital_effect": rule.capital_effect,
            "description": rule.description,
        }
        for rule in CANONICAL_DECISION_PRECEDENCE
    ]


@dataclass(frozen=True)
class DecisionStateInputs:
    validation_pass: bool
    trust_status: str
    thesis_status: str
    risk_status: str
    portfolio_status: str
    position_pct: Decimal
    gap_status: str
    gap_positive: bool
    expected_annualized_return: Decimal | None
    return_gate_pass: bool
    risk_gate_pass: bool
    can_add: bool
    package_complete: bool
    return_metrics_ready: bool


def _hard_risk_failure(inputs: DecisionStateInputs) -> bool:
    return inputs.risk_status == "FAIL" or not inputs.risk_gate_pass


def _matches(rule: DecisionRule, inputs: DecisionStateInputs) -> bool:
    pos = inputs.position_pct > 0
    new = inputs.position_pct == 0
    unresolved_gap = inputs.gap_status in {"UNKNOWN", "BLOCKED", "INCOMPATIBLE", "AMBIGUOUS"}
    hard_risk_failure = _hard_risk_failure(inputs)
    negative_return = (
        inputs.expected_annualized_return is not None
        and inputs.expected_annualized_return < 0
    )

    conditions: dict[str, bool] = {
        "V00_VALIDATION_UNRESOLVED": not inputs.validation_pass,
        "T00_TRUST_NOT_PASS": inputs.trust_status != "PASS",
        "U20_RETURN_METRICS_UNRESOLVED": not inputs.return_metrics_ready,
        "EP10_THESIS_BROKEN": pos and inputs.thesis_status == "BROKEN",
        "EP11_THESIS_UNKNOWN": pos and inputs.thesis_status == "UNKNOWN",
        "EP15_RISK_UNKNOWN": pos and inputs.risk_status == "UNKNOWN",
        "EP20_RISK_HARD_FAIL": pos and hard_risk_failure,
        "EP30_PORTFOLIO_UNKNOWN": pos and inputs.portfolio_status == "UNKNOWN",
        "EP31_PORTFOLIO_BLOCKED": pos and inputs.portfolio_status == "BLOCKED",
        "EP40_EXPECTED_RETURN_NEGATIVE": pos and negative_return,
        "NP10_PORTFOLIO_UNKNOWN": new and inputs.portfolio_status == "UNKNOWN",
        "NP11_PORTFOLIO_BLOCKED": new and inputs.portfolio_status == "BLOCKED",
        "NP20_THESIS_BROKEN": new and inputs.thesis_status == "BROKEN",
        "NP21_THESIS_UNKNOWN": new and inputs.thesis_status == "UNKNOWN",
        "NP30_RISK_UNKNOWN": new and inputs.risk_status == "UNKNOWN",
        "NP31_RISK_HARD_FAIL": new and hard_risk_failure,
        "NP40_EXPECTED_RETURN_NEGATIVE": new and negative_return,
        "G00_GAP_UNRESOLVED_NEW": new and unresolved_gap,
        "G10_GAP_NONPOSITIVE_NEW": new and inputs.gap_status == "PASS" and not inputs.gap_positive,
        "R00_RETURN_QUALIFIED_NEW_PACKAGE_MISSING": new and inputs.gap_positive and inputs.return_gate_pass and not inputs.package_complete,
        "R10_RETURN_QUALIFIED_NEW": new and inputs.gap_positive and inputs.return_gate_pass,
        "R20_RETURN_NOT_QUALIFIED_NEW": new and inputs.gap_positive and not inputs.return_gate_pass,
        "EP50_GAP_UNRESOLVED": pos and unresolved_gap,
        "EP60_GAP_NONPOSITIVE_NEG_RETURN": pos and inputs.gap_status == "PASS" and not inputs.gap_positive and negative_return,
        "EP70_GAP_NONPOSITIVE": pos and inputs.gap_status == "PASS" and not inputs.gap_positive,
        "R30_RETURN_QUALIFIED_EXISTING_PACKAGE_MISSING": pos and inputs.gap_positive and inputs.return_gate_pass and inputs.can_add and not inputs.package_complete,
        "R40_RETURN_QUALIFIED_EXISTING_ADD": pos and inputs.gap_positive and inputs.return_gate_pass and inputs.can_add,
        "R50_RETURN_NOT_QUALIFIED_EXISTING": pos and inputs.gap_positive and not inputs.return_gate_pass,
        "R60_EXISTING_DEFAULT_HOLD": pos,
        "R70_NEW_DEFAULT_NO_BUY": new,
    }
    return conditions[rule.rule_id]


def evaluate_decision_state(inputs: DecisionStateInputs) -> dict[str, Any]:
    normalized = DecisionStateInputs(
        validation_pass=bool(inputs.validation_pass),
        trust_status=str(inputs.trust_status).upper(),
        thesis_status=str(inputs.thesis_status).upper(),
        risk_status=str(inputs.risk_status).upper(),
        portfolio_status=str(inputs.portfolio_status).upper(),
        position_pct=Decimal(inputs.position_pct),
        gap_status=str(inputs.gap_status).upper(),
        gap_positive=bool(inputs.gap_positive),
        expected_annualized_return=(
            None
            if inputs.expected_annualized_return is None
            else Decimal(inputs.expected_annualized_return)
        ),
        return_gate_pass=bool(inputs.return_gate_pass),
        risk_gate_pass=bool(inputs.risk_gate_pass),
        can_add=bool(inputs.can_add),
        package_complete=bool(inputs.package_complete),
        return_metrics_ready=bool(inputs.return_metrics_ready),
    )

    for rule in CANONICAL_DECISION_PRECEDENCE:
        if rule.scope == "EXISTING_POSITION" and normalized.position_pct <= 0:
            continue
        if rule.scope == "NEW_CAPITAL" and normalized.position_pct != 0:
            continue
        if _matches(rule, normalized):
            return {
                "precedence_version": DECISION_PRECEDENCE_VERSION,
                "precedence_rule_id": rule.rule_id,
                "precedence_rank": rule.rank,
                "decision_scope": rule.scope,
                "action": rule.action,
                "primary_reason": rule.reason,
                "capital_effect": rule.capital_effect,
                "new_capital_allowed": rule.action in {"BUY", "ADD"},
            }

    raise RuntimeError("decision precedence table has no matching terminal rule")


def validate_precedence_table() -> None:
    ids = [rule.rule_id for rule in CANONICAL_DECISION_PRECEDENCE]
    if len(ids) != len(set(ids)):
        raise ValueError("decision precedence rule IDs must be unique")
    universal = [r for r in CANONICAL_DECISION_PRECEDENCE if r.scope == "UNIVERSAL"]
    if [r.rule_id for r in universal] != ["V00_VALIDATION_UNRESOLVED", "T00_TRUST_NOT_PASS", "U20_RETURN_METRICS_UNRESOLVED"]:
        raise ValueError("universal precedence must begin with validation then Trust")
    scopes = {r.scope for r in CANONICAL_DECISION_PRECEDENCE}
    if scopes != {"UNIVERSAL", "EXISTING_POSITION", "NEW_CAPITAL"}:
        raise ValueError("decision precedence scopes are incomplete")
    existing_ids = [r.rule_id for r in CANONICAL_DECISION_PRECEDENCE if r.scope == "EXISTING_POSITION"]
    expected_existing_prefix = ["EP10_THESIS_BROKEN", "EP11_THESIS_UNKNOWN", "EP15_RISK_UNKNOWN"]
    if existing_ids[:3] != expected_existing_prefix:
        raise ValueError("existing-position protection precedence is not frozen")
    new_ids = [r.rule_id for r in CANONICAL_DECISION_PRECEDENCE if r.scope == "NEW_CAPITAL"]
    expected_new_prefix = ["NP10_PORTFOLIO_UNKNOWN", "NP11_PORTFOLIO_BLOCKED", "NP20_THESIS_BROKEN"]
    if new_ids[:3] != expected_new_prefix:
        raise ValueError("new-capital precedence must begin with Portfolio Constraint")


validate_precedence_table()


__all__ = [
    "CANONICAL_DECISION_PRECEDENCE",
    "DECISION_PRECEDENCE_VERSION",
    "DecisionRule",
    "DecisionStateInputs",
    "decision_precedence_table",
    "evaluate_decision_state",
    "validate_precedence_table",
]
