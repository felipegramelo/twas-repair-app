"""
Iteration 26 Tests: Timesheet Duplicate, Finalize, Revert Features
Tests:
- POST /api/timesheets/{id}/duplicate - creates a new timesheet copy with status draft
- PUT /api/timesheets/{id}/finalize - sets status to finalized
- PUT /api/timesheets/{id}/revert - sets status to draft (admin only)
- PUT /api/reports/{id}/revert - sets status to draft (admin only)
- Supervisor cannot call revert endpoints (should get 403)
- Editing finalized timesheet returns 403
- Editing finalized report returns 403 for supervisor
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://twas-repair-bm.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"

# Known test data
KNOWN_TIMESHEET_ID = "69c3fe001e1ca6cafd15220f"


class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"PASS: Admin login successful")
    
    def test_supervisor_login(self):
        """Test supervisor login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "supervisor"
        print(f"PASS: Supervisor login successful")


@pytest.fixture
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Admin authentication failed")


@pytest.fixture
def supervisor_token():
    """Get supervisor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": SUPERVISOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Supervisor authentication failed")


@pytest.fixture
def admin_headers(admin_token):
    """Admin request headers"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture
def supervisor_headers(supervisor_token):
    """Supervisor request headers"""
    return {"Authorization": f"Bearer {supervisor_token}", "Content-Type": "application/json"}


