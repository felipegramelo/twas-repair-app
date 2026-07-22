"""
Iteration 53: Test that ?download=1 triggers OneDrive webhook upload for
timesheets and reports PDF endpoints, and that omitting it does NOT trigger it.

Also validates:
- Reports PDF accepts token via query param (used by native supervisor screens).
- Timesheets PDF accepts token via Authorization header OR query param.
"""
import os
import time
import subprocess
import pytest
import requests

BASE_URL = "http://localhost:8001"  # backend logs live locally; use local for speed
BACKEND_LOG = "/var/log/supervisor/backend.err.log"


def _tail_lines(n=200):
    try:
        out = subprocess.check_output(["tail", "-n", str(n), BACKEND_LOG], text=True)
        return out
    except Exception:
        return ""


def _log_size():
    try:
        return os.path.getsize(BACKEND_LOG)
    except Exception:
        return 0


def _wait_for_log(marker, since_offset, timeout=15):
    """Poll the backend log for the marker starting after byte offset since_offset."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            with open(BACKEND_LOG, "r", errors="ignore") as f:
                f.seek(since_offset)
                new_data = f.read()
            if marker in new_data:
                return True, new_data
        except Exception:
            pass
        time.sleep(0.5)
    try:
        with open(BACKEND_LOG, "r", errors="ignore") as f:
            f.seek(since_offset)
            return False, f.read()
    except Exception:
        return False, ""


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "admin@twasrepair.com", "password": "admin123"},
                      timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    body = r.json()
    return body.get("access_token") or body.get("token")


@pytest.fixture(scope="module")
def supervisor_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "supervisor@twasrepair.com", "password": "super123"},
                      timeout=15)
    assert r.status_code == 200, f"Supervisor login failed: {r.status_code} {r.text}"
    body = r.json()
    return body.get("access_token") or body.get("token")


@pytest.fixture(scope="module")
def timesheet_id(admin_token):
    r = requests.get(f"{BASE_URL}/api/timesheets",
                     headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    # /api/timesheets returns a plain list per code (List[dict])
    assert isinstance(data, list) and len(data) > 0, "No timesheets in DB to test with"
    return data[0]["id"]


@pytest.fixture(scope="module")
def report_id(admin_token):
    r = requests.get(f"{BASE_URL}/api/reports",
                     headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "reports" in data and len(data["reports"]) > 0, "No reports in DB to test with"
    return data["reports"][0]["id"]


class TestTimesheetPDFDownload:
    """Timesheet PDF endpoint: verify OneDrive webhook fires only when download=1."""

    def test_timesheet_pdf_no_download_no_webhook(self, admin_token, timesheet_id):
        offset = _log_size()
        r = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=60,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF", "Response is not a PDF"
        # Give webhook loop a moment then verify absence
        time.sleep(2)
        with open(BACKEND_LOG, "r", errors="ignore") as f:
            f.seek(offset)
            new_log = f.read()
        assert "OneDrive upload OK [timesheet]" not in new_log, (
            "Webhook fired without download=1! New log:\n" + new_log[-1000:]
        )

    def test_timesheet_pdf_with_download_triggers_webhook(self, admin_token, timesheet_id):
        offset = _log_size()
        r = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf?download=1",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=60,
        )
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        found, log_slice = _wait_for_log("OneDrive upload OK [timesheet]", offset, timeout=20)
        assert found, (
            "Expected 'OneDrive upload OK [timesheet]' in backend log after download=1. "
            f"Tail:\n{log_slice[-2000:]}"
        )


class TestReportPDFDownload:
    """Report PDF endpoint: verify OneDrive webhook fires only when download=1."""

    def test_report_pdf_with_download_via_header_triggers_webhook(self, admin_token, report_id):
        offset = _log_size()
        r = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/pdf?download=1",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=90,
        )
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
        assert r.content[:4] == b"%PDF"
        found, log_slice = _wait_for_log("OneDrive upload OK [report]", offset, timeout=25)
        assert found, (
            "Expected 'OneDrive upload OK [report]' in backend log after download=1. "
            f"Tail:\n{log_slice[-2000:]}"
        )

    def test_report_pdf_token_query_param_works(self, admin_token, report_id):
        # Native supervisor screens use token as query param (no Authorization header)
        r = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/pdf?token={admin_token}&download=0",
            timeout=90,
        )
        assert r.status_code == 200, f"Token as query param must work: {r.status_code} {r.text[:200]}"
        assert r.content[:4] == b"%PDF"

    def test_timesheet_pdf_token_query_param_works(self, admin_token, timesheet_id):
        # Verify timesheet endpoint also accepts token= query (per code review of route)
        r = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf?token={admin_token}",
            timeout=60,
        )
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"


class TestFrontendStaticVerification:
    """Static grep-based verification that native download URLs include download=1."""

    def _read(self, path):
        with open(path, "r") as f:
            return f.read()

    def test_admin_timesheets_download_has_download_param(self):
        content = self._read("/app/frontend/app/admin/timesheets.tsx")
        # handleDownloadPDF native URL must include download=1
        assert "/pdf?t=${Date.now()}&download=1" in content, \
            "admin/timesheets.tsx native download URL missing &download=1"

    def test_supervisor_index_download_has_download_param(self):
        content = self._read("/app/frontend/app/supervisor/index.tsx")
        # Timesheet download URL (native)
        assert "/timesheets/${timesheet.id}/pdf?t=${Date.now()}&download=1" in content, \
            "supervisor/index.tsx timesheet download URL missing &download=1"
        # Report download URL (native, uses token= query param)
        assert "&download=1" in content and "reports/${report.id}/pdf?token=" in content, \
            "supervisor/index.tsx report download URL missing token+download=1"

    def test_supervisor_edit_report_share_has_download_param(self):
        content = self._read("/app/frontend/app/supervisor/edit-report.tsx")
        assert "getPdfUrl() + '&download=1'" in content, \
            "edit-report.tsx handleSharePDF URL missing &download=1"
        assert "reportAPI.downloadPDF(id!, true)" in content, \
            "edit-report.tsx handleSharePDF must call downloadPDF with forceDownload=true"

    def test_open_pdf_handlers_do_not_use_download(self):
        # handleOpenPDF must NOT contain download=1 (preview should not upload)
        import re
        for path in [
            "/app/frontend/app/admin/timesheets.tsx",
            "/app/frontend/app/supervisor/index.tsx",
            "/app/frontend/app/supervisor/edit-report.tsx",
        ]:
            content = self._read(path)
            # Find handleOpenPDF fn body up to the next `const handle` declaration
            m = re.search(r"handleOpenPDF\s*=\s*async[^{]*\{", content)
            assert m, f"handleOpenPDF not found in {path}"
            start = m.end()
            # End = start of next `const handle...` (e.g. handleSharePDF / handleDownloadPDF)
            m2 = re.search(r"\n\s*const\s+handle\w+\s*=", content[start:])
            end = start + (m2.start() if m2 else 1500)
            body = content[start:end]
            assert "download=1" not in body, \
                f"handleOpenPDF in {path} contains download=1 (would upload on preview)"
            # And it must not call downloadPDF(id, true)
            assert not re.search(r"downloadPDF\([^)]*,\s*true\s*\)", body), \
                f"handleOpenPDF in {path} calls downloadPDF(..., true) which forces download"

    def test_services_api_download_flag(self):
        content = self._read("/app/frontend/services/api.ts")
        # timesheetAPI/reportAPI downloadPDF: forceDownload -> ?download=1
        assert 'forceDownload ? \'&download=1\' : \'\'' in content, \
            "services/api.ts must gate &download=1 on forceDownload"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
