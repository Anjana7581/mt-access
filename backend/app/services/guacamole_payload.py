
"""Build short-lived Guacamole authentication payloads."""

import time

from app.config import settings
from app.services.rdp import build_rdp_connection


def build_auth_payload(
    *,
    username: str,
    connection_name: str,
    hostname: str,
    rdp_username: str,
    rdp_password: str,
    remote_app_alias: str,
    allowed_aliases: set[str],
    port: int = 3389,
) -> dict:
    """
    Build a short-lived JSON authentication payload.

    All connection details must come from trusted backend records,
    never directly from client request data.
    """

    if not isinstance(username, str) or not username.strip():
        raise ValueError("Guacamole username is required.")

    ttl = settings.guac_token_ttl_seconds

    if isinstance(ttl, bool) or not isinstance(ttl, int) or not 1 <= ttl <= 300:
        raise ValueError("Guacamole token TTL must be between 1 and 300 seconds.")

    connection = build_rdp_connection(
        hostname=hostname,
        username=rdp_username,
        password=rdp_password,
        remote_app_alias=remote_app_alias,
        allowed_aliases=allowed_aliases,
        connection_name=connection_name,
        port=port,
    )

    expires = int(time.time() * 1000) + (ttl * 1000)

    return {
        "username": username.strip(),
        "expires": expires,
        "connections": {
            connection_name: connection,
        },
    }
