from __future__ import annotations

from typing import Any

from .valuation import route_model

LEVELS = {"NONE", "LOW", "MEDIUM", "HIGH"}
MATERIALITY = {"LOW", "MEDIUM", "HIGH"}
NODE_TYPES = {
    "operating_business",
    "subsidiary",
    "pipeline",
    "investment_asset",
    "cash",
    "debt",
    "minority_interest",
    "financial",
}
ATTRIBUTE_FIELDS = (
    "earnings_stability",
    "cash_flow_visibility",
    "capital_intensity",
    "cyclicality",
    "asset_intensity",
    "reinvestment_intensity",
    "payout_characteristic",
    "pipeline_optionality",
    "maturity",
)

NON_OPERATING = {"investment_asset", "cash", "debt", "minority_interest"}


def _level(value: Any, field: str) -> str:
    result = str(value or "").strip().upper()
    if result not in LEVELS:
        raise ValueError(f"{field} must be one of {sorted(LEVELS)}")
    return result


def _materiality(value: Any, field: str) -> str:
    result = str(value or "").strip().upper()
    if result not in MATERIALITY:
        raise ValueError(f"{field} must be one of {sorted(MATERIALITY)}")
    return result


def classify_economic_profile(node: dict[str, Any]) -> str:
    kind = str(node["node_type"]).strip().lower()
    attrs = node["economic_attributes"]
    maturity = str(attrs["maturity"]).strip().upper()
    if maturity not in {"MATURE", "COMMERCIAL", "DEVELOPMENT"}:
        raise ValueError("economic_attributes.maturity must be MATURE/COMMERCIAL/DEVELOPMENT")
    pipeline = _level(attrs["pipeline_optionality"], "economic_attributes.pipeline_optionality")
    earnings = _level(attrs["earnings_stability"], "economic_attributes.earnings_stability")
    cash_flow = _level(attrs["cash_flow_visibility"], "economic_attributes.cash_flow_visibility")
    capital = _level(attrs["capital_intensity"], "economic_attributes.capital_intensity")
    cyclical = _level(attrs["cyclicality"], "economic_attributes.cyclicality")
    asset = _level(attrs["asset_intensity"], "economic_attributes.asset_intensity")
    payout = _level(attrs["payout_characteristic"], "economic_attributes.payout_characteristic")

    if kind == "pipeline" or pipeline == "HIGH" or maturity == "DEVELOPMENT":
        return "innovative_drug_pipeline"
    if kind == "operating_business" and maturity == "COMMERCIAL" and pipeline in {"MEDIUM", "HIGH"}:
        return "innovative_drug_commercial"
    if kind == "investment_asset":
        return "asset_heavy"
    if kind == "operating_business" and cyclical == "HIGH" and asset == "HIGH":
        return "cyclical_asset_heavy"
    if cyclical == "HIGH":
        return "cyclical"
    if kind == "financial" or (kind == "operating_business" and payout == "HIGH" and asset == "LOW"):
        return "dividend_financial"
    if asset == "HIGH":
        return "asset_heavy"
    if earnings == "HIGH" and cash_flow == "HIGH" and capital in {"LOW", "MEDIUM"}:
        return "mature_cash_earning_business"
    if cash_flow == "HIGH":
        return "cash_flow_business"
    if capital == "HIGH":
        return "enterprise_operating_business"
    return "mature_earnings"


def _core_reason(node: dict[str, Any], profile: str) -> list[str]:
    attrs = node["economic_attributes"]
    reasons: list[str] = []
    if node["materiality"] == "HIGH":
        reasons.append("HIGH_MATERIALITY")
    if node["node_type"] in {"pipeline", "investment_asset", "subsidiary"}:
        reasons.append(f"STRUCTURAL_{node['node_type'].upper()}")
    if attrs["pipeline_optionality"] in {"MEDIUM", "HIGH"}:
        reasons.append("PIPELINE_OPTIONALITY")
    if attrs["cyclicality"] == "HIGH":
        reasons.append("CYCLICALITY")
    if attrs["capital_intensity"] == "HIGH":
        reasons.append("CAPITAL_INTENSIVE")
    if profile not in {"mature_earnings", "mature_cash_earning_business"}:
        reasons.append("NON_STANDARD_ECONOMIC_PROFILE")
    return reasons or ["PRIMARY_OPERATING_VALUE_DRIVER"]


