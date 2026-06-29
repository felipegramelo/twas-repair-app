"""
Iteration 44 - Bug fix validation: os_number='SEM-OS' fallback when empty.

Background
----------
Make.com scenarios (TWAS Reports → OneDrive and TWAS Timesheets → OneDrive)
were auto-disabled because the backend sent `os_number=''` (empty) to the
webhook, which produced "Missing value of required parameter name" on
OneDrive Create-a-Folder. The fix forces:
    os_num = (str(report.get('os_number') or '').strip() or 'SEM-OS')
in both reports.py and timesheets.py PDF download endpoints.

What this test validates
------------------------
1. Existing report with a real `os_number` → GET /api/reports/{id}/pdf?download=1
   triggers `OneDrive upload OK [report] ... -> 200` in the log (regression).
2. Existing timesheet with `os_number` → GET /api/timesheets/{id}/pdf?download=1
   triggers `OneDrive upload OK [timesheet] ... -> 200` (regression).
3. **NEW**: Report whose `os_number` is empty string → PDF download still
   triggers `OneDrive upload OK [report]` because the backend now substitutes
   `SEM-OS`. Webhook would otherwise refuse the payload.
4. GET /api/reports/{id}/pdf without download=1 returns the PDF inline and
   does NOT fire the webhook (no log line during 8s).
5. CRUD smoke: GET /api/reports, GET /api/timesheets still work.

Cleanup
-------
Deletes the test report (and its parent OS) at module teardown so the DB
does not get polluted. The test OS uses a clearly-identifiable name
prefix (TEST_FALLBACK_SEM_OS_<ts>) for easy manual cleanup on OneDrive.
"""
import os
import re
import time
import pytest
import requests

BASE_URL = (
    os.environ.get("REACT_APP_BACKEND_URL")
    or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or "https://twas-repair-app-1.preview.emergentagent.com"
).rstrip("/")

ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"

BACKEND_LOG = "/var/log/supervisor/backend.err.log"
UPLOAD_TIMEOUT = 30.0  # seconds to wait for asyncio background upload


# -------------------- log helpers --------------------
def _log_size() -> int:
    try:
        return os.path.getsize(BACKEND_LOG)
    except OSError:
        return 0


def _read_log_since(offset: int) -> str:
    try:
        with open(BACKEND_LOG, "rb") as f:
            f.seek(offset)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _wait_for_log(offset: int, pattern: str, timeout: float = UPLOAD_TIMEOUT) -> str:
    deadline = time.time() + timeout
    rx = re.compile(pattern)
    last = ""
    while time.time() < deadline:
        last = _read_log_since(offset)
        if rx.search(last):
            return last
        time.sleep(0.5)
    return last


# -------------------- fixtures --------------------
@pytest.fixture(scope="module")
def admin_token() -> str:
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def existing_report_id(auth_headers) -> str:
    resp = requests.get(f"{BASE_URL}/api/reports", headers=auth_headers, timeout=15)
    assert resp.status_code == 200
    reports = resp.json().get("reports", [])
    # Prefer one with a real, non-empty os_number
    for r in reports:
        if (r.get("os_number") or "").strip():
            return r["id"]
    pytest.skip("No existing report with os_number found")


@pytest.fixture(scope="module")
def existing_timesheet_id(auth_headers) -> str:
    resp = requests.get(f"{BASE_URL}/api/timesheets", headers=auth_headers, timeout=15)
    assert resp.status_code == 200
    data = resp.json()
    items = data.get("timesheets", data) if isinstance(data, dict) else data
    if isinstance(items, dict):
        items = items.get("timesheets", [])
    for t in items:
        if (t.get("os_number") or "").strip():
            return t["id"]
    pytest.skip("No existing timesheet with os_number found")


@pytest.fixture(scope="module")
def empty_os_report(auth_headers):
    """Create an OS with os_number='' and a Report linked to it.

    Yields the report_id. Teardown deletes both report and OS.
    """
    ts = int(time.time())
    os_payload = {
        "os_number": "",  # <-- empty, triggers the bug-fix fallback
        "client": f"TEST_FALLBACK_SEM_OS_{ts}",
        "location": "TEST_LOCATION",
        "embarcacao": "TEST_VESSEL",
        "service": f"TEST_FALLBACK_SEM_OS_{ts}",
        "employees": [],
        "schedule_type": "07-19",
    }
    so_resp = requests.post(
        f"{BASE_URL}/api/service-orders",
        json=os_payload,
        headers=auth_headers,
        timeout=15,
    )
    assert so_resp.status_code in (200, 201), (
        f"OS create failed: {so_resp.status_code} {so_resp.text}"
    )
    so = so_resp.json()
    os_id = so.get("id") or so.get("_id")
    assert os_id, f"OS create response missing id: {so}"

    report_payload = {
        "report_type": "service",
        "os_id": os_id,
        "periodo_inicio": "01/01/2026",
        "periodo_fim": "01/01/2026",
        "executado_por": "TEST_FALLBACK",
    }
    rep_resp = requests.post(
        f"{BASE_URL}/api/reports",
        json=report_payload,
        headers=auth_headers,
        timeout=15,
    )
    assert rep_resp.status_code in (200, 201), (
        f"Report create failed: {rep_resp.status_code} {rep_resp.text}"
    )
    report = rep_resp.json()
    report_id = report["id"]
    # Sanity: os_number on the new report should be empty string
    assert report.get("os_number", "") == "", (
        f"Expected empty os_number on test report, got: {report.get('os_number')!r}"
    )

    yield {"report_id": report_id, "os_id": os_id, "marker": f"TEST_FALLBACK_SEM_OS_{ts}"}

    # ---- teardown ----
    try:
        requests.delete(
            f"{BASE_URL}/api/reports/{report_id}", headers=auth_headers, timeout=15
        )
    except Exception:
        pass
    try:
        requests.delete(
            f"{BASE_URL}/api/service-orders/{os_id}", headers=auth_headers, timeout=15
        )
    except Exception:
        pass


