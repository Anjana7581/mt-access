
import pytest

from app.services import guacamole


@pytest.mark.anyio
async def test_issue_rdp_token_connects_payload_builder_to_token_service(
    monkeypatch,
):
    expected_payload = {
        "username": "client-004",
        "expires": 1800000000000,
        "connections": {},
    }

    captured = {}

    def fake_build_payload(**kwargs):
        captured["builder_args"] = kwargs
        return expected_payload

    async def fake_issue_token(payload, transport=None):
        captured["payload"] = payload
        captured["transport"] = transport
        return {"authToken": "test-token"}

    monkeypatch.setattr(
        guacamole,
        "build_auth_payload",
        fake_build_payload,
    )
    monkeypatch.setattr(
        guacamole,
        "issue_token",
        fake_issue_token,
    )

    fake_transport = object()

    result = await guacamole.issue_rdp_token(
        username="client-004",
        connection_name="Client MT5",
        hostname="192.168.1.100",
        rdp_username="test-client",
        rdp_password="test-password",
        remote_app_alias="MT5",
        allowed_aliases={"MT5"},
        transport=fake_transport,
    )

    assert result["authToken"] == "test-token"
    assert captured["payload"] is expected_payload
    assert captured["transport"] is fake_transport
    assert captured["builder_args"]["remote_app_alias"] == "MT5"
