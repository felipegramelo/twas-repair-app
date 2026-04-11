"""
Tests for Admin Features:
- Change Password endpoint
- Admin Management CRUD endpoints (GET all, CREATE, UPDATE, DELETE admins)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://twas-repair-app-1.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"

class TestChangePassword:
    """Tests for PUT /api/auth/change-password endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Could not authenticate: {response.status_code}")
        return response.json()["access_token"]
    
    def test_change_password_wrong_current(self, auth_token):
        """Test changing password with wrong current password - should return 400"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.put(f"{BASE_URL}/api/auth/change-password", 
            json={
                "current_password": "wrongpassword123",
                "new_password": "newpassword123"
            },
            headers=headers
        )
        assert response.status_code == 400
        assert "Senha atual incorreta" in response.json().get("detail", "")
        print("PASSED: Wrong current password returns 400 with correct message")
    
    def test_change_password_short_new_password(self, auth_token):
        """Test changing password with new password too short - should return 400"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.put(f"{BASE_URL}/api/auth/change-password", 
            json={
                "current_password": ADMIN_PASSWORD,
                "new_password": "12345"  # Only 5 chars
            },
            headers=headers
        )
        assert response.status_code == 400
        assert "6 caracteres" in response.json().get("detail", "")
        print("PASSED: Short new password returns 400 with correct message")
    
    def test_change_password_success_and_revert(self, auth_token):
        """Test changing password successfully and reverting to original"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        new_password = "temporarypassword123"
        
        # Step 1: Change to new password
        response = requests.put(f"{BASE_URL}/api/auth/change-password", 
            json={
                "current_password": ADMIN_PASSWORD,
                "new_password": new_password
            },
            headers=headers
        )
        assert response.status_code == 200
        assert "sucesso" in response.json().get("message", "").lower()
        print("PASSED: Password changed successfully")
        
        # Step 2: Login with new password
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": new_password
        })
        assert login_response.status_code == 200
        new_token = login_response.json()["access_token"]
        print("PASSED: Can login with new password")
        
        # Step 3: Revert to original password
        revert_headers = {"Authorization": f"Bearer {new_token}"}
        revert_response = requests.put(f"{BASE_URL}/api/auth/change-password", 
            json={
                "current_password": new_password,
                "new_password": ADMIN_PASSWORD
            },
            headers=revert_headers
        )
        assert revert_response.status_code == 200
        print("PASSED: Password reverted to original")
        
        # Step 4: Verify login with original password works
        final_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert final_login.status_code == 200
        print("PASSED: Original password works after revert")
    
    def test_change_password_no_auth(self):
        """Test changing password without authentication - should return 401/403"""
        response = requests.put(f"{BASE_URL}/api/auth/change-password", 
            json={
                "current_password": ADMIN_PASSWORD,
                "new_password": "newpassword123"
            }
        )
        assert response.status_code in [401, 403]
        print("PASSED: No auth returns 401/403")


class TestAdminManagement:
    """Tests for Admin Management CRUD endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Could not authenticate: {response.status_code}")
        return response.json()["access_token"]
    
    @pytest.fixture
    def current_user_id(self, auth_token):
        """Get current user ID"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        if response.status_code != 200:
            pytest.skip("Could not get current user")
        return response.json()["id"]
    
    def test_get_all_admins(self, auth_token):
        """Test GET /api/users/admins - should return list of admins"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/users/admins", headers=headers)
        
        assert response.status_code == 200
        admins = response.json()
        assert isinstance(admins, list)
        assert len(admins) >= 1  # At least the current admin
        
        # Check structure
        admin = admins[0]
        assert "id" in admin
        assert "email" in admin
        assert "name" in admin
        assert "role" in admin
        assert admin["role"] == "admin"
        print(f"PASSED: GET admins returns {len(admins)} admin(s)")
    
    def test_create_update_delete_admin(self, auth_token):
        """Test full CRUD cycle for admin management"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # CREATE: Create new admin
        new_admin = {
            "email": "TEST_novoadmin@twasrepair.com",
            "name": "TEST Novo Admin",
            "password": "novoadmin123"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/users/admins", 
            json=new_admin, headers=headers)
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["email"] == new_admin["email"]
        assert created["name"] == new_admin["name"]
        assert created["role"] == "admin"
        admin_id = created["id"]
        print(f"PASSED: Created admin with id {admin_id}")
        
        # READ: Verify admin appears in list
        get_response = requests.get(f"{BASE_URL}/api/users/admins", headers=headers)
        assert get_response.status_code == 200
        admins = get_response.json()
        admin_ids = [a["id"] for a in admins]
        assert admin_id in admin_ids
        print("PASSED: New admin appears in GET list")
        
        # UPDATE: Update admin name
        update_data = {
            "email": "TEST_novoadmin@twasrepair.com",
            "name": "TEST Updated Admin Name"
        }
        update_response = requests.put(f"{BASE_URL}/api/users/admins/{admin_id}",
            json=update_data, headers=headers)
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == "TEST Updated Admin Name"
        print("PASSED: Admin name updated")
        
        # DELETE: Delete the admin
        delete_response = requests.delete(f"{BASE_URL}/api/users/admins/{admin_id}",
            headers=headers)
        assert delete_response.status_code == 200
        print("PASSED: Admin deleted")
        
        # VERIFY DELETE: Admin should not appear in list
        get_after_delete = requests.get(f"{BASE_URL}/api/users/admins", headers=headers)
        admins_after = get_after_delete.json()
        admin_ids_after = [a["id"] for a in admins_after]
        assert admin_id not in admin_ids_after
        print("PASSED: Deleted admin no longer in list")
    
    def test_cannot_delete_self(self, auth_token, current_user_id):
        """Test that admin cannot delete their own account"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.delete(f"{BASE_URL}/api/users/admins/{current_user_id}",
            headers=headers)
        assert response.status_code == 400
        assert "própria conta" in response.json().get("detail", "")
        print("PASSED: Cannot delete own account - returns 400")
    
    def test_create_admin_duplicate_email(self, auth_token):
        """Test creating admin with existing email - should fail"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.post(f"{BASE_URL}/api/users/admins", 
            json={
                "email": ADMIN_EMAIL,  # Already exists
                "name": "Duplicate Admin",
                "password": "somepassword123"
            },
            headers=headers
        )
        assert response.status_code == 400
        assert "já cadastrado" in response.json().get("detail", "").lower()
        print("PASSED: Duplicate email returns 400")
    
    def test_admins_no_auth(self):
        """Test accessing admin endpoints without authentication"""
        # GET without auth
        get_response = requests.get(f"{BASE_URL}/api/users/admins")
        assert get_response.status_code in [401, 403]
        print("PASSED: GET admins without auth returns 401/403")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
