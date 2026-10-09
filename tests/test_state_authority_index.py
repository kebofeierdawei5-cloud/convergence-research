from pathlib import Path

STATE = Path("docs/PROJECT_STATE_INDEX.md")

def test_state_index_declares_single_current_authority():
    text = STATE.read_text(encoding="utf-8")
    assert "Snapshot: 2026-10-09" in text
    assert text.count("## CURRENT ACTIVE DEVELOPMENT AUTHORITY — 2026-10-09") == 1
    assert "**Current canonical main:**" in text


def test_current_authority_points_to_b2d_live_gate():
    text = STATE.read_text(encoding="utf-8")
    start = text.index("## CURRENT ACTIVE DEVELOPMENT AUTHORITY")
    end = text.index("## 2. Investment Core capability boundary")
    current = text[start:end]
    assert "B2-D Canonical Refresh + Live Provider Boundary" in current
    assert "B2-D Live Provider Invocation / Evidence                BLOCKED" in current
    assert "B2-D" in current and "B2-E" in current and "B2-F" in current

def test_current_next_batch_prioritizes_free_first_company_evidence():
    text = STATE.read_text(encoding="utf-8")
    start = text.index("### Current next development batch")
    end = text.index("### Explicit non-blockers", start)
    current = text[start:end]
    assert "Route A — free-first single-company evidence intake" in current
    assert "operator-supplied raw originals" in current
    assert "B2-D LIVE remains a separately tracked model-integration gate" in current
    assert "NOT_ADMITTED" in current


def test_stale_pilot_next_sequence_is_marked_historical():
    text = STATE.read_text(encoding="utf-8")
    section9_start = text.index("## 9. Historical MVP / Research boundary record")
    section10_start = text.index("## 10. A02 Runtime Evidence")
    section9 = text[section9_start:section10_start]
    assert "PILOT-00 → PILOT-01 → PILOT-02 → PILOT-03 → PILOT-04 → MVP Pilot Acceptance" not in section9


def test_historical_sections_are_explicitly_time_local():
    text = STATE.read_text(encoding="utf-8")
    marker = "> **Historical-record notice:** Sections 12–24 preserve immutable milestone records."
    assert marker in text
