
import time

import pytest

from app.services.guacamole_payload import build_auth_payload


def valid_payload():
    return build_auth_payload(
        username="client-004",
        connection_name="Client MT5",
        hostname="192.168.1.100",
        rdp_username="test-client",
        rdp_password="test-password",
        remote_app_alias="MT5",
        allowed_aliases={"MT5"},
    )


def test_auth_payload_structure():
    result = valid_payload()

    assert result["username"] == "client-004"
    assert "expires" in result
    assert "Client MT5" in result["connections"]

    connection = result["connections"]["Client MT5"]
    assert connection["protocol"] == "rdp"
    assert connection["parameters"]["remote-app"] == "||MT5"


def test_auth_payload_expiry():
    before = int(time.time() * 1000)
    result = valid_payload()
    after = int(time.time() * 1000)

    ttl_ms = 60 * 1000

    assert before + ttl_ms <= result["expires"] <= after + ttl_ms


def test_auth_payload_rejects_unapproved_alias():
    with pytest.raises(ValueError, match="not approved"):
        build_auth_payload(
            username="client-004",
            connection_name="Client MT5",
            hostname="192.168.1.100",
            rdp_username="test-client",
            rdp_password="test-password",
            remote_app_alias="CMD",
            allowed_aliases={"MT5"},
        )


def test_auth_payload_rejects_missing_username():
    with pytest.raises(ValueError, match="username"):
        build_auth_payload(
            username="",
            connection_name="Client MT5",
            hostname="192.168.1.100",
            rdp_username="test-client",
            rdp_password="test-password",
            remote_app_alias="MT5",
            allowed_aliases={"MT5"},
        )
