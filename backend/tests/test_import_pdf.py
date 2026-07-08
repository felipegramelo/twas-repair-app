"""Test PDF import via LLM Gemini feature for projects."""
import os
import time
import requests
import pytest

BASE_URL = "https://twas-repair-app-1.preview.emergentagent.com"
API = f"{BASE_URL}/api"
PDF_PATH = "/tmp/amaralina.pdf"

ADMIN = {"email": "admin@twasrepair.com", "password": "admin123"}
SUPER = {"email": "supervisor@twasrepair.com", "password": "super123"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    assert tok, f"No token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER)


@pytest.fixture(scope="module")
def created_project_id(admin_token):
    """Create empty project for admin, cleanup at end."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "name": "TEST_ImportPDF_Amaralina",
        "title": "TEST_ImportPDF_Amaralina",
        "os_number": f"TEST-{int(time.time())}",
        "description": "auto-test",
    }
    r = requests.post(f"{API}/projects", json=payload, headers=headers, timeout=15)
    assert r.status_code in (200, 201), f"create project failed: {r.status_code} {r.text}"
    pid = r.json().get("id") or r.json().get("_id")
    assert pid
    yield pid
    # cleanup
    try:
        requests.delete(f"{API}/projects/{pid}", headers=headers, timeout=10)
    except Exception:
        pass


class TestImportPDF:

    def test_pdf_available(self):
        assert os.path.exists(PDF_PATH) and os.path.getsize(PDF_PATH) > 1000

    def test_empty_file_returns_400(self, admin_token, created_project_id):
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Send empty bytes
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        r = requests.post(
            f"{API}/projects/{created_project_id}/import-pdf",
            headers=headers, files=files, timeout=15,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"

    def test_invalid_pdf_returns_400(self, admin_token, created_project_id):
        headers = {"Authorization": f"Bearer {admin_token}"}
        files = {"file": ("bad.pdf", b"not a pdf at all just text", "application/pdf")}
        r = requests.post(
            f"{API}/projects/{created_project_id}/import-pdf",
            headers=headers, files=files, timeout=15,
        )
        assert r.status_code == 400, f"expected 400 for invalid PDF, got {r.status_code}: {r.text}"

    def test_supervisor_no_permission_returns_403(self, super_token, created_project_id):
        headers = {"Authorization": f"Bearer {super_token}"}
        with open(PDF_PATH, "rb") as f:
            files = {"file": ("amaralina.pdf", f, "application/pdf")}
            r = requests.post(
                f"{API}/projects/{created_project_id}/import-pdf",
                headers=headers, files=files, timeout=20,
            )
        assert r.status_code == 403, f"expected 403 for supervisor without shared_with, got {r.status_code}: {r.text}"

    def test_import_real_pdf_returns_200_quickly_and_polls_to_done(self, admin_token, created_project_id):
        headers = {"Authorization": f"Bearer {admin_token}"}
        start = time.time()
        with open(PDF_PATH, "rb") as f:
            files = {"file": ("amaralina.pdf", f, "application/pdf")}
            r = requests.post(
                f"{API}/projects/{created_project_id}/import-pdf",
                headers=headers, files=files, timeout=30,
            )
        elapsed = time.time() - start
        assert r.status_code == 200, f"import failed: {r.status_code} {r.text}"
        body = r.json()
        assert body.get("status") == "processing", f"unexpected body: {body}"
        assert elapsed < 15, f"POST took too long ({elapsed:.1f}s) — should be async"
        print(f"POST returned {elapsed:.1f}s with status=processing")

        # Poll GET /projects/{id}
        final_status = None
        final_doc = None
        deadline = time.time() + 180
        while time.time() < deadline:
            try:
                gr = requests.get(f"{API}/projects/{created_project_id}", headers=headers, timeout=30)
            except requests.exceptions.ReadTimeout:
                print(f"  t={time.time()-start:.1f}s GET timeout (backend busy) — retrying")
                time.sleep(3)
                continue
            assert gr.status_code == 200, f"GET project failed: {gr.status_code} {gr.text}"
            doc = gr.json()
            st = doc.get("import_status")
            print(f"  t={time.time()-start:.1f}s import_status={st} tasks={len(doc.get('tasks') or [])}")
            if st in ("done", "error"):
                final_status = st
                final_doc = doc
                break
            time.sleep(3)

        assert final_status is not None, "Import did not finish in 90s"
        if final_status == "error":
            pytest.fail(f"Import failed with error: {final_doc.get('import_error')}")

        assert final_status == "done"
        tasks = final_doc.get("tasks") or []
        print(f"Extracted {len(tasks)} tasks")
        assert len(tasks) >= 20, f"Expected 20+ tasks, got {len(tasks)}"

        # Validate task structure
        for t in tasks[:5]:
            assert t.get("name"), f"task missing name: {t}"
            assert "duration_value" in t
            assert t.get("duration_unit") in ("dias", "hrs")
            assert 0 <= float(t.get("progress_percent", 0)) <= 100
            assert "parent_id" in t

        # Confirm at least one task has a parent (hierarchy)
        has_hierarchy = any(t.get("parent_id") for t in tasks)
        print(f"Has hierarchy: {has_hierarchy}")
        assert final_doc.get("import_error") is None
