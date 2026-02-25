"""
Backend tests for Timesheet API and PDF generation
Covers: CRUD operations, PDF generation for single/multi-page timesheets
"""
import pytest
import requests
import os
import io
from datetime import datetime
from PyPDF2 import PdfReader

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://duty-sheet.preview.emergentagent.com')

# Test credentials
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"

# Existing test data
# Existing test data - fetched dynamically to avoid stale IDs
EXISTING_TIMESHEET_ID = "699dfc74f83c38c3a573cf8d"  # May vary
EXISTING_SERVICE_ORDER_ID = "699df3e6cf749c0aece02e93"  # May vary
EXISTING_EMPLOYEE_ID = None  # Will be fetched dynamically


@pytest.fixture(scope="module")
def supervisor_token():
    """Get supervisor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": SUPERVISOR_PASSWORD
    })
    assert response.status_code == 200, f"Supervisor login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def api_client(supervisor_token):
    """Requests session with supervisor auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {supervisor_token}"
    })
    return session


@pytest.fixture(scope="module")
def valid_employee_id(supervisor_token):
    """Fetch a valid employee ID from the database"""
    response = requests.get(
        f"{BASE_URL}/api/employees",
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    if response.status_code == 200 and response.json():
        return response.json()[0]["id"]
    return None


def get_id(data):
    """Helper to get ID from response data that may have 'id' or '_id'"""
    return data.get("id") or data.get("_id")


class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_supervisor_login_success(self):
        """Test supervisor can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "supervisor"
        print(f"Supervisor login success: {data['user']['name']}")
    
    def test_admin_login_success(self):
        """Test admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"Admin login success: {data['user']['name']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401


class TestTimesheetCRUD:
    """Timesheet CRUD operation tests"""
    
    def test_get_timesheets_list(self, api_client):
        """GET /api/timesheets - Get all timesheets"""
        response = api_client.get(f"{BASE_URL}/api/timesheets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} timesheets")
    
    def test_get_existing_timesheet_by_id(self, api_client):
        """GET /api/timesheets/{id} - Get existing timesheet"""
        response = api_client.get(f"{BASE_URL}/api/timesheets/{EXISTING_TIMESHEET_ID}")
        assert response.status_code == 200
        data = response.json()
        # API may return 'id' or '_id' depending on serialization
        timesheet_id = get_id(data)
        assert timesheet_id == EXISTING_TIMESHEET_ID, f"Expected {EXISTING_TIMESHEET_ID}, got {timesheet_id}"
        assert "entries" in data
        assert "os_number" in data
        print(f"Timesheet {EXISTING_TIMESHEET_ID}: OS {data['os_number']}, {len(data['entries'])} entries")
    
    def test_create_and_delete_timesheet(self, api_client):
        """POST /api/timesheets - Create a new timesheet, then delete it"""
        # Create timesheet with 2 entries
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": [
                {
                    "date": "15/01/2026",
                    "employee_id": EXISTING_EMPLOYEE_ID,
                    "employee_name": "Test Employee",
                    "employee_function": "T",
                    "service_start": "08:00",
                    "service_end": "17:00",
                    "travel_start": "",
                    "travel_end": ""
                },
                {
                    "date": "16/01/2026",
                    "employee_id": EXISTING_EMPLOYEE_ID,
                    "employee_name": "Test Employee",
                    "employee_function": "T",
                    "service_start": "08:30",
                    "service_end": "17:30",
                    "travel_start": "07:00",
                    "travel_end": "08:00"
                }
            ],
            "observations": "TEST_timesheet for API testing"
        }
        
        # Create
        response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        created = response.json()
        assert "id" in created
        assert created["os_id"] == EXISTING_SERVICE_ORDER_ID
        assert len(created["entries"]) == 2
        assert created["observations"] == "TEST_timesheet for API testing"
        print(f"Created timesheet: {created['id']}")
        
        timesheet_id = created["id"]
        
        # Verify by GET
        get_response = api_client.get(f"{BASE_URL}/api/timesheets/{timesheet_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["id"] == timesheet_id
        
        # Delete
        delete_response = api_client.delete(f"{BASE_URL}/api/timesheets/{timesheet_id}")
        assert delete_response.status_code == 200
        print(f"Deleted timesheet: {timesheet_id}")
        
        # Verify deletion
        get_after_delete = api_client.get(f"{BASE_URL}/api/timesheets/{timesheet_id}")
        assert get_after_delete.status_code == 404
    
    def test_update_timesheet(self, api_client):
        """PUT /api/timesheets/{id} - Update an existing timesheet"""
        # First create a timesheet to update
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": [
                {
                    "date": "17/01/2026",
                    "employee_id": EXISTING_EMPLOYEE_ID,
                    "employee_name": "Original Employee",
                    "employee_function": "T",
                    "service_start": "09:00",
                    "service_end": "18:00",
                    "travel_start": "",
                    "travel_end": ""
                }
            ],
            "observations": "TEST_original observations"
        }
        
        response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert response.status_code == 200
        created = response.json()
        timesheet_id = created["id"]
        
        # Update the timesheet
        update_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": [
                {
                    "date": "17/01/2026",
                    "employee_id": EXISTING_EMPLOYEE_ID,
                    "employee_name": "Updated Employee",
                    "employee_function": "E",
                    "service_start": "10:00",
                    "service_end": "19:00",
                    "travel_start": "09:00",
                    "travel_end": "09:30"
                }
            ],
            "observations": "TEST_updated observations"
        }
        
        update_response = api_client.put(f"{BASE_URL}/api/timesheets/{timesheet_id}", json=update_payload)
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        updated = update_response.json()
        assert updated["entries"][0]["employee_name"] == "Updated Employee"
        assert updated["entries"][0]["employee_function"] == "E"
        assert updated["observations"] == "TEST_updated observations"
        print(f"Updated timesheet: {timesheet_id}")
        
        # Verify update persisted
        get_response = api_client.get(f"{BASE_URL}/api/timesheets/{timesheet_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["entries"][0]["service_start"] == "10:00"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/timesheets/{timesheet_id}")


