from __future__ import annotations

"""Read-only configuration preflight for D1-A; never claims production acceptance."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from iios_mvp.canonical_host_v01 import HOST_VERSION, load_host_config
from iios_mvp.live_provider_preflight_v01 import load_live_provider_config

TRUSTED_FACTORY = "iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime"
POLICY_ID = "IIOS-D1A-HOST-ACCEPTANCE-PREFLIGHT-0.1"


def _keypair_matches(private_b64: str, public_b64: str) -> bool:
    try:
        private_raw = base64.b64decode(private_b64, validate=True)
        public_raw = base64.b64decode(public_b64, validate=True)
        if len(private_raw) != 32 or len(public_raw) != 32:
            return False
        key = Ed25519PrivateKey.from_private_bytes(private_raw)
        derived = key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return hmac.compare_digest(derived, public_raw)
    except Exception:
        return False


def build_preflight_report(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    values = os.environ if env is None else env
    checks: dict[str, bool] = {}
    blockers: list[str] = []
    host = None
    provider = None

    try:
        host = load_host_config(dict(values))
        checks["host_configuration_valid"] = True
    except Exception as exc:
        checks["host_configuration_valid"] = False
        blockers.append("HOST_CONFIG:" + str(exc))

    factory_spec = str(values.get("IIOS_CANONICAL_RUNTIME_FACTORY", "")).strip()
    checks["trusted_factory_is_canonical_provider_factory"] = factory_spec == TRUSTED_FACTORY
    if not checks["trusted_factory_is_canonical_provider_factory"]:
        blockers.append("TRUSTED_FACTORY_NOT_CANONICAL_PROVIDER_FACTORY")

    try:
        provider = load_live_provider_config(dict(values))
        checks["provider_configuration_valid"] = True
    except Exception as exc:
        checks["provider_configuration_valid"] = False
        blockers.append("PROVIDER_CONFIG:" + str(exc))

    admission_root_raw = str(values.get("IIOS_CANONICAL_ADMISSION_ROOT", "")).strip()
    admission_root = Path(admission_root_raw).expanduser() if admission_root_raw else None
    checks["canonical_admission_root_exists"] = bool(admission_root and admission_root.is_dir())
    if not checks["canonical_admission_root_exists"]:
        blockers.append("CANONICAL_ADMISSION_ROOT_MISSING_OR_NOT_DIRECTORY")

    public_key_b64 = str(values.get("IIOS_LLM_PROVIDER_RUNTIME_PUBLIC_KEY_B64", "")).strip()
    checks["runtime_keypair_matches_pinned_public_key"] = bool(
        provider and public_key_b64
        and _keypair_matches(provider.runtime_private_key_b64, public_key_b64)
    )
    if not checks["runtime_keypair_matches_pinned_public_key"]:
        blockers.append("RUNTIME_KEYPAIR_PIN_MISMATCH_OR_MISSING")

    endpoint = urlparse(provider.base_url) if provider else None
    now = datetime.now(timezone.utc).isoformat()
    config_pass = all(checks.values()) and not blockers
    return {
        "schema_version": POLICY_ID,
        "record_class": "LOCAL_HOST_CONFIGURATION_PREFLIGHT_NOT_PRODUCTION_ACCEPTANCE",
        "checked_at": now,
        "host_version": HOST_VERSION,
        "status": "CONFIG_PREFLIGHT_PASS_NOT_PRODUCTION_ACCEPTED" if config_pass else "BLOCKED",
        "checks": checks,
        "blockers": blockers,
        "sanitized_configuration": {
            "factory_spec": factory_spec or None,
            "host_bind": str(host["host"]) if host else None,
            "host_port": int(host["port"]) if host else None,
            "loopback_only": bool(host["loopback_only"]) if host else None,
            "provider_id": str(provider.provider_id) if provider else None,
            "provider_version": str(provider.provider_version) if provider else None,
            "provider_protocol": str(provider.protocol) if provider else None,
            "provider_model_configured": bool(provider and provider.model),
            "provider_auth_mode": str(provider.auth_mode) if provider else None,
            "provider_deployment_mode": str(provider.deployment_mode) if provider else None,
            "provider_endpoint_scheme": endpoint.scheme if endpoint else None,
            "provider_endpoint_host_present": bool(endpoint and endpoint.hostname),
            "provider_api_key_required_by_selected_auth_mode": bool(provider and provider.auth_mode == "BEARER"),
            "admission_root_present": checks["canonical_admission_root_exists"],
        },
        "production_acceptance": False,
        "host_process_probed": False,
        "healthz_probed": False,
        "readyz_probed": False,
        "actual_provider_invocation_performed": False,
        "signed_live_provider_receipt_verified": False,
        "durable_admission_store_replayed": False,
        "canonical_run_completed": False,
        "formal_decision_created": False,
        "publication_created": False,
        "run_receipt_created": False,
        "independent_replay_passed": False,
        "human_approval_required": True,
        "auto_execution": False,
        "next_gate": (
            "A configuration preflight only establishes local settings. Production Host acceptance still requires a real host-origin request, actual authorized provider calls, independently verified Ed25519 live receipts, durable evidence/outputs, and a clean replay. Never paste secrets into PRs or public logs."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="D1-A config preflight; explicitly not production acceptance.")
    parser.add_argument("--out", type=Path, help="optional sanitized report path; file must not already exist")
    args = parser.parse_args()
    report = build_preflight_report()
    raw = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        if args.out.exists() or args.out.is_symlink():
            print(json.dumps({"status": "BLOCKED", "reason": "OUTPUT_FILE_ALREADY_EXISTS"}, sort_keys=True))
            return 2
        args.out.write_text(raw, encoding="utf-8")
        try:
            os.chmod(args.out, 0o600)
        except OSError:
            pass
    print(json.dumps({
        "status": report["status"],
        "checks": report["checks"],
        "blockers": report["blockers"],
        "production_acceptance": False,
        "actual_provider_invocation_performed": False,
        "run_receipt_created": False,
        "auto_execution": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "CONFIG_PREFLIGHT_PASS_NOT_PRODUCTION_ACCEPTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
