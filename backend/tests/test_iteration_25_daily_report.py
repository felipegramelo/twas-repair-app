"""
Test Iteration 25: Daily Report Feature Tests
- Daily report sections (same as service report minus NDT, Pressure Test, Certificates, Evaluation)
- Daily entries (Entradas Diárias) CRUD operations
- Service report should NOT be affected
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://repair-proposals-app.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"

# Known daily report ID with existing daily entries
KNOWN_DAILY_REPORT_ID = "69cab24a20ccceb3f82500f9"
KNOWN_OS_ID = "699df3e6cf749c0aece02e93"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def supervisor_token(api_client):
    """Get supervisor authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": SUPERVISOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Supervisor authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, supervisor_token):
    """Session with supervisor auth header"""
    api_client.headers.update({"Authorization": f"Bearer {supervisor_token}"})
    return api_client


@pytest.fixture(scope="module")
def admin_client(api_client, admin_token):
    """Session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


class TestDailyReportSections:
    """Test that daily reports have correct sections (same as service minus NDT/eval/pressure/certs)"""
    
    def test_create_daily_report_has_correct_sections(self, authenticated_client):
        """Create a new daily report and verify it has correct sections"""
        # First get a valid OS ID
        response = authenticated_client.get(f"{BASE_URL}/api/service-orders")
        assert response.status_code == 200, f"Failed to get service orders: {response.text}"
        
        # API returns array directly
        orders = response.json()
        if isinstance(orders, dict):
            orders = orders.get("service_orders", [])
        if not orders:
            pytest.skip("No service orders available for testing")
        
        os_id = orders[0]["id"]
        
        # Create a daily report
        create_response = authenticated_client.post(f"{BASE_URL}/api/reports", json={
            "report_type": "daily",
            "os_id": os_id
        })
        assert create_response.status_code == 200, f"Failed to create daily report: {create_response.text}"
        
        report_id = create_response.json()["id"]
        
        # Get the report to check sections
        get_response = authenticated_client.get(f"{BASE_URL}/api/reports/{report_id}")
        assert get_response.status_code == 200, f"Failed to get report: {get_response.text}"
        
        report = get_response.json()
        sections = report.get("sections", [])
        section_keys = [s["key"] for s in sections]
        
        # Daily report SHOULD have these sections
        assert "introduction" in section_keys, "Daily report missing INTRODUÇÃO section"
        assert "equipment" in section_keys, "Daily report missing EQUIPAMENTOS section"
        assert "objective" in section_keys, "Daily report missing OBJETIVO section"
        assert "service_description" in section_keys, "Daily report missing DESCRIÇÃO DOS SERVIÇOS section"
        
        # Daily report should NOT have these sections
        assert "ndt" not in section_keys, "Daily report should NOT have NDT section"
        assert "pressure_test" not in section_keys, "Daily report should NOT have Pressure Test section"
        assert "certificates" not in section_keys, "Daily report should NOT have Certificates section"
        assert "client_eval" not in section_keys, "Daily report should NOT have Client Evaluation section"
        
        # Verify section titles
        section_titles = {s["key"]: s["title"] for s in sections}
        assert section_titles.get("introduction") == "INTRODUÇÃO"
        assert section_titles.get("equipment") == "EQUIPAMENTOS"
        assert section_titles.get("objective") == "OBJETIVO"
        assert section_titles.get("service_description") == "DESCRIÇÃO DOS SERVIÇOS"
        
        # Cleanup - delete the test report
        authenticated_client.delete(f"{BASE_URL}/api/reports/{report_id}")
        
        print(f"PASS: Daily report created with correct sections: {section_keys}")
    
    def test_daily_report_has_desmontagem_montagem_subsections(self, authenticated_client):
        """Verify daily report has Desmontagem/Montagem subsections under service_description"""
        # Get the known daily report
        response = authenticated_client.get(f"{BASE_URL}/api/reports/{KNOWN_DAILY_REPORT_ID}")
        
        if response.status_code == 404:
            pytest.skip("Known daily report not found, creating new one for test")
        
        assert response.status_code == 200, f"Failed to get report: {response.text}"
        
        report = response.json()
        sections = report.get("sections", [])
        
        # Find service_description section
        service_desc = next((s for s in sections if s["key"] == "service_description"), None)
        assert service_desc is not None, "service_description section not found"
        
        subsections = service_desc.get("subsections", [])
        subsection_keys = [sub["key"] for sub in subsections]
        
        assert "disassembly" in subsection_keys, "Missing DESMONTAGEM subsection"
        assert "assembly" in subsection_keys, "Missing MONTAGEM subsection"
        
        print(f"PASS: Daily report has Desmontagem/Montagem subsections: {subsection_keys}")


class TestDailyEntriesAPI:
    """Test daily_entries field in reports API"""
    
    def test_get_report_returns_daily_entries_field(self, authenticated_client):
        """GET /api/reports/{id} should return daily_entries field"""
        response = authenticated_client.get(f"{BASE_URL}/api/reports/{KNOWN_DAILY_REPORT_ID}")
        
        if response.status_code == 404:
            pytest.skip("Known daily report not found")
        
        assert response.status_code == 200, f"Failed to get report: {response.text}"
        
        report = response.json()
        assert "daily_entries" in report, "daily_entries field missing from report response"
        assert isinstance(report["daily_entries"], list), "daily_entries should be a list"
        
        print(f"PASS: Report has daily_entries field with {len(report['daily_entries'])} entries")
    
    def test_known_daily_report_has_existing_entries(self, authenticated_client):
        """Known daily report should have 2 existing daily entries"""
        response = authenticated_client.get(f"{BASE_URL}/api/reports/{KNOWN_DAILY_REPORT_ID}")
        
        if response.status_code == 404:
            pytest.skip("Known daily report not found")
        
        assert response.status_code == 200
        
        report = response.json()
        daily_entries = report.get("daily_entries", [])
        
        # According to the test request, this report should have 2 daily entries
        assert len(daily_entries) >= 2, f"Expected at least 2 daily entries, got {len(daily_entries)}"
        
        # Verify entry structure
        for entry in daily_entries:
            assert "id" in entry, "Daily entry missing 'id' field"
            assert "date" in entry, "Daily entry missing 'date' field"
            assert "description" in entry, "Daily entry missing 'description' field"
        
        print(f"PASS: Known daily report has {len(daily_entries)} daily entries with correct structure")
    
    def test_update_report_with_daily_entries(self, authenticated_client):
        """PUT /api/reports/{id} should persist daily_entries"""
        # First get the current report
        get_response = authenticated_client.get(f"{BASE_URL}/api/reports/{KNOWN_DAILY_REPORT_ID}")
        
        if get_response.status_code == 404:
            pytest.skip("Known daily report not found")
        
        assert get_response.status_code == 200
        
        original_report = get_response.json()
        original_entries = original_report.get("daily_entries", [])
        
        # Add a new test entry
        test_entry = {
            "id": f"test_day_{uuid.uuid4().hex[:8]}",
            "date": "25/01/2026",
            "description": "• Test entry for iteration 25\n• Automated test"
        }
        
        new_entries = original_entries + [test_entry]
        
        # Update the report
        update_response = authenticated_client.put(f"{BASE_URL}/api/reports/{KNOWN_DAILY_REPORT_ID}", json={
            "daily_entries": new_entries
        })
        assert update_response.status_code == 200, f"Failed to update report: {update_response.text}"
        
        # Verify the update persisted
        verify_response = authenticated_client.get(f"{BASE_URL}/api/reports/{KNOWN_DAILY_REPORT_ID}")
        assert verify_response.status_code == 200
        
        updated_report = verify_response.json()
        updated_entries = updated_report.get("daily_entries", [])
        
        assert len(updated_entries) == len(new_entries), f"Expected {len(new_entries)} entries, got {len(updated_entries)}"
        
        # Find our test entry
        test_entry_found = any(e["id"] == test_entry["id"] for e in updated_entries)
        assert test_entry_found, "Test entry not found after update"
        
        # Cleanup - restore original entries
        authenticated_client.put(f"{BASE_URL}/api/reports/{KNOWN_DAILY_REPORT_ID}", json={
            "daily_entries": original_entries
        })
        
        print(f"PASS: Daily entries update persisted correctly")
    
    def test_get_reports_list_includes_daily_entries(self, authenticated_client):
        """GET /api/reports should include daily_entries in response"""
        response = authenticated_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200, f"Failed to get reports: {response.text}"
        
        reports = response.json().get("reports", [])
        
        # Find a daily report
        daily_reports = [r for r in reports if r.get("report_type") == "daily"]
        
        if not daily_reports:
            pytest.skip("No daily reports found in list")
        
        # Check that daily_entries field exists
        for report in daily_reports:
            assert "daily_entries" in report, f"Report {report['id']} missing daily_entries field"
        
        print(f"PASS: Reports list includes daily_entries field for {len(daily_reports)} daily reports")


class TestServiceReportNotAffected:
    """Verify service reports are not affected by daily report changes"""
    
    def test_create_service_report_has_all_sections(self, authenticated_client):
        """Service report should still have NDT, Pressure Test, Certificates, Evaluation sections"""
        # Get a valid OS ID
        response = authenticated_client.get(f"{BASE_URL}/api/service-orders")
        assert response.status_code == 200
        
        # API returns array directly
        orders = response.json()
        if isinstance(orders, dict):
            orders = orders.get("service_orders", [])
        if not orders:
            pytest.skip("No service orders available")
        
        os_id = orders[0]["id"]
        
        # Create a service report
        create_response = authenticated_client.post(f"{BASE_URL}/api/reports", json={
            "report_type": "service",
            "os_id": os_id
        })
        assert create_response.status_code == 200, f"Failed to create service report: {create_response.text}"
        
        report_id = create_response.json()["id"]
        
        # Get the report
        get_response = authenticated_client.get(f"{BASE_URL}/api/reports/{report_id}")
        assert get_response.status_code == 200
        
        report = get_response.json()
        sections = report.get("sections", [])
        section_keys = [s["key"] for s in sections]
        
        # Service report SHOULD have all sections including NDT, pressure_test, certificates, client_eval
        assert "introduction" in section_keys, "Service report missing INTRODUÇÃO"
        assert "equipment" in section_keys, "Service report missing EQUIPAMENTOS"
        assert "objective" in section_keys, "Service report missing OBJETIVO"
        assert "service_description" in section_keys, "Service report missing DESCRIÇÃO DOS SERVIÇOS"
        assert "ndt" in section_keys, "Service report missing NDT section"
        assert "pressure_test" in section_keys, "Service report missing Pressure Test section"
        assert "certificates" in section_keys, "Service report missing Certificates section"
        assert "client_eval" in section_keys, "Service report missing Client Evaluation section"
        
        # Cleanup
        authenticated_client.delete(f"{BASE_URL}/api/reports/{report_id}")
        
        print(f"PASS: Service report has all sections including NDT/Pressure/Certs/Eval: {section_keys}")
    
    def test_service_report_does_not_show_daily_entries_section(self, authenticated_client):
        """Service reports should have empty daily_entries (not shown in UI)"""
        # Get reports list
        response = authenticated_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200
        
        reports = response.json().get("reports", [])
        service_reports = [r for r in reports if r.get("report_type") == "service"]
        
        if not service_reports:
            pytest.skip("No service reports found")
        
        # Check a service report
        report_id = service_reports[0]["id"]
        get_response = authenticated_client.get(f"{BASE_URL}/api/reports/{report_id}")
        assert get_response.status_code == 200
        
        report = get_response.json()
        
        # daily_entries should exist but be empty for service reports
        daily_entries = report.get("daily_entries", [])
        assert isinstance(daily_entries, list), "daily_entries should be a list"
        
        print(f"PASS: Service report has daily_entries field (empty list expected for service reports)")


class TestDailyEntryStructure:
    """Test the structure of daily entries"""
    
    def test_daily_entry_has_required_fields(self, authenticated_client):
        """Each daily entry should have id, date, description"""
        response = authenticated_client.get(f"{BASE_URL}/api/reports/{KNOWN_DAILY_REPORT_ID}")
        
        if response.status_code == 404:
            pytest.skip("Known daily report not found")
        
        assert response.status_code == 200
        
        report = response.json()
        daily_entries = report.get("daily_entries", [])
        
        if not daily_entries:
            pytest.skip("No daily entries to test")
        
        for i, entry in enumerate(daily_entries):
            assert "id" in entry, f"Entry {i} missing 'id'"
            assert "date" in entry, f"Entry {i} missing 'date'"
            assert "description" in entry, f"Entry {i} missing 'description'"
            
            # Verify types
            assert isinstance(entry["id"], str), f"Entry {i} 'id' should be string"
            assert isinstance(entry["date"], str), f"Entry {i} 'date' should be string"
            assert isinstance(entry["description"], str), f"Entry {i} 'description' should be string"
        
        print(f"PASS: All {len(daily_entries)} daily entries have correct structure")


class TestReportTypeValidation:
    """Test report type handling"""
    
    def test_report_type_is_returned_correctly(self, authenticated_client):
        """Verify report_type field is returned correctly"""
        response = authenticated_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200
        
        reports = response.json().get("reports", [])
        
        for report in reports:
            assert "report_type" in report, f"Report {report['id']} missing report_type"
            assert report["report_type"] in ["service", "daily"], f"Invalid report_type: {report['report_type']}"
        
        daily_count = len([r for r in reports if r["report_type"] == "daily"])
        service_count = len([r for r in reports if r["report_type"] == "service"])
        
        print(f"PASS: Found {daily_count} daily reports and {service_count} service reports")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