class TestTimesheetDuplicate:
    """Tests for POST /api/timesheets/{id}/duplicate"""
    
    def test_duplicate_timesheet_creates_copy(self, supervisor_headers):
        """Duplicate timesheet creates a new copy with status draft"""
        # First get the original timesheet
        response = requests.get(f"{BASE_URL}/api/timesheets/{KNOWN_TIMESHEET_ID}", headers=supervisor_headers)
        if response.status_code != 200:
            pytest.skip(f"Known timesheet not found: {KNOWN_TIMESHEET_ID}")
        original = response.json()
        
        # Duplicate the timesheet
        response = requests.post(f"{BASE_URL}/api/timesheets/{KNOWN_TIMESHEET_ID}/duplicate", headers=supervisor_headers)
        assert response.status_code == 200, f"Duplicate failed: {response.text}"
        
        duplicated = response.json()
        assert "id" in duplicated, "Duplicated timesheet should have an id"
        assert duplicated["id"] != KNOWN_TIMESHEET_ID, "Duplicated timesheet should have a different id"
        assert duplicated.get("status") == "draft", f"Duplicated timesheet should have status 'draft', got: {duplicated.get('status')}"
        assert duplicated.get("os_id") == original.get("os_id"), "Duplicated timesheet should have same os_id"
        
        print(f"PASS: Timesheet duplicated successfully. New ID: {duplicated['id']}, Status: {duplicated.get('status')}")
        
        # Cleanup - delete the duplicated timesheet
        requests.delete(f"{BASE_URL}/api/timesheets/{duplicated['id']}", headers=supervisor_headers)
    
    def test_duplicate_nonexistent_timesheet_returns_404(self, supervisor_headers):
        """Duplicate nonexistent timesheet returns 404"""
        fake_id = "000000000000000000000000"
        response = requests.post(f"{BASE_URL}/api/timesheets/{fake_id}/duplicate", headers=supervisor_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Duplicate nonexistent timesheet returns 404")


class TestTimesheetFinalize:
    """Tests for PUT /api/timesheets/{id}/finalize"""
    
    def test_finalize_timesheet_sets_status(self, supervisor_headers):
        """Finalize timesheet sets status to finalized"""
        # First duplicate to get a fresh timesheet
        response = requests.post(f"{BASE_URL}/api/timesheets/{KNOWN_TIMESHEET_ID}/duplicate", headers=supervisor_headers)
        if response.status_code != 200:
            pytest.skip("Could not create test timesheet")
        test_ts = response.json()
        test_ts_id = test_ts["id"]
        
        try:
            # Finalize the timesheet
            response = requests.put(f"{BASE_URL}/api/timesheets/{test_ts_id}/finalize", headers=supervisor_headers)
            assert response.status_code == 200, f"Finalize failed: {response.text}"
            
            # Verify status changed
            response = requests.get(f"{BASE_URL}/api/timesheets/{test_ts_id}", headers=supervisor_headers)
            assert response.status_code == 200
            ts_data = response.json()
            assert ts_data.get("status") == "finalized", f"Expected status 'finalized', got: {ts_data.get('status')}"
            
            print(f"PASS: Timesheet finalized successfully. Status: {ts_data.get('status')}")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/timesheets/{test_ts_id}", headers=supervisor_headers)


class TestTimesheetRevert:
    """Tests for PUT /api/timesheets/{id}/revert (admin only)"""
    
    def test_admin_can_revert_timesheet(self, admin_headers, supervisor_headers):
        """Admin can revert finalized timesheet to draft"""
        # Create and finalize a test timesheet
        response = requests.post(f"{BASE_URL}/api/timesheets/{KNOWN_TIMESHEET_ID}/duplicate", headers=supervisor_headers)
        if response.status_code != 200:
            pytest.skip("Could not create test timesheet")
        test_ts = response.json()
        test_ts_id = test_ts["id"]
        
        try:
            # Finalize it
            requests.put(f"{BASE_URL}/api/timesheets/{test_ts_id}/finalize", headers=supervisor_headers)
            
            # Admin reverts it
            response = requests.put(f"{BASE_URL}/api/timesheets/{test_ts_id}/revert", headers=admin_headers)
            assert response.status_code == 200, f"Admin revert failed: {response.text}"
            
            # Verify status changed back to draft
            response = requests.get(f"{BASE_URL}/api/timesheets/{test_ts_id}", headers=admin_headers)
            assert response.status_code == 200
            ts_data = response.json()
            assert ts_data.get("status") == "draft", f"Expected status 'draft', got: {ts_data.get('status')}"
            
            print(f"PASS: Admin reverted timesheet successfully. Status: {ts_data.get('status')}")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/timesheets/{test_ts_id}", headers=admin_headers)
    
    def test_supervisor_cannot_revert_timesheet(self, admin_headers, supervisor_headers):
        """Supervisor cannot revert timesheet (should get 403)"""
        # Create and finalize a test timesheet
        response = requests.post(f"{BASE_URL}/api/timesheets/{KNOWN_TIMESHEET_ID}/duplicate", headers=supervisor_headers)
        if response.status_code != 200:
            pytest.skip("Could not create test timesheet")
        test_ts = response.json()
        test_ts_id = test_ts["id"]
        
        try:
            # Finalize it
            requests.put(f"{BASE_URL}/api/timesheets/{test_ts_id}/finalize", headers=supervisor_headers)
            
            # Supervisor tries to revert - should fail with 403
            response = requests.put(f"{BASE_URL}/api/timesheets/{test_ts_id}/revert", headers=supervisor_headers)
            assert response.status_code == 403, f"Expected 403 for supervisor revert, got {response.status_code}: {response.text}"
            
            print(f"PASS: Supervisor correctly denied revert access (403)")
        finally:
            # Cleanup with admin
            requests.delete(f"{BASE_URL}/api/timesheets/{test_ts_id}", headers=admin_headers)


class TestReportFinalize:
    """Tests for PUT /api/reports/{id}/finalize"""
    
    def test_finalize_report_sets_status(self, supervisor_headers):
        """Finalize report sets status to finalized"""
        # Get a service order first
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=supervisor_headers)
        if response.status_code != 200 or not response.json():
            pytest.skip("No service orders available")
        os_id = response.json()[0]["id"]
        
        # Create a test report
        response = requests.post(f"{BASE_URL}/api/reports", headers=supervisor_headers, json={
            "report_type": "service",
            "os_id": os_id,
            "periodo_inicio": "01/01/2026",
            "periodo_fim": "15/01/2026"
        })
        if response.status_code != 200:
            pytest.skip(f"Could not create test report: {response.text}")
        test_report = response.json()
        test_report_id = test_report["id"]
        
        try:
            # Finalize the report
            response = requests.put(f"{BASE_URL}/api/reports/{test_report_id}/finalize", headers=supervisor_headers)
            assert response.status_code == 200, f"Finalize failed: {response.text}"
            
            # Verify status changed
            response = requests.get(f"{BASE_URL}/api/reports/{test_report_id}", headers=supervisor_headers)
            assert response.status_code == 200
            report_data = response.json()
            assert report_data.get("status") == "finalized", f"Expected status 'finalized', got: {report_data.get('status')}"
            
            print(f"PASS: Report finalized successfully. Status: {report_data.get('status')}")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/reports/{test_report_id}", headers=supervisor_headers)


