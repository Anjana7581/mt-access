
import httpx
import pytest

from app.services.guacamole import issue_token, revoke_token


@pytest.mark.anyio
async def test_issue_token_success():
    def handler(request):
        assert request.url.path.endswith("/api/tokens")
        assert "data" in request.content.decode()

        return httpx.Response(
            200,
            json={
                "authToken": "test-auth-token",
                "username": "test-client",
                "dataSource": "json",
                "availableDataSources": ["json"],
            },
        )

    transport = httpx.MockTransport(handler)
    result = await issue_token(
        {
            "username": "test-client",
            "expires": 1800000000000,
            "connections": {},
        },
        transport=transport,
    )

    assert result["authToken"] == "test-auth-token"
    assert result["username"] == "test-client"
    assert result["dataSource"] == "json"


@pytest.mark.anyio
async def test_revoke_token_success():
    def handler(request):
        assert request.method == "DELETE"
        assert request.url.path.endswith("/api/tokens/test-auth-token")
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    result = await revoke_token(
        "test-auth-token",
        transport=transport,
    )

    assert result is True


@pytest.mark.anyio
async def test_issue_token_rejects_missing_secret(monkeypatch):
    from app.services.guacamole import settings

    monkeypatch.setattr(settings, "guac_json_secret_key", "")

    with pytest.raises(RuntimeError, match="not configured"):
        await issue_token({"username": "test-client"})


@pytest.mark.anyio
async def test_revoke_token_rejects_empty_token():
    with pytest.raises(ValueError, match="authentication token"):
        await revoke_token("")
