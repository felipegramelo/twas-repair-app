"""Iteration 49 backend tests — Project shared_with permission model.

Rules (new):
- Admin CRUD all projects/tasks; supervisors only see & edit projects listed in shared_with.
- POST /api/projects/{id}/share (admin only)
- GET /api/projects/_/supervisors (admin only)
- Supervisor cannot create/delete projects (403) or mutate shared_with.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or "https://twas-repair-app-1.preview.emergentagent.com"
API = BASE_URL.rstrip("/") + "/api"

ADMIN = {"email": "admin@twasrepair.com", "password": "admin123"}
SUPER = {"email": "supervisor@twasrepair.com", "password": "super123"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    body = r.json()
    return body["access_token"] if "access_token" in body else body.get("token"), body.get("user", {})


@pytest.fixture(scope="module")
def admin_ctx():
    token, user = _login(ADMIN)
    return {"token": token, "user": user, "h": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="module")
def super_ctx():
    token, user = _login(SUPER)
    return {"token": token, "user": user, "h": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="module")
def project_ids(admin_ctx):
    ids = []
    yield ids
    for pid in ids:
        try:
            requests.delete(f"{API}/projects/{pid}", headers=admin_ctx["h"], timeout=15)
        except Exception:
            pass


# ---------- Auth sanity ----------
def test_login_shapes(admin_ctx, super_ctx):
    assert admin_ctx["token"]
    assert super_ctx["token"]
    assert admin_ctx["user"].get("role", "").lower() == "admin"
    assert super_ctx["user"].get("role", "").lower() == "supervisor"
    assert super_ctx["user"].get("id")


# ---------- Supervisors picker ----------
def test_list_supervisors_admin(admin_ctx, super_ctx):
    r = requests.get(f"{API}/projects/_/supervisors", headers=admin_ctx["h"], timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert any(s.get("email") == SUPER["email"] for s in data)
    for s in data:
        assert "id" in s and "name" in s and "email" in s


def test_list_supervisors_forbidden_for_supervisor(super_ctx):
    r = requests.get(f"{API}/projects/_/supervisors", headers=super_ctx["h"], timeout=15)
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"


# ---------- Project creation & visibility ----------
def _mk_project_payload(title="TEST_Iter49_Project"):
    return {
        "os_number": "TEST-OS-49",
        "title": title,
        "embarcacao": "Nave",
        "client": "TWAS",
        "location": "Rio",
        "start_date": "2026-01-01",
        "end_date": "2026-01-10",
        "lock_end_date": False,
        "description": "iter49",
        "shared_with": [],
        "tasks": [
            {"name": "Task A", "duration_value": 3, "duration_unit": "dias",
             "start_date": "2026-01-01", "end_date": "2026-01-03", "progress_percent": 0, "order": 1},
        ],
    }


def test_admin_creates_project_supervisor_cannot_see(admin_ctx, super_ctx, project_ids):
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=_mk_project_payload("TEST_Iter49_Unshared"), timeout=30)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    project_ids.append(pid)

    r2 = requests.get(f"{API}/projects", headers=super_ctx["h"], timeout=15)
    assert r2.status_code == 200
    ids = [p["id"] for p in r2.json()]
    assert pid not in ids, f"Supervisor should not see unshared project {pid}, saw: {ids}"

    # Supervisor also can't GET the specific project
    r3 = requests.get(f"{API}/projects/{pid}", headers=super_ctx["h"], timeout=15)
    assert r3.status_code == 403, f"expected 403, got {r3.status_code}"


def test_supervisor_cannot_create_project(super_ctx):
    r = requests.post(f"{API}/projects", headers=super_ctx["h"], json=_mk_project_payload("TEST_Iter49_SupCreate"), timeout=15)
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"


def test_share_then_supervisor_sees(admin_ctx, super_ctx, project_ids):
    # Create a fresh project
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=_mk_project_payload("TEST_Iter49_Shared"), timeout=30)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    project_ids.append(pid)

    sup_id = super_ctx["user"]["id"]
    rs = requests.post(f"{API}/projects/{pid}/share", headers=admin_ctx["h"],
                       json={"supervisor_ids": [sup_id]}, timeout=15)
    assert rs.status_code == 200, rs.text
    assert sup_id in rs.json().get("shared_with", [])

    # Supervisor now lists it
    r2 = requests.get(f"{API}/projects", headers=super_ctx["h"], timeout=15)
    assert r2.status_code == 200
    assert any(p["id"] == pid for p in r2.json())


def test_supervisor_task_ops_on_shared(admin_ctx, super_ctx, project_ids):
    # Create + share
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=_mk_project_payload("TEST_Iter49_TaskOps"), timeout=30)
    pid = r.json()["id"]
    project_ids.append(pid)
    sup_id = super_ctx["user"]["id"]
    requests.post(f"{API}/projects/{pid}/share", headers=admin_ctx["h"], json={"supervisor_ids": [sup_id]}, timeout=15)

    # Supervisor POST task
    r_add = requests.post(f"{API}/projects/{pid}/tasks", headers=super_ctx["h"],
                          json={"name": "SupTask", "duration_value": 1, "duration_unit": "dias",
                                "start_date": "2026-01-05", "end_date": "2026-01-06",
                                "progress_percent": 0, "order": 2}, timeout=15)
    assert r_add.status_code == 200, r_add.text
    tid = r_add.json()["task"]["id"]

    # Supervisor PUT task
    r_put = requests.put(f"{API}/projects/{pid}/tasks/{tid}", headers=super_ctx["h"],
                         json={"name": "SupTaskEdited"}, timeout=15)
    assert r_put.status_code == 200, r_put.text

    # PATCH progress
    r_pp = requests.patch(f"{API}/projects/{pid}/tasks/{tid}/progress", headers=super_ctx["h"],
                          json={"progress_percent": 50}, timeout=15)
    assert r_pp.status_code == 200, r_pp.text

    # DELETE task
    r_del = requests.delete(f"{API}/projects/{pid}/tasks/{tid}", headers=super_ctx["h"], timeout=15)
    assert r_del.status_code == 200, r_del.text


def test_supervisor_cannot_delete_project(admin_ctx, super_ctx, project_ids):
    # even for a shared project
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=_mk_project_payload("TEST_Iter49_NoDel"), timeout=30)
    pid = r.json()["id"]
    project_ids.append(pid)
    sup_id = super_ctx["user"]["id"]
    requests.post(f"{API}/projects/{pid}/share", headers=admin_ctx["h"], json={"supervisor_ids": [sup_id]}, timeout=15)

    r_del = requests.delete(f"{API}/projects/{pid}", headers=super_ctx["h"], timeout=15)
    assert r_del.status_code == 403, f"expected 403, got {r_del.status_code}"

    # Confirm still exists via admin
    r_g = requests.get(f"{API}/projects/{pid}", headers=admin_ctx["h"], timeout=15)
    assert r_g.status_code == 200


def test_supervisor_ops_on_unshared_return_403(admin_ctx, super_ctx, project_ids):
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=_mk_project_payload("TEST_Iter49_ForeignProj"), timeout=30)
    pid = r.json()["id"]
    project_ids.append(pid)
    # Not shared with supervisor.

    # add task
    r_add = requests.post(f"{API}/projects/{pid}/tasks", headers=super_ctx["h"],
                          json={"name": "X", "duration_value": 1, "duration_unit": "dias",
                                "start_date": "2026-01-05", "end_date": "2026-01-06",
                                "progress_percent": 0, "order": 1}, timeout=15)
    assert r_add.status_code == 403

    # update project
    r_put = requests.put(f"{API}/projects/{pid}", headers=super_ctx["h"], json={"title": "hack"}, timeout=15)
    assert r_put.status_code == 403

    # delete
    r_del = requests.delete(f"{API}/projects/{pid}", headers=super_ctx["h"], timeout=15)
    assert r_del.status_code == 403


def test_admin_put_updates_shared_with(admin_ctx, super_ctx, project_ids):
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=_mk_project_payload("TEST_Iter49_AdminPut"), timeout=30)
    pid = r.json()["id"]
    project_ids.append(pid)
    sup_id = super_ctx["user"]["id"]
    r_put = requests.put(f"{API}/projects/{pid}", headers=admin_ctx["h"],
                        json={"shared_with": [sup_id], "title": "TEST_Iter49_AdminPutUpdated"}, timeout=15)
    assert r_put.status_code == 200, r_put.text
    body = r_put.json()
    assert sup_id in body.get("shared_with", [])
    assert body.get("title") == "TEST_Iter49_AdminPutUpdated"


def test_supervisor_put_ignores_shared_with(admin_ctx, super_ctx, project_ids):
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=_mk_project_payload("TEST_Iter49_SupPut"), timeout=30)
    pid = r.json()["id"]
    project_ids.append(pid)
    sup_id = super_ctx["user"]["id"]
    requests.post(f"{API}/projects/{pid}/share", headers=admin_ctx["h"], json={"supervisor_ids": [sup_id]}, timeout=15)

    # Supervisor tries to clear shared_with (should be silently ignored)
    r_put = requests.put(f"{API}/projects/{pid}", headers=super_ctx["h"],
                         json={"shared_with": [], "title": "TEST_Iter49_SupPutTitle"}, timeout=15)
    assert r_put.status_code == 200, r_put.text
    body = r_put.json()
    assert body.get("title") == "TEST_Iter49_SupPutTitle"
    assert sup_id in body.get("shared_with", []), "shared_with should not have been cleared by supervisor"


def test_admin_sees_all_projects(admin_ctx, project_ids):
    r = requests.get(f"{API}/projects", headers=admin_ctx["h"], timeout=15)
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    for pid in project_ids:
        assert pid in ids, f"admin should see project {pid}"


def test_supervisor_share_forbidden(super_ctx, admin_ctx, project_ids):
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=_mk_project_payload("TEST_Iter49_ShareForbid"), timeout=30)
    pid = r.json()["id"]
    project_ids.append(pid)
    r2 = requests.post(f"{API}/projects/{pid}/share", headers=super_ctx["h"],
                       json={"supervisor_ids": []}, timeout=15)
    assert r2.status_code == 403


# ---------- Regression: auto-recalc & cascade delete ----------
def test_auto_recalc_end_date(admin_ctx, project_ids):
    payload = _mk_project_payload("TEST_Iter49_Recalc")
    payload["lock_end_date"] = False
    payload["end_date"] = "2026-01-05"
    payload["tasks"] = [
        {"name": "T1", "duration_value": 2, "duration_unit": "dias",
         "start_date": "2026-01-01", "end_date": "2026-01-20", "progress_percent": 0, "order": 1},
    ]
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=payload, timeout=30)
    assert r.status_code == 200
    pid = r.json()["id"]
    project_ids.append(pid)
    assert r.json().get("end_date", "").startswith("2026-01-20"), f"got {r.json().get('end_date')}"


def test_cascade_delete_task(admin_ctx, project_ids):
    payload = _mk_project_payload("TEST_Iter49_Cascade")
    payload["tasks"] = []
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=payload, timeout=30)
    pid = r.json()["id"]
    project_ids.append(pid)

    # add parent
    rp = requests.post(f"{API}/projects/{pid}/tasks", headers=admin_ctx["h"],
                       json={"name": "Parent", "duration_value": 1, "duration_unit": "dias",
                             "start_date": "2026-01-01", "end_date": "2026-01-02",
                             "progress_percent": 0, "order": 1}, timeout=15)
    parent_id = rp.json()["task"]["id"]

    # child
    rc = requests.post(f"{API}/projects/{pid}/tasks", headers=admin_ctx["h"],
                       json={"name": "Child", "duration_value": 1, "duration_unit": "dias",
                             "parent_id": parent_id,
                             "start_date": "2026-01-01", "end_date": "2026-01-02",
                             "progress_percent": 0, "order": 1}, timeout=15)
    child_id = rc.json()["task"]["id"]

    rd = requests.delete(f"{API}/projects/{pid}/tasks/{parent_id}", headers=admin_ctx["h"], timeout=15)
    assert rd.status_code == 200
    deleted = set(rd.json().get("deleted_ids", []))
    assert parent_id in deleted and child_id in deleted


def test_pdf_regression(admin_ctx, project_ids):
    payload = _mk_project_payload("TEST_Iter49_PDF")
    r = requests.post(f"{API}/projects", headers=admin_ctx["h"], json=payload, timeout=30)
    pid = r.json()["id"]
    project_ids.append(pid)
    r2 = requests.get(f"{API}/projects/{pid}/pdf", headers=admin_ctx["h"], timeout=30)
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("application/pdf")
    assert len(r2.content) > 500