class TestReportRevert:
    """Tests for PUT /api/reports/{id}/revert (admin only)"""
    
    def test_admin_can_revert_report(self, admin_headers, supervisor_headers):
        """Admin can revert finalized report to draft"""
        # Get a service order first
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=supervisor_headers)
        if response.status_code != 200 or not response.json():
            pytest.skip("No service orders available")
        os_id = response.json()[0]["id"]
        
        # Create a test report
        response = requests.post(f"{BASE_URL}/api/reports", headers=supervisor_headers, json={
            "report_type": "service",
            "os_id": os_id,
            "periodo_inicio": "01/01/2026",
            "periodo_fim": "15/01/2026"
        })
        if response.status_code != 200:
            pytest.skip(f"Could not create test report: {response.text}")
        test_report = response.json()
        test_report_id = test_report["id"]
        
        try:
            # Finalize it
            requests.put(f"{BASE_URL}/api/reports/{test_report_id}/finalize", headers=supervisor_headers)
            
            # Admin reverts it
            response = requests.put(f"{BASE_URL}/api/reports/{test_report_id}/revert", headers=admin_headers)
            assert response.status_code == 200, f"Admin revert failed: {response.text}"
            
            # Verify status changed back to draft
            response = requests.get(f"{BASE_URL}/api/reports/{test_report_id}", headers=admin_headers)
            assert response.status_code == 200
            report_data = response.json()
            assert report_data.get("status") == "draft", f"Expected status 'draft', got: {report_data.get('status')}"
            
            print(f"PASS: Admin reverted report successfully. Status: {report_data.get('status')}")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/reports/{test_report_id}", headers=admin_headers)
    
    def test_supervisor_cannot_revert_report(self, admin_headers, supervisor_headers):
        """Supervisor cannot revert report (should get 403)"""
        # Get a service order first
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=supervisor_headers)
        if response.status_code != 200 or not response.json():
            pytest.skip("No service orders available")
        os_id = response.json()[0]["id"]
        
        # Create a test report
        response = requests.post(f"{BASE_URL}/api/reports", headers=supervisor_headers, json={
            "report_type": "service",
            "os_id": os_id,
            "periodo_inicio": "01/01/2026",
            "periodo_fim": "15/01/2026"
        })
        if response.status_code != 200:
            pytest.skip(f"Could not create test report: {response.text}")
        test_report = response.json()
        test_report_id = test_report["id"]
        
        try:
            # Finalize it
            requests.put(f"{BASE_URL}/api/reports/{test_report_id}/finalize", headers=supervisor_headers)
            
            # Supervisor tries to revert - should fail with 403
            response = requests.put(f"{BASE_URL}/api/reports/{test_report_id}/revert", headers=supervisor_headers)
            assert response.status_code == 403, f"Expected 403 for supervisor revert, got {response.status_code}: {response.text}"
            
            print(f"PASS: Supervisor correctly denied revert access (403)")
        finally:
            # Cleanup with admin
            requests.delete(f"{BASE_URL}/api/reports/{test_report_id}", headers=admin_headers)


