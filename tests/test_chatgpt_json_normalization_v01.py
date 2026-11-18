from __future__ import annotations

import pytest

from iios_mvp.local_investment_pilot_v01 import (
    LocalInvestmentPilotError,
    _extract_json_object,
)


def test_extract_json_object_normalizes_chatgpt_smart_quotes():
    source = (
        '{“response_mode”: “IIOS-RESEARCH-PATCH-0.1”, '
        '“research”: {“assessment”: {“trust”: {“status”: “UNKNOWN”}}}}'
    )

    result = _extract_json_object(source)

    assert result == {
        "response_mode": "IIOS-RESEARCH-PATCH-0.1",
        "research": {"assessment": {"trust": {"status": "UNKNOWN"}}},
    }


def test_extract_json_object_quotes_bare_javascript_object_keys():
    source = (
        '{response_mode: "IIOS-RESEARCH-PATCH-0.1", '
        'research: {assessment: {trust: {status: "UNKNOWN"}}}}'
    )

    result = _extract_json_object(source)

    assert result["response_mode"] == "IIOS-RESEARCH-PATCH-0.1"
    assert result["research"]["assessment"]["trust"]["status"] == "UNKNOWN"


def test_extract_json_object_normalizes_fullwidth_separators_only_outside_strings():
    source = (
        '{“response_mode”： “IIOS-RESEARCH-PATCH-0.1”， '
        '“research”： {“assessment”： {“trust”： {“status”： “UNKNOWN”}}}}'
    )

    result = _extract_json_object(source)

    assert result["research"]["assessment"]["trust"]["status"] == "UNKNOWN"


def test_extract_json_object_preserves_curly_quotes_inside_valid_json_strings():
    source = (
        '{"response_mode":"IIOS-RESEARCH-PATCH-0.1",'
        '"research":{"note":"保留“这段引号”原样"}}'
    )

    result = _extract_json_object(source)

    assert result["research"]["note"] == "保留“这段引号”原样"


def test_extract_json_object_accepts_literal_escape_wrapper_from_copy():
    source = (
        '<escape>{"response_mode":"IIOS-RESEARCH-PATCH-0.1",'
        '"research":{"status":"UNKNOWN"}}</escape>'
    )

    result = _extract_json_object(source)

    assert result["response_mode"] == "IIOS-RESEARCH-PATCH-0.1"


def test_extract_json_object_does_not_guess_invalid_values_after_key_normalization():
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_JSON_INVALID"):
        _extract_json_object('{response_mode: undefined, research: {}}')
