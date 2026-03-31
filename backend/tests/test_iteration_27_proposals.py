"""
Test suite for Iteration 27: Proposta Comercial (Commercial Proposal) Feature
Tests CRUD operations, auto-numbering, proposta_access permission, and PDF generation
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"


class TestAuth:
    """Authentication tests for proposal feature"""
    
    def test_admin_login(self):
        """Test admin login returns proposta_access field"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        # proposta_access should be in user response
        assert "proposta_access" in data["user"], "proposta_access field missing from login response"
        print(f"Admin proposta_access: {data['user'].get('proposta_access')}")
    
    def test_supervisor_login(self):
        """Test supervisor login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
    
    def test_me_endpoint_returns_proposta_access(self):
        """Test /auth/me returns proposta_access field"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["access_token"]
        
        # Call /me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "proposta_access" in data, "proposta_access field missing from /me response"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin token for authenticated requests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def supervisor_token():
    """Get supervisor token for authenticated requests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": SUPERVISOR_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Supervisor login failed: {response.text}")
    return response.json()["access_token"]


class TestProposalCRUD:
    """Test Proposal CRUD operations"""
    
    def test_list_proposals_requires_admin(self, supervisor_token):
        """Supervisor should not be able to list proposals"""
        response = requests.get(f"{BASE_URL}/api/proposals", headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        # Should be 403 (not admin) or 401
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_list_proposals_admin_with_access(self, admin_token):
        """Admin with proposta_access can list proposals"""
        response = requests.get(f"{BASE_URL}/api/proposals", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"List proposals failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} existing proposals")
    
    def test_create_proposal_with_auto_numbering(self, admin_token):
        """Test creating a proposal generates auto-number in YYMM - Seq format"""
        payload = {
            "empresa": "TEST_Empresa Teste LTDA",
            "contato": "João Silva",
            "email": "joao@teste.com",
            "embarcacao": "Plataforma P-99",
            "equipamento": "Turbina Principal",
            "observacoes": "Observações de teste",
            "itens": [
                {"titulo": "Serviço 1", "descricao": "Descrição do serviço 1", "valor": 1500.00},
                {"titulo": "Serviço 2", "descricao": "Descrição do serviço 2", "valor": 2500.00}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code in [200, 201], f"Create proposal failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "No id in response"
        assert "numero_proposta" in data, "No numero_proposta in response"
        
        # Verify auto-numbering format: YYMM - Seq (e.g., 2603 - 01)
        numero = data["numero_proposta"]
        print(f"Created proposal with number: {numero}")
        assert " - " in numero, f"numero_proposta should contain ' - ', got: {numero}"
        parts = numero.split(" - ")
        assert len(parts) == 2, f"numero_proposta should have 2 parts, got: {parts}"
        assert len(parts[0]) == 4, f"YYMM part should be 4 chars, got: {parts[0]}"
        
        # Verify data persistence
        assert data["empresa"] == payload["empresa"]
        assert data["contato"] == payload["contato"]
        assert data["email"] == payload["email"]
        assert len(data["itens"]) == 2
        
        # Store for cleanup
        TestProposalCRUD.created_proposal_id = data["id"]
        TestProposalCRUD.created_proposal_numero = data["numero_proposta"]
    
    def test_get_proposal_by_id(self, admin_token):
        """Test getting a single proposal by ID"""
        proposal_id = getattr(TestProposalCRUD, 'created_proposal_id', None)
        if not proposal_id:
            pytest.skip("No proposal created in previous test")
        
        response = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get proposal failed: {response.text}"
        data = response.json()
        assert data["id"] == proposal_id
        assert data["empresa"] == "TEST_Empresa Teste LTDA"
    
    def test_update_proposal(self, admin_token):
        """Test updating a proposal"""
        proposal_id = getattr(TestProposalCRUD, 'created_proposal_id', None)
        if not proposal_id:
            pytest.skip("No proposal created in previous test")
        
        update_payload = {
            "empresa": "TEST_Empresa Atualizada LTDA",
            "contato": "Maria Santos",
            "itens": [
                {"titulo": "Serviço Atualizado", "descricao": "Nova descrição", "valor": 3000.00}
            ]
        }
        response = requests.put(f"{BASE_URL}/api/proposals/{proposal_id}", json=update_payload, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Update proposal failed: {response.text}"
        data = response.json()
        
        # Verify update
        assert data["empresa"] == "TEST_Empresa Atualizada LTDA"
        assert data["contato"] == "Maria Santos"
        assert len(data["itens"]) == 1
        assert data["itens"][0]["valor"] == 3000.00
        
        # Verify numero_proposta is preserved
        assert data["numero_proposta"] == TestProposalCRUD.created_proposal_numero
    
    def test_get_proposal_not_found(self, admin_token):
        """Test getting non-existent proposal returns 404"""
        response = requests.get(f"{BASE_URL}/api/proposals/000000000000000000000000", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 404
    
    def test_delete_proposal(self, admin_token):
        """Test deleting a proposal"""
        proposal_id = getattr(TestProposalCRUD, 'created_proposal_id', None)
        if not proposal_id:
            pytest.skip("No proposal created in previous test")
        
        response = requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Delete proposal failed: {response.text}"
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert get_response.status_code == 404, "Proposal should be deleted"


class TestProposalPDF:
    """Test PDF generation for proposals"""
    
    @pytest.fixture(autouse=True)
    def setup_proposal(self, admin_token):
        """Create a proposal for PDF testing"""
        payload = {
            "empresa": "TEST_PDF Empresa",
            "contato": "PDF Contato",
            "email": "pdf@teste.com",
            "embarcacao": "Navio Teste",
            "equipamento": "Motor Principal",
            "observacoes": "Teste de PDF",
            "itens": [
                {"titulo": "Item PDF 1", "descricao": "Descrição item 1", "valor": 5000.00},
                {"titulo": "Item PDF 2", "descricao": "Descrição item 2", "valor": 3000.00}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        if response.status_code in [200, 201]:
            self.proposal_id = response.json()["id"]
            self.admin_token = admin_token
        else:
            pytest.skip(f"Could not create proposal for PDF test: {response.text}")
        
        yield
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proposals/{self.proposal_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
    
    def test_generate_pdf_comercial(self, admin_token):
        """Test generating commercial PDF (with prices)"""
        response = requests.get(
            f"{BASE_URL}/api/proposals/{self.proposal_id}/pdf?tipo=comercial&token={admin_token}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"PDF comercial generation failed: {response.text}"
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 1000, "PDF content seems too small"
        print(f"PDF Comercial size: {len(response.content)} bytes")
    
    def test_generate_pdf_tecnica(self, admin_token):
        """Test generating technical PDF (without prices)"""
        response = requests.get(
            f"{BASE_URL}/api/proposals/{self.proposal_id}/pdf?tipo=tecnica&token={admin_token}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"PDF tecnica generation failed: {response.text}"
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 1000, "PDF content seems too small"
        print(f"PDF Técnica size: {len(response.content)} bytes")
    
    def test_pdf_requires_token(self):
        """Test PDF endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/proposals/{self.proposal_id}/pdf?tipo=comercial")
        assert response.status_code == 401, "PDF should require authentication"


