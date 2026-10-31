from __future__ import annotations

"""B72: aggregate operating-feasibility exceptions and remediation requirements.

B72 is a read-only aggregation layer over B69/B70/B71. It keeps the B61 and
B63 requirement lenses separate, preserves numerical and semantic review as
independent axes, and never turns conditional evidence into formal admission.
"""

from typing import Any, Mapping

B72_SCHEMA = "IIOS-OPERATING-FEASIBILITY-EXCEPTION-REGISTER-0.1"
B69_SCHEMA = "IIOS-SOTP-OPERATING-FEASIBILITY-AUDIT-0.1"
B70_SCHEMA = "IIOS-OPERATING-FEASIBILITY-EVIDENCE-ASSESSMENT-0.1"
B71_SCHEMA = "IIOS-OPERATING-FEASIBILITY-SEMANTIC-REVIEW-0.1"

_SCENARIOS = ("bear", "base", "bull")
_CLAIM_UNITS = {
    "SUPPORTED_SALES_VOLUME": "tonnes",
    "SUPPORTED_NET_ASP": "CNY/tonne",
    "SUPPORTED_UNIT_VARIABLE_COST": "CNY/tonne",
    "EFFECTIVE_CAPACITY_AVAILABLE": "tonnes",
    "CAPACITY_AVAILABLE_DATE": "date",
    "INCREMENTAL_CAPEX_REQUIRED": "CNY",
    "INCREMENTAL_CAPEX_FUNDED": "CNY",
    "INCREMENTAL_WORKING_CAPITAL_REQUIRED": "CNY",
    "INCREMENTAL_WORKING_CAPITAL_FUNDED": "CNY",
}


