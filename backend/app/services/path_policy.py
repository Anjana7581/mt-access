"""Server-side policy for executable paths.

This is the single place that decides what may ever be stored as a launchable
application. The Windows Agent (Phase 3) must re-apply the same rules, and only ever
receive an application *id*, never a path from a client.

Rules: absolute local drive path, no UNC, no '..', no alternate data streams, must live
under an allowed root, file name must match the type (MT4=terminal.exe, MT5=terminal64.exe),
and the working directory must be the executable's own folder.
"""
from pathlib import PureWindowsPath

from ..config import settings

EXE_BY_TYPE = {"MT4": "terminal.exe", "MT5": "terminal64.exe"}
_FORBIDDEN = set('<>"|?*')


class PathPolicyError(ValueError):
    pass


def _roots() -> list[PureWindowsPath]:
    return [PureWindowsPath(r.strip()) for r in settings.allowed_app_roots.split(";") if r.strip()]


def validate_app_paths(app_type: str, executable_path: str, working_directory: str | None) -> tuple[str, str]:
    raw = (executable_path or "").strip()
    if not raw:
        raise PathPolicyError("Executable path is required")
    if any(c in _FORBIDDEN or ord(c) < 32 for c in raw) or raw.count(":") != 1:
        raise PathPolicyError("Executable path contains invalid characters")

    exe = PureWindowsPath(raw)
    if not exe.drive or not exe.root or exe.drive.startswith("\\\\"):
        raise PathPolicyError(r"Executable path must be an absolute local path such as C:\Trading\MT5\ClientA\terminal64.exe")
    if ".." in exe.parts:
        raise PathPolicyError("Path traversal ('..') is not allowed")

    expected = EXE_BY_TYPE.get(app_type)
    if expected is None:
        raise PathPolicyError("Unknown application type")
    if exe.name.lower() != expected:
        raise PathPolicyError(f"{app_type} executable must be named {expected}")

    if not any(exe.is_relative_to(root) and exe != root for root in _roots()):
        raise PathPolicyError("Executable is outside the allowed installation roots")

    wd = PureWindowsPath(working_directory.strip()) if working_directory and working_directory.strip() else exe.parent
    if wd != exe.parent:
        raise PathPolicyError("Working directory must be the folder containing the executable")
    return str(exe), str(wd)
