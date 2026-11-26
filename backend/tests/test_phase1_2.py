from conftest import login

MT5_A = r"C:\Trading\MT5\ClientA\terminal64.exe"
MT5_B = r"C:\Trading\MT5\ClientB\terminal64.exe"


def mk_client(c, h, email="a@example.com", **kw):
    r = c.post("/api/clients", headers=h, json={"name": "Client A", "email": email, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def mk_app(c, h, path=MT5_A, typ="MT5"):
    r = c.post("/api/applications", headers=h, json={
        "application_name": "MT5 " + path, "application_type": typ, "executable_path": path})
    assert r.status_code == 201, r.text
    return r.json()


# ---------- auth ----------
def test_login_me_logout(client, admin):
    assert client.get("/api/auth/me", headers=admin).json()["role"] == "admin"
    assert client.post("/api/auth/logout", headers=admin).status_code == 204
    assert client.get("/api/auth/me", headers=admin).status_code == 401   # token revoked


def test_bad_login_generic_and_lockout(client):
    r1 = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})
    r2 = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "wrong"})
    assert r1.status_code == r2.status_code == 401 and r1.json() == r2.json()
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "admin@example.com", "password": "wrong"})
    r = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "AdminPass123"})
    assert r.status_code == 429


def test_requires_auth(client):
    assert client.get("/api/clients").status_code == 401
    assert client.get("/api/clients", headers={"Authorization": "Bearer junk"}).status_code == 401


# ---------- clients ----------
def test_create_client_generates_code_and_password(client, admin):
    c = mk_client(client, admin)
    assert c["client_code"] == f"CLIENT{c['id']:03d}" and len(c["initial_password"]) >= 10
    login(client, "a@example.com", c["initial_password"])


def test_client_validation_and_duplicates(client, admin):
    mk_client(client, admin, client_code="client001")
    assert client.post("/api/clients", headers=admin, json={"name": "x", "email": "a@example.com"}).status_code == 409
    assert client.post("/api/clients", headers=admin, json={"name": "x", "email": "b@example.com", "client_code": "CLIENT001"}).status_code == 409
    assert client.post("/api/clients", headers=admin, json={"name": "x", "email": "c@example.com", "password": "short"}).status_code == 422


def test_deactivate_kicks_out_and_blocks_login(client, admin):
    c = mk_client(client, admin, password="ClientPass123")
    h = login(client, "a@example.com", "ClientPass123")
    client.put(f"/api/clients/{c['id']}", headers=admin, json={"status": "inactive"})
    assert client.get("/api/auth/me", headers=h).status_code == 401
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "ClientPass123"}).status_code == 401


def test_reset_password(client, admin):
    c = mk_client(client, admin, password="ClientPass123")
    h = login(client, "a@example.com", "ClientPass123")
    new = client.post(f"/api/clients/{c['id']}/reset-password", headers=admin, json={}).json()["generated_password"]
    assert client.get("/api/auth/me", headers=h).status_code == 401
    login(client, "a@example.com", new)


def test_client_cannot_use_admin_api(client, admin):
    mk_client(client, admin, password="ClientPass123")
    h = login(client, "a@example.com", "ClientPass123")
    for method, url in [("get", "/api/clients"), ("get", "/api/applications"), ("get", "/api/assignments")]:
        assert getattr(client, method)(url, headers=h).status_code == 403
    assert client.post("/api/applications", headers=h, json={}).status_code == 403


def test_activity_history(client, admin):
    c = mk_client(client, admin, password="ClientPass123")
    login(client, "a@example.com", "ClientPass123")
    acts = [a["activity"] for a in client.get(f"/api/clients/{c['id']}/activity", headers=admin).json()]
    assert "login" in acts


# ---------- applications ----------
def test_application_path_policy(client, admin):
    bad = [
        (r"C:\Windows\System32\cmd.exe", "MT5"),
        (r"C:\Trading\MT5\A\notepad.exe", "MT5"),
        (r"C:\Trading\MT5\A\terminal.exe", "MT5"),          # wrong exe for type
        (r"C:\Trading\..\Windows\terminal64.exe", "MT5"),   # traversal
        (r"\\server\share\terminal64.exe", "MT5"),          # UNC
        (r"terminal64.exe", "MT5"),                         # relative
        (r"D:\Other\terminal64.exe", "MT5"),                # outside root
        (r"C:\Trading\MT5\A\terminal64.exe:evil", "MT5"),   # ADS
        (r"C:\Trading\MT5\A\terminal64.exe", "MT4"),        # type mismatch
    ]
    for path, typ in bad:
        r = client.post("/api/applications", headers=admin, json={
            "application_name": "x", "application_type": typ, "executable_path": path})
        assert r.status_code == 422, (path, r.text)
    r = client.post("/api/applications", headers=admin, json={
        "application_name": "x", "application_type": "MT5", "executable_path": MT5_A,
        "working_directory": r"C:\Trading\MT5\Other"})
    assert r.status_code == 422


