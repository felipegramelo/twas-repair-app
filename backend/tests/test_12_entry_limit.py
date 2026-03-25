"""
Backend tests for 12-entry limit per timesheet feature
Tests: POST and PUT /api/timesheets endpoints with entry limit validation

Feature: Corporate timesheet should allow MAX 12 entries. 
When trying to add 13th entry, system returns 400 error with Portuguese message.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://report-pdf-engine.preview.emergentagent.com')

# Test credentials
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"

# Existing test data
EXISTING_SERVICE_ORDER_ID = "699df3e6cf749c0aece02e93"
EXISTING_EMPLOYEE_ID = "699df05b67a32342504627bc"  # Carlos Mendes


@pytest.fixture(scope="module")
def supervisor_token():
    """Get supervisor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": SUPERVISOR_PASSWORD
    })
    assert response.status_code == 200, f"Supervisor login failed: {response.text}"
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
    return EXISTING_EMPLOYEE_ID  # Fallback


def get_id(data):
    """Helper to get ID from response data that may have 'id' or '_id'"""
    return data.get("id") or data.get("_id")


def create_entries(count: int, employee_id: str):
    """Helper to create N entries for testing"""
    entries = []
    for i in range(count):
        entries.append({
            "date": f"{(i % 28) + 1:02d}/01/2026",
            "employee_id": employee_id,
            "employee_name": f"Test Worker {i+1}",
            "employee_function": ["E", "EN", "Sup", "T", "M", "TS"][i % 6],
            "service_start": f"{8 + (i % 4):02d}:00",
            "service_end": f"{17 + (i % 3):02d}:00",
            "travel_start": "",
            "travel_end": ""
        })
    return entries


class TestTimesheetEntryLimitPOST:
    """Tests for POST /api/timesheets - Entry limit validation on CREATE"""
    
    def test_create_timesheet_with_12_entries_success(self, api_client, valid_employee_id):
        """POST /api/timesheets - Creating with exactly 12 entries should SUCCEED"""
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": create_entries(12, valid_employee_id),
            "observations": "TEST_12 entries - should succeed"
        }
        
        response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        created = response.json()
        timesheet_id = get_id(created)
        assert timesheet_id is not None
        assert len(created["entries"]) == 12
        print(f"SUCCESS: Created timesheet with 12 entries (ID: {timesheet_id})")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/timesheets/{timesheet_id}")
    
    def test_create_timesheet_with_13_entries_fails(self, api_client, valid_employee_id):
        """POST /api/timesheets - Creating with 13 entries should return 400 error"""
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": create_entries(13, valid_employee_id),
            "observations": "TEST_13 entries - should FAIL"
        }
        
        response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        # Verify error message mentions the 12 limit
        error_data = response.json()
        error_message = error_data.get("detail", "")
        assert "12" in error_message, f"Error message should mention 12 limit: {error_message}"
        print(f"SUCCESS: 13 entries rejected with 400. Message: {error_message}")
    
    def test_create_timesheet_with_15_entries_fails(self, api_client, valid_employee_id):
        """POST /api/timesheets - Creating with 15 entries should return 400 error"""
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": create_entries(15, valid_employee_id),
            "observations": "TEST_15 entries - should FAIL"
        }
        
        response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        error_data = response.json()
        error_message = error_data.get("detail", "")
        assert "12" in error_message or "Máximo" in error_message, f"Error should mention limit: {error_message}"
        print(f"SUCCESS: 15 entries rejected with 400. Message: {error_message}")
    
    def test_create_timesheet_with_1_entry_success(self, api_client, valid_employee_id):
        """POST /api/timesheets - Creating with 1 entry should succeed"""
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": create_entries(1, valid_employee_id),
            "observations": "TEST_1 entry - should succeed"
        }
        
        response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        timesheet_id = get_id(response.json())
        print(f"SUCCESS: Created timesheet with 1 entry (ID: {timesheet_id})")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/timesheets/{timesheet_id}")


class TestTimesheetEntryLimitPUT:
    """Tests for PUT /api/timesheets/{id} - Entry limit validation on UPDATE"""
    
    def test_update_timesheet_to_12_entries_success(self, api_client, valid_employee_id):
        """PUT /api/timesheets/{id} - Updating to 12 entries should SUCCEED"""
        # First create with 5 entries
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": create_entries(5, valid_employee_id),
            "observations": "TEST_will update to 12 entries"
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert create_response.status_code == 200
        timesheet_id = get_id(create_response.json())
        
        # Update to 12 entries
        update_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": create_entries(12, valid_employee_id),
            "observations": "TEST_updated to 12 entries"
        }
        
        update_response = api_client.put(f"{BASE_URL}/api/timesheets/{timesheet_id}", json=update_payload)
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        updated = update_response.json()
        assert len(updated["entries"]) == 12
        print(f"SUCCESS: Updated timesheet to 12 entries (ID: {timesheet_id})")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/timesheets/{timesheet_id}")
    
    def test_update_timesheet_to_13_entries_fails(self, api_client, valid_employee_id):
        """PUT /api/timesheets/{id} - Updating to 13 entries should return 400 error"""
        # First create with 5 entries
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": create_entries(5, valid_employee_id),
            "observations": "TEST_will try to update to 13 entries"
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert create_response.status_code == 200
        timesheet_id = get_id(create_response.json())
        
        # Try to update to 13 entries - should fail
        update_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": create_entries(13, valid_employee_id),
            "observations": "TEST_13 entries update - should FAIL"
        }
        
        update_response = api_client.put(f"{BASE_URL}/api/timesheets/{timesheet_id}", json=update_payload)
        assert update_response.status_code == 400, f"Expected 400, got {update_response.status_code}: {update_response.text}"
        
        error_data = update_response.json()
        error_message = error_data.get("detail", "")
        assert "12" in error_message, f"Error message should mention 12 limit: {error_message}"
        print(f"SUCCESS: 13 entries update rejected with 400. Message: {error_message}")
        
        # Verify timesheet still has original 5 entries
        get_response = api_client.get(f"{BASE_URL}/api/timesheets/{timesheet_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert len(fetched["entries"]) == 5, "Timesheet should still have 5 entries after failed update"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/timesheets/{timesheet_id}")
    
    def test_update_existing_12_entry_timesheet_with_12_entries(self, api_client, valid_employee_id):
        """PUT /api/timesheets/{id} - Editing an existing 12-entry timesheet (changing data, not count) should succeed"""
        # Create with 12 entries
        create_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": create_entries(12, valid_employee_id),
            "observations": "TEST_12 entries original"
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/timesheets", json=create_payload)
        assert create_response.status_code == 200
        timesheet_id = get_id(create_response.json())
        
        # Update with same 12 entries but different data
        entries = create_entries(12, valid_employee_id)
        entries[0]["employee_name"] = "Updated Worker Name"  # Change one field
        update_payload = {
            "os_id": EXISTING_SERVICE_ORDER_ID,
            "entries": entries,
            "observations": "TEST_12 entries updated - same count"
        }
        
        update_response = api_client.put(f"{BASE_URL}/api/timesheets/{timesheet_id}", json=update_payload)
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        updated = update_response.json()
        assert len(updated["entries"]) == 12
        assert updated["entries"][0]["employee_name"] == "Updated Worker Name"
        print(f"SUCCESS: Updated 12-entry timesheet (same count, different data)")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/timesheets/{timesheet_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
