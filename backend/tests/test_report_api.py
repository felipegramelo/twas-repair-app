"""
Test file for Report API endpoints in TWAS REPAIR unified app.
Tests CRUD operations for reports with local MongoDB backend.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://report-pdf-engine.preview.emergentagent.com')

# Test credentials
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"

class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_supervisor_login_success(self):
        """Test supervisor login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == SUPERVISOR_EMAIL
        assert data["user"]["role"] == "supervisor"
        
    def test_admin_login_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401


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
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Admin authentication failed")


class TestServiceOrderEndpoints:
    """Service order endpoint tests"""
    
    def test_get_service_orders(self, supervisor_token):
        """Test getting all service orders"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Verify service order structure
        if len(data) > 0:
            so = data[0]
            assert "id" in so
            assert "os_number" in so
            assert "client" in so
            assert "location" in so
            assert "service" in so


class TestReportCRUD:
    """Report CRUD operations tests"""
    
    def test_get_reports(self, supervisor_token):
        """Test getting all reports"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/reports", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        assert isinstance(data["reports"], list)
        
    def test_get_report_by_id(self, supervisor_token):
        """Test getting a specific report by ID"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        # First get all reports
        list_response = requests.get(f"{BASE_URL}/api/reports", headers=headers)
        reports = list_response.json()["reports"]
        
        if len(reports) > 0:
            report_id = reports[0]["id"]
            response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == report_id
            assert "report_type" in data
            assert "os_number" in data
            assert "client" in data
        else:
            pytest.skip("No reports available to test")
            
    def test_create_report_and_verify(self, supervisor_token):
        """Test creating a new report and verify it persists"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        
        # First get a service order ID
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        service_orders = so_response.json()
        
        if len(service_orders) == 0:
            pytest.skip("No service orders available")
            
        os_id = service_orders[0]["id"]
        
        # Create a test report
        create_payload = {
            "report_type": "service",
            "os_id": os_id,
            "periodo": "TEST_01/01 a 05/01/2026",
            "executado_por": "TEST_User"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/reports", json=create_payload, headers=headers)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        created_report = create_response.json()
        assert "id" in created_report
        report_id = created_report["id"]
        
        # Verify by GET
        get_response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        assert get_response.status_code == 200
        fetched_report = get_response.json()
        assert fetched_report["report_type"] == "service"
        assert fetched_report["os_id"] == os_id
        
        # Cleanup - delete the test report
        delete_response = requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        assert delete_response.status_code == 200
        
    def test_update_report_and_verify(self, supervisor_token):
        """Test updating a report with editable fields (sections-based API)"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        
        # Get a service order ID
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        service_orders = so_response.json()
        
        if len(service_orders) == 0:
            pytest.skip("No service orders available")
            
        os_id = service_orders[0]["id"]
        
        # Create a test report
        create_response = requests.post(f"{BASE_URL}/api/reports", json={
            "report_type": "daily",
            "os_id": os_id,
            "periodo_inicio": "01/01/2026",
            "periodo_fim": "05/01/2026",
            "executado_por": "TEST_Initial_User"
        }, headers=headers)
        
        assert create_response.status_code == 200
        report_id = create_response.json()["id"]
        
        # Update with new period and sections content
        update_payload = {
            "periodo_inicio": "10/01/2026",
            "periodo_fim": "15/01/2026",
            "executado_por": "TEST_Updated_User",
            "sections": [
                {"key": "introduction", "number": "1", "title": "INTRODUÇÃO", "content": "TEST_Introduction text", "enabled": True, "subsections": []},
                {"key": "equipment", "number": "2", "title": "EQUIPAMENTOS", "content": "TEST_Equipment text", "enabled": True, "subsections": []},
                {"key": "objective", "number": "3", "title": "OBJETIVO", "content": "TEST_Objective text", "enabled": True, "subsections": []},
                {"key": "daily_activities", "number": "4", "title": "DESCRIÇÃO DAS ATIVIDADES DIÁRIAS", "content": "TEST_Activities", "enabled": True, "subsections": []},
                {"key": "observations", "number": "5", "title": "OBSERVAÇÕES", "content": "TEST_Observations", "enabled": True, "subsections": []},
            ]
        }
        
        update_response = requests.put(f"{BASE_URL}/api/reports/{report_id}", json=update_payload, headers=headers)
        assert update_response.status_code == 200
        
        # Verify update persisted
        get_response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        assert get_response.status_code == 200
        updated_report = get_response.json()
        
        assert updated_report["periodo_inicio"] == "10/01/2026"
        assert updated_report["periodo_fim"] == "15/01/2026"
        assert updated_report["executado_por"] == "TEST_Updated_User"
        # Verify sections were updated
        sections = updated_report.get("sections", [])
        assert len(sections) >= 5
        intro_section = next((s for s in sections if s["key"] == "introduction"), None)
        assert intro_section is not None
        assert intro_section["content"] == "TEST_Introduction text"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        
    def test_delete_report_and_verify(self, supervisor_token):
        """Test deleting a report"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        
        # Get a service order ID
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        service_orders = so_response.json()
        
        if len(service_orders) == 0:
            pytest.skip("No service orders available")
            
        os_id = service_orders[0]["id"]
        
        # Create a test report to delete
        create_response = requests.post(f"{BASE_URL}/api/reports", json={
            "report_type": "service",
            "os_id": os_id,
            "periodo": "TEST_TO_DELETE",
            "executado_por": "TEST_User"
        }, headers=headers)
        
        assert create_response.status_code == 200
        report_id = create_response.json()["id"]
        
        # Delete the report
        delete_response = requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        assert delete_response.status_code == 200
        
        # Verify it's gone
        get_response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        assert get_response.status_code == 404
        
    def test_report_pdf_generation(self, supervisor_token):
        """Test PDF generation for a report"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        
        # Get reports
        list_response = requests.get(f"{BASE_URL}/api/reports", headers=headers)
        reports = list_response.json()["reports"]
        
        if len(reports) > 0:
            report_id = reports[0]["id"]
            pdf_response = requests.get(f"{BASE_URL}/api/reports/{report_id}/pdf", headers=headers)
            assert pdf_response.status_code == 200
            assert pdf_response.headers.get("content-type") == "application/pdf"
            # Check PDF starts with PDF magic bytes
            assert pdf_response.content[:4] == b'%PDF'
        else:
            pytest.skip("No reports available to test PDF generation")


class TestTimesheetRegressionTests:
    """Regression tests to ensure existing timesheet CRUD still works"""
    
    def test_get_timesheets(self, supervisor_token):
        """Test getting all timesheets"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/timesheets", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_timesheet_structure(self, supervisor_token):
        """Test timesheet data structure"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/timesheets", headers=headers)
        timesheets = response.json()
        
        if len(timesheets) > 0:
            ts = timesheets[0]
            assert "id" in ts
            assert "os_number" in ts
            assert "client" in ts
            assert "location" in ts
            assert "service" in ts
            assert "entries" in ts
            assert "supervisor_name" in ts
        else:
            pytest.skip("No timesheets available to test")
            
    def test_timesheet_pdf_generation(self, supervisor_token):
        """Test timesheet PDF generation still works"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/timesheets", headers=headers)
        timesheets = response.json()
        
        if len(timesheets) > 0:
            ts_id = timesheets[0]["id"]
            pdf_response = requests.get(f"{BASE_URL}/api/timesheets/{ts_id}/pdf", headers=headers)
            assert pdf_response.status_code == 200
            assert pdf_response.headers.get("content-type") == "application/pdf"
        else:
            pytest.skip("No timesheets available to test PDF generation")


class TestReportNotFoundErrors:
    """Test error handling for non-existent reports"""
    
    def test_get_nonexistent_report(self, supervisor_token):
        """Test getting a report that doesn't exist"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/000000000000000000000000", headers=headers)
        assert response.status_code == 404
        
    def test_update_nonexistent_report(self, supervisor_token):
        """Test updating a report that doesn't exist"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.put(f"{BASE_URL}/api/reports/000000000000000000000000", json={
            "periodo": "test"
        }, headers=headers)
        assert response.status_code == 404
        
    def test_delete_nonexistent_report(self, supervisor_token):
        """Test deleting a report that doesn't exist"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.delete(f"{BASE_URL}/api/reports/000000000000000000000000", headers=headers)
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