def _txt(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _record_indexes(b70: Mapping[str, Any]):
    by_id: dict[str, list[Mapping[str, Any]]] = {}
    by_key: dict[tuple[str, str, str, str], list[Mapping[str, Any]]] = {}
    for row in _rows(b70.get("records")):
        record_id = _txt(row.get("record_id"))
        if record_id:
            by_id.setdefault(record_id, []).append(row)
        key = (
            _txt(row.get("scenario")).lower(),
            _txt(row.get("product_id")),
            _txt(row.get("forecast_period")),
            _txt(row.get("claim_type")).upper(),
        )
        by_key.setdefault(key, []).append(row)
    return by_id, by_key


def _review_index(b71: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    out: dict[str, list[Mapping[str, Any]]] = {}
    for row in _rows(b71.get("reviews")):
        record_id = _txt(row.get("record_id"))
        if record_id:
            out.setdefault(record_id, []).append(row)
    return out


def _records_for_claim(
    *,
    record_ids: list[str],
    by_id: Mapping[str, list[Mapping[str, Any]]],
    by_key: Mapping[tuple[str, str, str, str], list[Mapping[str, Any]]],
    scenario: str,
    product_id: str,
    period: str,
    claim_types: tuple[str, ...],
) -> tuple[list[Mapping[str, Any]], bool, bool]:
    found: list[Mapping[str, Any]] = []
    ambiguous = False
    scope_mismatch = False
    for claim_type in claim_types:
        candidates: list[Mapping[str, Any]] = []
        if record_ids:
            for record_id in record_ids:
                typed_rows = [
                    row for row in by_id.get(record_id, [])
                    if _txt(row.get("claim_type")).upper() == claim_type
                ]
                matching_rows = [
                    row for row in typed_rows
                    if _txt(row.get("scenario")).lower() == scenario
                    and _txt(row.get("product_id")) == product_id
                    and _txt(row.get("forecast_period")) == period
                ]
                if typed_rows and len(matching_rows) != len(typed_rows):
                    scope_mismatch = True
                candidates.extend(matching_rows)
        if not candidates and not scope_mismatch:
            candidates.extend(
                by_key.get((scenario, product_id, period, claim_type), [])
            )
        if len(candidates) > 1:
            ambiguous = True
        elif candidates:
            found.extend(candidates)
    unique: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(found):
        key = _txt(row.get("record_id")) or f"__row_{index}"
        unique[key] = row
    return list(unique.values()), ambiguous, scope_mismatch


def _semantic_review_state(
    records: list[Mapping[str, Any]],
    reviews_by_record: Mapping[str, list[Mapping[str, Any]]],
    *,
    b71_available: bool,
) -> tuple[str, list[Mapping[str, Any]]]:
    if not b71_available:
        return "SEMANTIC_REVIEW_INPUT_UNAVAILABLE", []
    if not records:
        return "SEMANTIC_REVIEW_NOT_PROVIDED", []
    reviews: list[Mapping[str, Any]] = []
    missing_review = False
    duplicate_review = False
    for record in records:
        record_id = _txt(record.get("record_id"))
        matches = reviews_by_record.get(record_id, []) if record_id else []
        if not matches:
            missing_review = True
        elif len(matches) > 1:
            duplicate_review = True
            reviews.extend(matches)
        else:
            reviews.append(matches[0])
    if duplicate_review:
        return "SEMANTIC_REVIEW_DUPLICATE_OR_AMBIGUOUS", reviews
    states = [_txt(row.get("status")).upper() for row in reviews]
    if any(state in {"SEMANTIC_REVIEW_CONTRADICTED", "SEMANTIC_REVIEW_NOT_SUPPORTED"} for state in states):
        return "HUMAN_REVIEW_CONTRADICTS_OR_DOES_NOT_SUPPORT_CLAIM", reviews
    if any(state == "SEMANTIC_REVIEW_INDEPENDENCE_UNRESOLVED" for state in states):
        return "REVIEW_INDEPENDENCE_UNRESOLVED", reviews
    if any(state == "SEMANTIC_REVIEW_PARTIAL" for state in states):
        return "HUMAN_REVIEW_PARTIAL", reviews
    if any(state == "SEMANTIC_REVIEW_UNABLE_TO_VERIFY" for state in states):
        return "HUMAN_REVIEW_UNABLE_TO_VERIFY", reviews
    if missing_review:
        return "SEMANTIC_REVIEW_COVERAGE_INCOMPLETE", reviews
    if states and all(
        state == "HUMAN_SEMANTIC_REVIEW_SUPPORTED_CONDITIONALLY"
        and row.get("review_independence_conditionally_declared") is True
        for state, row in zip(states, reviews)
    ):
        return "HUMAN_REVIEW_SUPPORTED_CONDITIONALLY", reviews
    if any(state in {
        "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE",
        "SEMANTIC_REVIEW_NOT_COMPLETE",
        "SEMANTIC_REVIEW_CHECKS_FAILED",
        "SEMANTIC_REVIEW_CHECK_FAILURE_CONFLICTS_WITH_SUPPORT_DECISION",
    } for state in states):
        return "HUMAN_REVIEW_BLOCKED_OR_INCOMPLETE", reviews
    return "HUMAN_REVIEW_NOT_COMPLETE", reviews


def _evidence_state(
    raw_status: Any,
    *,
    records: list[Mapping[str, Any]],
    ambiguous: bool,
    scope_mismatch: bool = False,
) -> str:
    status = _txt(raw_status).upper()
    data_classes = {_txt(row.get("data_class")).upper() for row in records}
    if scope_mismatch:
        return "EVIDENCE_RECORD_SCOPE_MISMATCH"
    if ambiguous or status == "AMBIGUOUS_DUPLICATE_CLAIMS_NOT_SUMMED":
        return "AMBIGUOUS_DUPLICATE_CLAIMS_NOT_SUMMED"
    if "ANALYST_ASSUMPTION" in data_classes:
        return "ANALYST_ASSUMPTION_ONLY_NOT_CORROBORATION"
    if status in {
        "LINKED_CLAIM_NUMERICALLY_COVERS_REQUIREMENT",
        "LINKED_CLAIM_AVAILABLE_BY_FORECAST_END",
        "LINKED_FUNDING_CLAIM_COVERS_REQUIREMENT",
    }:
        return "LINKED_VALUE_COVERS_NUMERICAL_REQUIREMENT"
    if status in {
        "LINKED_CLAIM_NUMERICALLY_BELOW_REQUIREMENT",
        "LINKED_CLAIM_NUMERICALLY_ABOVE_ALLOWED_COST",
    }:
        return "LINKED_VALUE_FAILS_NUMERICAL_REQUIREMENT"
    if status in {
        "LINKED_FUNDING_CLAIM_SHORTFALL",
    }:
        return "LINKED_FUNDING_SHORTFALL"
    if status in {
        "LINKED_CLAIM_AVAILABLE_AFTER_FORECAST_END",
        "LINKED_CAPACITY_AVAILABLE_AFTER_FORECAST_END_NOT_COVERAGE",
    }:
        return "CAPACITY_AVAILABLE_TOO_LATE"
    if status == "EVIDENCE_NOT_PROVIDED":
        return "EVIDENCE_NOT_PROVIDED"
    if status in {
        "CLAIM_NOT_ELIGIBLE_FOR_COMPARISON",
        "FUNDING_CLAIM_NOT_ELIGIBLE_FOR_COMPARISON",
    }:
        return "EVIDENCE_LINKAGE_NOT_ELIGIBLE"
    if status in {
        "FUNDING_REQUIREMENT_OR_AVAILABLE_AMOUNT_NOT_IDENTIFIABLE",
        "FUNDING_AMOUNT_NOT_IDENTIFIABLE",
        "REQUIRED_OR_EVIDENCE_VALUE_NOT_IDENTIFIABLE",
        "FORECAST_PERIOD_END_NOT_IDENTIFIABLE",
    }:
        return "REQUIRED_OR_EVIDENCE_VALUE_NOT_IDENTIFIABLE"
    return "UNCLASSIFIED_OR_UNRESOLVED"


def _remediation(
    final_status: str,
    *,
    claim_type: str,
    requirement_label: str,
) -> dict[str, Any]:
    plans = {
        "CONDITIONALLY_SUPPORTED_NOT_FORMALLY_ADMITTED": (
            "FORMAL_EVIDENCE_ADMISSION",
            "EVIDENCE_GOVERNANCE_OWNER",
            "将已审核主张连同原始材料提交正式 Evidence/PIT 准入；同时补齐其他未覆盖经营约束。",
            ["正式准入流程结论", "原始材料与主张范围一致", "仍未覆盖的需求/价格/成本/资金条件已单独处理"],
        ),
        "NUMERICAL_LINKAGE_ONLY_REVIEW_PENDING": (
            "INDEPENDENT_SEMANTIC_REVIEW",
            "INDEPENDENT_REVIEWER",
            "按 B71 对原始来源逐项完成该类主张的完整审核；不得只补一条笼统的支持意见。",
            ["B71 完整必检项", "每个 PASS 检查项有对应来源引用", "审核人与编制人分离及利益冲突声明"],
        ),
        "QUANTIFIED_REQUIREMENT_GAP": (
            "REBUILD_OPERATING_DRIVER_PLAN",
            "OPERATING_OWNER_AND_RESEARCHER",
            "核实缺口对应的销量、净售价或单位成本驱动，提出可执行的产品/客户/合同/成本行动；不得通过下调 B68 门槛制造通过。",
            ["与现价隐含门槛同期间同口径的更新数据", "差异原因和可执行措施", "对 B4 产销/利润/现金流影响的独立复核"],
        ),
        "INCREMENTAL_FUNDING_SHORTFALL": (
            "RESOLVE_INCREMENTAL_FUNDING_SHORTFALL",
            "FINANCE_OWNER_AND_PROJECT_OWNER",
            "核实增量资本开支或营运资金缺口的资金来源、可用时间和未被重复占用情况；必要时重做项目/产销方案。",
            ["增量资金需求计算依据", "无抵押/无重复占用的可用资金证据", "资金可用时间覆盖支出时间"],
        ),
        "EXPANSION_AVAILABLE_AFTER_FORECAST_PERIOD": (
            "REPLAN_EXPANSION_TIMING",
            "PROJECT_OWNER_AND_OPERATIONS",
            "核实建设、许可、设备验收、试生产、爬坡和首批合格产品日期；晚于预测期的产能不能覆盖该期要求。",
            ["项目里程碑原始依据", "首批合格产品而非机械完工日期", "按预测期重新核算的有效产能"],
        ),
        "CLAIM_CONTRADICTED_BY_HUMAN_REVIEW": (
            "WITHDRAW_OR_RECONCILE_CONTRADICTED_CLAIM",
            "CLAIM_OWNER_AND_INDEPENDENT_REVIEWER",
            "暂停将该主张作为经营支撑，回到原始材料查明矛盾；修正或撤回主张后重新绑定证据并审核。",
            ["矛盾点逐项说明", "更正/撤回后的唯一主张记录", "新来源集合及重新完成的独立审核"],
        ),
        "ANALYST_ASSUMPTION_ONLY_NOT_CORROBORATION": (
            "REPLACE_ANALYST_ASSUMPTION_WITH_PRIMARY_EVIDENCE",
            "RESEARCHER",
            "该值仅是分析师假设，不能作为经营证据；寻找截止日兼容的发行人/交易所/监管原始材料，否则保留为 UNKNOWN。",
            ["Primary-class 原始材料", "与产品/情景/期间完全匹配的主张", "重新通过 B70 与 B71"],
        ),
        "EVIDENCE_NOT_PROVIDED": (
            "COLLECT_MISSING_OPERATING_EVIDENCE",
            "RESEARCHER_AND_OPERATING_OWNER",
            "补充与该产品、情景、预测期间和主张类型精确匹配的原始证据；没有材料时保持 UNKNOWN，不以分析师推测填补。",
            ["唯一 record_id", "明确数据类别、口径和单位", "截止日兼容的主来源引用"],
        ),
        "EVIDENCE_LINKAGE_NOT_ELIGIBLE": (
            "REPAIR_EVIDENCE_LINEAGE",
            "EVIDENCE_OWNER",
            "先修复来源身份、主来源类别、域名/类别一致性和 PIT 时间问题；修复前不得做数值支持判断。",
            ["唯一可解析来源 ID", "Primary-class 与域名类别一致", "PIT 时间兼容且无截止日之后信息"],
        ),
        "AMBIGUOUS_DUPLICATE_CLAIMS_NOT_SUMMED": (
            "RESOLVE_DUPLICATE_CLAIM_SCOPE",
            "CLAIM_OWNER",
            "查明重复记录是重复合同、订单重叠还是不同范围；按净额和唯一经济事项整理，禁止把重复记录求和。",
            ["唯一主张键", "订单/合同重叠与取消核对", "明确去重或分拆口径"],
        ),
        "EVIDENCE_RECORD_SCOPE_MISMATCH": (
            "RESOLVE_EVIDENCE_RECORD_SCOPE_MISMATCH",
            "EVIDENCE_OWNER",
            "证据记录的情景、产品、预测期或主张类型与当前要求不一致；重新绑定精确匹配的记录，禁止跨情景或跨产品复用。",
            ["情景/产品/预测期/主张类型完全匹配的唯一 record_id", "原始证据范围与经营主张一致", "重新生成的 B70/B71 记录"],
        ),
        "CAPACITY_NOT_IDENTIFIABLE": (
            "VERIFY_EFFECTIVE_CAPACITY",
            "OPERATIONS_OWNER",
            "核实有效产能、产品线映射、检修、良率、瓶颈、切换和爬坡；名义产能内不等于有效产能通过。",
            ["有效产能口径", "产线/产品映射与瓶颈", "预测期内有效产能及良率依据"],
        ),
        "INVALID_NEGATIVE_REQUIRED_PRODUCTION": (
            "RECONCILE_PRODUCTION_AND_INVENTORY_ARITHMETIC",
            "OPERATIONS_OWNER_AND_RESEARCHER",
            "核查所需销量、产销库存差额和生产口径；负数所需产量不能解释为可实现的经营能力。",
            ["产量与销量的原始口径", "库存变动及库存政策依据", "重新核对后的非负所需产量"],
        ),
        "NAMEPLATE_CAPACITY_CONSTRAINT": (
            "REMEDIATE_NAMEPLATE_CAPACITY_CONSTRAINT",
            "OPERATIONS_OWNER_AND_PROJECT_OWNER",
            "按当前 B61 或 B63 独立门槛核实扩产/外协/产品组合或库存策略；不要合并两个门槛，也不要假定扩建自动可用。",
            ["所需产量与产销库存差额复核", "扩产/外协/产品策略原始依据", "预测期内有效产能和资金计划"],
        ),
        "CONDITIONAL_NAMEPLATE_FIT_ONLY": (
            "VERIFY_NON_NAMEPLATE_CONSTRAINTS",
            "OPERATIONS_OWNER",
            "名义产能算术暂未超限，但仍需验证有效产能、订单需求、良率、检修、产线共享和库存政策。",
            ["有效产能与良率依据", "订单/客户需求依据", "库存释放/补库计划"],
        ),
        "NOT_IDENTIFIABLE_UNCOVERED_DIMENSION": (
            "COLLECT_UNMODELED_OPERATING_DRIVER_EVIDENCE",
            "RESEARCHER_AND_OPERATING_OWNER",
            "该经营维度没有被现有结构化主张充分覆盖；补充原始材料和可验证的因果机制，否则继续保持 NOT_IDENTIFIABLE。",
            ["定义明确的经营维度和期间", "对应原始证据及口径", "与 B4 和估值驱动的因果衔接"],
        ),
        "REVIEW_INDEPENDENCE_UNRESOLVED": (
            "OBTAIN_INDEPENDENT_REVIEW",
            "INDEPENDENT_REVIEWER",
            "由与主张编制人不同、无已知利益冲突的审核人重新审核，并保留角色、关系和冲突声明。",
            ["不同审核人身份声明", "独立关系声明", "无已知利益冲突声明及完整 B71 检查项"],
        ),
        "HUMAN_REVIEW_PARTIAL": (
            "COMPLETE_PARTIAL_SEMANTIC_REVIEW",
            "INDEPENDENT_REVIEWER",
            "定位未被来源支持的子项，拆分主张或补齐原始材料后重新逐项审核。",
            ["未支持子项清单", "新增来源引用", "完整必检项 PASS 或明确否定结论"],
        ),
        "HUMAN_REVIEW_UNABLE_TO_VERIFY": (
            "RESOLVE_UNVERIFIABLE_CLAIM",
            "CLAIM_OWNER_AND_INDEPENDENT_REVIEWER",
            "查明无法核验的具体原因；无法取得原件或核对不了关键事实时，不得将该主张计为支持。",
            ["可核验原始材料", "明确的范围/时间/单位", "重新审核结论"],
        ),
        "HUMAN_REVIEW_BLOCKED_OR_INCOMPLETE": (
            "COMPLETE_OR_REPAIR_SEMANTIC_REVIEW",
            "INDEPENDENT_REVIEWER",
            "修复审核记录的必检项、来源映射、时间、角色或身份关系缺失；不能用未完成审核替代支持。",
            ["完整 B71 审核记录", "所有必检项和来源映射", "有效的时间及独立性声明"],
        ),
        "SEMANTIC_REVIEW_DUPLICATE_OR_AMBIGUOUS": (
            "RESOLVE_DUPLICATE_REVIEWS",
            "REVIEW_COORDINATOR",
            "为一个 B70 主张保留唯一审核记录；多份冲突审核先解释差异，不能择取有利结论。",
            ["唯一 review_id / record_id 映射", "冲突审核差异说明", "最终唯一审核结论"],
        ),
        "REQUIRED_OR_EVIDENCE_VALUE_NOT_IDENTIFIABLE": (
            "IDENTIFY_REQUIREMENT_OR_CLAIM_VALUE",
            "RESEARCHER",
            "补齐门槛值或证据值所需的期间、单位、数值与基础口径；没有可核实值时保持 UNKNOWN。",
            ["有限且同口径的数值", "明确单位/期间/数据类别", "B70 可复核比较结果"],
        ),
    }
    key, owner, action, closure = plans.get(
        final_status,
        (
            "REVIEW_UNRESOLVED_OPERATING_REQUIREMENT",
            "RESEARCHER_AND_OPERATING_OWNER",
            "核实该项经营要求的证据、口径和执行路径；在问题解决前不把它视为已通过。",
            ["可追溯的原始证据", "明确的整改责任人和执行计划", "重新生成并复核 B72 结果"],
        ),
    )
    return {
        "action_id": f"B72:{claim_type}:{requirement_label}",
        "remediation_type": key,
        "status": "OPEN_REMEDIATION_REQUIRED",
        "owner_role": owner,
        "next_action": action,
        "closure_evidence_required": closure,
        "automatically_closed": False,
    }


def _semantic_final_status(evidence_state: str, semantic_state: str) -> str:
    if semantic_state == "HUMAN_REVIEW_CONTRADICTS_OR_DOES_NOT_SUPPORT_CLAIM":
        return "CLAIM_CONTRADICTED_BY_HUMAN_REVIEW"
    if evidence_state == "LINKED_VALUE_FAILS_NUMERICAL_REQUIREMENT":
        return "QUANTIFIED_REQUIREMENT_GAP"
    if evidence_state == "LINKED_FUNDING_SHORTFALL":
        return "INCREMENTAL_FUNDING_SHORTFALL"
    if evidence_state == "CAPACITY_AVAILABLE_TOO_LATE":
        return "EXPANSION_AVAILABLE_AFTER_FORECAST_PERIOD"
    if evidence_state == "ANALYST_ASSUMPTION_ONLY_NOT_CORROBORATION":
        return "ANALYST_ASSUMPTION_ONLY_NOT_CORROBORATION"
    if evidence_state == "EVIDENCE_NOT_PROVIDED":
        return "EVIDENCE_NOT_PROVIDED"
    if evidence_state == "EVIDENCE_LINKAGE_NOT_ELIGIBLE":
        return "EVIDENCE_LINKAGE_NOT_ELIGIBLE"
    if evidence_state == "EVIDENCE_RECORD_SCOPE_MISMATCH":
        return "EVIDENCE_RECORD_SCOPE_MISMATCH"
    if evidence_state == "AMBIGUOUS_DUPLICATE_CLAIMS_NOT_SUMMED":
        return "AMBIGUOUS_DUPLICATE_CLAIMS_NOT_SUMMED"
    if evidence_state == "REQUIRED_OR_EVIDENCE_VALUE_NOT_IDENTIFIABLE":
        return "REQUIRED_OR_EVIDENCE_VALUE_NOT_IDENTIFIABLE"
    if evidence_state == "LINKED_VALUE_COVERS_NUMERICAL_REQUIREMENT":
        if semantic_state == "HUMAN_REVIEW_SUPPORTED_CONDITIONALLY":
            return "CONDITIONALLY_SUPPORTED_NOT_FORMALLY_ADMITTED"
        if semantic_state == "SEMANTIC_REVIEW_NOT_PROVIDED":
            return "NUMERICAL_LINKAGE_ONLY_REVIEW_PENDING"
        if semantic_state == "REVIEW_INDEPENDENCE_UNRESOLVED":
            return "REVIEW_INDEPENDENCE_UNRESOLVED"
        if semantic_state == "HUMAN_REVIEW_PARTIAL":
            return "HUMAN_REVIEW_PARTIAL"
        if semantic_state == "HUMAN_REVIEW_UNABLE_TO_VERIFY":
            return "HUMAN_REVIEW_UNABLE_TO_VERIFY"
        if semantic_state == "SEMANTIC_REVIEW_DUPLICATE_OR_AMBIGUOUS":
            return "SEMANTIC_REVIEW_DUPLICATE_OR_AMBIGUOUS"
        return "HUMAN_REVIEW_BLOCKED_OR_INCOMPLETE"
    if semantic_state == "REVIEW_INDEPENDENCE_UNRESOLVED":
        return "REVIEW_INDEPENDENCE_UNRESOLVED"
    if semantic_state == "HUMAN_REVIEW_PARTIAL":
        return "HUMAN_REVIEW_PARTIAL"
    if semantic_state == "HUMAN_REVIEW_UNABLE_TO_VERIFY":
        return "HUMAN_REVIEW_UNABLE_TO_VERIFY"
    if semantic_state == "SEMANTIC_REVIEW_DUPLICATE_OR_AMBIGUOUS":
        return "SEMANTIC_REVIEW_DUPLICATE_OR_AMBIGUOUS"
    if semantic_state == "HUMAN_REVIEW_BLOCKED_OR_INCOMPLETE":
        return "HUMAN_REVIEW_BLOCKED_OR_INCOMPLETE"
    if evidence_state == "UNCLASSIFIED_OR_UNRESOLVED":
        return "REQUIRED_OR_EVIDENCE_VALUE_NOT_IDENTIFIABLE"
    return "NOT_IDENTIFIABLE"


def _make_requirement_row(
    *,
    scenario: str,
    lens: str,
    segment_id: str,
    product_id: str,
    period: str,
    requirement_type: str,
    raw_status: str,
    required_value: Any = None,
    evidence_value: Any = None,
    unit: str = "UNKNOWN",
    record_ids: list[str] | None = None,
    by_id: Mapping[str, list[Mapping[str, Any]]],
    by_key: Mapping[tuple[str, str, str, str], list[Mapping[str, Any]]],
    reviews_by_record: Mapping[str, list[Mapping[str, Any]]],
    b71_available: bool,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record_ids = [item for item in (record_ids or []) if _txt(item)]
    claim_types = (requirement_type,) if requirement_type in _CLAIM_UNITS else ()
    records, ambiguous, scope_mismatch = _records_for_claim(
        record_ids=record_ids,
        by_id=by_id,
        by_key=by_key,
        scenario=scenario,
        product_id=product_id,
        period=period,
        claim_types=claim_types,
    )
    semantic_state, reviews = _semantic_review_state(
        records, reviews_by_record, b71_available=b71_available
    )
    evidence_state = _evidence_state(
        raw_status, records=records, ambiguous=ambiguous, scope_mismatch=scope_mismatch
    )
    final_status = _semantic_final_status(evidence_state, semantic_state)
    record_ids_out = sorted({
        _txt(row.get("record_id")) for row in records if _txt(row.get("record_id"))
    })
    refs = sorted({
        str(ref).strip()
        for row in records
        for ref in (row.get("evidence_refs") if isinstance(row.get("evidence_refs"), list) else [])
        if str(ref).strip()
    })
    review_ids = sorted({
        _txt(row.get("review_id")) for row in reviews if _txt(row.get("review_id"))
    })
    independent = bool(reviews) and all(
        row.get("review_independence_conditionally_declared") is True
        for row in reviews
    )
    label = f"{scenario}:{lens}:{segment_id}:{product_id}:{requirement_type}"
    row = {
        "requirement_id": label,
        "scenario": scenario,
        "lens": lens,
        "segment_id": segment_id,
        "product_id": product_id,
        "requirement_type": requirement_type,
        "required_value": required_value,
        "evidence_value": evidence_value,
        "unit": unit,
        "b70_comparison_status": raw_status,
        "evidence_linkage_status": evidence_state,
        "b70_record_ids": record_ids_out,
        "evidence_refs": refs,
        "semantic_review_status": semantic_state,
        "b71_review_ids": review_ids,
        "review_independence_conditionally_declared": independent,
        "exception_status": final_status,
        "requirement_is_operationally_proven": False,
        "formal_evidence_pit_admission": False,
        "remediation": _remediation(
            final_status,
            claim_type=requirement_type,
            requirement_label=label,
        ),
    }
    if extra:
        row["details"] = dict(extra)
    return row


def _capacity_arithmetic_row(
    *,
    scenario: str,
    lens: str,
    segment_id: str,
    product: Mapping[str, Any],
    b71_available: bool,
) -> dict[str, Any]:
    status = _txt(product.get("capacity_status")).upper()
    if status == "EXCEEDS_NAMEPLATE_CAPACITY":
        final_status = "NAMEPLATE_CAPACITY_CONSTRAINT"
    elif status == "NOT_FEASIBLE_NEGATIVE_REQUIRED_PRODUCTION":
        final_status = "INVALID_NEGATIVE_REQUIRED_PRODUCTION"
    elif status == "WITHIN_NAMEPLATE_CAPACITY_CONDITIONAL":
        final_status = "CONDITIONAL_NAMEPLATE_FIT_ONLY"
    else:
        final_status = "CAPACITY_NOT_IDENTIFIABLE"
    product_id = _txt(product.get("product_id")) or "UNKNOWN"
    label = f"{scenario}:{lens}:{segment_id}:{product_id}:B69_NAMEPLATE_CAPACITY"
    lineage = _map(product.get("capacity_measure_lineage"))
    return {
        "requirement_id": label,
        "scenario": scenario,
        "lens": lens,
        "segment_id": segment_id,
        "product_id": product_id,
        "requirement_type": "B69_NAMEPLATE_CAPACITY_ARITHMETIC",
        "required_value": product.get("required_production_tonnes_under_unchanged_inventory_movement"),
        "evidence_value": product.get("nameplate_capacity_tonnes_per_year"),
        "unit": "tonnes/year",
        "b70_comparison_status": status or "UNKNOWN",
        "evidence_linkage_status": "B69_CONDITIONAL_NAMEPLATE_ARITHMETIC_ONLY",
        "b70_record_ids": [],
        "evidence_refs": list(lineage.get("evidence_refs") or []),
        "semantic_review_status": "NOT_APPLICABLE_TO_B69_ARITHMETIC",
        "b71_review_ids": [],
        "review_independence_conditionally_declared": False,
        "exception_status": final_status,
        "required_capacity_utilization": product.get("required_capacity_utilization"),
        "remaining_nameplate_capacity_tonnes": product.get("remaining_nameplate_capacity_tonnes"),
        "inventory_policy_assumption": product.get("inventory_policy_assumption"),
        "requirement_is_operationally_proven": False,
        "formal_evidence_pit_admission": False,
        "remediation": _remediation(
            final_status,
            claim_type="B69_NAMEPLATE_CAPACITY",
            requirement_label=label,
        ),
    }


def _uncovered_dimension_row(
    *,
    scenario: str,
    lens: str,
    segment_id: str,
    product: Mapping[str, Any],
    dimension: str,
    source_status: Any,
) -> dict[str, Any]:
    product_id = _txt(product.get("product_id")) or "UNKNOWN"
    label = f"{scenario}:{lens}:{segment_id}:{product_id}:{dimension}"
    final_status = "NOT_IDENTIFIABLE_UNCOVERED_DIMENSION"
    return {
        "requirement_id": label,
        "scenario": scenario,
        "lens": lens,
        "segment_id": segment_id,
        "product_id": product_id,
        "requirement_type": dimension,
        "required_value": None,
        "evidence_value": None,
        "unit": "NOT_QUANTIFIED",
        "b70_comparison_status": _txt(source_status) or "UNKNOWN",
        "evidence_linkage_status": "NO_COMPLETE_TYPED_CLAIM_FOR_FULL_DIMENSION",
        "b70_record_ids": [],
        "evidence_refs": [],
        "semantic_review_status": "NOT_COVERED_BY_B71",
        "b71_review_ids": [],
        "review_independence_conditionally_declared": False,
        "exception_status": final_status,
        "requirement_is_operationally_proven": False,
        "formal_evidence_pit_admission": False,
        "remediation": _remediation(
            final_status,
            claim_type=dimension,
            requirement_label=label,
        ),
    }


def _summarize(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in rows:
        key = _txt(row.get("exception_status")) or "UNKNOWN"
        counts[key] = counts.get(key, 0) + 1
    return {
        "requirement_row_count": len(rows),
        "status_counts": counts,
        "open_remediation_count": sum(
            _map(row.get("remediation")).get("status") == "OPEN_REMEDIATION_REQUIRED"
            for row in rows
        ),
        "supported_count_is_not_formal_admission": True,
    }


def build_operating_feasibility_exception_register(
    *,
    b69_audit: Mapping[str, Any],
    b70_assessment: Mapping[str, Any],
    b71_review: Mapping[str, Any],
) -> dict[str, Any]:
    """Build per-scenario/per-lens exceptions with explicit human remediation."""
    result: dict[str, Any] = {
        "schema_version": B72_SCHEMA,
        "status": "INPUT_SCHEMA_BLOCKED",
        "scenarios": {},
        "requirement_rows": [],
        "summary": {},
        "overall_operational_feasibility_status": (
            "NOT_IDENTIFIABLE_PENDING_COMPLETE_OPERATING_COVERAGE_AND_FORMAL_ADMISSION"
        ),
        "formal_evidence_pit_admission_created": False,
        "forecast_or_valuation_admission_created": False,
        "b4_or_b68_inputs_modified": False,
        "sotp_or_mie_modified": False,
        "required_return_or_target_entry_modified": False,
        "portfolio_constraints_or_decision_modified": False,
        "decision_authority": False,
        "execution_authority": False,
        "cross_lens_aggregation_performed": False,
        "non_additive_lenses_preserved": True,
        "limitations": [
            "B61 单段利润门槛与 B63 全 B4 利润向量门槛是替代分析视角；B72 在每个情景下分别汇总，不相加、不平均、不赋概率。",
            "B70 数值覆盖只代表链接主张的数值达到或未达到门槛；B71 是人工审核声明。二者均不自动构成正式 Evidence/PIT 准入。",
            "缺失证据、审核缺失或未覆盖维度是 UNKNOWN/覆盖缺口，不是反证；只有明确的数值缺口或人工审核反证才标记为相应问题。",
            "B69 名义产能内仅代表在既定库存移动假设下算术未超名义产能，不代表有效产能、需求、良率、爬坡或现金流可执行。",
            "整改记录只生成责任角色、下一步和关闭证据要求；本批不自动关闭任务，不替代操作者对原始材料的核验。",
            "本节点不更改 B4/B42/B43/B55/B61-B71、SOTP、MIE、15% 年化收益门槛、目标入场价、组合约束或 Decision。",
        ],
    }
    if _txt(_map(b69_audit).get("schema_version")) != B69_SCHEMA:
        result["issues"] = ["B69_SCHEMA_MISSING_OR_MISMATCH"]
        return result
    if _txt(_map(b70_assessment).get("schema_version")) != B70_SCHEMA:
        result["issues"] = ["B70_SCHEMA_MISSING_OR_MISMATCH"]
        return result
    if _txt(_map(b71_review).get("schema_version")) != B71_SCHEMA:
        result["issues"] = ["B71_SCHEMA_MISSING_OR_MISMATCH"]
        return result

    by_id, by_key = _record_indexes(b70_assessment)
    reviews_by_record = _review_index(b71_review)
    forecast_period = _txt(b69_audit.get("forecast_period")) or "UNKNOWN"
    b70_scenarios = _map(b70_assessment.get("scenarios"))
    for scenario in _SCENARIOS:
        b69_scenario = _map(_map(b69_audit.get("scenarios")).get(scenario))
        b70_scenario = _map(b70_scenarios.get(scenario))
        b69_lenses = _rows(b69_scenario.get("requirement_lenses"))
        b70_lenses = _rows(b70_scenario.get("requirement_lenses"))
        lens_outputs: list[dict[str, Any]] = []
        for b69_lens in b69_lenses:
            lens_name = _txt(b69_lens.get("lens")) or "UNKNOWN"
            segment_id = _txt(b69_lens.get("segment_id")) or "UNKNOWN"
            b70_lens_matches = [
                row for row in b70_lenses
                if _txt(row.get("lens")) == lens_name
                and _txt(row.get("segment_id")) == segment_id
            ]
            b70_lens = b70_lens_matches[0] if len(b70_lens_matches) == 1 else {}
            b70_products = {
                _txt(row.get("product_id")): row
                for row in _rows(b70_lens.get("products"))
                if _txt(row.get("product_id"))
            }
            products_out: list[dict[str, Any]] = []
            lens_rows: list[Mapping[str, Any]] = []
            for b69_product in _rows(b69_lens.get("products")):
                product_id = _txt(b69_product.get("product_id")) or "UNKNOWN"
                b70_product = _map(b70_products.get(product_id))
                product_rows: list[dict[str, Any]] = []
                for comparison in _rows(b70_product.get("comparisons")):
                    claim_type = _txt(comparison.get("claim_type")).upper() or "UNKNOWN"
                    if claim_type not in _CLAIM_UNITS:
                        continue
                    record_ids = [_txt(comparison.get("record_id"))] if _txt(comparison.get("record_id")) else []
                    row = _make_requirement_row(
                        scenario=scenario,
                        lens=lens_name,
                        segment_id=segment_id,
                        product_id=product_id,
                        period=forecast_period,
                        requirement_type=claim_type,
                        raw_status=_txt(comparison.get("status")) or "UNKNOWN",
                        required_value=comparison.get("required_value"),
                        evidence_value=comparison.get("evidence_value"),
                        unit=_CLAIM_UNITS[claim_type],
                        record_ids=record_ids,
                        by_id=by_id,
                        by_key=by_key,
                        reviews_by_record=reviews_by_record,
                        b71_available=True,
                        extra={
                            "comparison_direction": comparison.get("comparison_direction"),
                            "basis": comparison.get("basis"),
                            "record_issues": comparison.get("record_issues") or [],
                        },
                    )
                    product_rows.append(row)
                    lens_rows.append(row)
                    result["requirement_rows"].append(row)

                date_comparison = _map(b70_product.get("capacity_available_date_comparison"))
                if date_comparison:
                    row = _make_requirement_row(
                        scenario=scenario,
                        lens=lens_name,
                        segment_id=segment_id,
                        product_id=product_id,
                        period=forecast_period,
                        requirement_type="CAPACITY_AVAILABLE_DATE",
                        raw_status=_txt(date_comparison.get("status")) or "UNKNOWN",
                        required_value=date_comparison.get("required_by_date"),
                        evidence_value=date_comparison.get("evidence_value"),
                        unit="date",
                        record_ids=[_txt(date_comparison.get("record_id"))] if _txt(date_comparison.get("record_id")) else [],
                        by_id=by_id,
                        by_key=by_key,
                        reviews_by_record=reviews_by_record,
                        b71_available=True,
                        extra={"required_by_date": date_comparison.get("required_by_date")},
                    )
                    product_rows.append(row)
                    lens_rows.append(row)
                    result["requirement_rows"].append(row)

                for funding in _rows(b70_product.get("incremental_funding_comparisons")):
                    funding_type = _txt(funding.get("funding_type")).upper()
                    if funding_type == "INCREMENTAL_CAPEX_REQUIRED":
                        claim_types = ("INCREMENTAL_CAPEX_REQUIRED", "INCREMENTAL_CAPEX_FUNDED")
                    elif funding_type == "INCREMENTAL_WORKING_CAPITAL_REQUIRED":
                        claim_types = (
                            "INCREMENTAL_WORKING_CAPITAL_REQUIRED",
                            "INCREMENTAL_WORKING_CAPITAL_FUNDED",
                        )
                    else:
                        continue
                    record_ids = [
                        _txt(funding.get("required_record_id")),
                        _txt(funding.get("funded_record_id")),
                    ]
                    records, ambiguous, scope_mismatch = _records_for_claim(
                        record_ids=[item for item in record_ids if item],
                        by_id=by_id,
                        by_key=by_key,
                        scenario=scenario,
                        product_id=product_id,
                        period=forecast_period,
                        claim_types=claim_types,
                    )
                    semantic_state, semantic_reviews = _semantic_review_state(
                        records, reviews_by_record, b71_available=True
                    )
                    evidence_state = _evidence_state(
                        funding.get("status"), records=records, ambiguous=ambiguous,
                        scope_mismatch=scope_mismatch,
                    )
                    final_status = _semantic_final_status(evidence_state, semantic_state)
                    label = f"{scenario}:{lens_name}:{segment_id}:{product_id}:{funding_type}"
                    refs = sorted({
                        str(ref).strip()
                        for record in records
                        for ref in (record.get("evidence_refs") if isinstance(record.get("evidence_refs"), list) else [])
                        if str(ref).strip()
                    })
                    row = {
                        "requirement_id": label,
                        "scenario": scenario,
                        "lens": lens_name,
                        "segment_id": segment_id,
                        "product_id": product_id,
                        "requirement_type": funding_type,
                        "required_value": funding.get("required_amount_cny"),
                        "evidence_value": funding.get("funded_amount_cny"),
                        "unit": "CNY",
                        "b70_comparison_status": _txt(funding.get("status")) or "UNKNOWN",
                        "evidence_linkage_status": evidence_state,
                        "b70_record_ids": sorted({
                            _txt(record.get("record_id")) for record in records if _txt(record.get("record_id"))
                        }),
                        "evidence_refs": refs,
                        "semantic_review_status": semantic_state,
                        "b71_review_ids": sorted({
                            _txt(review.get("review_id")) for review in semantic_reviews if _txt(review.get("review_id"))
                        }),
                        "review_independence_conditionally_declared": bool(semantic_reviews) and all(
                            review.get("review_independence_conditionally_declared") is True
                            for review in semantic_reviews
                        ),
                        "exception_status": final_status,
                        "requirement_is_operationally_proven": False,
                        "formal_evidence_pit_admission": False,
                        "remediation": _remediation(
                            final_status,
                            claim_type=funding_type,
                            requirement_label=label,
                        ),
                    }
                    if ambiguous or scope_mismatch:
                        row["details"] = {
                            "duplicate_record_scope": "AMBIGUOUS_NOT_SUMMED" if ambiguous else None,
                            "evidence_record_scope_mismatch": scope_mismatch,
                        }
                    product_rows.append(row)
                    lens_rows.append(row)
                    result["requirement_rows"].append(row)

                capacity_row = _capacity_arithmetic_row(
                    scenario=scenario,
                    lens=lens_name,
                    segment_id=segment_id,
                    product=b69_product,
                    b71_available=True,
                )
                product_rows.append(capacity_row)
                lens_rows.append(capacity_row)
                result["requirement_rows"].append(capacity_row)

                # B69's broader demand/pricing/cost findings are deliberately
                # retained as uncovered dimensions even if a narrow B70 claim
                # numerically covers a single-driver threshold.
                for dimension, source_key in (
                    ("CUSTOMER_DEMAND_SUSTAINABILITY_AND_ELASTICITY", "demand_feasibility_status"),
                    ("PRICE_ELASTICITY_AND_COMPETITIVE_RESPONSE", "pricing_feasibility_status"),
                    ("COST_CURVE_AND_SAVINGS_EXECUTION", "unit_cost_feasibility_status"),
                ):
                    uncovered = _uncovered_dimension_row(
                        scenario=scenario,
                        lens=lens_name,
                        segment_id=segment_id,
                        product=b69_product,
                        dimension=dimension,
                        source_status=b69_product.get(source_key),
                    )
                    product_rows.append(uncovered)
                    lens_rows.append(uncovered)
                    result["requirement_rows"].append(uncovered)

                products_out.append({
                    "product_id": product_id,
                    "requirements": product_rows,
                    "summary": _summarize(product_rows),
                    "b69_unmodified_capacity_status": b69_product.get("capacity_status"),
                    "b69_unmodified_demand_status": b69_product.get("demand_feasibility_status"),
                    "b69_unmodified_pricing_status": b69_product.get("pricing_feasibility_status"),
                    "b69_unmodified_unit_cost_status": b69_product.get("unit_cost_feasibility_status"),
                    "non_additive_driver_alternatives": True,
                })
            lens_outputs.append({
                "segment_id": segment_id,
                "lens": lens_name,
                "non_additive": True,
                "products": products_out,
                "summary": _summarize(lens_rows),
            })
        result["scenarios"][scenario] = {
            "scenario": scenario,
            "requirement_lenses": lens_outputs,
            "cross_lens_aggregation_performed": False,
        }

    result["status"] = "OPERATING_FEASIBILITY_EXCEPTION_REGISTER_BUILT"
    result["summary"] = {
        "scenario_count": len(result["scenarios"]),
        "lens_count_by_scenario": {
            scenario: len(_rows(_map(result["scenarios"].get(scenario)).get("requirement_lenses")))
            for scenario in _SCENARIOS
        },
        "requirement_row_count_including_alternative_lenses": len(result["requirement_rows"]),
        "counts_are_not_distinct_economic_obligations": True,
        "cross_lens_aggregation_performed": False,
        "all_remediation_tasks_start_open": True,
        "no_exception_is_automatically_closed": True,
    }
    return result
