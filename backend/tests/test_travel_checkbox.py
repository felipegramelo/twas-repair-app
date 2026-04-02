"""
Test Travel Checkbox Feature for Timesheet App
- Tests that travel_start/travel_end can be set to '-' when no travel
- Tests that travel times can be set when travel checkbox is checked
- Tests PDF generation with entries that have travel='-'
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://repair-proposals-app.preview.emergentagent.com').rstrip('/')

class TestTravelCheckboxFeature:
    """Test the travel checkbox feature implementation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get available service orders
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        assert so_response.status_code == 200
        self.service_orders = so_response.json()
        assert len(self.service_orders) > 0, "No service orders available for testing"
        
        # Get available employees
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert emp_response.status_code == 200
        self.employees = emp_response.json()
        assert len(self.employees) > 0, "No employees available for testing"
    
    def test_create_entry_without_travel(self):
        """Test creating an entry with travel checkbox unchecked (travel = '-')"""
        print("Testing entry creation without travel (checkbox unchecked)")
        
        # Create a timesheet with an entry that has no travel (travel_start='-', travel_end='-')
        payload = {
            "os_id": self.service_orders[0]["id"],
            "entries": [
                {
                    "date": "15/03/2026",
                    "employee_id": self.employees[0]["id"],
                    "employee_name": self.employees[0]["name"],
                    "employee_function": "T",
                    "service_start": "08:00",
                    "service_end": "17:00",
                    "travel_start": "-",  # No travel - checkbox unchecked
                    "travel_end": "-"
                }
            ],
            "observations": "TEST_TRAVEL_UNCHECKED - Entry without travel",
            "supervisor_function": "Supervisor (Sup)"
        }
        
        response = requests.post(f"{BASE_URL}/api/timesheets", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Failed to create timesheet: {response.text}"
        
        data = response.json()
        self.created_ts_id = data["id"]
        
        # Verify the entry was saved with travel='-'
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["travel_start"] == "-", f"Expected travel_start='-', got '{entry['travel_start']}'"
        assert entry["travel_end"] == "-", f"Expected travel_end='-', got '{entry['travel_end']}'"
        print(f"SUCCESS: Entry created with travel_start='{entry['travel_start']}', travel_end='{entry['travel_end']}'")
        
        # Cleanup
        delete_response = requests.delete(f"{BASE_URL}/api/timesheets/{self.created_ts_id}", headers=self.headers)
        assert delete_response.status_code == 200, "Failed to delete test timesheet"
        print("Test timesheet cleaned up")
    
    def test_create_entry_with_travel(self):
        """Test creating an entry with travel checkbox checked (actual travel times)"""
        print("Testing entry creation with travel (checkbox checked)")
        
        payload = {
            "os_id": self.service_orders[0]["id"],
            "entries": [
                {
                    "date": "16/03/2026",
                    "employee_id": self.employees[0]["id"],
                    "employee_name": self.employees[0]["name"],
                    "employee_function": "T",
                    "service_start": "08:00",
                    "service_end": "17:00",
                    "travel_start": "07:00",  # Has travel - checkbox checked
                    "travel_end": "18:00"
                }
            ],
            "observations": "TEST_TRAVEL_CHECKED - Entry with travel",
            "supervisor_function": "Supervisor (Sup)"
        }
        
        response = requests.post(f"{BASE_URL}/api/timesheets", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Failed to create timesheet: {response.text}"
        
        data = response.json()
        self.created_ts_id = data["id"]
        
        # Verify the entry was saved with actual travel times
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["travel_start"] == "07:00", f"Expected travel_start='07:00', got '{entry['travel_start']}'"
        assert entry["travel_end"] == "18:00", f"Expected travel_end='18:00', got '{entry['travel_end']}'"
        print(f"SUCCESS: Entry created with travel_start='{entry['travel_start']}', travel_end='{entry['travel_end']}'")
        
        # Cleanup
        delete_response = requests.delete(f"{BASE_URL}/api/timesheets/{self.created_ts_id}", headers=self.headers)
        assert delete_response.status_code == 200, "Failed to delete test timesheet"
        print("Test timesheet cleaned up")
    
    def test_pdf_generation_with_no_travel_entries(self):
        """Test that PDF generates correctly for entries with travel='-'"""
        print("Testing PDF generation with entries that have travel='-'")
        
        # Create timesheet with no-travel entry
        payload = {
            "os_id": self.service_orders[0]["id"],
            "entries": [
                {
                    "date": "17/03/2026",
                    "employee_id": self.employees[0]["id"],
                    "employee_name": self.employees[0]["name"],
                    "employee_function": "T",
                    "service_start": "08:00",
                    "service_end": "17:00",
                    "travel_start": "-",
                    "travel_end": "-"
                }
            ],
            "observations": "TEST_PDF_NO_TRAVEL",
            "supervisor_function": "Supervisor (Sup)"
        }
        
        response = requests.post(f"{BASE_URL}/api/timesheets", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Failed to create timesheet: {response.text}"
        
        ts_id = response.json()["id"]
        
        # Generate PDF
        pdf_response = requests.get(f"{BASE_URL}/api/timesheets/{ts_id}/pdf", headers=self.headers)
        assert pdf_response.status_code == 200, f"PDF generation failed: {pdf_response.status_code}"
        assert pdf_response.headers.get("content-type") == "application/pdf", "Response is not a PDF"
        assert len(pdf_response.content) > 1000, "PDF content seems too small"
        print(f"SUCCESS: PDF generated, size={len(pdf_response.content)} bytes")
        
        # Cleanup
        delete_response = requests.delete(f"{BASE_URL}/api/timesheets/{ts_id}", headers=self.headers)
        assert delete_response.status_code == 200
        print("Test timesheet cleaned up")
    
    def test_update_entry_toggle_travel(self):
        """Test updating an entry - toggle travel on/off"""
        print("Testing update entry - toggling travel checkbox")
        
        # Create with travel
        payload = {
            "os_id": self.service_orders[0]["id"],
            "entries": [
                {
                    "date": "18/03/2026",
                    "employee_id": self.employees[0]["id"],
                    "employee_name": self.employees[0]["name"],
                    "employee_function": "T",
                    "service_start": "08:00",
                    "service_end": "17:00",
                    "travel_start": "07:00",
                    "travel_end": "18:00"
                }
            ],
            "observations": "TEST_UPDATE_TRAVEL",
            "supervisor_function": "Supervisor (Sup)"
        }
        
        response = requests.post(f"{BASE_URL}/api/timesheets", json=payload, headers=self.headers)
        assert response.status_code == 200
        ts_id = response.json()["id"]
        
        # Update - toggle travel off (uncheck checkbox)
        update_payload = {
            "os_id": self.service_orders[0]["id"],
            "entries": [
                {
                    "date": "18/03/2026",
                    "employee_id": self.employees[0]["id"],
                    "employee_name": self.employees[0]["name"],
                    "employee_function": "T",
                    "service_start": "08:00",
                    "service_end": "17:00",
                    "travel_start": "-",  # Travel unchecked
                    "travel_end": "-"
                }
            ],
            "observations": "TEST_UPDATE_TRAVEL - Travel toggled OFF",
            "supervisor_function": "Supervisor (Sup)"
        }
        
        update_response = requests.put(f"{BASE_URL}/api/timesheets/{ts_id}", json=update_payload, headers=self.headers)
        assert update_response.status_code == 200
        
        updated_data = update_response.json()
        entry = updated_data["entries"][0]
        assert entry["travel_start"] == "-", f"Expected travel_start='-' after update, got '{entry['travel_start']}'"
        assert entry["travel_end"] == "-", f"Expected travel_end='-' after update, got '{entry['travel_end']}'"
        print(f"SUCCESS: Entry updated with travel toggled OFF - travel_start='{entry['travel_start']}'")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/timesheets/{ts_id}", headers=self.headers)
        print("Test timesheet cleaned up")
    
    def test_mixed_entries_some_with_travel(self):
        """Test timesheet with mixed entries - some with travel, some without"""
        print("Testing mixed entries - some with travel, some without")
        
        payload = {
            "os_id": self.service_orders[0]["id"],
            "entries": [
                {
                    "date": "19/03/2026",
                    "employee_id": self.employees[0]["id"],
                    "employee_name": self.employees[0]["name"],
                    "employee_function": "T",
                    "service_start": "08:00",
                    "service_end": "17:00",
                    "travel_start": "-",  # No travel
                    "travel_end": "-"
                },
                {
                    "date": "19/03/2026",
                    "employee_id": self.employees[1]["id"] if len(self.employees) > 1 else self.employees[0]["id"],
                    "employee_name": self.employees[1]["name"] if len(self.employees) > 1 else self.employees[0]["name"],
                    "employee_function": "E",
                    "service_start": "09:00",
                    "service_end": "18:00",
                    "travel_start": "08:00",  # Has travel
                    "travel_end": "19:00"
                }
            ],
            "observations": "TEST_MIXED_TRAVEL",
            "supervisor_function": "Supervisor (Sup)"
        }
        
        response = requests.post(f"{BASE_URL}/api/timesheets", json=payload, headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        ts_id = data["id"]
        
        # Verify both entries saved correctly
        assert len(data["entries"]) == 2
        
        # Find the entry without travel
        no_travel_entry = next((e for e in data["entries"] if e["travel_start"] == "-"), None)
        assert no_travel_entry is not None, "Entry without travel not found"
        
        # Find the entry with travel
        with_travel_entry = next((e for e in data["entries"] if e["travel_start"] != "-"), None)
        assert with_travel_entry is not None, "Entry with travel not found"
        assert with_travel_entry["travel_start"] == "08:00"
        
        print(f"SUCCESS: Mixed entries saved - one without travel, one with travel")
        
        # Test PDF generation with mixed entries
        pdf_response = requests.get(f"{BASE_URL}/api/timesheets/{ts_id}/pdf", headers=self.headers)
        assert pdf_response.status_code == 200, "PDF generation failed for mixed entries"
        print(f"SUCCESS: PDF generated for mixed entries, size={len(pdf_response.content)} bytes")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/timesheets/{ts_id}", headers=self.headers)
        print("Test timesheet cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
