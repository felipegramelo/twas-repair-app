"""
Iteration 35: iOS Native Fixes Testing
Tests for:
1. Backend: Login, proposals CRUD, PDF generation
2. Verify all APIs still work after iOS native fixes
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://twas-repair-preview.preview.emergentagent.com')

class TestAuthAPI:
    """Authentication endpoint tests"""
    
    def test_admin_login_success(self):
        """Test admin login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "admin@twasrepair.com"
        assert data["user"]["role"] == "admin"
        assert data["user"]["proposta_access"] == True
        
    def test_supervisor_login_success(self):
        """Test supervisor login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "supervisor@twasrepair.com"
        assert data["user"]["role"] == "supervisor"
        
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401


class TestProposalsAPI:
    """Proposals CRUD tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
        
    def test_get_proposals_list(self, auth_token):
        """Test getting proposals list"""
        response = requests.get(
            f"{BASE_URL}/api/proposals",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_create_proposal_with_servico(self, auth_token):
        """Test creating proposal with servico field"""
        payload = {
            "empresa": "TEST_Empresa Teste",
            "contato": "Contato Teste",
            "email": "test@test.com",
            "embarcacao": "Embarcacao Teste",
            "equipamento": "Equipamento Teste",
            "servico": "Reparo de valvulas",
            "observacoes": "Observacoes teste",
            "itens": [
                {
                    "id": "item1",
                    "titulo": "Secao 1",
                    "descricao": "Descricao da secao 1",
                    "valor": 1000.00,
                    "subsections": []
                }
            ],
            "termos_gerais": "Termos gerais de teste"
        }
        response = requests.post(
            f"{BASE_URL}/api/proposals",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["empresa"] == "TEST_Empresa Teste"
        assert data["servico"] == "Reparo de valvulas"
        assert "id" in data
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/proposals/{data['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
    def test_proposal_pdf_generation_comercial(self, auth_token):
        """Test PDF generation for comercial type"""
        # First create a proposal
        payload = {
            "empresa": "TEST_PDF_Empresa",
            "contato": "Contato PDF",
            "email": "pdf@test.com",
            "embarcacao": "Embarcacao PDF",
            "equipamento": "Equipamento PDF",
            "servico": "Servico para PDF",
            "observacoes": "",
            "itens": [
                {
                    "id": "item1",
                    "titulo": "Secao PDF",
                    "descricao": "Descricao",
                    "valor": 500.00,
                    "subsections": []
                }
            ],
            "termos_gerais": "Termos"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/proposals",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=payload
        )
        assert create_response.status_code == 200
        proposal_id = create_response.json()["id"]
        
        # Test PDF generation
        pdf_response = requests.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=comercial",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert pdf_response.status_code == 200
        assert pdf_response.headers.get("content-type") == "application/pdf"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/proposals/{proposal_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
    def test_proposal_pdf_generation_tecnica(self, auth_token):
        """Test PDF generation for tecnica type"""
        # First create a proposal
        payload = {
            "empresa": "TEST_PDF_Tecnica",
            "contato": "Contato Tecnica",
            "email": "tecnica@test.com",
            "embarcacao": "Embarcacao Tecnica",
            "equipamento": "Equipamento Tecnica",
            "servico": "Servico Tecnica",
            "observacoes": "",
            "itens": [
                {
                    "id": "item1",
                    "titulo": "Secao Tecnica",
                    "descricao": "Descricao tecnica",
                    "valor": 750.00,
                    "subsections": []
                }
            ],
            "termos_gerais": "Termos"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/proposals",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=payload
        )
        assert create_response.status_code == 200
        proposal_id = create_response.json()["id"]
        
        # Test PDF generation
        pdf_response = requests.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=tecnica",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert pdf_response.status_code == 200
        assert pdf_response.headers.get("content-type") == "application/pdf"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/proposals/{proposal_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )


class TestServiceOrdersAPI:
    """Service Orders API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
        
    def test_get_service_orders(self, auth_token):
        """Test getting service orders list"""
        response = requests.get(
            f"{BASE_URL}/api/service-orders",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestTimesheetsAPI:
    """Timesheets API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get supervisor auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
        
    def test_get_timesheets(self, auth_token):
        """Test getting timesheets list"""
        response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestReportsAPI:
    """Reports API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get supervisor auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
        
    def test_get_reports(self, auth_token):
        """Test getting reports list"""
        response = requests.get(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # API returns {"reports": [...]} or list
        if isinstance(data, dict):
            assert "reports" in data
            assert isinstance(data["reports"], list)
        else:
            assert isinstance(data, list)


class TestEmployeesAPI:
    """Employees API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
        
    def test_get_employees(self, auth_token):
        """Test getting employees list"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestArchiveAPI:
    """Archive API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
        
    def test_get_os_archive(self, auth_token):
        """Test getting OS archive"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
