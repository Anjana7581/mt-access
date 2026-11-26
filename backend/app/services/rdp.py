
"""Build restricted, trusted Apache Guacamole RDP connections."""

import ipaddress
import re


def _validate_hostname(hostname: str) -> str:
    if not isinstance(hostname, str) or not hostname.strip():
        raise ValueError("RDP hostname is required.")

    hostname = hostname.strip()

    if len(hostname) > 253 or any(c in hostname for c in "/\\:@?#"):
        raise ValueError("Invalid RDP hostname.")

    try:
        ipaddress.ip_address(hostname)
        return hostname
    except ValueError:
        pass

    if not re.fullmatch(
        r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?",
        hostname,
    ):
        raise ValueError("Invalid RDP hostname.")

    if ".." in hostname:
        raise ValueError("Invalid RDP hostname.")

    return hostname


def build_rdp_connection(
    *,
    hostname: str,
    username: str,
    password: str,
    remote_app_alias: str,
    allowed_aliases: set[str],
    connection_name: str,
    port: int = 3389,
) -> dict:
    """
    Build one restricted RDP connection.

    All arguments must come from trusted backend configuration/database
    records. Never pass client-supplied connection details here.
    """

    hostname = _validate_hostname(hostname)

    if not isinstance(username, str) or not username.strip():
        raise ValueError("RDP username is required.")

    if not isinstance(password, str) or not password:
        raise ValueError("RDP password is required.")

    if not isinstance(remote_app_alias, str):
        raise ValueError("RemoteApp alias must be a string.")

    if remote_app_alias not in allowed_aliases:
        raise ValueError("RemoteApp alias is not approved.")

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", remote_app_alias):
        raise ValueError("Invalid RemoteApp alias format.")

    if not isinstance(connection_name, str) or not re.fullmatch(
        r"[A-Za-z0-9 _-]{1,80}",
        connection_name,
    ):
        raise ValueError("Invalid connection name.")

    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("Invalid RDP port.")

    return {
        "protocol": "rdp",
        "parameters": {
            "hostname": hostname,
            "port": str(port),
            "username": username,
            "password": password,
            "security": "nla",
            "ignore-cert": "false",
            "remote-app": f"||{remote_app_alias}",
            "disable-copy": "true",
            "disable-paste": "true",
            "enable-drive": "false",
            "enable-printing": "false",
        },
    }