def test_application_crud_and_case_insensitive_root(client, admin):
    a = mk_app(client, admin, r"c:\trading\mt5\clienta\terminal64.exe")
    assert a["working_directory"].lower() == r"c:\trading\mt5\clienta"
    assert client.post("/api/applications", headers=admin, json={
        "application_name": "dup", "application_type": "MT5", "executable_path": r"C:\Trading\MT5\ClientA\terminal64.exe"}).status_code == 409
    r = client.put(f"/api/applications/{a['id']}", headers=admin, json={"executable_path": MT5_B})
    assert r.status_code == 200 and r.json()["working_directory"] == r"C:\Trading\MT5\ClientB"
    r = client.put(f"/api/applications/{a['id']}", headers=admin, json={"executable_path": r"C:\Windows\x\terminal64.exe"})
    assert r.status_code == 422
    assert client.delete(f"/api/applications/{a['id']}", headers=admin).status_code == 204


# ---------- assignments ----------
def test_full_assignment_flow(client, admin):
    ca, cb = mk_client(client, admin, "a@example.com", password="ClientPass123"), mk_client(client, admin, "b@example.com", password="ClientPass123")
    a, b = mk_app(client, admin, MT5_A), mk_app(client, admin, MT5_B)

    r = client.post("/api/assignments", headers=admin, json={"client_id": ca["id"], "application_id": a["id"]})
    assert r.status_code == 201 and r.json()["application"]["executable_path"] == MT5_A
    # same installation can't go to a second client; a client can't get two
    assert client.post("/api/assignments", headers=admin, json={"client_id": cb["id"], "application_id": a["id"]}).status_code == 409
    assert client.post("/api/assignments", headers=admin, json={"client_id": ca["id"], "application_id": b["id"]}).status_code == 409
    assert client.post("/api/assignments", headers=admin, json={"client_id": cb["id"], "application_id": b["id"]}).status_code == 201

    # change: A -> free app is fine, to B's app is not
    assert client.put(f"/api/assignments/{ca['id']}", headers=admin, json={"application_id": b["id"]}).status_code == 409

    # in use -> can't delete app
    assert client.delete(f"/api/applications/{a['id']}", headers=admin).status_code == 409

    # visible in client listing (view assignment)
    lst = client.get("/api/clients", headers=admin).json()
    assert {c["email"]: c["assignment"]["application"]["executable_path"] for c in lst} == {"a@example.com": MT5_A, "b@example.com": MT5_B}

    # client sees only their own
    ha = login(client, "a@example.com", "ClientPass123")
    assert client.get(f"/api/assignments/{ca['id']}", headers=ha).json()["application_id"] == a["id"]
    assert client.get(f"/api/assignments/{cb['id']}", headers=ha).status_code == 403

    # unassign then reassign
    assert client.delete(f"/api/assignments/{ca['id']}", headers=admin).status_code == 204
    assert client.get(f"/api/assignments/{ca['id']}", headers=admin).status_code == 404
    assert client.post("/api/assignments", headers=admin, json={"client_id": ca["id"], "application_id": a["id"]}).status_code == 201


def test_cannot_assign_inactive_or_to_admin(client, admin):
    c = mk_client(client, admin)
    a = mk_app(client, admin)
    client.put(f"/api/applications/{a['id']}", headers=admin, json={"status": "inactive"})
    assert client.post("/api/assignments", headers=admin, json={"client_id": c["id"], "application_id": a["id"]}).status_code == 409
    admin_id = client.get("/api/auth/me", headers=admin).json()["id"]
    assert client.post("/api/assignments", headers=admin, json={"client_id": admin_id, "application_id": a["id"]}).status_code == 404


def test_delete_client_removes_assignment(client, admin):
    c, a = mk_client(client, admin), mk_app(client, admin)
    client.post("/api/assignments", headers=admin, json={"client_id": c["id"], "application_id": a["id"]})
    assert client.delete(f"/api/clients/{c['id']}", headers=admin).status_code == 204
    assert client.get("/api/assignments", headers=admin).json() == []
