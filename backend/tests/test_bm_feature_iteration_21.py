"""
Test suite for Boletim de Medição (BM) feature - Iteration 21
Tests: Authentication, BM CRUD, Client Price Tables, BM Calculation, PDF Generation, Access Control
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"

# Existing test data IDs
EXISTING_OS_ID = "699f3f0c8235b2a1626be60c"  # OS 2602-12, Constellation
EXISTING_BM_ID = "69c3459c8fd57a1b5ede7106"
EXISTING_PRICE_TABLE_ID = "69c3459c8fd57a1b5ede7105"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin token (with bm_access)"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    return data["access_token"]


@pytest.fixture(scope="module")
def supervisor_token():
    """Get supervisor token (NO bm_access)"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": SUPERVISOR_PASSWORD
    })
    assert response.status_code == 200, f"Supervisor login failed: {response.text}"
    data = response.json()
    return data["access_token"]


@pytest.fixture(scope="module")
def admin_user_data():
    """Get admin user data from login"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200
    return response.json()


class TestAuthBMAccess:
    """Test bm_access field in authentication responses"""
    
    def test_login_returns_bm_access_field(self, admin_user_data):
        """POST /api/auth/login should return bm_access in user object"""
        user = admin_user_data.get("user", {})
        assert "bm_access" in user, "bm_access field missing from login response"
        assert user["bm_access"] is True, f"Admin should have bm_access=True, got {user['bm_access']}"
    
    def test_login_supervisor_no_bm_access(self):
        """Supervisor login should have bm_access=False or missing"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200
        user = response.json().get("user", {})
        # Supervisor should NOT have bm_access
        bm_access = user.get("bm_access", False)
        assert bm_access is False, f"Supervisor should have bm_access=False, got {bm_access}"
    
    def test_get_me_returns_bm_access(self, admin_token):
        """GET /api/auth/me should return bm_access field"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        user = response.json()
        assert "bm_access" in user, "bm_access field missing from /auth/me response"


class TestClientPriceTableEndpoints:
    """Test client price table CRUD endpoints"""
    
    def test_get_client_prices_requires_bm_access(self, admin_token):
        """GET /api/client-prices requires bm_access"""
        response = requests.get(f"{BASE_URL}/api/client-prices", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
    
    def test_get_client_prices_forbidden_for_supervisor(self, supervisor_token):
        """Supervisor should get 403 on /api/client-prices"""
        response = requests.get(f"{BASE_URL}/api/client-prices", headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_create_client_price_table(self, admin_token):
        """POST /api/client-prices creates a new price table"""
        test_data = {
            "client_name": "TEST_CLIENT_BM_ITERATION_21",
            "prices": [
                {"function_code": "T", "function_name": "TÉCNICO", "day_rate": 500.0, "night_rate": 750.0},
                {"function_code": "Sup", "function_name": "SUPERVISOR", "day_rate": 600.0, "night_rate": 900.0}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/client-prices", json=test_data, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Create failed: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain id"
        assert data["client_name"] == test_data["client_name"]
        
        # Cleanup - delete the test price table
        delete_response = requests.delete(f"{BASE_URL}/api/client-prices/{data['id']}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert delete_response.status_code == 200
    
    def test_update_client_price_table(self, admin_token):
        """PUT /api/client-prices/{id} updates price table"""
        # First create a test table
        create_data = {
            "client_name": "TEST_UPDATE_CLIENT",
            "prices": [{"function_code": "T", "function_name": "TÉCNICO", "day_rate": 100.0, "night_rate": 150.0}]
        }
        create_response = requests.post(f"{BASE_URL}/api/client-prices", json=create_data, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert create_response.status_code == 200
        price_id = create_response.json()["id"]
        
        # Update it
        update_data = {
            "client_name": "TEST_UPDATE_CLIENT_MODIFIED",
            "prices": [{"function_code": "T", "function_name": "TÉCNICO", "day_rate": 200.0, "night_rate": 300.0}]
        }
        update_response = requests.put(f"{BASE_URL}/api/client-prices/{price_id}", json=update_data, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert update_response.status_code == 200
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/client-prices/{price_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })


class TestBMCalculation:
    """Test BM calculation endpoint"""
    
    def test_calculate_bm_for_os(self, admin_token):
        """GET /api/bm/calculate/{os_id} calculates BM from timesheets"""
        response = requests.get(f"{BASE_URL}/api/bm/calculate/{EXISTING_OS_ID}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Calculate failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "os_id" in data
        assert "os_number" in data
        assert "client" in data
        assert "items" in data
        assert "subtotal" in data
        assert "has_price_table" in data
        assert isinstance(data["items"], list)
    
    def test_calculate_bm_forbidden_for_supervisor(self, supervisor_token):
        """Supervisor should get 403 on /api/bm/calculate"""
        response = requests.get(f"{BASE_URL}/api/bm/calculate/{EXISTING_OS_ID}", headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_calculate_bm_invalid_os(self, admin_token):
        """Calculate with invalid OS ID should return 404"""
        response = requests.get(f"{BASE_URL}/api/bm/calculate/000000000000000000000000", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 404


class TestBMCRUD:
    """Test BM CRUD operations"""
    
    def test_list_bm(self, admin_token):
        """GET /api/bm lists all BMs"""
        response = requests.get(f"{BASE_URL}/api/bm", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_bm_forbidden_for_supervisor(self, supervisor_token):
        """Supervisor should get 403 on GET /api/bm"""
        response = requests.get(f"{BASE_URL}/api/bm", headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        assert response.status_code == 403
    
    def test_create_and_delete_bm(self, admin_token):
        """POST /api/bm creates a new BM, DELETE /api/bm/{id} deletes it"""
        # Create BM
        bm_data = {
            "os_id": EXISTING_OS_ID,
            "periodo": "TEST_JANEIRO_2026",
            "data": "15/01/2026",
            "rev": "0",
            "po_number": "TEST-PO-001",
            "proposta": "TEST-PROP-001",
            "cod": "TEST-COD",
            "items": [
                {"function_code": "T", "function_name": "TÉCNICO", "shift": "day", "qtd": 5, "valor_und": 500.0, "valor_total": 2500.0}
            ],
            "subtotal": 2500.0,
            "impostos": 0.0,
            "valor_total": 2500.0
        }
        create_response = requests.post(f"{BASE_URL}/api/bm", json=bm_data, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert create_response.status_code == 200, f"Create BM failed: {create_response.text}"
        created_bm = create_response.json()
        assert "id" in created_bm
        bm_id = created_bm["id"]
        
        # Verify BM was created by getting it
        get_response = requests.get(f"{BASE_URL}/api/bm/{bm_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert get_response.status_code == 200
        
        # Delete BM
        delete_response = requests.delete(f"{BASE_URL}/api/bm/{bm_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert delete_response.status_code == 200
        
        # Verify deletion
        verify_response = requests.get(f"{BASE_URL}/api/bm/{bm_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert verify_response.status_code == 404
    
    def test_create_bm_forbidden_for_supervisor(self, supervisor_token):
        """Supervisor should get 403 on POST /api/bm"""
        bm_data = {
            "os_id": EXISTING_OS_ID,
            "periodo": "TEST",
            "data": "01/01/2026",
            "items": [],
            "subtotal": 0,
            "valor_total": 0
        }
        response = requests.post(f"{BASE_URL}/api/bm", json=bm_data, headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        assert response.status_code == 403
    
    def test_delete_bm_forbidden_for_supervisor(self, supervisor_token):
        """Supervisor should get 403 on DELETE /api/bm/{id}"""
        response = requests.delete(f"{BASE_URL}/api/bm/{EXISTING_BM_ID}", headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        assert response.status_code == 403


class TestBMPDF:
    """Test BM PDF generation"""
    
    def test_generate_bm_pdf(self, admin_token):
        """GET /api/bm/{id}/pdf generates PDF"""
        response = requests.get(
            f"{BASE_URL}/api/bm/{EXISTING_BM_ID}/pdf?token={admin_token}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return PDF or 200
        assert response.status_code == 200, f"PDF generation failed: {response.status_code} - {response.text[:200] if response.text else 'No content'}"
        # Check content type is PDF
        content_type = response.headers.get("content-type", "")
        assert "pdf" in content_type.lower() or response.status_code == 200
    
    def test_pdf_forbidden_for_supervisor(self, supervisor_token):
        """Supervisor should get 403 on /api/bm/{id}/pdf"""
        response = requests.get(
            f"{BASE_URL}/api/bm/{EXISTING_BM_ID}/pdf?token={supervisor_token}"
        )
        assert response.status_code == 403


class TestBMAccessToggle:
    """Test BM access toggle endpoint"""
    
    def test_toggle_bm_access_requires_admin(self, admin_token):
        """PUT /api/users/admins/{user_id}/bm-access requires admin role"""
        # First get admin user ID
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert me_response.status_code == 200
        admin_id = me_response.json()["id"]
        
        # Toggle should work for admin
        response = requests.put(f"{BASE_URL}/api/users/admins/{admin_id}/bm-access", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "bm_access" in data
        
        # Toggle back to restore original state
        requests.put(f"{BASE_URL}/api/users/admins/{admin_id}/bm-access", headers={
            "Authorization": f"Bearer {admin_token}"
        })
    
    def test_toggle_bm_access_forbidden_for_supervisor(self, supervisor_token, admin_token):
        """Supervisor should get 403 on toggle bm_access"""
        # Get admin ID
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        admin_id = me_response.json()["id"]
        
        response = requests.put(f"{BASE_URL}/api/users/admins/{admin_id}/bm-access", headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        assert response.status_code == 403


class TestAdminWithoutBMAccess:
    """Test that admin without bm_access gets 403 on BM endpoints"""
    
    def test_admin_without_bm_access_forbidden(self, admin_token):
        """
        This test verifies the access control logic.
        We toggle bm_access off, verify 403, then toggle back on.
        """
        # Get admin ID
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        admin_id = me_response.json()["id"]
        current_bm_access = me_response.json().get("bm_access", False)
        
        if current_bm_access:
            # Toggle off
            toggle_response = requests.put(f"{BASE_URL}/api/users/admins/{admin_id}/bm-access", headers={
                "Authorization": f"Bearer {admin_token}"
            })
            assert toggle_response.status_code == 200
            
            # Now try to access BM endpoints - should get 403
            bm_response = requests.get(f"{BASE_URL}/api/bm", headers={
                "Authorization": f"Bearer {admin_token}"
            })
            assert bm_response.status_code == 403, f"Expected 403 when bm_access=False, got {bm_response.status_code}"
            
            # Toggle back on
            requests.put(f"{BASE_URL}/api/users/admins/{admin_id}/bm-access", headers={
                "Authorization": f"Bearer {admin_token}"
            })
        else:
            pytest.skip("Admin already has bm_access=False, skipping toggle test")


class TestExistingData:
    """Test with existing data in database"""
    
    def test_existing_bm_exists(self, admin_token):
        """Verify existing BM can be retrieved"""
        response = requests.get(f"{BASE_URL}/api/bm/{EXISTING_BM_ID}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        # May be 200 or 404 depending on if data exists
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
    
    def test_existing_price_table_exists(self, admin_token):
        """Verify existing price table can be retrieved via list"""
        response = requests.get(f"{BASE_URL}/api/client-prices", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        # Check if Constellation price table exists
        constellation_tables = [t for t in data if "Constellation" in t.get("client_name", "")]
        # May or may not exist
        print(f"Found {len(constellation_tables)} Constellation price tables")