def _validate_node(node: Any, index: int) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise ValueError(f"company_value_core.nodes[{index}] must be an object")
    for field in ("id", "name", "node_type", "materiality", "economic_attributes"):
        if not node.get(field):
            raise ValueError(f"company_value_core.nodes[{index}].{field} is required")
    node_id = str(node["id"]).strip()
    node_type = str(node["node_type"]).strip().lower()
    if node_type not in NODE_TYPES:
        raise ValueError(f"company_value_core.nodes[{index}].node_type unsupported: {node_type}")
    materiality = _materiality(node["materiality"], f"company_value_core.nodes[{index}].materiality")
    attrs = node["economic_attributes"]
    if not isinstance(attrs, dict):
        raise ValueError(f"company_value_core.nodes[{index}].economic_attributes must be an object")
    for field in ATTRIBUTE_FIELDS:
        if field not in attrs:
            raise ValueError(f"company_value_core.nodes[{index}].economic_attributes.{field} is required")
        if field != "maturity":
            _level(attrs[field], f"company_value_core.nodes[{index}].economic_attributes.{field}")
        else:
            maturity = str(attrs[field]).strip().upper()
            if maturity not in {"MATURE", "COMMERCIAL", "DEVELOPMENT"}:
                raise ValueError(
                    f"company_value_core.nodes[{index}].economic_attributes.maturity "
                    f"must be one of ['COMMERCIAL', 'DEVELOPMENT', 'MATURE']"
                )

    ownership = node.get("ownership_pct", 100)
    try:
        ownership_f = float(ownership)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"company_value_core.nodes[{index}].ownership_pct must be numeric") from exc
    if ownership_f <= 0 or ownership_f > 100:
        raise ValueError(f"company_value_core.nodes[{index}].ownership_pct must be > 0 and <= 100")

    normalized = dict(node)
    normalized["id"] = node_id
    normalized["node_type"] = node_type
    normalized["materiality"] = materiality
    normalized["ownership_pct"] = ownership_f
    normalized["economic_attributes"] = dict(attrs)
    return normalized


def scan_company_value_core(company_value_core: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(company_value_core, dict):
        raise ValueError("company_value_core must be an object")
    version = str(company_value_core.get("version", "")).strip()
    if version != "1.0":
        raise ValueError("company_value_core.version must be '1.0'")

    raw_nodes = company_value_core.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("company_value_core.nodes must be a non-empty list")

    nodes = [_validate_node(node, i) for i, node in enumerate(raw_nodes)]
    ids = [node["id"] for node in nodes]
    if len(ids) != len(set(ids)):
        raise ValueError("company_value_core.nodes.id must be unique")

    material_nodes = [node for node in nodes if node["materiality"] == "HIGH"]
    if not material_nodes:
        raise ValueError("company_value_core requires at least one HIGH-materiality node")

    enriched: list[dict[str, Any]] = []
    for node in nodes:
        profile = classify_economic_profile(node)
        route = route_model(profile)
        core = bool(
            node["materiality"] == "HIGH"
            or node["node_type"] in {"pipeline", "investment_asset", "subsidiary"}
        )
        enriched.append({
            **node,
            "derived_economic_profile": profile,
            "candidate_valuation_models": route["candidate_models"],
            "model_router_suggestion": route["candidate_models"][0],
            "independent_valuation_required": core,
            "core_value_reasons": _core_reason(node, profile) if core else ["SUPPORTING_VALUE_NODE"],
        })

    operating = [node for node in enriched if node["node_type"] not in NON_OPERATING]
    material_operating = [node for node in operating if node["materiality"] == "HIGH"]
    operating_profiles = {node["derived_economic_profile"] for node in material_operating}
    if len(operating_profiles) >= 2:
        overall_profile = "mixed_segments"
        profile_basis = "material operating nodes have heterogeneous economic profiles"
    elif material_operating:
        overall_profile = material_operating[0]["derived_economic_profile"]
        profile_basis = "single dominant operating economic profile"
    elif operating:
        overall_profile = operating[0]["derived_economic_profile"]
        profile_basis = "no HIGH-materiality operating node; first operating profile used"
    else:
        overall_profile = "asset_heavy"
        profile_basis = "value map contains only non-operating assets/claims"

    core_assets = []
    for node in enriched:
        if node["materiality"] == "HIGH" or node["node_type"] in {"pipeline", "investment_asset", "subsidiary"}:
            core_assets.append({
                "id": node["id"],
                "name": node["name"],
                "node_type": node["node_type"],
                "materiality": node["materiality"],
                "derived_economic_profile": node["derived_economic_profile"],
                "recommended_primary_model": node["recommended_primary_model"],
                "candidate_valuation_models": node["candidate_valuation_models"],
                "independent_valuation_required": node["independent_valuation_required"],
                "reasons": node["core_value_reasons"],
            })

    model_route = route_model(overall_profile)
    valuation_required = sum(1 for node in core_assets if node["independent_valuation_required"])

    return {
        "schema_version": "IIOS-VALUE-CORE-SCAN-1.0",
        "status": "PASS",
        "overall_economic_profile": overall_profile,
        "profile_basis": profile_basis,
        "model_router_input": overall_profile,
        "model_route": model_route,
        "value_construction_map": enriched,
        "value_structure": {
            "node_count": len(enriched),
            "material_node_count": len(material_nodes),
            "operating_node_count": len(operating),
            "material_operating_profiles": sorted(operating_profiles),
            "core_asset_count": len(core_assets),
            "independent_valuation_required_count": valuation_required,
        },
        "nodes": enriched,
        "core_assets": core_assets,
    }
