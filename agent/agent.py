
"""MetaTrader Windows Agent.

The Agent polls the backend and monitors local MT4/MT5 processes.
A backend/network interruption must NOT close a running application.
Only an explicit stop command from the backend closes an application.

Queued reports/events are persisted locally so an Agent restart does not
silently lose information collected during a backend outage.
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import PureWindowsPath

import psutil
import requests


VERSION = "0.3.0"

EXE_BY_TYPE = {
    "MT4": "terminal.exe",
    "MT5": "terminal64.exe",
}

log = logging.getLogger("agent")


class AgentError(Exception):
    pass


# ---------------- configuration ----------------

def load_config(path: str = "agent.env") -> dict:
    env = {}

    if os.path.exists(path):
        with open(path, encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()

    allowed_env = (
        "BACKEND_URL",
        "AGENT_SECRET",
        "AGENT_NAME",
        "ALLOWED_APP_ROOTS",
        "POLL_SECONDS",
        "AGENT_STATE_FILE",
    )

    env.update({
        key: value
        for key, value in os.environ.items()
        if key in allowed_env
    })

    cfg = {
        "url": env.get(
            "BACKEND_URL",
            "http://127.0.0.1:8000",
        ).rstrip("/"),
        "secret": env.get("AGENT_SECRET", ""),
        "name": env.get("AGENT_NAME", "host-1"),
        "roots": [
            root.strip()
            for root in env.get("ALLOWED_APP_ROOTS", r"C:\Trading").split(";")
            if root.strip()
        ],
        "poll": max(1.0, float(env.get("POLL_SECONDS", "2"))),
        "state_file": env.get("AGENT_STATE_FILE", "agent_state.json"),
    }

    if len(cfg["secret"]) < 24:
        sys.exit(
            "AGENT_SECRET missing or too short "
            "(minimum 24 characters) in agent.env"
        )

    return cfg


# ---------------- path validation ----------------

def validate_paths(
    app_type: str,
    executable_path: str,
    working_directory: str | None,
    roots: list[str],
) -> tuple[str, str]:
    raw = (executable_path or "").strip()

    if (
        not raw
        or any(c in '<>"|?*' or ord(c) < 32 for c in raw)
        or raw.count(":") != 1
    ):
        raise AgentError("Invalid executable path")

    exe = PureWindowsPath(raw)

    if (
        not exe.drive
        or not exe.root
        or exe.drive.startswith("\\\\")
        or ".." in exe.parts
    ):
        raise AgentError(
            "Executable path must be an absolute local path without '..'"
        )

    if exe.name.lower() != EXE_BY_TYPE.get(app_type, ""):
        raise AgentError(
            "Executable name does not match application type"
        )

    allowed = any(
        exe.is_relative_to(PureWindowsPath(root))
        and exe != PureWindowsPath(root)
        for root in roots
    )

    if not allowed:
        raise AgentError(
            "Executable is outside this host's allowed roots"
        )

    wd = (
        PureWindowsPath(working_directory)
        if working_directory
        else exe.parent
    )

    if wd != exe.parent:
        raise AgentError(
            "Working directory must be the executable's folder"
        )

    return str(exe), str(wd)


def same_path(a: str, b: str) -> bool:
    return (
        os.path.normcase(os.path.normpath(a))
        == os.path.normcase(os.path.normpath(b))
    )


def find_running(exe: str) -> psutil.Process | None:
    """Find a process only when its executable path matches exactly."""
    for process in psutil.process_iter(["pid", "exe"]):
        try:
            process_exe = process.info.get("exe")

            if process_exe and same_path(process_exe, exe):
                return process

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

        except psutil.Error:
            continue

    return None


def alive(proc: psutil.Process) -> bool:
    try:
        return (
            proc.is_running()
            and proc.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.Error:
        return False


def close_process(proc: psutil.Process, grace: int = 10) -> None:
    """Close the exact process after an explicit backend stop command."""
    if not alive(proc):
        return

    try:
        if os.name == "nt":
            result = subprocess.run(
                ["taskkill", "/PID", str(proc.pid)],
                capture_output=True,
                text=True,
                timeout=grace + 5,
            )

            if result.returncode != 0 and alive(proc):
                log.warning(
                    "Close request for pid %s returned %s: %s",
                    proc.pid,
                    result.returncode,
                    result.stderr.strip(),
                )

        else:
            proc.terminate()

        proc.wait(timeout=grace)

    except psutil.TimeoutExpired:
        log.warning(
            "pid %s did not close gracefully; forcing termination",
            proc.pid,
        )
        proc.kill()
        proc.wait(timeout=5)

    except psutil.NoSuchProcess:
        return

    if alive(proc):
        raise AgentError(
            f"Could not terminate application process {proc.pid}"
        )


# ---------------- agent ----------------

class Agent:
    def __init__(self, cfg: dict):
        self.cfg = dict(cfg)
        self.cfg.setdefault("state_file", "agent_state.json")

        self.http = requests.Session()
        self.http.headers["X-Agent-Secret"] = self.cfg["secret"]

        # session_id -> psutil.Process
        self.procs: dict[str, psutil.Process] = {}

        # Reports are (session_id, status, pid, message).
        self.pending_reports: list[tuple] = []
        self.pending_events: list[dict] = []

        self.backend_was_offline = False
        self._load_state()

    # ---------- durable local queue ----------

    def _save_state(self) -> None:
        path = self.cfg["state_file"]
        temp_path = path + ".tmp"

        payload = {
            "pending_reports": [
                [sid, status, pid, message]
                for sid, status, pid, message in self.pending_reports
            ],
            "pending_events": self.pending_events,
        }

        try:
            folder = os.path.dirname(os.path.abspath(path))
            os.makedirs(folder, exist_ok=True)

            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False)

            os.replace(temp_path, path)

        except OSError:
            log.exception("Could not persist Agent queue to %s", path)

    def _load_state(self) -> None:
        path = self.cfg["state_file"]

        if not os.path.isfile(path):
            return

        try:
            with open(path, encoding="utf-8") as file:
                payload = json.load(file)

            reports = payload.get("pending_reports", [])
            events = payload.get("pending_events", [])

            self.pending_reports = [
                (item[0], item[1], item[2], item[3])
                for item in reports
                if isinstance(item, list) and len(item) == 4
            ]

            self.pending_events = [
                item for item in events
                if isinstance(item, dict)
            ]

            log.info(
                "Restored Agent queue: %s reports, %s events",
                len(self.pending_reports),
                len(self.pending_events),
            )

        except (OSError, ValueError, TypeError, KeyError):
            log.exception(
                "Could not read Agent state file %s; starting with an empty queue",
                path,
            )

    # ---------- API ----------

    def api(self, method: str, path: str, **kwargs):
        response = self.http.request(
            method,
            self.cfg["url"] + path,
            timeout=10,
            **kwargs,
        )

        response.raise_for_status()
        return response.json() if response.content else None

    @staticmethod
    def _retryable(exc: requests.RequestException) -> bool:
        """Retry network errors, rate limits and server errors only."""
        response = getattr(exc, "response", None)

        if response is None:
            return True

        return (
            response.status_code == 429
            or response.status_code >= 500
        )

    def queue_event(self, event: str, details: str = "") -> None:
        self.pending_events.append({
            "name": self.cfg["name"],
            "event": event[:80],
            "details": details[:1000],
        })

        self._save_state()
        log.warning("%s: %s", event, details)

    def report(
        self,
        sid: str,
        status: str,
        pid: int | None = None,
        message: str | None = None,
    ) -> None:
        item = (
            sid,
            status,
            pid,
            (message or "")[:250] or None,
        )

        try:
            self._send_report(item)

        except requests.RequestException as exc:
            if not self._retryable(exc):
                log.error(
                    "Discarding non-retryable report for session %s: %s",
                    sid,
                    exc,
                )
                return

            self.pending_reports.append(item)
            self._save_state()

            log.error(
                "Report queued: %s for session %s: %s",
                status,
                sid,
                exc,
            )

    def _send_report(self, item: tuple) -> None:
        sid, status, pid, message = item

        self.api(
            "POST",
            f"/api/agent/sessions/{sid}/report",
            json={
                "status": status,
                "pid": pid,
                "message": message,
            },
        )

    def flush_pending(self) -> None:
        """Send persisted events/reports in order; keep transient failures."""
        while self.pending_events:
            event = self.pending_events[0]

            try:
                self.api(
                    "POST",
                    "/api/agent/events",
                    json=event,
                )

            except requests.RequestException as exc:
                if self._retryable(exc):
                    raise

                log.error("Discarding non-retryable queued event: %s", exc)

            self.pending_events.pop(0)
            self._save_state()

        while self.pending_reports:
            report_item = self.pending_reports[0]

            try:
                self._send_report(report_item)

            except requests.RequestException as exc:
                if self._retryable(exc):
                    raise

                log.error(
                    "Discarding non-retryable queued report for %s: %s",
                    report_item[0],
                    exc,
                )

            self.pending_reports.pop(0)
            self._save_state()

    # ---------- application process management ----------

    def validated(self, cmd: dict) -> tuple[str, str]:
        return validate_paths(
            cmd["application_type"],
            cmd["executable_path"],
            cmd.get("working_directory"),
            self.cfg["roots"],
        )

    def launch(self, cmd: dict) -> None:
        sid = cmd["session_id"]

        try:
            exe, wd = self.validated(cmd)

            if not os.path.isfile(exe):
                raise AgentError(
                    f"Executable not found on host: {exe}"
                )

            # A repeated launch command or lost response must not create
            # another MT terminal for the same installation.
            existing = find_running(exe)

            if existing:
                self.procs[sid] = existing

                log.info(
                    "Reusing already-running installation pid=%s session=%s",
                    existing.pid,
                    sid,
                )

                self.report(
                    sid,
                    "running",
                    pid=existing.pid,
                    message="Existing application process recovered",
                )
                return

            popen = subprocess.Popen(
                [exe],
                cwd=wd,
                shell=False,
                close_fds=True,
            )

            process = psutil.Process(popen.pid)
            self.procs[sid] = process

            log.info(
                "Launched %s pid=%s session=%s",
                exe,
                popen.pid,
                sid,
            )

            self.report(
                sid,
                "running",
                pid=popen.pid,
                message="Application process started",
            )

        except Exception as exc:
            log.exception("Launch failed for session %s", sid)

            self.queue_event(
                "application_launch_failed",
                f"session={sid}; error={exc}",
            )

            self.report(
                sid,
                "failed",
                message=str(exc),
            )

    def adopt(
        self,
        sid: str,
        pid: int | None,
        exe: str,
    ) -> psutil.Process | None:
        """Adopt an existing exact-path process after an Agent restart."""
        current = self.procs.get(sid)

        if current and alive(current):
            return current

        if pid:
            try:
                process = psutil.Process(pid)

                if alive(process) and same_path(process.exe(), exe):
                    self.procs[sid] = process

                    log.info(
                        "Adopted process by PID pid=%s session=%s",
                        pid,
                        sid,
                    )
                    return process

            except psutil.Error:
                pass

        # PID may be missing if the process started but its report was lost.
        process = find_running(exe)

        if process:
            self.procs[sid] = process

            log.info(
                "Adopted process by executable path pid=%s session=%s",
                process.pid,
                sid,
            )

            self.queue_event(
                "application_process_adopted",
                f"session={sid}; pid={process.pid}",
            )

            return process

        return None

    @staticmethod
    def _age_seconds(started_at: str | None) -> float | None:
        if not started_at:
            return None

        try:
            started = datetime.fromisoformat(
                started_at.replace("Z", "+00:00")
            )

            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)

            return max(
                0.0,
                (
                    datetime.now(timezone.utc) - started
                ).total_seconds(),
            )

        except (TypeError, ValueError):
            return None

    def recover_launching(self, item: dict) -> None:
        """Reconcile a launch whose acknowledgement may have been lost."""
        sid = item["session_id"]

        try:
            exe, _ = self.validated(item)
            process = self.adopt(sid, item.get("pid"), exe)

            if process:
                self.report(
                    sid,
                    "running",
                    pid=process.pid,
                    message="Existing application recovered after Agent reconnect",
                )
                return

            age = self._age_seconds(item.get("started_at"))
            timeout = max(
                10,
                int(item.get("launch_timeout_seconds") or 60),
            )

            # Wait before retrying. First check the exact executable path
            # to avoid launching a duplicate after a lost status report.
            if age is not None and age >= timeout:
                self.queue_event(
                    "application_launch_recovery_retry",
                    f"session={sid}; no matching process found after {int(age)} seconds",
                )

                self.launch(item)

        except Exception as exc:
            log.exception(
                "Could not recover launching session %s",
                sid,
            )

            self.queue_event(
                "application_recovery_failed",
                f"session={sid}; error={exc}",
            )

    def recover_running(self, item: dict) -> None:
        """Reattach the Agent monitor to a backend-recorded running process."""
        sid = item["session_id"]

        try:
            exe, _ = self.validated(item)
            process = self.adopt(sid, item.get("pid"), exe)

            if process:
                return

            self.queue_event(
                "application_process_missing",
                f"session={sid}; expected_pid={item.get('pid')}; executable={exe}",
            )

            self.report(
                sid,
                "failed",
                pid=item.get("pid"),
                message="Application process was not found during Agent recovery",
            )

        except Exception as exc:
            log.exception(
                "Could not reconcile running session %s",
                sid,
            )

            self.queue_event(
                "application_recovery_failed",
                f"session={sid}; error={exc}",
            )

    def stop(self, cmd: dict) -> None:
        """Stop only the exact application requested by an admin command."""
        sid = cmd["session_id"]
        process = None

        try:
            exe, _ = self.validated(cmd)
            process = self.adopt(sid, cmd.get("pid"), exe)

            if process:
                close_process(process)

            self.procs.pop(sid, None)

            log.info(
                "Application terminated: session=%s",
                sid,
            )

            self.report(
                sid,
                "stopped",
                message="Application termination confirmed by Agent",
            )

        except Exception as exc:
            log.exception(
                "Stop failed for session %s",
                sid,
            )

            # Do not report failed. The backend must keep stop_requested
            # and send the admin's stop command again on the next poll.
            if process and alive(process):
                self.procs[sid] = process

            self.queue_event(
                "application_termination_failed",
                f"session={sid}; error={exc}; termination will be retried",
            )

    def monitor_local_processes(self) -> None:
        """Monitor tracked MT processes even when the backend is unreachable."""
        for sid, process in list(self.procs.items()):
            if alive(process):
                continue

            del self.procs[sid]

            log.error(
                "Application process exited unexpectedly: session=%s pid=%s",
                sid,
                process.pid,
            )

            self.queue_event(
                "application_exited_unexpectedly",
                f"session={sid}; pid={process.pid}",
            )

            self.report(
                sid,
                "failed",
                pid=process.pid,
                message="Application process exited unexpectedly",
            )

    # ---------- polling loop ----------

    def cycle(self) -> None:
        self.api(
            "POST",
            "/api/agent/heartbeat",
            json={
                "name": self.cfg["name"],
                "version": VERSION,
            },
        )

        if self.backend_was_offline:
            self.queue_event(
                "agent_backend_reconnected",
                "Agent successfully reconnected to backend",
            )
            self.backend_was_offline = False

        self.flush_pending()

        work = self.api("GET", "/api/agent/work")

        for command in work.get("commands", []):
            if command.get("action") == "launch":
                self.launch(command)

            elif command.get("action") == "stop":
                self.stop(command)

        for item in work.get("recovering", []):
            self.recover_launching(item)

        for item in work.get("running", []):
            self.recover_running(item)

        # Never close a local process just because it is absent from the
        # backend's expected list. Only an explicit stop command can close it.
        self.monitor_local_processes()
        self.flush_pending()

    def run(self) -> None:
        log.info(
            "Agent %s v%s -> %s (roots: %s)",
            self.cfg["name"],
            VERSION,
            self.cfg["url"],
            ";".join(self.cfg["roots"]),
        )

        if (
            self.cfg["url"].startswith("http://")
            and not any(
                host in self.cfg["url"]
                for host in ("127.0.0.1", "localhost")
            )
        ):
            log.warning(
                "BACKEND_URL uses plain HTTP for a remote host. "
                "Use HTTPS to protect the Agent secret."
            )

        while True:
            try:
                self.cycle()

            except requests.RequestException as exc:
                if not self.backend_was_offline:
                    self.backend_was_offline = True

                    self.queue_event(
                        "agent_backend_unreachable",
                        str(exc),
                    )

                log.warning(
                    "Backend unreachable. Local MT processes will continue running: %s",
                    exc,
                )

            except Exception:
                log.exception("Unexpected Agent cycle error")

                self.queue_event(
                    "agent_internal_error",
                    "Unexpected error; check agent.log",
                )

            finally:
                # This runs even when backend communication fails.
                self.monitor_local_processes()

            time.sleep(self.cfg["poll"])


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                "agent.log",
                encoding="utf-8",
            ),
        ],
    )

    try:
        Agent(load_config()).run()

    except KeyboardInterrupt:
        log.info("Agent stopped manually")