class TestPDFGenerationSinglePage:
    """PDF Generation tests for single-page timesheets (<=12 entries)"""
    
    def test_pdf_generation_existing_timesheet(self, api_client):
        """Generate PDF for existing timesheet and verify it's a valid PDF"""
        response = api_client.get(
            f"{BASE_URL}/api/timesheets/{EXISTING_TIMESHEET_ID}/pdf",
            headers={"Accept": "application/pdf"}
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        
        # Verify it's a valid PDF
        pdf_data = io.BytesIO(response.content)
        reader = PdfReader(pdf_data)
        num_pages = len(reader.pages)
        assert num_pages >= 1
        print(f"Generated PDF with {num_pages} page(s) for existing timesheet")
    
    def test_pdf_content_single_page(self, api_client):
        """Create single-page timesheet (<=12 entries) and verify PDF sections"""
        # Create timesheet with 5 entries
        entries = []
        for i in range(5):
            entries.append({
                "date": f"{10+i}/01/2026",
                "employee_id": EXISTING_EMPLOYEE_ID,
                "employee_name": f"Employee {i+1}",
                "employee_function": "T",
                "service_start": "08:00",
                "service_end": "17:00",
                "travel_start": "",
                "travel_end": ""
            })
        
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": entries,
            "observations": "TEST_PDF single page - should contain all sections: observations, legend, approval, footer"
        }
        
        response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert response.status_code == 200
        timesheet_id = response.json()["id"]
        
        # Generate PDF
        pdf_response = api_client.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf",
            headers={"Accept": "application/pdf"}
        )
        assert pdf_response.status_code == 200
        
        pdf_data = io.BytesIO(pdf_response.content)
        reader = PdfReader(pdf_data)
        num_pages = len(reader.pages)
        
        # Single page expected for 5 entries
        assert num_pages == 1, f"Expected 1 page, got {num_pages}"
        
        # Extract text from page
        page_text = reader.pages[0].extract_text()
        
        # Verify key sections present
        assert "RELATÓRIO DE HORAS" in page_text or "TIME SHEET" in page_text, "Missing header"
        assert "Legenda" in page_text or "Caption" in page_text, "Missing legend section"
        assert "Aprovação" in page_text or "Approval" in page_text, "Missing approval section"
        assert "Observações" in page_text or "Remarks" in page_text, "Missing observations section"
        assert "TWAS REPAIR" in page_text, "Missing footer company info"
        assert "Página 1 de 1" in page_text, "Missing page number"
        
        print(f"Single-page PDF verified with all required sections")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/timesheets/{timesheet_id}")


