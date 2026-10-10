from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from iios_mvp.canonical_host_v01 import (
    HostConfigurationError,
    HostRequestError,
    load_host_config,
    load_trusted_bundle,
    make_handler,
    validate_bundle_id,
)


def _roots(tmp_path):
    bundles = tmp_path / "bundles"
    data = tmp_path / "data"
    output = tmp_path / "output"
    bundles.mkdir()
    data.mkdir()
    output.mkdir()
    (data / "raw").mkdir()
    (data / "manifest.json").write_text(json.dumps({"evidence": []}), encoding="utf-8")
    bundle = {
        "raw_request": "分析 605016，截至2026-10-09",
        "company": "百龙创园",
        "investment_case": {"case_id": "test-case"},
        "evidence_manifest_path": str(data / "manifest.json"),
        "evidence_root": str(data / "raw"),
        "artifact_type": "THESIS_ASSESSMENT",
        "semantic_prompt": "test-only",
        "decision_relevance": "test-only",
        "run_id": "caller-chosen-run-id",
        "request_id": "caller-chosen-request-id",
        "semantic_facts": [{"statement": "caller-controlled"}],
        "semantic_inferences": [{"statement": "caller-controlled"}],
        "semantic_assumptions": [{"text": "caller-controlled"}],
        "semantic_uncertainties": [{"text": "caller-controlled"}],
    }
    (bundles / "case-bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    return bundles, data, output


def _config(bundles, data, output, **overrides):
    base = {
        "bundle_root": bundles.resolve(),
        "data_root": data.resolve(),
        "output_root": output.resolve(),
        "token": "A" * 40,
        "factory_spec": "trusted_runtime.factory:build",
        "host": "127.0.0.1",
        "port": 8765,
        "timeout_seconds": 10,
        "version": "test",
        "loopback_only": True,
    }
    return {**base, **overrides}


def _request(handler, *, method, path, body=b"", token=None, content_type="application/json"):
    instance = object.__new__(handler)
    instance.command = method
    instance.path = path
    instance.headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(body)),
        **({"Authorization": f"Bearer {token}"} if token else {}),
    }
    instance.rfile = io.BytesIO(body)
    instance.wfile = io.BytesIO()
    instance.request_version = "HTTP/1.1"
    instance.close_connection = False
    instance._headers_buffer = []
    instance.responses = []
    instance.send_response = lambda status, message=None: instance.responses.append(status)
    instance.send_header = lambda *args: None
    instance.end_headers = lambda: None
    instance.wfile = io.BytesIO()
    return instance


def test_bundle_id_rejects_path_and_traversal():
    for value in ("../secrets", ".", "a/b", "a\\b", "", None, 3, "has space"):
        with pytest.raises(HostRequestError):
            validate_bundle_id(value)
    assert validate_bundle_id("case_605016_20261009") == "case_605016_20261009"


def test_host_configuration_fails_closed_without_runtime_factory():
    with pytest.raises(HostConfigurationError, match="HOST_CONFIG_MISSING"):
        load_host_config({})


def test_host_remote_bind_requires_tls_termination_and_explicit_allow(tmp_path):
    bundles, data, output = _roots(tmp_path)
    env = {
        "IIOS_HOST_BUNDLE_ROOT": str(bundles),
        "IIOS_HOST_DATA_ROOT": str(data),
        "IIOS_HOST_OUTPUT_ROOT": str(output),
        "IIOS_HOST_AUTH_TOKEN": "T" * 40,
        "IIOS_CANONICAL_RUNTIME_FACTORY": "trusted_runtime.factory:build",
        "IIOS_HOST_BIND": "0.0.0.0",
        "IIOS_HOST_PORT": "8765",
        "IIOS_HOST_ALLOW_REMOTE": "true",
    }
    with pytest.raises(HostConfigurationError, match="REMOTE_BIND_REQUIRES"):
        load_host_config(env)
    env["IIOS_HOST_TLS_TERMINATED"] = "true"
    config = load_host_config(env)
    assert config["loopback_only"] is False


def test_load_trusted_bundle_overwrites_ids_and_clears_caller_semantic_claims(tmp_path):
    bundles, data, _ = _roots(tmp_path)
    loaded = load_trusted_bundle(
        bundle_id="case-bundle",
        bundle_root=bundles,
        data_root=data,
    )
    assert loaded["run_id"] == "caller-chosen-run-id"  # host overwrites only when accepting a run
    assert loaded["request_id"] == "caller-chosen-request-id"
    assert loaded["semantic_facts"] == []
    assert loaded["semantic_inferences"] == []
    assert loaded["semantic_assumptions"] == []
    assert loaded["semantic_uncertainties"] == []


