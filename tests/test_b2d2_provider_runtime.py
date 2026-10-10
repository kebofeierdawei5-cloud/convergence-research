import pytest

from iios_mvp.provider_runtime_v01 import (
    ProviderRuntimeBoundaryError,
    build_provider_auth_headers,
    validate_provider_runtime_policy,
)


def test_external_bearer_runtime_is_valid():
    policy = validate_provider_runtime_policy(
        base_url="https://api.example/v1/responses",
        protocol="OPENAI_RESPONSES",
        auth_mode="BEARER",
        deployment_mode="EXTERNAL",
    )
    assert policy.auth_mode == "BEARER"
    assert policy.deployment_mode == "EXTERNAL"


def test_self_hosted_no_auth_loopback_http_is_valid():
    policy = validate_provider_runtime_policy(
        base_url="http://127.0.0.1:8000/v1/responses",
        protocol="OPENAI_RESPONSES",
        auth_mode="NONE",
        deployment_mode="SELF_HOSTED",
    )
    assert policy.auth_mode == "NONE"
    assert policy.deployment_mode == "SELF_HOSTED"


@pytest.mark.parametrize("url", [
    "http://provider.example/v1/responses",
    "http://192.168.1.10:8000/v1/responses",
])
def test_self_hosted_loopback_http_with_bearer_auth_is_rejected():
    with pytest.raises(ProviderRuntimeBoundaryError, match="must use HTTPS"):
        validate_provider_runtime_policy(
            base_url="http://127.0.0.1:11434/v1/responses",
            protocol="OPENAI_RESPONSES",
            auth_mode="BEARER",
            deployment_mode="SELF_HOSTED",
        )


def test_non_loopback_http_is_rejected(url):
    with pytest.raises(
        ProviderRuntimeBoundaryError,
        match="must use HTTPS unless SELF_HOSTED on loopback",
    ):
        validate_provider_runtime_policy(
            base_url=url,
            protocol="OPENAI_RESPONSES",
            auth_mode="NONE",
            deployment_mode="SELF_HOSTED",
        )


def test_external_http_is_rejected():
    with pytest.raises(ProviderRuntimeBoundaryError, match="must use HTTPS"):
        validate_provider_runtime_policy(
            base_url="http://localhost:8000/v1/responses",
            protocol="OPENAI_RESPONSES",
            auth_mode="BEARER",
            deployment_mode="EXTERNAL",
        )


def test_unknown_auth_mode_is_rejected():
    with pytest.raises(ProviderRuntimeBoundaryError, match="auth mode"):
        validate_provider_runtime_policy(
            base_url="https://provider.example/v1/responses",
            protocol="OPENAI_RESPONSES",
            auth_mode="TOKEN",
            deployment_mode="EXTERNAL",
        )


def test_none_auth_does_not_emit_authorization_header():
    assert build_provider_auth_headers(auth_mode="NONE", api_key="") == {}


def test_none_auth_rejects_accidental_secret():
    with pytest.raises(ProviderRuntimeBoundaryError, match="must not receive"):
        build_provider_auth_headers(auth_mode="NONE", api_key="secret")


def test_bearer_auth_emits_only_bearer_header():
    assert build_provider_auth_headers(
        auth_mode="BEARER",
        api_key="secret",
    ) == {"Authorization": "Bearer secret"}


def test_bearer_auth_requires_secret():
    with pytest.raises(ProviderRuntimeBoundaryError, match="requires an API key"):
        build_provider_auth_headers(auth_mode="BEARER", api_key="")


def test_provider_identity_is_not_part_of_runtime_policy():
    policy = validate_provider_runtime_policy(
        base_url="https://selfhosted.example/v1/responses",
        protocol="OPENAI_RESPONSES",
        auth_mode="BEARER",
        deployment_mode="SELF_HOSTED",
    )
    assert not hasattr(policy, "provider_id")
