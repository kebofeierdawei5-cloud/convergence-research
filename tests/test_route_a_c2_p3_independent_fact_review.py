from datetime import datetime

from tools.route_a_c2_p3_independent_fact_review import (
    CUTOFF, conservative_known_at, reuse_rights_cleared
)

def test_public_access_does_not_imply_reuse_or_retention_rights():
    assert reuse_rights_cleared("PUBLIC_ACCESS_REUSE_UNKNOWN") is False
    assert reuse_rights_cleared("UNKNOWN") is False
    assert reuse_rights_cleared("PERMITTED_INTERNAL_USE") is True
    assert reuse_rights_cleared("UNKNOWN", "explicit private retention grant") is True

def test_date_only_publication_uses_conservative_end_of_day_bound():
    assert conservative_known_at("2026-08-20").isoformat() == "2026-08-20T23:59:59+08:00"
    assert conservative_known_at("2026-08-20") <= CUTOFF
    assert conservative_known_at("2026-10-09") > CUTOFF

def test_cutoff_is_midnight_not_end_of_observation_day():
    assert datetime.fromisoformat("2026-10-09T23:59:59+08:00") > CUTOFF
