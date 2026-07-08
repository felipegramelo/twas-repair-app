"""Backend tests for Projects (Cronograma) module - iteration 45."""
import os
import io
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("REACT_APP_BACKEND_URL") or "https://twas-repair-app-1.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_CREDS = {"email": "admin@twasrepair.com", "password": "admin123"}
SUPER_CREDS = {"email": "supervisor@twasrepair.com", "password": "super123"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"] if "access_token" in r.json() else r.json().get("token")


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_CREDS)


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_CREDS)


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def sample_os(admin_token):
    """Pick an existing OS or create one."""
    r = requests.get(f"{API}/service-orders", headers=_h(admin_token), timeout=30)
    if r.status_code == 200 and isinstance(r.json(), list) and r.json():
        return r.json()[0].get("os_number") or r.json()[0].get("number") or "TEST-OS"
    # fallback
    return "TEST-OS-45"


created_projects = []
stash = {}


class TestProjectsCRUD:
    def test_01_admin_create_project(self, admin_token, sample_os):
        payload = {
            "os_number": sample_os,
            "title": "TEST_ Cronograma Iteration 45",
            "embarcacao": "Test Vessel",
            "client": "Test Client",
            "start_date": "2026-01-15",
            "lock_end_date": False,
            "tasks": [
                {"name": "Fase 1 - Desmontagem", "duration_value": 5, "duration_unit": "dias",
                 "start_date": "2026-01-15", "end_date": "2026-01-20", "progress_percent": 0, "order": 1},
                {"name": "Fase 2 - Montagem", "duration_value": 3, "duration_unit": "dias",
                 "start_date": "2026-01-21", "end_date": "2026-01-24", "progress_percent": 0, "order": 2},
            ],
        }
        r = requests.post(f"{API}/projects", json=payload, headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        data = r.json()
        assert "id" in data
        assert data["title"] == payload["title"]
        assert data["os_number"] == sample_os
        assert len(data["tasks"]) == 2
        for t in data["tasks"]:
            assert "id" in t and len(t["id"]) >= 8
        # Auto-recalc: end_date should be max task end (2026-01-24)
        assert (data.get("end_date") or "").startswith("2026-01-24"), f"end_date auto-recalc failed: {data.get('end_date')}"
        created_projects.append(data["id"])

    def test_02_supervisor_create_forbidden(self, super_token, sample_os):
        payload = {"os_number": sample_os, "title": "TEST_ super try", "tasks": []}
        r = requests.post(f"{API}/projects", json=payload, headers=_h(super_token), timeout=30)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"

    def test_03_list_projects_admin(self, admin_token):
        r = requests.get(f"{API}/projects", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert any(p["id"] == created_projects[0] for p in r.json())

    def test_04_list_projects_supervisor(self, super_token):
        r = requests.get(f"{API}/projects", headers=_h(super_token), timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_05_get_project_detail(self, admin_token):
        pid = created_projects[0]
        r = requests.get(f"{API}/projects/{pid}", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == pid
        assert len(d["tasks"]) == 2

    def test_06_update_project_admin(self, admin_token):
        pid = created_projects[0]
        r = requests.put(f"{API}/projects/{pid}",
                         json={"title": "TEST_ Cronograma Updated", "lock_end_date": False},
                         headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        assert r.json()["title"] == "TEST_ Cronograma Updated"

    def test_07_update_project_supervisor_forbidden(self, super_token):
        pid = created_projects[0]
        r = requests.put(f"{API}/projects/{pid}", json={"title": "hax"},
                         headers=_h(super_token), timeout=30)
        assert r.status_code == 403

    def test_08_add_task_admin_and_subtask(self, admin_token):
        pid = created_projects[0]
        # add new root task
        r = requests.post(f"{API}/projects/{pid}/tasks",
                          json={"name": "Fase 3 - Testes", "duration_value": 2, "duration_unit": "dias",
                                "start_date": "2026-01-25", "end_date": "2026-01-27",
                                "progress_percent": 0, "order": 3},
                          headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        new_task = r.json()["task"]
        parent_task_id = new_task["id"]

        # add sub-task
        r2 = requests.post(f"{API}/projects/{pid}/tasks",
                           json={"name": "Fase 3.1 - Sub-task", "parent_id": parent_task_id,
                                 "duration_value": 1, "duration_unit": "hrs",
                                 "start_date": "2026-01-25", "end_date": "2026-01-25",
                                 "progress_percent": 0, "order": 1},
                           headers=_h(admin_token), timeout=30)
        assert r2.status_code == 200
        sub = r2.json()["task"]
        assert sub["parent_id"] == parent_task_id

        # verify hierarchy persisted
        det = requests.get(f"{API}/projects/{pid}", headers=_h(admin_token)).json()
        parent_ids = {t["id"]: t.get("parent_id") for t in det["tasks"]}
        assert parent_ids[sub["id"]] == parent_task_id
        # stash for later cascade test
        stash["phase3_parent"] = parent_task_id
        stash["phase3_sub"] = sub["id"]

    def test_09_update_task_admin(self, admin_token):
        pid = created_projects[0]
        det = requests.get(f"{API}/projects/{pid}", headers=_h(admin_token)).json()
        task_id = det["tasks"][0]["id"]
        r = requests.put(f"{API}/projects/{pid}/tasks/{task_id}",
                         json={"name": "Fase 1 - Desmontagem (edit)", "duration_value": 6, "order": 10},
                         headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        t = next(t for t in d["tasks"] if t["id"] == task_id)
        assert t["name"] == "Fase 1 - Desmontagem (edit)"
        assert t["duration_value"] == 6
        assert t["order"] == 10

    def test_10_supervisor_progress_clamp(self, super_token, admin_token):
        pid = created_projects[0]
        det = requests.get(f"{API}/projects/{pid}", headers=_h(admin_token)).json()
        task_id = det["tasks"][0]["id"]

        # negative -> 0
        r = requests.patch(f"{API}/projects/{pid}/tasks/{task_id}/progress",
                           json={"progress_percent": -25}, headers=_h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        t = next(t for t in r.json()["tasks"] if t["id"] == task_id)
        assert t["progress_percent"] == 0

        # >100 -> 100
        r = requests.patch(f"{API}/projects/{pid}/tasks/{task_id}/progress",
                           json={"progress_percent": 250}, headers=_h(super_token), timeout=30)
        assert r.status_code == 200
        t = next(t for t in r.json()["tasks"] if t["id"] == task_id)
        assert t["progress_percent"] == 100

        # normal value
        r = requests.patch(f"{API}/projects/{pid}/tasks/{task_id}/progress",
                           json={"progress_percent": 42.5}, headers=_h(super_token), timeout=30)
        assert r.status_code == 200
        t = next(t for t in r.json()["tasks"] if t["id"] == task_id)
        assert abs(t["progress_percent"] - 42.5) < 0.01

    def test_11_supervisor_cannot_put_task(self, super_token, admin_token):
        pid = created_projects[0]
        det = requests.get(f"{API}/projects/{pid}", headers=_h(admin_token)).json()
        task_id = det["tasks"][0]["id"]
        r = requests.put(f"{API}/projects/{pid}/tasks/{task_id}",
                         json={"name": "hacked"}, headers=_h(super_token), timeout=30)
        assert r.status_code == 403

    def test_12_delete_task_cascade(self, admin_token):
        pid = created_projects[0]
        # find phase3_parent stashed
        parent_id = stash["phase3_parent"]

        # add a second sub-task to phase3_parent
        r = requests.post(f"{API}/projects/{pid}/tasks",
                          json={"name": "Fase 3.2 - Sub-task 2", "parent_id": parent_id,
                                "duration_value": 1, "duration_unit": "hrs",
                                "start_date": "2026-01-26", "end_date": "2026-01-26"},
                          headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        sub2_id = r.json()["task"]["id"]

        # ensure we have parent + 2 subs
        before = requests.get(f"{API}/projects/{pid}", headers=_h(admin_token)).json()
        ids_before = {t["id"] for t in before["tasks"]}
        assert parent_id in ids_before and sub2_id in ids_before

        # Delete parent -> should cascade
        r = requests.delete(f"{API}/projects/{pid}/tasks/{parent_id}", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        deleted = r.json().get("deleted_ids", [])
        assert parent_id in deleted
        assert sub2_id in deleted
        # first sub too
        first_sub_id = stash["phase3_sub"]
        assert first_sub_id in deleted

        after = requests.get(f"{API}/projects/{pid}", headers=_h(admin_token)).json()
        ids_after = {t["id"] for t in after["tasks"]}
        assert parent_id not in ids_after and sub2_id not in ids_after and first_sub_id not in ids_after

    def test_13_auto_recalc_end_date(self, admin_token, sample_os):
        # Create fresh project lock_end_date=False
        payload = {
            "os_number": sample_os, "title": "TEST_ recalc project",
            "start_date": "2026-02-01", "lock_end_date": False, "tasks": []
        }
        r = requests.post(f"{API}/projects", json=payload, headers=_h(admin_token))
        assert r.status_code == 200
        pid = r.json()["id"]
        created_projects.append(pid)

        # add task ending 2026-02-15 -> project.end_date auto=2026-02-15
        r = requests.post(f"{API}/projects/{pid}/tasks",
                          json={"name": "T1", "start_date": "2026-02-01",
                                "end_date": "2026-02-15", "duration_value": 15},
                          headers=_h(admin_token))
        assert r.status_code == 200
        det = requests.get(f"{API}/projects/{pid}", headers=_h(admin_token)).json()
        assert (det.get("end_date") or "").startswith("2026-02-15"), f"got {det.get('end_date')}"

        # Lock end_date and change to 2026-02-20 explicitly via PUT
        r = requests.put(f"{API}/projects/{pid}",
                         json={"lock_end_date": True, "end_date": "2026-02-20"},
                         headers=_h(admin_token))
        assert r.status_code == 200

        # add another task with end 2026-03-30 -> should NOT auto-recalc
        r = requests.post(f"{API}/projects/{pid}/tasks",
                          json={"name": "T2", "start_date": "2026-03-01",
                                "end_date": "2026-03-30", "duration_value": 30},
                          headers=_h(admin_token))
        assert r.status_code == 200
        det2 = requests.get(f"{API}/projects/{pid}", headers=_h(admin_token)).json()
        # end_date must remain 2026-02-20 because lock_end_date=True
        assert (det2.get("end_date") or "").startswith("2026-02-20"), f"lock failed - got {det2.get('end_date')}"

    def test_14_project_pdf_query_token(self, admin_token):
        pid = created_projects[0]
        r = requests.get(f"{API}/projects/{pid}/pdf?download=1&token={admin_token}", timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 1024
        assert r.content[:5] == b"%PDF-"
        assert "attachment" in r.headers.get("content-disposition", "").lower()

    def test_15_project_pdf_header_token_inline(self, admin_token):
        pid = created_projects[0]
        r = requests.get(f"{API}/projects/{pid}/pdf", headers=_h(admin_token), timeout=60)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        assert "inline" in r.headers.get("content-disposition", "").lower()

    def test_16_project_pdf_no_token_401(self):
        pid = created_projects[0]
        r = requests.get(f"{API}/projects/{pid}/pdf", timeout=30)
        assert r.status_code == 401

    def test_17_regression_reports_and_timesheets(self, admin_token):
        r1 = requests.get(f"{API}/reports", headers=_h(admin_token), timeout=30)
        assert r1.status_code == 200, f"reports regression: {r1.status_code}"
        r2 = requests.get(f"{API}/timesheets", headers=_h(admin_token), timeout=30)
        assert r2.status_code == 200, f"timesheets regression: {r2.status_code}"

    def test_99_cleanup(self, admin_token):
        for item in created_projects:
            if isinstance(item, str) and len(item) >= 20:
                try:
                    requests.delete(f"{API}/projects/{item}", headers=_h(admin_token), timeout=30)
                except Exception:
                    pass
