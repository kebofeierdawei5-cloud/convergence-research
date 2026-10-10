from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import shlex
import stat
from threading import Thread

import pytest

from tools.prepare_iios_local_ollama_runtime import (
    LocalRuntimeSetupError,
    prepare_local_runtime,
)


class _Handler(BaseHTTPRequestHandler):
    model_names = ["qwen3:8b"]
    version = "0.13.3"
    redirect_version = False

    def do_GET(self):
        if self.path == "/api/version" and self.redirect_version:
            self.send_response(302)
            self.send_header("Location", "/api/tags")
            self.end_headers()
            return
        if self.path == "/api/version":
            body = {"version": self.version}
            status = 200
        elif self.path == "/api/tags":
            body = {"models": [{"name": name} for name in self.model_names]}
            status = 200
        else:
            body = {"error": "not_found"}
            status = 404
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_args):
        return


@pytest.fixture
def ollama_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def _env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, _, raw = line.partition("=")
        assert key.startswith("export ")
        values[key.removeprefix("export ")] = shlex.split(raw)[0]
    return values


def test_local_runtime_setup_generates_private_config_without_api_key(tmp_path, ollama_server):
    workspace = tmp_path / ".iios-local"
    result = prepare_local_runtime(workspace=workspace, ollama_url=ollama_server, model="qwen3:8b")
    env_path = Path(result["env_file"])
    env = _env(env_path)

    assert result["status"] == "LOCAL_RUNTIME_CONFIGURED_NOT_PRODUCTION_ACCEPTED"
    assert env["IIOS_LLM_PROVIDER_BASE_URL"] == f"{ollama_server}/v1/responses"
    assert env["IIOS_LLM_PROVIDER_AUTH_MODE"] == "NONE"
    assert env["IIOS_LLM_PROVIDER_DEPLOYMENT_MODE"] == "SELF_HOSTED"
    assert env["IIOS_CANONICAL_RUNTIME_FACTORY"].endswith(":build_canonical_runtime")
    assert env["IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64"]
    assert env["IIOS_LLM_PROVIDER_RUNTIME_PUBLIC_KEY_B64"]
    assert "IIOS_LLM_PROVIDER_API_KEY" not in env
    assert stat.S_IMODE(env_path.stat().st_mode) == 0o600
    assert (workspace / "bundles").is_dir()
    assert (workspace / "data").is_dir()
    assert (workspace / "outputs").is_dir()
    assert (workspace / "admissions").is_dir()
    assert list((workspace / "admissions").iterdir()) == []
    assert list((workspace / "bundles").iterdir()) == []


def test_existing_secret_environment_is_never_overwritten(tmp_path, ollama_server):
    workspace = tmp_path / ".iios-local"
    first = prepare_local_runtime(workspace=workspace, ollama_url=ollama_server)
    env_path = Path(first["env_file"])
    before = env_path.read_bytes()
    with pytest.raises(LocalRuntimeSetupError, match="NOT_OVERWRITTEN"):
        prepare_local_runtime(workspace=workspace, ollama_url=ollama_server)
    assert env_path.read_bytes() == before


@pytest.mark.parametrize("url", [
    "http://provider.example:11434",
    "http://192.168.1.20:11434",
    "https://127.0.0.1:11434",
    "http://user:pass@127.0.0.1:11434",
    "http://127.0.0.1:11434/path",
])
def test_setup_refuses_non_local_or_ambiguous_endpoint(tmp_path, url):
    with pytest.raises(LocalRuntimeSetupError):
        prepare_local_runtime(workspace=tmp_path / "x", ollama_url=url)


def test_setup_refuses_too_old_ollama_responses_api(tmp_path, ollama_server):
    _Handler.version = "0.13.2"
    try:
        with pytest.raises(LocalRuntimeSetupError, match="BELOW_RESPONSES_API_MINIMUM"):
            prepare_local_runtime(workspace=tmp_path / "x", ollama_url=ollama_server)
    finally:
        _Handler.version = "0.13.3"


def test_setup_refuses_missing_model(tmp_path, ollama_server):
    _Handler.model_names = ["other:1b"]
    try:
        with pytest.raises(LocalRuntimeSetupError, match="MODEL_NOT_INSTALLED"):
            prepare_local_runtime(workspace=tmp_path / "x", ollama_url=ollama_server)
    finally:
        _Handler.model_names = ["qwen3:8b"]



def test_setup_refuses_redirect_from_local_preflight(tmp_path, ollama_server):
    _Handler.redirect_version = True
    try:
        with pytest.raises(LocalRuntimeSetupError, match="REDIRECTS_NOT_PERMITTED"):
            prepare_local_runtime(workspace=tmp_path / "redirect", ollama_url=ollama_server)
    finally:
        _Handler.redirect_version = False