class TestPDFGenerationMultiPage:
    """PDF Generation tests for multi-page timesheets (>12 entries)"""
    
    def test_pdf_multipage_15_entries(self, api_client):
        """Create timesheet with 15 entries, verify 2-page PDF with per-page sections"""
        # Create 15 entries to force pagination
        entries = []
        for i in range(15):
            entries.append({
                "date": f"{(i % 28) + 1}/01/2026",
                "employee_id": EXISTING_EMPLOYEE_ID,
                "employee_name": f"Worker {i+1}",
                "employee_function": ["E", "EN", "Sup", "T", "M", "TS"][i % 6],
                "service_start": f"{8 + (i % 4):02d}:00",
                "service_end": f"{17 + (i % 3):02d}:00",
                "travel_start": "07:00" if i % 3 == 0 else "",
                "travel_end": "08:00" if i % 3 == 0 else ""
            })
        
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": entries,
            "observations": "TEST_Multi-page PDF - Page 1 should show this text, Page 2 should have empty observation box"
        }
        
        response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert response.status_code == 200
        created = response.json()
        timesheet_id = created["id"]
        
        # Verify 15 entries were created
        assert len(created["entries"]) == 15, f"Expected 15 entries, got {len(created['entries'])}"
        
        # Generate PDF
        pdf_response = api_client.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf",
            headers={"Accept": "application/pdf"}
        )
        assert pdf_response.status_code == 200
        
        pdf_data = io.BytesIO(pdf_response.content)
        reader = PdfReader(pdf_data)
        num_pages = len(reader.pages)
        
        # Should be 2 pages for 15 entries (12 per page limit)
        assert num_pages == 2, f"Expected 2 pages for 15 entries, got {num_pages}"
        print(f"Multi-page PDF generated with {num_pages} pages")
        
        # Verify page 1 content
        page1_text = reader.pages[0].extract_text()
        assert "RELATÓRIO DE HORAS" in page1_text or "TIME SHEET" in page1_text, "Missing header on page 1"
        assert "Legenda" in page1_text or "Caption" in page1_text, "Missing legend on page 1"
        assert "Aprovação" in page1_text or "Approval" in page1_text, "Missing approval on page 1"
        assert "Observações" in page1_text or "Remarks" in page1_text, "Missing observations on page 1"
        assert "TWAS REPAIR" in page1_text, "Missing footer on page 1"
        assert "Página 1 de 2" in page1_text, "Missing 'Page 1 of 2' on page 1"
        
        # Verify page 2 content - should also have all sections
        page2_text = reader.pages[1].extract_text()
        assert "RELATÓRIO DE HORAS" in page2_text or "TIME SHEET" in page2_text, "Missing header on page 2"
        assert "Legenda" in page2_text or "Caption" in page2_text, "Missing legend on page 2"
        assert "Aprovação" in page2_text or "Approval" in page2_text, "Missing approval on page 2"
        assert "Observações" in page2_text or "Remarks" in page2_text, "Missing observations on page 2"
        assert "TWAS REPAIR" in page2_text, "Missing footer on page 2"
        assert "Página 2 de 2" in page2_text, "Missing 'Page 2 of 2' on page 2"
        
        print("Multi-page PDF verified: Both pages have all required sections (header, legend, approval, observations, footer)")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/timesheets/{timesheet_id}")
    
    def test_pdf_multipage_24_entries(self, api_client):
        """Create timesheet with 24 entries, verify 2-page PDF"""
        # Create 24 entries
        entries = []
        for i in range(24):
            entries.append({
                "date": f"{(i % 28) + 1}/01/2026",
                "employee_id": EXISTING_EMPLOYEE_ID,
                "employee_name": f"Technician {i+1}",
                "employee_function": "T",
                "service_start": "08:00",
                "service_end": "18:00",
                "travel_start": "",
                "travel_end": ""
            })
        
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": entries,
            "observations": "TEST_24 entries PDF"
        }
        
        response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert response.status_code == 200
        timesheet_id = response.json()["id"]
        
        # Generate PDF
        pdf_response = api_client.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf",
            headers={"Accept": "application/pdf"}
        )
        assert pdf_response.status_code == 200
        
        pdf_data = io.BytesIO(pdf_response.content)
        reader = PdfReader(pdf_data)
        num_pages = len(reader.pages)
        
        # Should be 2 pages for 24 entries
        assert num_pages == 2, f"Expected 2 pages for 24 entries, got {num_pages}"
        print(f"24-entry PDF generated with {num_pages} pages")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/timesheets/{timesheet_id}")


class TestServiceOrderAPIs:
    """Service Order API tests"""
    
    def test_get_service_orders(self, api_client):
        """GET /api/service-orders - Get all service orders"""
        response = api_client.get(f"{BASE_URL}/api/service-orders")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} service orders")
    
    def test_get_service_order_by_id(self, api_client):
        """GET /api/service-orders/{id} - Get existing service order"""
        response = api_client.get(f"{BASE_URL}/api/service-orders/{EXISTING_SERVICE_ORDER_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("id") == EXISTING_SERVICE_ORDER_ID
        assert "os_number" in data
        assert "client" in data
        print(f"Service Order: {data['os_number']} - {data['client']}")


class TestEmployeeAPIs:
    """Employee API tests"""
    
    def test_get_employees(self, api_client):
        """GET /api/employees - Get all employees"""
        response = api_client.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} employees")
    
    def test_get_employee_by_id(self, api_client):
        """GET /api/employees/{id} - Get existing employee"""
        response = api_client.get(f"{BASE_URL}/api/employees/{EXISTING_EMPLOYEE_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("id") == EXISTING_EMPLOYEE_ID
        assert "name" in data
        print(f"Employee: {data['name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
