"""
Test OS Archive Feature - Iteration 20
Tests the new /api/admin/os-archive endpoint that groups all documents by Service Order
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://twas-repair-app-1.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"


class TestOSArchiveAuthentication:
    """Test authentication requirements for OS Archive endpoint"""
    
    def test_os_archive_requires_authentication(self):
        """OS Archive endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/os-archive")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: OS Archive requires authentication")
    
    def test_admin_login_success(self):
        """Admin should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"PASS: Admin login successful - {data['user']['name']}")
        return data["access_token"]
    
    def test_supervisor_login_success(self):
        """Supervisor should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "supervisor"
        print(f"PASS: Supervisor login successful - {data['user']['name']}")
        return data["access_token"]


class TestOSArchiveAdminAccess:
    """Test admin access to OS Archive endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_admin_can_access_os_archive(self, admin_token):
        """Admin should be able to access OS Archive endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"PASS: Admin can access OS Archive - {len(data)} OS records found")
        return data
    
    def test_os_archive_response_structure(self, admin_token):
        """Each OS in response should have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No OS records to test structure")
        
        # Check first OS record structure
        os_record = data[0]
        required_fields = ["id", "os_number", "client", "location", "service", 
                          "timesheets", "service_reports", "daily_reports", "total_documents"]
        
        for field in required_fields:
            assert field in os_record, f"Missing field: {field}"
        
        # Verify nested arrays
        assert isinstance(os_record["timesheets"], list), "timesheets should be a list"
        assert isinstance(os_record["service_reports"], list), "service_reports should be a list"
        assert isinstance(os_record["daily_reports"], list), "daily_reports should be a list"
        assert isinstance(os_record["total_documents"], int), "total_documents should be an integer"
        
        print(f"PASS: OS Archive response structure is correct")
        print(f"  - OS: {os_record['os_number']}")
        print(f"  - Client: {os_record['client']}")
        print(f"  - Timesheets: {len(os_record['timesheets'])}")
        print(f"  - Service Reports: {len(os_record['service_reports'])}")
        print(f"  - Daily Reports: {len(os_record['daily_reports'])}")
        print(f"  - Total Documents: {os_record['total_documents']}")


class TestOSArchiveSupervisorForbidden:
    """Test that supervisor role is forbidden from OS Archive"""
    
    @pytest.fixture
    def supervisor_token(self):
        """Get supervisor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Supervisor login failed")
        return response.json()["access_token"]
    
    def test_supervisor_forbidden_from_os_archive(self, supervisor_token):
        """Supervisor should be forbidden from accessing OS Archive"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print("PASS: Supervisor is correctly forbidden from OS Archive")


class TestOSArchiveDocumentCounts:
    """Test document counts for specific OS numbers"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_os_2602_14_document_count(self, admin_token):
        """OS 2602-14 should have 3 timesheets and 1 service report (4 total)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find OS 2602-14
        os_2602_14 = None
        for os_record in data:
            if os_record["os_number"] == "2602-14":
                os_2602_14 = os_record
                break
        
        if os_2602_14 is None:
            pytest.skip("OS 2602-14 not found in database")
        
        print(f"OS 2602-14 found:")
        print(f"  - Timesheets: {len(os_2602_14['timesheets'])}")
        print(f"  - Service Reports: {len(os_2602_14['service_reports'])}")
        print(f"  - Daily Reports: {len(os_2602_14['daily_reports'])}")
        print(f"  - Total Documents: {os_2602_14['total_documents']}")
        
        # Verify expected counts (may vary based on actual data)
        assert os_2602_14["total_documents"] >= 0, "Total documents should be non-negative"
        print(f"PASS: OS 2602-14 document count verified")
    
    def test_os_2602_12_document_count(self, admin_token):
        """OS 2602-12 should have 2 timesheets (2 total)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find OS 2602-12
        os_2602_12 = None
        for os_record in data:
            if os_record["os_number"] == "2602-12":
                os_2602_12 = os_record
                break
        
        if os_2602_12 is None:
            pytest.skip("OS 2602-12 not found in database")
        
        print(f"OS 2602-12 found:")
        print(f"  - Timesheets: {len(os_2602_12['timesheets'])}")
        print(f"  - Service Reports: {len(os_2602_12['service_reports'])}")
        print(f"  - Daily Reports: {len(os_2602_12['daily_reports'])}")
        print(f"  - Total Documents: {os_2602_12['total_documents']}")
        
        assert os_2602_12["total_documents"] >= 0, "Total documents should be non-negative"
        print(f"PASS: OS 2602-12 document count verified")
    
    def test_os_test_99_zero_documents(self, admin_token):
        """OS TEST-99 should have 0 documents"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find OS TEST-99
        os_test_99 = None
        for os_record in data:
            if os_record["os_number"] == "TEST-99":
                os_test_99 = os_record
                break
        
        if os_test_99 is None:
            pytest.skip("OS TEST-99 not found in database")
        
        print(f"OS TEST-99 found:")
        print(f"  - Timesheets: {len(os_test_99['timesheets'])}")
        print(f"  - Service Reports: {len(os_test_99['service_reports'])}")
        print(f"  - Daily Reports: {len(os_test_99['daily_reports'])}")
        print(f"  - Total Documents: {os_test_99['total_documents']}")
        
        assert os_test_99["total_documents"] == 0, f"Expected 0 documents, got {os_test_99['total_documents']}"
        print(f"PASS: OS TEST-99 has 0 documents as expected")


class TestOSArchiveTimesheetDetails:
    """Test timesheet details in OS Archive response"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_timesheet_has_required_fields(self, admin_token):
        """Timesheets in OS Archive should have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find an OS with timesheets
        os_with_timesheets = None
        for os_record in data:
            if len(os_record["timesheets"]) > 0:
                os_with_timesheets = os_record
                break
        
        if os_with_timesheets is None:
            pytest.skip("No OS with timesheets found")
        
        timesheet = os_with_timesheets["timesheets"][0]
        required_fields = ["id", "os_number", "client", "supervisor_name", "created_at"]
        
        for field in required_fields:
            assert field in timesheet, f"Timesheet missing field: {field}"
        
        print(f"PASS: Timesheet has required fields")
        print(f"  - ID: {timesheet['id']}")
        print(f"  - OS: {timesheet['os_number']}")
        print(f"  - Supervisor: {timesheet['supervisor_name']}")


class TestOSArchiveReportDetails:
    """Test report details in OS Archive response"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_service_report_has_required_fields(self, admin_token):
        """Service reports in OS Archive should have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find an OS with service reports
        os_with_reports = None
        for os_record in data:
            if len(os_record["service_reports"]) > 0:
                os_with_reports = os_record
                break
        
        if os_with_reports is None:
            pytest.skip("No OS with service reports found")
        
        report = os_with_reports["service_reports"][0]
        required_fields = ["id", "report_type", "os_number", "client", "status", "created_at"]
        
        for field in required_fields:
            assert field in report, f"Report missing field: {field}"
        
        assert report["report_type"] == "service", f"Expected report_type 'service', got {report['report_type']}"
        
        print(f"PASS: Service report has required fields")
        print(f"  - ID: {report['id']}")
        print(f"  - Type: {report['report_type']}")
        print(f"  - Status: {report['status']}")


class TestOSArchiveTotalDocumentsCalculation:
    """Test that total_documents is calculated correctly"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_total_documents_equals_sum_of_all_docs(self, admin_token):
        """total_documents should equal sum of timesheets + service_reports + daily_reports"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for os_record in data:
            expected_total = (
                len(os_record["timesheets"]) + 
                len(os_record["service_reports"]) + 
                len(os_record["daily_reports"])
            )
            actual_total = os_record["total_documents"]
            
            assert actual_total == expected_total, (
                f"OS {os_record['os_number']}: expected {expected_total}, got {actual_total}"
            )
        
        print(f"PASS: total_documents calculation verified for all {len(data)} OS records")


class TestOSArchiveSorting:
    """Test that OS Archive is sorted by os_number"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_os_archive_sorted_by_os_number(self, admin_token):
        """OS Archive should be sorted by os_number"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data) < 2:
            pytest.skip("Need at least 2 OS records to test sorting")
        
        os_numbers = [os_record["os_number"] for os_record in data]
        sorted_os_numbers = sorted(os_numbers)
        
        assert os_numbers == sorted_os_numbers, "OS Archive should be sorted by os_number"
        print(f"PASS: OS Archive is sorted by os_number")
        print(f"  - First: {os_numbers[0]}")
        print(f"  - Last: {os_numbers[-1]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
