from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from research.b2.source_capture_plan import validate_company_source_capture_plan

ROOT = Path(__file__).resolve().parents[3]
PLAN_PATH = ROOT / "examples" / "real_cases" / "RC-CN-A-300750-20261004_b2b_capture_plan.json"
REGISTRY_PATH = ROOT / "configs" / "source_registry_v0.1.json"


def _rehash(plan: dict) -> dict:
    body = {key: value for key, value in plan.items() if key != "audit"}
    plan["audit"]["plan_sha256"] = hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return plan


class CompanySourceCapturePlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        self.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_canonical_catl_plan_is_valid_but_pending_raw(self):
        errors = validate_company_source_capture_plan(self.plan, self.registry)
        self.assertEqual(errors, [])
        self.assertEqual(self.plan["plan_status"], "BLOCKED_PENDING_RAW")
        self.assertTrue(all(item["status"] == "PENDING_RAW" for item in self.plan["capture_requirements"]))

    def test_unknown_source_ref_blocks(self):
        bad = copy.deepcopy(self.plan)
        bad["capture_requirements"][0]["source_ref"] = "NOT:REGISTERED"
        errors = validate_company_source_capture_plan(_rehash(bad), self.registry)
        self.assertTrue(any("SOURCE_REF_UNKNOWN" in item for item in errors))

    def test_missing_group_blocks(self):
        bad = copy.deepcopy(self.plan)
        bad["capture_requirements"] = [
            item for item in bad["capture_requirements"]
            if "trust_governance_events" not in item["field_groups"]
        ]
        errors = validate_company_source_capture_plan(_rehash(bad), self.registry)
        self.assertTrue(any("REQUIRED_FIELD_GROUPS_UNCOVERED" in item for item in errors))

    def test_trade_date_requires_historical_capable_source(self):
        bad = copy.deepcopy(self.plan)
        for item in bad["capture_requirements"]:
            if item["field_groups"] == ["market_price"]:
                item["source_ref"] = "WESTOCK:CSI800_CURRENT"
        errors = validate_company_source_capture_plan(_rehash(bad), self.registry)
        self.assertTrue(any("PIT_CAPABILITY_MISMATCH" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
