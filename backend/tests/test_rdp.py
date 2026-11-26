
import pytest

from app.services.rdp import build_rdp_connection


def valid_connection():
    return build_rdp_connection(
        hostname="192.168.1.100",
        username="test-client",
        password="test-password",
        remote_app_alias="MT5",
        allowed_aliases={"MT5", "MT4"},
        connection_name="Client MT5",
    )


def test_build_rdp_connection_success():
    result = valid_connection()

    assert result["protocol"] == "rdp"

    params = result["parameters"]

    assert params["hostname"] == "192.168.1.100"
    assert params["port"] == "3389"
    assert params["username"] == "test-client"
    assert params["remote-app"] == "||MT5"


def test_clipboard_and_redirection_disabled():
    params = valid_connection()["parameters"]

    assert params["disable-copy"] == "true"
    assert params["disable-paste"] == "true"
    assert params["enable-drive"] == "false"
    assert params["enable-printing"] == "false"


def test_unapproved_remote_app_rejected():
    with pytest.raises(ValueError, match="not approved"):
        build_rdp_connection(
            hostname="192.168.1.100",
            username="test-client",
            password="test-password",
            remote_app_alias="CMD",
            allowed_aliases={"MT5"},
            connection_name="Client MT5",
        )


def test_invalid_hostname_rejected():
    with pytest.raises(ValueError, match="hostname"):
        build_rdp_connection(
            hostname="invalid/host",
            username="test-client",
            password="test-password",
            remote_app_alias="MT5",
            allowed_aliases={"MT5"},
            connection_name="Client MT5",
        )


def test_invalid_port_rejected():
    with pytest.raises(ValueError, match="port"):
        build_rdp_connection(
            hostname="192.168.1.100",
            username="test-client",
            password="test-password",
            remote_app_alias="MT5",
            allowed_aliases={"MT5"},
            connection_name="Client MT5",
            port=70000,
        )


def test_missing_password_rejected():
    with pytest.raises(ValueError, match="password"):
        build_rdp_connection(
            hostname="192.168.1.100",
            username="test-client",
            password="",
            remote_app_alias="MT5",
            allowed_aliases={"MT5"},
            connection_name="Client MT5",
        )
