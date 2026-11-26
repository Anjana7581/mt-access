"""Phase 3: sessions + agent protocol (SQLite). The agent itself is tested manually on Windows."""
import pytest

from app.config import settings
from conftest import login

SECRET = "s" * 32
AG = {"X-Agent-Secret": SECRET}
MT5 = r"C:\Trading\MT5\ClientA\terminal64.exe"


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setattr(settings, "agent_secret", SECRET)


@pytest.fixture()
def setup(client, admin):
    c = client.post("/api/clients", headers=admin, json={"name": "A", "email": "a@example.com", "password": "ClientPass123"}).json()
    app = client.post("/api/applications", headers=admin, json={
        "application_name": "MT5 A", "application_type": "MT5", "executable_path": MT5}).json()
    client.post("/api/assignments", headers=admin, json={"client_id": c["id"], "application_id": app["id"]})
    return {"c": c, "app": app, "h": login(client, "a@example.com", "ClientPass123")}


def online(client):
    assert client.post("/api/agent/heartbeat", headers=AG, json={"name": "host-1", "version": "0.1.0"}).status_code == 200


def test_agent_auth(client, monkeypatch):
    assert client.post("/api/agent/heartbeat", json={"name": "x"}).status_code == 401
    assert client.post("/api/agent/heartbeat", headers={"X-Agent-Secret": "wrong"}, json={"name": "x"}).status_code == 401
    assert client.get("/api/agent/work", headers={"Authorization": "Bearer whatever"}).status_code == 401
    monkeypatch.setattr(settings, "agent_secret", "")
    assert client.get("/api/agent/work", headers=AG).status_code == 503
    monkeypatch.setattr(settings, "agent_secret", SECRET)
    assert client.post("/api/agent/heartbeat", headers=AG, json={"name": "bad name!"}).status_code == 422


def test_launch_preconditions(client, admin, setup):
    h = setup["h"]
    assert client.post("/api/sessions/launch", headers=admin).status_code == 403
    assert client.post("/api/sessions/launch").status_code == 401
    assert client.post("/api/sessions/launch", headers=h).status_code == 503
    online(client)
    client.delete(f"/api/assignments/{setup['c']['id']}", headers=admin)
    assert client.post("/api/sessions/launch", headers=h).status_code == 409
    assert client.get("/api/sessions/status", headers=h).json()["status"] == "none"


def test_full_lifecycle(client, admin, setup):
    h = setup["h"]
    online(client)
    r = client.post("/api/sessions/launch", headers=h)
    assert r.status_code == 202 and r.json()["status"] == "pending"
    sid = r.json()["session_id"]
    assert client.post("/api/sessions/launch", headers=h).json()["session_id"] == sid

    w = client.get("/api/agent/work", headers=AG).json()
    assert [c["action"] for c in w["commands"]] == ["launch"]
    cmd = w["commands"][0]
    assert cmd["executable_path"] == MT5 and cmd["session_id"] == sid
    assert client.get("/api/agent/work", headers=AG).json()["commands"] == []
    assert client.get("/api/sessions/status", headers=h).json()["status"] == "launching"

    assert client.post(f"/api/agent/sessions/{sid}/report", headers=AG, json={"status": "running", "pid": 4242}).status_code == 200
    st = client.get("/api/sessions/status", headers=h).json()
    assert st["status"] == "running"
    assert "executable_path" not in st and "pid" not in st and MT5 not in str(st)
    w = client.get("/api/agent/work", headers=AG).json()
    assert w["running"][0]["pid"] == 4242 and sid in w["expected"]

    admin_view = client.get("/api/sessions", headers=admin).json()
    assert admin_view[0]["pid"] == 4242 and admin_view[0]["client_code"] == setup["c"]["client_code"]

    assert client.post("/api/sessions/disconnect", headers=h).json()["status"] == "stop_requested"
    w = client.get("/api/agent/work", headers=AG).json()
    assert w["commands"][0]["action"] == "stop" and w["commands"][0]["pid"] == 4242
    client.post(f"/api/agent/sessions/{sid}/report", headers=AG, json={"status": "stopped", "message": "closed"})
    assert client.get("/api/sessions/status", headers=h).json()["status"] == "stopped"
    assert client.get("/api/sessions", headers=admin).json() == []
    assert client.post(f"/api/agent/sessions/{sid}/report", headers=AG, json={"status": "running", "pid": 1}).json()["status"] == "stopped"
    assert client.post("/api/sessions/launch", headers=h).json()["session_id"] != sid


