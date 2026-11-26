
"""Backend integration with Apache Guacamole JSON authentication."""

from urllib.parse import quote

import httpx

from app.config import settings
from app.services.crypto import encrypt_guacamole_json
from app.services.guacamole_payload import build_auth_payload

TIMEOUT_SECONDS = 10.0


def _guac_base_url() -> str:
    url = settings.guac_internal_url.strip().rstrip("/")

    if not url.startswith(("http://", "https://")):
        raise RuntimeError("Invalid Guacamole internal URL.")

    return url


async def issue_token(payload: dict, transport=None) -> dict:
    """Authenticate a user with Guacamole using encrypted JSON."""

    if not settings.guac_json_secret_key:
        raise RuntimeError("Guacamole authentication is not configured.")

    # Temporary diagnostic: never print passwords or authentication tokens.
    connections = payload.get("connections") or {}

    print(
        "GUAC DEBUG:",
        {
            "username": payload.get("username"),
            "connection_count": len(connections),
            "connection_names": list(connections.keys()),
            "protocols": [
                item.get("protocol")
                for item in connections.values()
            ],
        },
    )

    encrypted_data = encrypt_guacamole_json(
        payload,
        settings.guac_json_secret_key,
    )

    url = f"{_guac_base_url()}/api/tokens"

    try:
        async with httpx.AsyncClient(
            transport=transport,
            timeout=TIMEOUT_SECONDS,
        ) as client:
            response = await client.post(
                url,
                data={"data": encrypted_data},
            )
            response.raise_for_status()
            result = response.json()

    except httpx.HTTPError as exc:
        raise RuntimeError(
            "Unable to communicate with Guacamole authentication service."
        ) from exc
    except ValueError as exc:
        raise RuntimeError(
            "Guacamole returned an invalid authentication response."
        ) from exc

    auth_token = result.get("authToken")

    if not isinstance(auth_token, str) or not auth_token:
        raise RuntimeError(
            "Guacamole did not return a valid authentication token."
        )

    return {
        "authToken": auth_token,
        "username": result.get("username"),
        "dataSource": result.get("dataSource"),
        "availableDataSources": result.get("availableDataSources", []),
    }


async def revoke_token(auth_token: str, transport=None) -> bool:
    """Invalidate an existing Guacamole authentication token."""

    if not isinstance(auth_token, str) or not auth_token.strip():
        raise ValueError("A valid Guacamole authentication token is required.")

    safe_token = quote(auth_token, safe="")
    url = f"{_guac_base_url()}/api/tokens/{safe_token}"

    try:
        async with httpx.AsyncClient(
            transport=transport,
            timeout=TIMEOUT_SECONDS,
        ) as client:
            response = await client.delete(url)
            response.raise_for_status()

    except httpx.HTTPError as exc:
        raise RuntimeError(
            "Unable to revoke the Guacamole authentication token."
        ) from exc

    return response.status_code == 204


async def issue_rdp_token(
    *,
    username: str,
    connection_name: str,
    hostname: str,
    rdp_username: str,
    rdp_password: str,
    remote_app_alias: str,
    allowed_aliases: set[str],
    port: int = 3389,
    transport=None,
) -> dict:
    """Build a restricted RDP payload and authenticate with Guacamole."""

    payload = build_auth_payload(
        username=username,
        connection_name=connection_name,
        hostname=hostname,
        rdp_username=rdp_username,
        rdp_password=rdp_password,
        remote_app_alias=remote_app_alias,
        allowed_aliases=allowed_aliases,
        port=port,
    )

    return await issue_token(payload, transport=transport)