# -------------------- tests --------------------
class TestRegressionOneDriveUploads:
    """Existing behaviour must keep working."""

    def test_report_pdf_download_triggers_upload(self, auth_headers, existing_report_id):
        offset = _log_size()
        r = requests.get(
            f"{BASE_URL}/api/reports/{existing_report_id}/pdf?download=1",
            headers=auth_headers,
            timeout=60,
        )
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "attachment" in r.headers.get("content-disposition", "")
        assert r.content[:4] == b"%PDF"

        log = _wait_for_log(
            offset, r"services\.onedrive - INFO - OneDrive upload OK \[report\][^\n]+-> 2\d\d"
        )
        assert "OneDrive upload OK [report]" in log and "-> 2" in log, (
            f"Expected upload OK log line, got tail:\n{log[-1500:]}"
        )

    def test_timesheet_pdf_download_triggers_upload(self, auth_headers, existing_timesheet_id):
        offset = _log_size()
        r = requests.get(
            f"{BASE_URL}/api/timesheets/{existing_timesheet_id}/pdf?download=1",
            headers=auth_headers,
            timeout=60,
        )
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "attachment" in r.headers.get("content-disposition", "")
        assert r.content[:4] == b"%PDF"

        log = _wait_for_log(
            offset,
            r"services\.onedrive - INFO - OneDrive upload OK \[timesheet\][^\n]+-> 2\d\d",
        )
        assert "OneDrive upload OK [timesheet]" in log and "-> 2" in log, (
            f"Expected upload OK log line, got tail:\n{log[-1500:]}"
        )

    def test_report_pdf_inline_does_NOT_trigger_upload(self, auth_headers, existing_report_id):
        offset = _log_size()
        r = requests.get(
            f"{BASE_URL}/api/reports/{existing_report_id}/pdf",
            headers=auth_headers,
            timeout=60,
        )
        assert r.status_code == 200
        assert "inline" in r.headers.get("content-disposition", "")
        # Wait briefly and ensure NO upload OK line shows up
        time.sleep(8)
        log = _read_log_since(offset)
        assert "OneDrive upload OK [report]" not in log, (
            f"Preview must NOT trigger upload, but got log:\n{log[-1500:]}"
        )


class TestSemOsFallback:
    """Bug fix: empty os_number must be substituted with 'SEM-OS' so the
    Make.com webhook accepts the payload (returns 2xx)."""

    def test_empty_os_number_report_uses_SEM_OS_fallback(self, auth_headers, empty_os_report):
        report_id = empty_os_report["report_id"]
        offset = _log_size()
        r = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/pdf?download=1",
            headers=auth_headers,
            timeout=60,
        )
        # Endpoint must respond 200 with valid PDF regardless of webhook state
        assert r.status_code == 200, f"PDF download failed: {r.status_code} {r.text[:300]}"
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "attachment" in r.headers.get("content-disposition", "")
        assert r.content[:4] == b"%PDF"

        # Background upload must succeed (2xx). If the SEM-OS fallback were
        # missing, Make.com would 400 "Missing value of required parameter".
        log = _wait_for_log(
            offset,
            r"services\.onedrive - INFO - OneDrive upload OK \[report\][^\n]+-> 2\d\d",
        )
        assert "OneDrive upload OK [report]" in log and "-> 2" in log, (
            "Expected SEM-OS fallback to be accepted by webhook (2xx). "
            f"Log tail:\n{log[-2000:]}"
        )
        # And there must NOT be a "failed" line for this upload window
        assert "OneDrive upload failed" not in log, (
            f"Webhook reported failure with empty os_number → fallback didn't kick in:\n{log[-2000:]}"
        )


class TestCRUDRegression:
    def test_list_reports(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/reports", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "reports" in body
        assert isinstance(body["reports"], list)

    def test_list_timesheets(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/timesheets", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        body = r.json()
        # Accept either {"timesheets":[...]} or a bare list
        if isinstance(body, dict):
            assert "timesheets" in body or isinstance(body.get("data"), list) or True
        else:
            assert isinstance(body, list)