def test_disconnect_before_agent_picks_up(client, setup):
    h = setup["h"]
    online(client)
    client.post("/api/sessions/launch", headers=h)
    assert client.post("/api/sessions/disconnect", headers=h).json()["status"] == "stopped"
    assert client.get("/api/agent/work", headers=AG).json()["commands"] == []
    assert client.post("/api/sessions/disconnect", headers=h).status_code == 404


def test_stop_while_launching_wins_over_running_report(client, setup):
    h = setup["h"]
    online(client)
    sid = client.post("/api/sessions/launch", headers=h).json()["session_id"]
    client.get("/api/agent/work", headers=AG)
    client.post("/api/sessions/disconnect", headers=h)
    client.post(f"/api/agent/sessions/{sid}/report", headers=AG, json={"status": "running", "pid": 77})
    assert client.get("/api/sessions/status", headers=h).json()["status"] == "stop_requested"
    assert client.get("/api/agent/work", headers=AG).json()["commands"][0]["action"] == "stop"


def test_revocation_stops_live_sessions(client, admin, setup):
    h = setup["h"]
    online(client)
    sid = client.post("/api/sessions/launch", headers=h).json()["session_id"]
    client.get("/api/agent/work", headers=AG)
    client.post(f"/api/agent/sessions/{sid}/report", headers=AG, json={"status": "running", "pid": 9})
    client.put(f"/api/clients/{setup['c']['id']}", headers=admin, json={"status": "inactive"})
    assert client.get("/api/sessions", headers=admin).json()[0]["status"] == "stop_requested"
    client.put(f"/api/clients/{setup['c']['id']}", headers=admin, json={"status": "active"})
    client.post(f"/api/agent/sessions/{sid}/report", headers=AG, json={"status": "stopped"})
    h2 = login(client, "a@example.com", "ClientPass123")
    sid2 = client.post("/api/sessions/launch", headers=h2).json()["session_id"]
    client.get("/api/agent/work", headers=AG)
    client.post(f"/api/agent/sessions/{sid2}/report", headers=AG, json={"status": "running", "pid": 10})
    client.delete(f"/api/assignments/{setup['c']['id']}", headers=admin)
    assert client.get("/api/sessions", headers=admin).json()[0]["status"] == "stop_requested"


def test_admin_terminate_and_agents_list(client, admin, setup):
    h = setup["h"]
    online(client)
    sid = client.post("/api/sessions/launch", headers=h).json()["session_id"]
    assert client.post(f"/api/sessions/{sid}/terminate", headers=h).status_code == 403
    assert client.post(f"/api/sessions/{sid}/terminate", headers=admin).json()["status"] == "stopped"
    assert client.post(f"/api/sessions/{sid}/terminate", headers=admin).status_code == 409
    assert client.post("/api/sessions/nope/terminate", headers=admin).status_code == 404
    ag = client.get("/api/agents", headers=admin).json()
    assert ag[0]["name"] == "host-1" and ag[0]["online"] is True
    assert client.get("/api/agents", headers=h).status_code == 403


def test_stale_launch_fails(client, setup, monkeypatch):
    h = setup["h"]
    online(client)
    client.post("/api/sessions/launch", headers=h)
    monkeypatch.setattr(settings, "launch_timeout_seconds", -1)
    st = client.get("/api/sessions/status", headers=h).json()
    assert st["status"] == "failed" and "in time" in st["message"]


def test_report_validation(client, setup):
    assert client.post("/api/agent/sessions/unknown/report", headers=AG, json={"status": "running", "pid": 1}).status_code == 404
    assert client.post("/api/agent/sessions/unknown/report", headers=AG, json={"status": "hacked"}).status_code == 422


def test_inactive_app_cancels_pending_launch(client, admin, setup):
    h = setup["h"]
    online(client)
    client.post("/api/sessions/launch", headers=h)
    client.put(f"/api/applications/{setup['app']['id']}", headers=admin, json={"status": "inactive"})
    assert client.get("/api/agent/work", headers=AG).json()["commands"] == []
    assert client.get("/api/sessions/status", headers=h).json()["status"] == "stopped"


# ---------------- application edits are blocked while a session is active ----------------
NEW_PATH = r"C:\Trading\MT5\ClientB\terminal64.exe"