class TestPropostaAccessToggle:
    """Test proposta_access permission toggle"""
    
    def test_toggle_proposta_access(self, admin_token):
        """Test toggling proposta_access for an admin"""
        # First get list of admins
        admins_response = requests.get(f"{BASE_URL}/api/users/admins", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert admins_response.status_code == 200
        admins = admins_response.json()
        
        if not admins:
            pytest.skip("No admins found")
        
        # Find the current admin
        admin_id = None
        for admin in admins:
            if admin["email"] == ADMIN_EMAIL:
                admin_id = admin["id"]
                initial_access = admin.get("proposta_access", False)
                break
        
        if not admin_id:
            pytest.skip("Could not find admin user")
        
        # Toggle access
        response = requests.put(f"{BASE_URL}/api/users/admins/{admin_id}/proposta-access", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Toggle proposta_access failed: {response.text}"
        data = response.json()
        assert "proposta_access" in data
        
        # Toggle back to original state
        requests.put(f"{BASE_URL}/api/users/admins/{admin_id}/proposta-access", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        print(f"proposta_access toggled successfully")


class TestAutoNumberingSequence:
    """Test auto-numbering sequence behavior"""
    
    def test_sequential_numbering(self, admin_token):
        """Test that proposals get sequential numbers"""
        created_ids = []
        created_numbers = []
        
        try:
            # Create 2 proposals
            for i in range(2):
                payload = {
                    "empresa": f"TEST_Seq Empresa {i}",
                    "contato": f"Contato {i}",
                    "email": f"seq{i}@teste.com",
                    "embarcacao": "",
                    "equipamento": "",
                    "observacoes": "",
                    "itens": [{"titulo": f"Item {i}", "descricao": "", "valor": 100.00}]
                }
                response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers={
                    "Authorization": f"Bearer {admin_token}"
                })
                assert response.status_code in [200, 201], f"Create failed: {response.text}"
                data = response.json()
                created_ids.append(data["id"])
                created_numbers.append(data["numero_proposta"])
            
            # Verify sequential numbering
            print(f"Created proposals: {created_numbers}")
            
            # Extract sequence numbers
            seq1 = int(created_numbers[0].split(" - ")[1])
            seq2 = int(created_numbers[1].split(" - ")[1])
            assert seq2 == seq1 + 1, f"Sequence should be consecutive: {seq1} -> {seq2}"
            
        finally:
            # Cleanup
            for pid in created_ids:
                requests.delete(f"{BASE_URL}/api/proposals/{pid}", headers={
                    "Authorization": f"Bearer {admin_token}"
                })


class TestSupervisorAccessDenied:
    """Test that supervisors cannot access proposal endpoints"""
    
    def test_supervisor_cannot_list_proposals(self, supervisor_token):
        """Supervisor should get 403 when listing proposals"""
        response = requests.get(f"{BASE_URL}/api/proposals", headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_supervisor_cannot_create_proposal(self, supervisor_token):
        """Supervisor should get 403 when creating proposals"""
        payload = {
            "empresa": "TEST_Supervisor Empresa",
            "contato": "Contato",
            "email": "sup@teste.com",
            "embarcacao": "",
            "equipamento": "",
            "observacoes": "",
            "itens": [{"titulo": "Item", "descricao": "", "valor": 100.00}]
        }
        response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers={
            "Authorization": f"Bearer {supervisor_token}"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
