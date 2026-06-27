"""
Test file for OneDrive (Make.com webhook) integration on PDF reports.

Validates:
- GET /api/reports/{id}/pdf?download=1 returns PDF with attachment disposition
  AND triggers asyncio background upload to Make.com (log: 'OneDrive upload OK [report]')
- GET /api/reports/{id}/pdf (no download) returns PDF inline and does NOT trigger upload
- Token works both via ?token= query param AND Authorization Bearer header
- GET /api/timesheets/{id}/pdf?download=1 does NOT trigger webhook (env empty)
- Basic CRUD endpoints (GET /api/reports, GET /api/reports/{id}) still work
- Webhook failures cannot break PDF response (validated via code: fire-and-forget + try/except)
"""

import os
import re
import time
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://twas-repair-app-1.preview.emergentagent.com",
).rstrip("/")

ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"

BACKEND_LOG = "/var/log/supervisor/backend.err.log"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


def _wait_for_log(offset: int, pattern: str, timeout: float = 15.0) -> str:
    """Poll the log for `pattern` (regex). Return matched line or ''. """
    deadline = time.time() + timeout
    rx = re.compile(pattern)
    last = ""
    while time.time() < deadline:
        last = _read_log_since(offset)
        if rx.search(last):
            return last
        time.sleep(0.5)
    return last  # for diagnostics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
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
def report_id(admin_token: str) -> str:
    resp = requests.get(
        f"{BASE_URL}/api/reports?limit=5",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert resp.status_code == 200, f"List reports failed: {resp.status_code}"
    payload = resp.json()
    items = payload if isinstance(payload, list) else payload.get("items") or payload.get("reports") or []
    assert items, "No reports available to test PDF generation"
    rid = items[0].get("id") or items[0].get("_id")
    assert rid, "Report has no id"
    return rid


@pytest.fixture(scope="module")
def timesheet_id(admin_token: str) -> str:
    resp = requests.get(
        f"{BASE_URL}/api/timesheets?limit=5",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert resp.status_code == 200, f"List timesheets failed: {resp.status_code}"
    payload = resp.json()
    items = payload if isinstance(payload, list) else payload.get("items") or payload.get("timesheets") or []
    assert items, "No timesheets available"
    tid = items[0].get("id") or items[0].get("_id")
    assert tid, "Timesheet has no id"
    return tid


# ---------------------------------------------------------------------------
# Reports - basic CRUD smoke
# ---------------------------------------------------------------------------
class TestReportsBasicEndpoints:
    def test_list_reports_works(self, admin_token):
        resp = requests.get(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert resp.status_code == 200
        body = resp.json()
        items = body if isinstance(body, list) else body.get("items") or body.get("reports") or []
        assert isinstance(items, list)

    def test_get_report_detail_works(self, admin_token, report_id):
        resp = requests.get(
            f"{BASE_URL}/api/reports/{report_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert (body.get("id") or body.get("_id")) == report_id


# ---------------------------------------------------------------------------
# PDF + OneDrive webhook integration
# ---------------------------------------------------------------------------
class TestPdfOneDriveIntegration:
    # ---- Auth via Bearer header + download=1 should trigger webhook -------
    def test_pdf_download_triggers_onedrive_upload_via_header(self, admin_token, report_id):
        offset = _log_size()
        resp = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/pdf?download=1",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=120,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert resp.headers.get("content-type", "").startswith("application/pdf"), \
            f"Unexpected content-type: {resp.headers.get('content-type')}"
        # Content-Disposition must be attachment when download=1
        cd = resp.headers.get("content-disposition", "")
        assert cd.lower().startswith("attachment"), f"Expected attachment disposition, got: {cd}"
        # PDF magic bytes
        assert resp.content[:4] == b"%PDF", "Response body is not a valid PDF"
        assert len(resp.content) > 1000, "PDF body suspiciously small"

        # Wait for background asyncio task to complete and log the upload
        log_chunk = _wait_for_log(offset, r"OneDrive upload OK \[report\]", timeout=30.0)
        assert "OneDrive upload OK [report]" in log_chunk, (
            "Expected 'OneDrive upload OK [report]' in backend.err.log within 30s after download=1 request. "
            f"Log tail captured (last 1500 chars): {log_chunk[-1500:]}"
        )

    # ---- Auth via ?token= query param + download=1 should trigger webhook --
    def test_pdf_download_via_token_query_param_triggers_upload(self, admin_token, report_id):
        offset = _log_size()
        resp = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/pdf?download=1&token={admin_token}",
            timeout=120,
        )
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"
        cd = resp.headers.get("content-disposition", "")
        assert cd.lower().startswith("attachment"), f"Expected attachment disposition, got: {cd}"

        log_chunk = _wait_for_log(offset, r"OneDrive upload OK \[report\]", timeout=30.0)
        assert "OneDrive upload OK [report]" in log_chunk, (
            "Expected webhook upload log entry after token-query-param download. "
            f"Log tail: {log_chunk[-1500:]}"
        )

    # ---- Preview (no download) MUST NOT trigger webhook -------------------
    def test_pdf_preview_does_not_trigger_onedrive_upload(self, admin_token, report_id):
        offset = _log_size()
        resp = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=120,
        )
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"
        cd = resp.headers.get("content-disposition", "")
        assert cd.lower().startswith("inline"), f"Expected inline disposition, got: {cd}"

        # Give asyncio scheduler a few seconds; ensure NO upload log appears
        time.sleep(8.0)
        log_chunk = _read_log_since(offset)
        assert "OneDrive upload OK [report]" not in log_chunk, (
            "Unexpected OneDrive upload log on preview (no download=1). "
            f"Log tail: {log_chunk[-1500:]}"
        )
        # Also no failure log referencing this kind should appear
        assert "OneDrive upload failed [report]" not in log_chunk
        assert "OneDrive upload exception [report]" not in log_chunk

    # ---- Timesheet endpoint must NOT trigger webhook (env empty) ----------
    def test_timesheet_download_does_not_trigger_webhook(self, admin_token, timesheet_id):
        offset = _log_size()
        resp = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf?download=1",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=120,
        )
        # Endpoint must still serve the PDF
        assert resp.status_code == 200, f"Timesheet PDF failed: {resp.status_code} {resp.text[:200]}"
        assert resp.content[:4] == b"%PDF"
        cd = resp.headers.get("content-disposition", "")
        assert cd.lower().startswith("attachment"), f"Expected attachment, got: {cd}"

        time.sleep(6.0)
        log_chunk = _read_log_since(offset)
        # Timesheet kind must never log an OK upload because MAKE_WEBHOOK_TIMESHEETS_URL is empty
        assert "OneDrive upload OK [timesheet]" not in log_chunk, (
            "Webhook fired for timesheet despite empty env. " f"Log tail: {log_chunk[-1500:]}"
        )

    # ---- Auth failures -----------------------------------------------------
    def test_pdf_without_token_returns_401(self, report_id):
        resp = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/pdf?download=1",
            timeout=20,
        )
        assert resp.status_code == 401

    def test_pdf_invalid_token_returns_401(self, report_id):
        resp = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/pdf?download=1&token=not-a-valid-jwt",
            timeout=20,
        )
        assert resp.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
