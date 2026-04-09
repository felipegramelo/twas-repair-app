"""
Iteration 38: Testing Document Sharing and Password Management Features
- POST /api/admin/share-document
- POST /api/admin/unshare-document
- GET /api/admin/document-shares/{type}/{id}
- PUT /api/admin/reset-password/{user_id}
- PUT /api/auth/change-password (for supervisor)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests for admin and supervisor"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data.get("user", {}).get("role") == "admin"
        return data["access_token"]
    
    def test_supervisor_login(self):
        """Test supervisor login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data.get("user", {}).get("role") == "supervisor"
        return data["access_token"]


class TestDocumentSharing:
    """Test document sharing endpoints (Admin only)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def supervisors_list(self, admin_token):
        """Get list of supervisors"""
        response = requests.get(
            f"{BASE_URL}/api/users/supervisors",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        return response.json()
    
    @pytest.fixture
    def sample_report(self, admin_token):
        """Get a sample report for testing"""
        response = requests.get(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        # API returns {"reports": [...]}
        reports = data.get("reports", []) if isinstance(data, dict) else data
        if reports and len(reports) > 0:
            return reports[0]
        return None
    
    @pytest.fixture
    def sample_timesheet(self, admin_token):
        """Get a sample timesheet for testing"""
        response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        timesheets = response.json()
        if timesheets:
            return timesheets[0]
        return None
    
    def test_share_document_report(self, admin_token, supervisors_list, sample_report):
        """Test sharing a report with supervisors"""
        if not sample_report:
            pytest.skip("No reports available for testing")
        if len(supervisors_list) < 1:
            pytest.skip("No supervisors available for testing")
        
        supervisor_id = supervisors_list[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/admin/share-document",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "document_id": sample_report["id"],
                "document_type": "report",
                "supervisor_ids": [supervisor_id]
            }
        )
        assert response.status_code == 200, f"Share document failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "compartilhado" in data.get("message", "").lower() or "sucesso" in data.get("message", "").lower()
    
    def test_share_document_timesheet(self, admin_token, supervisors_list, sample_timesheet):
        """Test sharing a timesheet with supervisors"""
        if not sample_timesheet:
            pytest.skip("No timesheets available for testing")
        if len(supervisors_list) < 1:
            pytest.skip("No supervisors available for testing")
        
        supervisor_id = supervisors_list[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/admin/share-document",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "document_id": sample_timesheet["id"],
                "document_type": "timesheet",
                "supervisor_ids": [supervisor_id]
            }
        )
        assert response.status_code == 200, f"Share timesheet failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
    
    def test_get_document_shares_report(self, admin_token, sample_report):
        """Test getting shares for a report"""
        if not sample_report:
            pytest.skip("No reports available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/document-shares/report/{sample_report['id']}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get document shares failed: {response.text}"
        data = response.json()
        assert "shared_with" in data
        assert isinstance(data["shared_with"], list)
    
    def test_get_document_shares_timesheet(self, admin_token, sample_timesheet):
        """Test getting shares for a timesheet"""
        if not sample_timesheet:
            pytest.skip("No timesheets available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/document-shares/timesheet/{sample_timesheet['id']}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get timesheet shares failed: {response.text}"
        data = response.json()
        assert "shared_with" in data
        assert isinstance(data["shared_with"], list)
    
    def test_unshare_document_report(self, admin_token, supervisors_list, sample_report):
        """Test unsharing a report"""
        if not sample_report:
            pytest.skip("No reports available for testing")
        if len(supervisors_list) < 1:
            pytest.skip("No supervisors available for testing")
        
        supervisor_id = supervisors_list[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/admin/unshare-document",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "document_id": sample_report["id"],
                "document_type": "report",
                "supervisor_ids": [supervisor_id]
            }
        )
        assert response.status_code == 200, f"Unshare document failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
    
    def test_share_document_forbidden_for_supervisor(self, supervisor_token, sample_report):
        """Test that supervisors cannot share documents"""
        if not sample_report:
            pytest.skip("No reports available for testing")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/share-document",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            json={
                "document_id": sample_report["id"],
                "document_type": "report",
                "supervisor_ids": ["some-id"]
            }
        )
        assert response.status_code == 403, f"Expected 403 for supervisor, got {response.status_code}"
    
    def test_get_shares_forbidden_for_supervisor(self, supervisor_token, sample_report):
        """Test that supervisors cannot get document shares"""
        if not sample_report:
            pytest.skip("No reports available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/document-shares/report/{sample_report['id']}",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for supervisor, got {response.status_code}"
    
    def test_share_nonexistent_document(self, admin_token):
        """Test sharing a non-existent document"""
        response = requests.post(
            f"{BASE_URL}/api/admin/share-document",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "document_id": "000000000000000000000000",
                "document_type": "report",
                "supervisor_ids": ["some-id"]
            }
        )
        assert response.status_code == 404, f"Expected 404 for non-existent document, got {response.status_code}"


class TestPasswordManagement:
    """Test password management endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def test_supervisor(self, admin_token):
        """Create a test supervisor for password reset testing"""
        # First try to find existing test supervisor
        response = requests.get(
            f"{BASE_URL}/api/users/supervisors",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        supervisors = response.json()
        for sup in supervisors:
            if sup["email"] == "TEST_pwdreset@twasrepair.com":
                return sup
        
        # Create new test supervisor
        response = requests.post(
            f"{BASE_URL}/api/users/supervisors",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "TEST_pwdreset@twasrepair.com",
                "name": "TEST Password Reset User",
                "password": "testpass123"
            }
        )
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 400 and "já cadastrado" in response.text:
            # Already exists, find it
            response = requests.get(
                f"{BASE_URL}/api/users/supervisors",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            for sup in response.json():
                if sup["email"] == "TEST_pwdreset@twasrepair.com":
                    return sup
        return None
    
    def test_admin_reset_supervisor_password(self, admin_token, test_supervisor):
        """Test admin resetting a supervisor's password"""
        if not test_supervisor:
            pytest.skip("Could not create test supervisor")
        
        response = requests.put(
            f"{BASE_URL}/api/admin/reset-password/{test_supervisor['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"new_password": "newpass123"}
        )
        assert response.status_code == 200, f"Reset password failed: {response.text}"
        data = response.json()
        assert "sucesso" in data.get("message", "").lower() or "redefinida" in data.get("message", "").lower()
        
        # Verify new password works
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "TEST_pwdreset@twasrepair.com",
            "password": "newpass123"
        })
        assert login_response.status_code == 200, "Login with new password failed"
        
        # Reset back to original password for cleanup
        requests.put(
            f"{BASE_URL}/api/admin/reset-password/{test_supervisor['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"new_password": "testpass123"}
        )
    
    def test_admin_reset_password_short_password(self, admin_token, test_supervisor):
        """Test admin reset with too short password"""
        if not test_supervisor:
            pytest.skip("Could not create test supervisor")
        
        response = requests.put(
            f"{BASE_URL}/api/admin/reset-password/{test_supervisor['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"new_password": "12345"}  # Too short
        )
        assert response.status_code == 400, f"Expected 400 for short password, got {response.status_code}"
    
    def test_admin_reset_password_nonexistent_user(self, admin_token):
        """Test admin reset for non-existent user"""
        response = requests.put(
            f"{BASE_URL}/api/admin/reset-password/000000000000000000000000",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"new_password": "newpass123"}
        )
        assert response.status_code == 404, f"Expected 404 for non-existent user, got {response.status_code}"
    
    def test_supervisor_cannot_reset_others_password(self, supervisor_token, test_supervisor):
        """Test that supervisor cannot reset another user's password"""
        if not test_supervisor:
            pytest.skip("Could not create test supervisor")
        
        response = requests.put(
            f"{BASE_URL}/api/admin/reset-password/{test_supervisor['id']}",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            json={"new_password": "newpass123"}
        )
        # Should be 403 (forbidden) or 401 (unauthorized)
        assert response.status_code in [401, 403], f"Expected 401/403 for supervisor, got {response.status_code}"
    
    def test_change_own_password(self, admin_token):
        """Test changing own password (admin)"""
        # Change password
        response = requests.put(
            f"{BASE_URL}/api/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "current_password": "admin123",
                "new_password": "admin123new"
            }
        )
        assert response.status_code == 200, f"Change password failed: {response.text}"
        
        # Verify new password works
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123new"
        })
        assert login_response.status_code == 200, "Login with new password failed"
        
        # Change back to original
        new_token = login_response.json()["access_token"]
        requests.put(
            f"{BASE_URL}/api/auth/change-password",
            headers={"Authorization": f"Bearer {new_token}"},
            json={
                "current_password": "admin123new",
                "new_password": "admin123"
            }
        )
    
    def test_change_password_wrong_current(self, admin_token):
        """Test change password with wrong current password"""
        response = requests.put(
            f"{BASE_URL}/api/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "current_password": "wrongpassword",
                "new_password": "newpass123"
            }
        )
        assert response.status_code in [400, 401], f"Expected 400/401 for wrong password, got {response.status_code}"
    
    def test_change_password_short_new(self, admin_token):
        """Test change password with too short new password"""
        response = requests.put(
            f"{BASE_URL}/api/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "current_password": "admin123",
                "new_password": "12345"  # Too short
            }
        )
        assert response.status_code == 400, f"Expected 400 for short password, got {response.status_code}"


class TestSupervisorSeesSharedDocuments:
    """Test that supervisor can see shared documents"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def supervisor_data(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    def test_supervisor_sees_own_and_shared_reports(self, admin_token, supervisor_data):
        """Test that supervisor can see their own reports and shared reports"""
        response = requests.get(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {supervisor_data['token']}"}
        )
        assert response.status_code == 200, f"Get reports failed: {response.text}"
        data = response.json()
        # API returns {"reports": [...]}
        reports = data.get("reports", []) if isinstance(data, dict) else data
        # Supervisor should see reports (either own or shared)
        assert isinstance(reports, list)
    
    def test_supervisor_sees_own_and_shared_timesheets(self, admin_token, supervisor_data):
        """Test that supervisor can see their own timesheets and shared timesheets"""
        response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {supervisor_data['token']}"}
        )
        assert response.status_code == 200, f"Get timesheets failed: {response.text}"
        timesheets = response.json()
        assert isinstance(timesheets, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