def _reach(client, h, stage):
    """Drive the client's session to `stage` (pending / launching / running / stop_requested); returns its id."""
    online(client)
    sid = client.post("/api/sessions/launch", headers=h).json()["session_id"]
    if stage != "pending":
        client.get("/api/agent/work", headers=AG)                                   # agent claims it -> launching
        if stage != "launching":
            client.post(f"/api/agent/sessions/{sid}/report", headers=AG, json={"status": "running", "pid": 4242})
            if stage == "stop_requested":
                client.post("/api/sessions/disconnect", headers=h)
    assert client.get("/api/sessions/status", headers=h).json()["status"] == stage
    return sid


def _app(client, admin, app_id):
    return client.get(f"/api/applications/{app_id}", headers=admin).json()


@pytest.mark.parametrize("stage", ["pending", "launching", "running", "stop_requested"])
def test_path_change_rejected_while_session_active(client, admin, setup, stage):
    _reach(client, setup["h"], stage)
    r = client.put(f"/api/applications/{setup['app']['id']}", headers=admin, json={"executable_path": NEW_PATH})
    assert r.status_code == 409
    assert _app(client, admin, setup["app"]["id"])["executable_path"] == MT5


def test_working_directory_change_rejected_while_session_active(client, admin, setup):
    _reach(client, setup["h"], "running")
    before = _app(client, admin, setup["app"]["id"])["working_directory"]
    r = client.put(f"/api/applications/{setup['app']['id']}", headers=admin, json={"working_directory": r"C:\Trading\MT5\Other"})
    assert r.status_code == 409
    assert _app(client, admin, setup["app"]["id"])["working_directory"] == before


def test_type_change_rejected_while_session_active(client, admin, setup):
    _reach(client, setup["h"], "running")
    r = client.put(f"/api/applications/{setup['app']['id']}", headers=admin, json={"application_type": "MT4"})
    assert r.status_code == 409
    assert _app(client, admin, setup["app"]["id"])["application_type"] == "MT5"


def test_name_only_edit_allowed_while_session_active(client, admin, setup):
    _reach(client, setup["h"], "running")
    r = client.put(f"/api/applications/{setup['app']['id']}", headers=admin, json={"application_name": "Renamed"})
    assert r.status_code == 200 and r.json()["application_name"] == "Renamed"
    assert client.get("/api/sessions", headers=admin).json()[0]["status"] == "running"


def test_deactivation_while_active_still_stops_session(client, admin, setup):
    _reach(client, setup["h"], "running")
    r = client.put(f"/api/applications/{setup['app']['id']}", headers=admin, json={"status": "inactive"})
    assert r.status_code == 200 and r.json()["status"] == "inactive"
    s = client.get("/api/sessions", headers=admin).json()[0]
    assert s["status"] == "stop_requested" and s["message"] == "Application deactivated"


def test_path_change_plus_deactivation_rejected_and_nothing_saved(client, admin, setup):
    _reach(client, setup["h"], "running")
    r = client.put(f"/api/applications/{setup['app']['id']}", headers=admin,
                   json={"executable_path": NEW_PATH, "status": "inactive"})
    assert r.status_code == 409
    a = _app(client, admin, setup["app"]["id"])
    assert a["executable_path"] == MT5 and a["status"] == "active"
    assert client.get("/api/sessions", headers=admin).json()[0]["status"] == "running"     # session untouched too


@pytest.mark.parametrize("how", ["stopped", "failed"])
def test_path_change_allowed_after_session_ended(client, admin, setup, monkeypatch, how):
    h = setup["h"]
    online(client)
    client.post("/api/sessions/launch", headers=h)
    if how == "stopped":
        client.post("/api/sessions/disconnect", headers=h)                           # pending -> stopped at once
    else:
        monkeypatch.setattr(settings, "launch_timeout_seconds", -1)
        client.get("/api/sessions/status", headers=h)                                # stale launch -> failed
    assert client.get("/api/sessions/status", headers=h).json()["status"] == how
    r = client.put(f"/api/applications/{setup['app']['id']}", headers=admin, json={"executable_path": NEW_PATH})
    assert r.status_code == 200 and r.json()["executable_path"] == NEW_PATH


@pytest.mark.parametrize("same", [r"c:\trading\mt5\clienta\TERMINAL64.EXE", "C:/Trading/MT5/ClientA/terminal64.exe"])
def test_same_path_different_spelling_is_not_a_change(client, admin, setup, same):
    _reach(client, setup["h"], "running")
    r = client.put(f"/api/applications/{setup['app']['id']}", headers=admin, json={"executable_path": same})
    assert r.status_code == 200
    assert client.get("/api/sessions", headers=admin).json()[0]["status"] == "running"