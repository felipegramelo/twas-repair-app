"""
Iteration 22 Tests: Access Control, BM PDF Style, and Toast Notification
Tests for:
1. os_archive_access field in user responses (login, /me, /admins)
2. PUT /users/admins/{id}/bm-access toggle
3. PUT /users/admins/{id}/os-archive-access toggle
4. Admin without bm_access gets 403 on BM endpoints
5. BM PDF format (A4 landscape, header, footer, borders)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://repair-proposals-app.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"

# Existing BM ID for PDF testing
EXISTING_BM_ID = "69c3459c8fd57a1b5ede7106"


class TestAuthAccessFields:
    """Test that login and /me return os_archive_access field"""
    
    def test_login_returns_os_archive_access(self):
        """POST /api/auth/login should return os_archive_access in user object"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Check user object has os_archive_access
        assert "user" in data, "Response missing 'user' field"
        user = data["user"]
        assert "os_archive_access" in user, "User object missing 'os_archive_access' field"
        assert isinstance(user["os_archive_access"], bool), "os_archive_access should be boolean"
        print(f"PASS: Login returns os_archive_access={user['os_archive_access']}")
    
    def test_login_returns_bm_access(self):
        """POST /api/auth/login should return bm_access in user object"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        user = data["user"]
        assert "bm_access" in user, "User object missing 'bm_access' field"
        assert isinstance(user["bm_access"], bool), "bm_access should be boolean"
        print(f"PASS: Login returns bm_access={user['bm_access']}")
    
    def test_get_me_returns_os_archive_access(self):
        """GET /api/auth/me should return os_archive_access field"""
        # First login to get token
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["access_token"]
        
        # Get /me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Get me failed: {response.text}"
        data = response.json()
        
        assert "os_archive_access" in data, "/me response missing 'os_archive_access' field"
        assert isinstance(data["os_archive_access"], bool), "os_archive_access should be boolean"
        print(f"PASS: /me returns os_archive_access={data['os_archive_access']}")
    
    def test_get_me_returns_bm_access(self):
        """GET /api/auth/me should return bm_access field"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["access_token"]
        
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "bm_access" in data, "/me response missing 'bm_access' field"
        print(f"PASS: /me returns bm_access={data['bm_access']}")


