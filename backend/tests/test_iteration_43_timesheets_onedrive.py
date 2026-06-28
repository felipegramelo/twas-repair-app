"""
Iteration 43 - OneDrive (Make.com webhook) integration for TIMESHEETS PDF.

Validates:
- GET /api/timesheets/{id}/pdf?download=1 returns valid PDF with attachment disposition
  AND triggers asyncio background upload to Make.com webhook
  (log: 'services.onedrive - INFO - OneDrive upload OK [timesheet] ...')
- GET /api/timesheets/{id}/pdf (no download) returns PDF inline and does NOT trigger upload
- Token works both via ?token= query param AND Authorization Bearer header
- Auth failures return 401
- Basic CRUD: GET /api/timesheets, GET /api/timesheets/{id} still work
- Reports smoke test: GET /api/reports/{id}/pdf?download=1 still triggers
  'OneDrive upload OK [report]' (regression guard)
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


# -- helpers ---------------------------------------------------------------
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


def _wait_for_log(offset: int, pattern: str, timeout: float = 30.0) -> str:
    deadline = time.time() + timeout
    rx = re.compile(pattern)
    last = ""
    while time.time() < deadline:
        last = _read_log_since(offset)
        if rx.search(last):
            return last
        time.sleep(0.5)
    return last


# -- fixtures --------------------------------------------------------------
@pytest.fixture(scope="module")
def admin_token() -> str:
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="module")
def timesheet_id(admin_token: str) -> str:
    resp = requests.get(
        f"{BASE_URL}/api/timesheets?limit=5",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert resp.status_code == 200, f"List timesheets failed: {resp.status_code} {resp.text[:200]}"
    payload = resp.json()
    items = payload if isinstance(payload, list) else (
        payload.get("items") or payload.get("timesheets") or []
    )
    assert items, "No timesheets available to test PDF generation"
    tid = items[0].get("id") or items[0].get("_id")
    assert tid, "Timesheet has no id"
    return tid


@pytest.fixture(scope="module")
def report_id(admin_token: str) -> str:
    resp = requests.get(
        f"{BASE_URL}/api/reports?limit=5",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert resp.status_code == 200
    payload = resp.json()
    items = payload if isinstance(payload, list) else (
        payload.get("items") or payload.get("reports") or []
    )
    assert items, "No reports available"
    return items[0].get("id") or items[0].get("_id")


# -- Timesheets CRUD smoke -------------------------------------------------
class TestTimesheetsBasicEndpoints:
    def test_list_timesheets(self, admin_token):
        resp = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert resp.status_code == 200
        body = resp.json()
        items = body if isinstance(body, list) else (
            body.get("items") or body.get("timesheets") or []
        )
        assert isinstance(items, list)

    def test_get_timesheet_detail(self, admin_token, timesheet_id):
        resp = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert (body.get("id") or body.get("_id")) == timesheet_id


# -- Timesheet PDF + OneDrive webhook --------------------------------------
class TestTimesheetPdfOneDriveIntegration:
    def test_pdf_download_via_bearer_header_triggers_upload(self, admin_token, timesheet_id):
        offset = _log_size()
        resp = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf?download=1",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=120,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert resp.headers.get("content-type", "").startswith("application/pdf"), \
            f"Unexpected content-type: {resp.headers.get('content-type')}"
        cd = resp.headers.get("content-disposition", "")
        assert cd.lower().startswith("attachment"), f"Expected attachment, got: {cd}"
        assert resp.content[:4] == b"%PDF", "Response body is not a valid PDF"
        assert len(resp.content) > 500, "PDF body suspiciously small"

        log_chunk = _wait_for_log(offset, r"OneDrive upload OK \[timesheet\]", timeout=30.0)
        assert "OneDrive upload OK [timesheet]" in log_chunk, (
            "Expected 'OneDrive upload OK [timesheet]' in backend.err.log within 30s. "
            f"Log tail (last 1500 chars): {log_chunk[-1500:]}"
        )

    def test_pdf_download_via_token_query_param_triggers_upload(self, admin_token, timesheet_id):
        offset = _log_size()
        resp = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf?download=1&token={admin_token}",
            timeout=120,
        )
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"
        cd = resp.headers.get("content-disposition", "")
        assert cd.lower().startswith("attachment"), f"Expected attachment, got: {cd}"

        log_chunk = _wait_for_log(offset, r"OneDrive upload OK \[timesheet\]", timeout=30.0)
        assert "OneDrive upload OK [timesheet]" in log_chunk, (
            "Expected webhook upload log after token-query-param download. "
            f"Log tail: {log_chunk[-1500:]}"
        )

    def test_pdf_preview_does_not_trigger_upload(self, admin_token, timesheet_id):
        offset = _log_size()
        resp = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=120,
        )
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"
        cd = resp.headers.get("content-disposition", "")
        assert cd.lower().startswith("inline"), f"Expected inline, got: {cd}"

        # Wait long enough for any background task to have logged something
        time.sleep(8.0)
        log_chunk = _read_log_since(offset)
        assert "OneDrive upload OK [timesheet]" not in log_chunk, (
            "Unexpected OneDrive upload log on preview (no download=1). "
            f"Log tail: {log_chunk[-1500:]}"
        )
        assert "OneDrive upload failed [timesheet]" not in log_chunk
        assert "OneDrive upload exception [timesheet]" not in log_chunk

    def test_pdf_without_token_returns_401(self, timesheet_id):
        resp = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf?download=1",
            timeout=20,
        )
        assert resp.status_code == 401

    def test_pdf_invalid_token_returns_401(self, timesheet_id):
        resp = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf?download=1&token=not-a-valid-jwt",
            timeout=20,
        )
        assert resp.status_code == 401


# -- Reports regression guard ----------------------------------------------
class TestReportsRegressionSmoke:
    def test_report_pdf_download_still_triggers_webhook(self, admin_token, report_id):
        offset = _log_size()
        resp = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/pdf?download=1",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=120,
        )
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"
        cd = resp.headers.get("content-disposition", "")
        assert cd.lower().startswith("attachment"), f"Expected attachment, got: {cd}"

        log_chunk = _wait_for_log(offset, r"OneDrive upload OK \[report\]", timeout=30.0)
        assert "OneDrive upload OK [report]" in log_chunk, (
            "Reports webhook regression: expected 'OneDrive upload OK [report]' log entry. "
            f"Log tail: {log_chunk[-1500:]}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
