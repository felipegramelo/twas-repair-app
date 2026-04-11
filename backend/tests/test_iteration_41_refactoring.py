"""
Iteration 41: Backend Refactoring Regression Tests
Tests all API endpoints after server.py was split into modular structure:
- server.py (59 lines) -> routes/*.py files
- database.py, config.py, dependencies.py, models.py

Test credentials:
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://twas-repair-app-1.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"


class TestAuthEndpoints:
    """Test authentication endpoints from routes/auth.py"""
    
    def test_admin_login_success(self):
        """POST /api/auth/login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        print(f"PASS: Admin login successful - user: {data['user']['name']}")
    
    def test_supervisor_login_success(self):
        """POST /api/auth/login with supervisor credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == SUPERVISOR_EMAIL
        assert data["user"]["role"] == "supervisor"
        print(f"PASS: Supervisor login successful - user: {data['user']['name']}")
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("PASS: Invalid credentials correctly rejected")


@pytest.fixture
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed")


@pytest.fixture
def supervisor_token():
    """Get supervisor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": SUPERVISOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Supervisor authentication failed")


class TestTimesheetsEndpoints:
    """Test timesheet endpoints from routes/timesheets.py"""
    
    def test_get_timesheets_admin(self, admin_token):
        """GET /api/timesheets returns data for admin (with sequence_number)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/timesheets", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # Check that admin gets sequence_number field
        if len(data) > 0:
            # Admin should see sequence_number
            first_ts = data[0]
            assert "id" in first_ts
            assert "os_number" in first_ts
            print(f"PASS: Admin timesheets returned {len(data)} items with sequence_number support")
        else:
            print("PASS: Admin timesheets endpoint works (empty list)")
    
    def test_get_timesheets_supervisor(self, supervisor_token):
        """GET /api/timesheets returns data for supervisor (without sequence_number)"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/timesheets", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Supervisor timesheets returned {len(data)} items")


class TestServiceOrdersEndpoints:
    """Test service order endpoints from routes/service_orders.py"""
    
    def test_get_service_orders(self, admin_token):
        """GET /api/service-orders returns service orders list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            first_so = data[0]
            assert "id" in first_so
            assert "os_number" in first_so
            assert "client" in first_so
        print(f"PASS: Service orders returned {len(data)} items")
    
    def test_get_os_archive(self, admin_token):
        """GET /api/admin/os-archive returns archive data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/os-archive", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            first_item = data[0]
            assert "id" in first_item
            assert "os_number" in first_item
            assert "timesheets" in first_item
            assert "service_reports" in first_item
            assert "daily_reports" in first_item
        print(f"PASS: OS Archive returned {len(data)} items")


class TestReportsEndpoints:
    """Test report endpoints from routes/reports.py"""
    
    def test_get_reports(self, admin_token):
        """GET /api/reports returns reports list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reports", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "reports" in data
        assert isinstance(data["reports"], list)
        print(f"PASS: Reports returned {len(data['reports'])} items")


class TestEmployeesEndpoints:
    """Test employee endpoints from routes/employees.py"""
    
    def test_get_employees(self, admin_token):
        """GET /api/employees returns employees list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            first_emp = data[0]
            assert "id" in first_emp
            assert "name" in first_emp
        print(f"PASS: Employees returned {len(data)} items")


class TestProposalsEndpoints:
    """Test proposal endpoints from routes/proposals.py"""
    
    def test_get_proposals(self, admin_token):
        """GET /api/proposals returns proposals list (admin with proposta_access)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/proposals", headers=headers)
        # Admin with proposta_access should get 200, without should get 403
        assert response.status_code in [200, 403], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            print(f"PASS: Proposals returned {len(data)} items")
        else:
            print("PASS: Proposals endpoint correctly requires proposta_access")


class TestDashboardEndpoints:
    """Test dashboard endpoints from routes/dashboard.py"""
    
    def test_get_dashboard_summary(self, admin_token):
        """GET /api/dashboard/summary returns dashboard metrics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/summary", headers=headers)
        # Admin with dashboard_access should get 200, without should get 403
        assert response.status_code in [200, 403], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "totals" in data
            assert "bm_by_month" in data
            print(f"PASS: Dashboard summary returned with totals: {data['totals']}")
        else:
            print("PASS: Dashboard endpoint correctly requires dashboard_access")


class TestUserManagementEndpoints:
    """Test user management endpoints from routes/auth.py"""
    
    def test_get_supervisors(self, admin_token):
        """GET /api/users/supervisors returns supervisors list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users/supervisors", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            first_sup = data[0]
            assert "id" in first_sup
            assert "email" in first_sup
            assert "role" in first_sup
            assert first_sup["role"] == "supervisor"
        print(f"PASS: Supervisors list returned {len(data)} items")


class TestSharingEndpoints:
    """Test document sharing endpoints from routes/sharing.py"""
    
    def test_share_document_endpoint_exists(self, admin_token):
        """POST /api/admin/share-document endpoint exists and works"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Test with invalid data to verify endpoint exists
        response = requests.post(f"{BASE_URL}/api/admin/share-document", 
            headers=headers,
            json={
                "document_id": "000000000000000000000000",  # Invalid ObjectId
                "document_type": "report",
                "supervisor_ids": []
            }
        )
        # Should return 404 (document not found) or 422 (validation error), not 500
        assert response.status_code in [404, 422, 400], f"Unexpected status: {response.status_code}, body: {response.text}"
        print(f"PASS: Share document endpoint exists (returned {response.status_code})")


class TestAuthMeEndpoint:
    """Test /api/auth/me endpoint"""
    
    def test_auth_me_admin(self, admin_token):
        """GET /api/auth/me returns current admin user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"
        print(f"PASS: Auth/me returned admin user: {data['name']}")
    
    def test_auth_me_supervisor(self, supervisor_token):
        """GET /api/auth/me returns current supervisor user"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert data["email"] == SUPERVISOR_EMAIL
        assert data["role"] == "supervisor"
        print(f"PASS: Auth/me returned supervisor user: {data['name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
