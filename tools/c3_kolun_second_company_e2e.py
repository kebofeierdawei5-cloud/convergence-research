from iios_mvp.store import (
    apply_monitoring_event,
    approve_revision,
    create_or_load_series,
    replay_decision_lifecycle,
    write_decision_revision,
    write_monitoring_validation,
    write_snapshot,
    write_trigger_contract,
    write_trigger_event,
    initialize_monitoring_state,
)
from iios_mvp.engine import sha256_obj

ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / "examples/real_cases/RC-CN-A-002422-20261004_c3_input.json"
PRICE_CAPTURE_PATH = (
    ROOT
    / "evidence/real_cases/RC-CN-A-002422-20261004/c3_price_capture.txt"
)
CASE_ID = "RC-CN-A-002422-20261004"
CUTOFF = date(2026, 10, 4)
PRICE = Decimal("40.85")
PRICE_EVIDENCE_SHA = "b59d6844530261896569dcd071f2fecb670fc26ad162a6ecbf31ccca1f464d7f"
AUTHORITY_REGISTRY: InMemoryCanonicalInvestmentAdmissionRegistry | None = None


def load_case_fixture() -> dict[str, Any]:
    payload = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    if payload["case_id"] != CASE_ID:
        raise ValueError("C3 fixture case_id mismatch")
    return payload