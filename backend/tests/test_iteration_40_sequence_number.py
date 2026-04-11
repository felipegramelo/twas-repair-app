"""
Iteration 40: Test sequence_number feature for timesheets
- Admin GET /api/timesheets returns sequence_number field
- Supervisor GET /api/timesheets does NOT return sequence_number field
- Timesheets with same os_id have different sequence_number values
- POST /api/timesheets assigns sequence_number automatically
- POST /api/timesheets/{id}/duplicate assigns new sequence_number
- GET /api/os-archive returns timesheets with sequence_number field
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://twas-repair-app-1.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


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
def service_order_id(admin_token):
    """Get a valid service order ID for testing"""
    response = requests.get(
        f"{BASE_URL}/api/service-orders",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200, f"Failed to get service orders: {response.text}"
    orders = response.json()
    assert len(orders) > 0, "No service orders found for testing"
    return orders[0]["id"]


class TestAdminTimesheetsSequenceNumber:
    """Test that admin sees sequence_number in timesheets"""
    
    def test_admin_get_timesheets_returns_sequence_number(self, admin_token):
        """Admin GET /api/timesheets should return sequence_number field"""
        response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get timesheets: {response.text}"
        timesheets = response.json()
        
        # Check that at least some timesheets exist
        if len(timesheets) > 0:
            # Check that sequence_number field exists in timesheets
            for ts in timesheets:
                assert "sequence_number" in ts, f"Timesheet {ts.get('id')} missing sequence_number field"
                assert ts["sequence_number"] is not None, f"Timesheet {ts.get('id')} has null sequence_number"
                assert isinstance(ts["sequence_number"], int), f"sequence_number should be int, got {type(ts['sequence_number'])}"
                assert ts["sequence_number"] >= 1, f"sequence_number should be >= 1, got {ts['sequence_number']}"
            print(f"PASS: Admin sees sequence_number in all {len(timesheets)} timesheets")
        else:
            pytest.skip("No timesheets found to test")
    
    def test_admin_timesheets_same_os_have_different_sequence_numbers(self, admin_token):
        """Timesheets with same os_id should have different sequence_number values"""
        response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        timesheets = response.json()
        
        # Group timesheets by os_id
        os_groups = {}
        for ts in timesheets:
            os_id = ts.get("os_id", "")
            if os_id not in os_groups:
                os_groups[os_id] = []
            os_groups[os_id].append(ts)
        
        # Check that within each OS group, sequence numbers are unique
        for os_id, ts_list in os_groups.items():
            if len(ts_list) > 1:
                seq_numbers = [ts.get("sequence_number") for ts in ts_list]
                unique_seq = set(seq_numbers)
                assert len(unique_seq) == len(seq_numbers), \
                    f"OS {os_id} has duplicate sequence_numbers: {seq_numbers}"
                print(f"PASS: OS {os_id} has {len(ts_list)} timesheets with unique sequence_numbers: {sorted(seq_numbers)}")


class TestSupervisorTimesheetsNoSequenceNumber:
    """Test that supervisor does NOT see sequence_number in timesheets"""
    
    def test_supervisor_get_timesheets_no_sequence_number(self, supervisor_token):
        """Supervisor GET /api/timesheets should NOT return sequence_number field"""
        response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200, f"Failed to get timesheets: {response.text}"
        timesheets = response.json()
        
        if len(timesheets) > 0:
            # Check that sequence_number field does NOT exist in supervisor's timesheets
            for ts in timesheets:
                # sequence_number should either not exist or be None/empty
                has_seq = "sequence_number" in ts and ts["sequence_number"] is not None
                assert not has_seq, \
                    f"Supervisor should NOT see sequence_number, but timesheet {ts.get('id')} has sequence_number={ts.get('sequence_number')}"
            print(f"PASS: Supervisor does NOT see sequence_number in {len(timesheets)} timesheets")
        else:
            pytest.skip("No timesheets found for supervisor")


class TestCreateTimesheetSequenceNumber:
    """Test that creating a timesheet assigns sequence_number automatically"""
    
    def test_create_timesheet_assigns_sequence_number(self, supervisor_token, service_order_id, admin_token):
        """POST /api/timesheets should assign sequence_number automatically"""
        # Create a test timesheet
        timesheet_data = {
            "os_id": service_order_id,
            "entries": [
                {
                    "date": "15/01/2026",
                    "employee_id": "test_emp_1",
                    "employee_name": "TEST_Employee_SeqNum",
                    "employee_function": "T",
                    "service_start": "08:00",
                    "service_end": "17:00",
                    "travel_start": "",
                    "travel_end": ""
                }
            ],
            "observations": "TEST_sequence_number_test",
            "supervisor_function": "Supervisor"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/timesheets",
            json=timesheet_data,
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200, f"Failed to create timesheet: {response.text}"
        created_ts = response.json()
        
        # Check that sequence_number was assigned
        assert "sequence_number" in created_ts, "Created timesheet missing sequence_number"
        assert created_ts["sequence_number"] is not None, "sequence_number is null"
        assert isinstance(created_ts["sequence_number"], int), f"sequence_number should be int"
        assert created_ts["sequence_number"] >= 1, f"sequence_number should be >= 1"
        
        created_id = created_ts["id"]
        print(f"PASS: Created timesheet {created_id} with sequence_number={created_ts['sequence_number']}")
        
        # Verify via admin GET that sequence_number is visible
        admin_response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code == 200
        admin_timesheets = admin_response.json()
        
        found_ts = next((ts for ts in admin_timesheets if ts["id"] == created_id), None)
        assert found_ts is not None, f"Created timesheet {created_id} not found in admin list"
        assert found_ts.get("sequence_number") == created_ts["sequence_number"], \
            f"sequence_number mismatch: created={created_ts['sequence_number']}, admin_view={found_ts.get('sequence_number')}"
        
        # Cleanup: delete the test timesheet
        delete_response = requests.delete(
            f"{BASE_URL}/api/timesheets/{created_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert delete_response.status_code == 200, f"Failed to delete test timesheet: {delete_response.text}"
        print(f"PASS: Cleaned up test timesheet {created_id}")


class TestDuplicateTimesheetSequenceNumber:
    """Test that duplicating a timesheet assigns new sequence_number"""
    
    def test_duplicate_timesheet_assigns_new_sequence_number(self, supervisor_token, admin_token):
        """POST /api/timesheets/{id}/duplicate should assign new sequence_number"""
        # First, get existing timesheets to find one to duplicate
        response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200
        timesheets = response.json()
        
        if len(timesheets) == 0:
            pytest.skip("No timesheets available to duplicate")
        
        # Find a non-finalized timesheet to duplicate
        original_ts = None
        for ts in timesheets:
            if ts.get("status") != "finalized":
                original_ts = ts
                break
        
        if original_ts is None:
            pytest.skip("No non-finalized timesheets available to duplicate")
        
        original_id = original_ts["id"]
        original_os_id = original_ts["os_id"]
        
        # Duplicate the timesheet
        dup_response = requests.post(
            f"{BASE_URL}/api/timesheets/{original_id}/duplicate",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert dup_response.status_code == 200, f"Failed to duplicate timesheet: {dup_response.text}"
        duplicated_ts = dup_response.json()
        
        # Check that duplicated timesheet has sequence_number
        assert "sequence_number" in duplicated_ts, "Duplicated timesheet missing sequence_number"
        assert duplicated_ts["sequence_number"] is not None, "Duplicated timesheet sequence_number is null"
        
        duplicated_id = duplicated_ts["id"]
        print(f"PASS: Duplicated timesheet {original_id} -> {duplicated_id} with sequence_number={duplicated_ts['sequence_number']}")
        
        # Verify via admin that both timesheets have different sequence_numbers
        admin_response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code == 200
        admin_timesheets = admin_response.json()
        
        # Find both timesheets in admin view
        original_in_admin = next((ts for ts in admin_timesheets if ts["id"] == original_id), None)
        duplicated_in_admin = next((ts for ts in admin_timesheets if ts["id"] == duplicated_id), None)
        
        if original_in_admin and duplicated_in_admin:
            # If same OS, sequence numbers should be different
            if original_in_admin.get("os_id") == duplicated_in_admin.get("os_id"):
                assert original_in_admin.get("sequence_number") != duplicated_in_admin.get("sequence_number"), \
                    f"Same OS timesheets should have different sequence_numbers"
                print(f"PASS: Original seq={original_in_admin.get('sequence_number')}, Duplicated seq={duplicated_in_admin.get('sequence_number')}")
        
        # Cleanup: delete the duplicated timesheet
        delete_response = requests.delete(
            f"{BASE_URL}/api/timesheets/{duplicated_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert delete_response.status_code == 200, f"Failed to delete duplicated timesheet: {delete_response.text}"
        print(f"PASS: Cleaned up duplicated timesheet {duplicated_id}")


class TestOSArchiveSequenceNumber:
    """Test that OS archive returns timesheets with sequence_number"""
    
    def test_os_archive_returns_sequence_number(self, admin_token):
        """GET /api/admin/os-archive should return timesheets with sequence_number field"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get OS archive: {response.text}"
        archives = response.json()
        
        # Find archives with timesheets
        archives_with_ts = [a for a in archives if len(a.get("timesheets", [])) > 0]
        
        if len(archives_with_ts) > 0:
            for archive in archives_with_ts:
                for ts in archive.get("timesheets", []):
                    assert "sequence_number" in ts, \
                        f"Timesheet {ts.get('id')} in OS archive missing sequence_number"
                    assert ts["sequence_number"] is not None, \
                        f"Timesheet {ts.get('id')} in OS archive has null sequence_number"
                    assert isinstance(ts["sequence_number"], int), \
                        f"sequence_number should be int"
            print(f"PASS: OS archive returns sequence_number for all timesheets in {len(archives_with_ts)} archives")
        else:
            pytest.skip("No archives with timesheets found")


class TestSequenceNumberFormat:
    """Test that sequence_number follows expected format (01, 02, 03...)"""
    
    def test_sequence_number_starts_from_one(self, admin_token):
        """sequence_number should start from 1 for each OS"""
        response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        timesheets = response.json()
        
        # Group by os_id
        os_groups = {}
        for ts in timesheets:
            os_id = ts.get("os_id", "")
            if os_id not in os_groups:
                os_groups[os_id] = []
            os_groups[os_id].append(ts)
        
        # Check each group has sequence starting from 1
        for os_id, ts_list in os_groups.items():
            seq_numbers = sorted([ts.get("sequence_number") for ts in ts_list])
            if len(seq_numbers) > 0:
                assert seq_numbers[0] == 1, \
                    f"OS {os_id} sequence should start from 1, but starts from {seq_numbers[0]}"
                # Check for consecutive numbers
                for i, seq in enumerate(seq_numbers):
                    expected = i + 1
                    assert seq == expected, \
                        f"OS {os_id} sequence should be consecutive: expected {expected}, got {seq}"
        
        print(f"PASS: All OS groups have consecutive sequence_numbers starting from 1")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