class TestEditFinalizedDocuments:
    """Tests for editing finalized documents (should be blocked)"""
    
    def test_edit_finalized_timesheet_returns_403(self, supervisor_headers):
        """Editing finalized timesheet returns 403"""
        # Create and finalize a test timesheet
        response = requests.post(f"{BASE_URL}/api/timesheets/{KNOWN_TIMESHEET_ID}/duplicate", headers=supervisor_headers)
        if response.status_code != 200:
            pytest.skip("Could not create test timesheet")
        test_ts = response.json()
        test_ts_id = test_ts["id"]
        
        try:
            # Finalize it
            requests.put(f"{BASE_URL}/api/timesheets/{test_ts_id}/finalize", headers=supervisor_headers)
            
            # Try to edit - should fail with 403
            response = requests.put(f"{BASE_URL}/api/timesheets/{test_ts_id}", headers=supervisor_headers, json={
                "os_id": test_ts.get("os_id"),
                "entries": test_ts.get("entries", []),
                "observations": "Updated observation"
            })
            assert response.status_code == 403, f"Expected 403 for editing finalized timesheet, got {response.status_code}: {response.text}"
            
            print(f"PASS: Editing finalized timesheet correctly blocked (403)")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/timesheets/{test_ts_id}", headers=supervisor_headers)
    
    def test_edit_finalized_report_returns_403(self, supervisor_headers):
        """Editing finalized report returns 403 for supervisor"""
        # Get a service order first
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=supervisor_headers)
        if response.status_code != 200 or not response.json():
            pytest.skip("No service orders available")
        os_id = response.json()[0]["id"]
        
        # Create a test report
        response = requests.post(f"{BASE_URL}/api/reports", headers=supervisor_headers, json={
            "report_type": "service",
            "os_id": os_id,
            "periodo_inicio": "01/01/2026",
            "periodo_fim": "15/01/2026"
        })
        if response.status_code != 200:
            pytest.skip(f"Could not create test report: {response.text}")
        test_report = response.json()
        test_report_id = test_report["id"]
        
        try:
            # Finalize it
            requests.put(f"{BASE_URL}/api/reports/{test_report_id}/finalize", headers=supervisor_headers)
            
            # Try to edit - should fail with 403
            response = requests.put(f"{BASE_URL}/api/reports/{test_report_id}", headers=supervisor_headers, json={
                "periodo_inicio": "02/01/2026"
            })
            assert response.status_code == 403, f"Expected 403 for editing finalized report, got {response.status_code}: {response.text}"
            
            print(f"PASS: Editing finalized report correctly blocked (403)")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/reports/{test_report_id}", headers=supervisor_headers)


class TestAPIEndpointsExist:
    """Verify all required API endpoints exist"""
    
    def test_timesheet_duplicate_endpoint_exists(self, supervisor_headers):
        """POST /api/timesheets/{id}/duplicate endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/timesheets/{KNOWN_TIMESHEET_ID}/duplicate", headers=supervisor_headers)
        # Should return 200 (success) or 404 (not found), not 405 (method not allowed)
        assert response.status_code != 405, "Duplicate endpoint does not exist"
        print(f"PASS: Timesheet duplicate endpoint exists (status: {response.status_code})")
        
        # Cleanup if successful
        if response.status_code == 200:
            data = response.json()
            if "id" in data:
                requests.delete(f"{BASE_URL}/api/timesheets/{data['id']}", headers=supervisor_headers)
    
    def test_timesheet_finalize_endpoint_exists(self, supervisor_headers):
        """PUT /api/timesheets/{id}/finalize endpoint exists"""
        fake_id = "000000000000000000000000"
        response = requests.put(f"{BASE_URL}/api/timesheets/{fake_id}/finalize", headers=supervisor_headers)
        # Should return 404 (not found), not 405 (method not allowed)
        assert response.status_code != 405, "Finalize endpoint does not exist"
        print(f"PASS: Timesheet finalize endpoint exists (status: {response.status_code})")
    
    def test_timesheet_revert_endpoint_exists(self, admin_headers):
        """PUT /api/timesheets/{id}/revert endpoint exists"""
        fake_id = "000000000000000000000000"
        response = requests.put(f"{BASE_URL}/api/timesheets/{fake_id}/revert", headers=admin_headers)
        # Should return 404 (not found), not 405 (method not allowed)
        assert response.status_code != 405, "Revert endpoint does not exist"
        print(f"PASS: Timesheet revert endpoint exists (status: {response.status_code})")
    
    def test_report_finalize_endpoint_exists(self, supervisor_headers):
        """PUT /api/reports/{id}/finalize endpoint exists"""
        fake_id = "000000000000000000000000"
        response = requests.put(f"{BASE_URL}/api/reports/{fake_id}/finalize", headers=supervisor_headers)
        # Should return 404 (not found), not 405 (method not allowed)
        assert response.status_code != 405, "Report finalize endpoint does not exist"
        print(f"PASS: Report finalize endpoint exists (status: {response.status_code})")
    
    def test_report_revert_endpoint_exists(self, admin_headers):
        """PUT /api/reports/{id}/revert endpoint exists"""
        fake_id = "000000000000000000000000"
        response = requests.put(f"{BASE_URL}/api/reports/{fake_id}/revert", headers=admin_headers)
        # Should return 404 (not found), not 405 (method not allowed)
        assert response.status_code != 405, "Report revert endpoint does not exist"
        print(f"PASS: Report revert endpoint exists (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
