import json

import pytest

import tools.iios_d1a_host_liveness_probe_v01 as probe


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self._raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def read(self, limit=-1):
        return self._raw[:limit]


class FakeConnection:
    responses = {}

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port

    def request(self, method, path, headers=None):
        self.path = path

    def getresponse(self):
        value = self.responses[self.path]
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        pass


def _set_good_responses(monkeypatch):
    FakeConnection.responses = {
        "/healthz": FakeResponse({
            "status": "OK",
            "host_version": probe.HOST_VERSION,
        }),
        "/readyz": FakeResponse({
            "status": "CONFIGURED_NOT_PRODUCTION_ACCEPTED",
            "runtime_factory_configured": True,
            "runtime_is_invoked_by_readiness_probe": False,
            "human_approval_required": True,
            "auto_execution": False,
        }),
    }
    monkeypatch.setattr(probe.http.client, "HTTPConnection", FakeConnection)


def test_liveness_pass_does_not_claim_production_acceptance(monkeypatch):
    _set_good_responses(monkeypatch)
    report = probe.probe_host()
    assert report["status"] == "HOST_LIVENESS_PROBED_NOT_PRODUCTION_ACCEPTED"
    assert report["probes"]["/healthz"]["contract_pass"] is True
    assert report["probes"]["/readyz"]["contract_pass"] is True
    assert len(report["probes"]["/healthz"]["response_sha256"]) == 64
    assert report["production_host_accepted"] is False
    assert report["actual_provider_invocation_performed"] is False
    assert report["complete_run_receipt_created"] is False


def test_bad_readiness_contract_blocks(monkeypatch):
    _set_good_responses(monkeypatch)
    FakeConnection.responses["/readyz"] = FakeResponse({
        "status": "OK",
        "runtime_factory_configured": True,
        "runtime_is_invoked_by_readiness_probe": True,
        "human_approval_required": True,
        "auto_execution": False,
    })
    report = probe.probe_host()
    assert report["status"] == "BLOCKED"
    assert "readyz_CONTRACT_MISMATCH" in report["blockers"]
    assert report["production_host_accepted"] is False


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.2", "provider.example", "::1"])
def test_non_loopback_targets_are_rejected(host):
    with pytest.raises(ValueError):
        probe.probe_host(host=host)


def test_endpoint_failure_is_blocked(monkeypatch):
    _set_good_responses(monkeypatch)
    FakeConnection.responses["/healthz"] = OSError("unavailable")
    report = probe.probe_host()
    assert report["status"] == "BLOCKED"
    assert "healthz_BLOCKED" in report["blockers"]
    assert report["actual_provider_invocation_performed"] is False


def test_report_is_private_and_not_overwritten(tmp_path):
    path = tmp_path / "private" / "probe.json"
    report = {"status": "BLOCKED", "production_host_accepted": False}
    probe._write(path, report)
    assert json.loads(path.read_text(encoding="utf-8")) == report
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError, match="OUTPUT_PATH_EXISTS_OR_UNSAFE"):
        probe._write(path, report)


def test_probe_report_has_only_hashes_not_raw_responses(monkeypatch):
    _set_good_responses(monkeypatch)
    report = probe.probe_host()
    encoded = json.dumps(report)
    assert "response_sha256" in encoded
    assert "response_body" not in encoded
    assert "127.0.0.1" in encoded