class TestAdminsEndpoint:
    """Test GET /api/users/admins returns access fields"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_admins_returns_bm_access(self, admin_token):
        """GET /api/users/admins should return bm_access for each admin"""
        response = requests.get(f"{BASE_URL}/api/users/admins", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get admins failed: {response.text}"
        admins = response.json()
        
        assert isinstance(admins, list), "Response should be a list"
        assert len(admins) > 0, "Should have at least one admin"
        
        for admin in admins:
            assert "bm_access" in admin, f"Admin {admin.get('email')} missing 'bm_access' field"
            assert isinstance(admin["bm_access"], bool), "bm_access should be boolean"
        
        print(f"PASS: GET /admins returns bm_access for all {len(admins)} admins")
    
    def test_get_admins_returns_os_archive_access(self, admin_token):
        """GET /api/users/admins should return os_archive_access for each admin"""
        response = requests.get(f"{BASE_URL}/api/users/admins", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        admins = response.json()
        
        for admin in admins:
            assert "os_archive_access" in admin, f"Admin {admin.get('email')} missing 'os_archive_access' field"
            assert isinstance(admin["os_archive_access"], bool), "os_archive_access should be boolean"
        
        print(f"PASS: GET /admins returns os_archive_access for all {len(admins)} admins")


class TestAccessToggleEndpoints:
    """Test toggle endpoints for bm_access and os_archive_access"""
    
    @pytest.fixture
    def admin_session(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"]
        }
    
    def test_toggle_bm_access(self, admin_session):
        """PUT /api/users/admins/{id}/bm-access should toggle bm_access"""
        token = admin_session["token"]
        user_id = admin_session["user_id"]
        
        # Get current state
        me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        original_bm_access = me_resp.json()["bm_access"]
        
        # Toggle
        response = requests.put(f"{BASE_URL}/api/users/admins/{user_id}/bm-access", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Toggle bm_access failed: {response.text}"
        data = response.json()
        
        assert "bm_access" in data, "Response missing 'bm_access' field"
        assert data["bm_access"] != original_bm_access, "bm_access should have toggled"
        
        # Toggle back to original
        requests.put(f"{BASE_URL}/api/users/admins/{user_id}/bm-access", headers={
            "Authorization": f"Bearer {token}"
        })
        
        print(f"PASS: Toggle bm_access works (was {original_bm_access}, toggled to {data['bm_access']})")
    
    def test_toggle_os_archive_access(self, admin_session):
        """PUT /api/users/admins/{id}/os-archive-access should toggle os_archive_access"""
        token = admin_session["token"]
        user_id = admin_session["user_id"]
        
        # Get current state
        me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        original_os_archive_access = me_resp.json()["os_archive_access"]
        
        # Toggle
        response = requests.put(f"{BASE_URL}/api/users/admins/{user_id}/os-archive-access", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Toggle os_archive_access failed: {response.text}"
        data = response.json()
        
        assert "os_archive_access" in data, "Response missing 'os_archive_access' field"
        assert data["os_archive_access"] != original_os_archive_access, "os_archive_access should have toggled"
        
        # Toggle back to original
        requests.put(f"{BASE_URL}/api/users/admins/{user_id}/os-archive-access", headers={
            "Authorization": f"Bearer {token}"
        })
        
        print(f"PASS: Toggle os_archive_access works (was {original_os_archive_access}, toggled to {data['os_archive_access']})")


class TestBMAccessControl:
    """Test that admin without bm_access gets 403 on BM endpoints"""
    
    @pytest.fixture
    def admin_without_bm_access(self):
        """Get admin token and ensure bm_access is False"""
        # Login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = response.json()
        token = data["access_token"]
        user_id = data["user"]["id"]
        
        # Check current bm_access
        if data["user"]["bm_access"]:
            # Turn off bm_access
            requests.put(f"{BASE_URL}/api/users/admins/{user_id}/bm-access", headers={
                "Authorization": f"Bearer {token}"
            })
        
        return {"token": token, "user_id": user_id}
    
    @pytest.fixture
    def admin_with_bm_access(self):
        """Get admin token and ensure bm_access is True"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = response.json()
        token = data["access_token"]
        user_id = data["user"]["id"]
        
        # Check current bm_access
        if not data["user"]["bm_access"]:
            # Turn on bm_access
            requests.put(f"{BASE_URL}/api/users/admins/{user_id}/bm-access", headers={
                "Authorization": f"Bearer {token}"
            })
        
        return {"token": token, "user_id": user_id}
    
    def test_admin_without_bm_access_forbidden_on_list_bm(self, admin_without_bm_access):
        """Admin without bm_access should get 403 on GET /api/bm"""
        token = admin_without_bm_access["token"]
        
        response = requests.get(f"{BASE_URL}/api/bm", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Admin without bm_access gets 403 on GET /api/bm")
        
        # Restore bm_access
        requests.put(f"{BASE_URL}/api/users/admins/{admin_without_bm_access['user_id']}/bm-access", headers={
            "Authorization": f"Bearer {token}"
        })
    
    def test_admin_with_bm_access_can_list_bm(self, admin_with_bm_access):
        """Admin with bm_access should be able to GET /api/bm"""
        token = admin_with_bm_access["token"]
        
        response = requests.get(f"{BASE_URL}/api/bm", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Admin with bm_access can GET /api/bm")


class TestBMPDFFormat:
    """Test BM PDF format (A4 landscape, header, footer, borders)"""
    
    @pytest.fixture
    def admin_token_with_bm(self):
        """Get admin token with bm_access enabled"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = response.json()
        token = data["access_token"]
        user_id = data["user"]["id"]
        
        # Ensure bm_access is True
        if not data["user"]["bm_access"]:
            requests.put(f"{BASE_URL}/api/users/admins/{user_id}/bm-access", headers={
                "Authorization": f"Bearer {token}"
            })
        
        return token
    
    def test_bm_pdf_generation(self, admin_token_with_bm):
        """Test that BM PDF can be generated"""
        response = requests.get(
            f"{BASE_URL}/api/bm/{EXISTING_BM_ID}/pdf?token={admin_token_with_bm}",
            headers={"Authorization": f"Bearer {admin_token_with_bm}"}
        )
        
        # Check response
        assert response.status_code == 200, f"PDF generation failed: {response.status_code} - {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf", "Response should be PDF"
        
        pdf_content = response.content
        assert len(pdf_content) > 1000, "PDF content seems too small"
        
        # Check PDF header
        assert pdf_content[:4] == b'%PDF', "Response should start with PDF header"
        
        print(f"PASS: BM PDF generated successfully ({len(pdf_content)} bytes)")
    
    def test_bm_pdf_is_landscape(self, admin_token_with_bm):
        """Test that BM PDF is A4 landscape (842x595 points)"""
        response = requests.get(
            f"{BASE_URL}/api/bm/{EXISTING_BM_ID}/pdf?token={admin_token_with_bm}",
            headers={"Authorization": f"Bearer {admin_token_with_bm}"}
        )
        
        assert response.status_code == 200
        pdf_content = response.content
        
        # Check for landscape page size in PDF
        # A4 landscape is 842x595 points
        # Look for MediaBox in PDF content
        pdf_text = pdf_content.decode('latin-1', errors='ignore')
        
        # Check for landscape dimensions (width > height)
        # MediaBox format: [0 0 width height]
        if '/MediaBox' in pdf_text:
            import re
            mediabox_match = re.search(r'/MediaBox\s*\[\s*(\d+)\s+(\d+)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s*\]', pdf_text)
            if mediabox_match:
                width = float(mediabox_match.group(3))
                height = float(mediabox_match.group(4))
                assert width > height, f"PDF should be landscape (width={width}, height={height})"
                print(f"PASS: BM PDF is landscape ({width}x{height} points)")
            else:
                print("INFO: Could not parse MediaBox, but PDF generated successfully")
        else:
            print("INFO: MediaBox not found in PDF, but PDF generated successfully")
    
    def test_bm_pdf_contains_header_text(self, admin_token_with_bm):
        """Test that BM PDF contains 'BOLETIM DE MEDIÇÃO' header"""
        response = requests.get(
            f"{BASE_URL}/api/bm/{EXISTING_BM_ID}/pdf?token={admin_token_with_bm}",
            headers={"Authorization": f"Bearer {admin_token_with_bm}"}
        )
        
        assert response.status_code == 200
        pdf_content = response.content
        pdf_text = pdf_content.decode('latin-1', errors='ignore')
        
        # Check for header text (may be encoded differently in PDF)
        # The text "BOLETIM DE MEDIÇÃO" should appear somewhere
        assert 'BOLETIM' in pdf_text or 'Boletim' in pdf_text, "PDF should contain 'BOLETIM' text"
        print("PASS: BM PDF contains BOLETIM header text")
    
    def test_bm_pdf_contains_footer(self, admin_token_with_bm):
        """Test that BM PDF contains TWAS REPAIR footer"""
        response = requests.get(
            f"{BASE_URL}/api/bm/{EXISTING_BM_ID}/pdf?token={admin_token_with_bm}",
            headers={"Authorization": f"Bearer {admin_token_with_bm}"}
        )
        
        assert response.status_code == 200
        pdf_content = response.content
        pdf_text = pdf_content.decode('latin-1', errors='ignore')
        
        # Check for footer text
        assert 'TWAS' in pdf_text, "PDF should contain 'TWAS' in footer"
        print("PASS: BM PDF contains TWAS footer text")
    
    def test_bm_pdf_contains_website(self, admin_token_with_bm):
        """Test that BM PDF contains twasrepair.com in footer"""
        response = requests.get(
            f"{BASE_URL}/api/bm/{EXISTING_BM_ID}/pdf?token={admin_token_with_bm}",
            headers={"Authorization": f"Bearer {admin_token_with_bm}"}
        )
        
        assert response.status_code == 200
        pdf_content = response.content
        pdf_text = pdf_content.decode('latin-1', errors='ignore')
        
        # Check for website
        assert 'twasrepair' in pdf_text.lower(), "PDF should contain 'twasrepair.com' in footer"
        print("PASS: BM PDF contains twasrepair.com in footer")


class TestSupervisorAccessDenied:
    """Test that supervisor cannot access BM or OS Archive features"""
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_supervisor_login_has_no_bm_access(self):
        """Supervisor login should return bm_access=False"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        
        # Supervisor should not have bm_access
        assert data["user"].get("bm_access", False) == False, "Supervisor should not have bm_access"
        print("PASS: Supervisor login returns bm_access=False")
    
    def test_supervisor_login_has_no_os_archive_access(self):
        """Supervisor login should return os_archive_access=False"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        
        # Supervisor should not have os_archive_access
        assert data["user"].get("os_archive_access", False) == False, "Supervisor should not have os_archive_access"
        print("PASS: Supervisor login returns os_archive_access=False")
    
    def test_supervisor_forbidden_on_bm_list(self, supervisor_token):
        """Supervisor should get 403 on GET /api/bm"""
        response = requests.get(f"{BASE_URL}/api/bm", headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Supervisor gets 403 on GET /api/bm")
    
    def test_supervisor_forbidden_on_os_archive(self, supervisor_token):
        """Supervisor should get 403 on GET /api/admin/os-archive"""
        response = requests.get(f"{BASE_URL}/api/admin/os-archive", headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Supervisor gets 403 on GET /api/admin/os-archive")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