def test_load_trusted_bundle_rejects_evidence_paths_outside_data_root(tmp_path):
    bundles, data, _ = _roots(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    bundle = json.loads((bundles / "case-bundle.json").read_text(encoding="utf-8"))
    bundle["evidence_manifest_path"] = str(outside)
    (bundles / "case-bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(HostRequestError, match="OUTSIDE_CONFIGURED_DATA_ROOT"):
        load_trusted_bundle(
            bundle_id="case-bundle",
            bundle_root=bundles,
            data_root=data,
        )


def test_post_requires_auth_and_only_bundle_id(tmp_path):
    bundles, data, output = _roots(tmp_path)
    config = _config(bundles, data, output)
    handler = make_handler(config, runner=lambda *a, **k: SimpleNamespace(returncode=0, stdout="{}", stderr=""))
    instance = _request(handler, method="POST", path="/v1/canonical-runs", body=b'{"bundle_id":"case-bundle"}')
    instance.do_POST()
    assert instance.responses == [401]

    body = json.dumps({"bundle_id": "case-bundle", "factory_spec": "attacker:factory"}).encode()
    instance = _request(handler, method="POST", path="/v1/canonical-runs", body=body, token=config["token"])
    instance.do_POST()
    assert instance.responses == [400]
    result = json.loads(instance.wfile.getvalue())
    assert result["reason"] == "REQUEST_MUST_CONTAIN_ONLY_BUNDLE_ID"


def test_post_uses_trusted_runtime_factory_and_server_generated_ids(tmp_path):
    bundles, data, output = _roots(tmp_path)
    config = _config(bundles, data, output)
    seen = {}

    def fake_runner(command, **kwargs):
        seen["command"] = command
        seen["env"] = kwargs["env"]
        bundle_path = Path(command[4])
        seen["bundle"] = json.loads(bundle_path.read_text(encoding="utf-8"))
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({
                "status": "CANONICAL_RUN_IN_PROGRESS",
                "run_id": seen["bundle"]["run_id"],
                "case_id": "test-case",
                "human_approval_required": True,
                "auto_execution": False,
                "publication_required": True,
                "human_report_required": True,
            }),
            stderr="must-not-be-returned",
        )

    handler = make_handler(config, runner=fake_runner)
    body = json.dumps({"bundle_id": "case-bundle"}).encode()
    instance = _request(handler, method="POST", path="/v1/canonical-runs", body=body, token=config["token"])
    instance.do_POST()
    assert instance.responses == [202]
    result = json.loads(instance.wfile.getvalue())
    assert result["status"] == "CANONICAL_RUN_IN_PROGRESS"
    assert result["run_id"].startswith("host-")
    assert result["request_id"].startswith("host-request-")
    assert result["human_approval_required"] is True
    assert result["auto_execution"] is False
    assert "factory_spec" not in seen["bundle"]
    assert seen["env"]["IIOS_CANONICAL_RUNTIME_FACTORY"] == "trusted_runtime.factory:build"
    assert seen["bundle"]["semantic_facts"] == []
    assert seen["bundle"]["semantic_assumptions"] == []
    assert not any("must-not-be-returned" in str(v) for v in result.values())
    assert (output / "host-inbox" / f"{result['run_id']}.request-bundle.json").is_file()


def test_post_blocked_cli_never_reports_success_or_execution(tmp_path):
    bundles, data, output = _roots(tmp_path)
    config = _config(bundles, data, output)

    def blocked_runner(*args, **kwargs):
        return SimpleNamespace(
            returncode=2,
            stdout=json.dumps({
                "status": "BLOCKED",
                "canonical_decision_created": False,
                "reason": "CANONICAL_RUNTIME_NOT_REGISTERED",
            }),
            stderr="sensitive error text",
        )

    handler = make_handler(config, runner=blocked_runner)
    body = json.dumps({"bundle_id": "case-bundle"}).encode()
    instance = _request(handler, method="POST", path="/v1/canonical-runs", body=body, token=config["token"])
    instance.do_POST()
    assert instance.responses == [409]
    result = json.loads(instance.wfile.getvalue())
    assert result["status"] == "BLOCKED"
    assert result["canonical_decision_created"] is False
    assert result["human_approval_required"] is True
    assert result["auto_execution"] is False
    assert "sensitive error text" not in json.dumps(result)
