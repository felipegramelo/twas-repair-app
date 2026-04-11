"""
Iteration 39: P0 Changes Testing
- Test 'Local' field in Proposals (create, update, retrieve)
- Test 'Informar P.O.' creates Service Order with correct field mapping:
  - proposal.local -> OS.location
  - proposal.embarcacao -> OS.embarcacao
  - proposal.servico -> OS.service
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data.get("user", {}).get("role") == "admin", "User is not admin"
        assert data.get("user", {}).get("proposta_access") == True, "Admin should have proposta_access"
        print(f"PASS: Admin login successful, proposta_access={data.get('user', {}).get('proposta_access')}")
        return data["access_token"]
    
    def test_supervisor_login(self):
        """Test supervisor login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data.get("user", {}).get("role") == "supervisor", "User is not supervisor"
        print("PASS: Supervisor login successful")
        return data["access_token"]


class TestProposalLocalField:
    """Test 'Local' field in Proposals CRUD"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_create_proposal_with_local(self, admin_token):
        """Test creating a proposal with 'local' field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "empresa": "TEST_Empresa P0",
            "contato": "TEST_Contato P0",
            "email": "test@p0.com",
            "embarcacao": "TEST_Plataforma P-99",
            "local": "TEST_Bacia de Santos",
            "equipamento": "TEST_Turbina Principal",
            "servico": "TEST_Reparo de valvulas",
            "itens": [
                {
                    "id": "item1",
                    "titulo": "Secao 1",
                    "descricao": "Descricao da secao 1",
                    "valor": 1000.00
                }
            ],
            "termos_gerais": "Termos de teste",
            "observacoes": "Observacoes de teste"
        }
        response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=headers)
        assert response.status_code == 200, f"Create proposal failed: {response.text}"
        data = response.json()
        
        # Verify 'local' field is saved
        assert data.get("local") == "TEST_Bacia de Santos", f"Local field not saved correctly: {data.get('local')}"
        assert data.get("embarcacao") == "TEST_Plataforma P-99", f"Embarcacao field not saved correctly"
        assert data.get("servico") == "TEST_Reparo de valvulas", f"Servico field not saved correctly"
        
        print(f"PASS: Proposal created with local='{data.get('local')}', embarcacao='{data.get('embarcacao')}', servico='{data.get('servico')}'")
        return data["id"]
    
    def test_get_proposal_with_local(self, admin_token):
        """Test retrieving a proposal returns 'local' field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First create a proposal
        payload = {
            "empresa": "TEST_Empresa Get",
            "contato": "TEST_Contato Get",
            "embarcacao": "TEST_Embarcacao Get",
            "local": "TEST_Local Get",
            "servico": "TEST_Servico Get",
            "itens": [{"id": "item1", "titulo": "Secao 1", "descricao": "Desc", "valor": 500}]
        }
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=headers)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        
        # Get the proposal
        get_resp = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}", headers=headers)
        assert get_resp.status_code == 200, f"Get proposal failed: {get_resp.text}"
        data = get_resp.json()
        
        assert data.get("local") == "TEST_Local Get", f"Local field not returned: {data.get('local')}"
        print(f"PASS: GET proposal returns local='{data.get('local')}'")
        return proposal_id
    
    def test_update_proposal_local(self, admin_token):
        """Test updating 'local' field in a proposal"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create proposal
        payload = {
            "empresa": "TEST_Empresa Update",
            "contato": "TEST_Contato Update",
            "local": "TEST_Local Original",
            "servico": "TEST_Servico Update",
            "itens": [{"id": "item1", "titulo": "Secao 1", "descricao": "Desc", "valor": 500}]
        }
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=headers)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        
        # Update local field
        update_payload = {"local": "TEST_Local Updated"}
        update_resp = requests.put(f"{BASE_URL}/api/proposals/{proposal_id}", json=update_payload, headers=headers)
        assert update_resp.status_code == 200, f"Update proposal failed: {update_resp.text}"
        
        # Verify update
        get_resp = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}", headers=headers)
        data = get_resp.json()
        assert data.get("local") == "TEST_Local Updated", f"Local field not updated: {data.get('local')}"
        print(f"PASS: Proposal local updated to '{data.get('local')}'")
        return proposal_id
    
    def test_list_proposals_includes_local(self, admin_token):
        """Test listing proposals includes 'local' field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/proposals", headers=headers)
        assert response.status_code == 200, f"List proposals failed: {response.text}"
        data = response.json()
        
        # Check that at least one proposal has 'local' field
        proposals_with_local = [p for p in data if p.get("local")]
        print(f"PASS: Found {len(proposals_with_local)} proposals with 'local' field out of {len(data)} total")
        assert len(proposals_with_local) > 0, "No proposals with 'local' field found"


class TestInformarPOFieldMapping:
    """Test that 'Informar P.O.' correctly maps fields to Service Order"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_informar_po_creates_os_with_correct_fields(self, admin_token):
        """
        CRITICAL TEST: When 'Informar P.O.' is submitted:
        - OS.location should be set from proposal.local
        - OS.embarcacao should be set from proposal.embarcacao
        - OS.service should be set from proposal.servico
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a proposal with specific values
        proposal_payload = {
            "empresa": "TEST_Empresa InformarPO",
            "contato": "TEST_Contato InformarPO",
            "email": "test@informarpo.com",
            "embarcacao": "TEST_Embarcacao_ForOS",
            "local": "TEST_Local_ForOS",
            "equipamento": "TEST_Equipamento",
            "servico": "TEST_Servico_ForOS",
            "itens": [
                {
                    "id": "item1",
                    "titulo": "Secao Teste",
                    "descricao": "Descricao teste",
                    "valor": 2500.00
                }
            ],
            "termos_gerais": "Termos teste",
            "observacoes": "Observacoes teste"
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=proposal_payload, headers=headers)
        assert create_resp.status_code == 200, f"Create proposal failed: {create_resp.text}"
        proposal = create_resp.json()
        proposal_id = proposal["id"]
        print(f"Created proposal: id={proposal_id}, local='{proposal.get('local')}', embarcacao='{proposal.get('embarcacao')}', servico='{proposal.get('servico')}'")
        
        # Submit Informar P.O.
        po_payload = {"po_number": "TEST_PO-2026-001"}
        po_resp = requests.put(f"{BASE_URL}/api/proposals/{proposal_id}/informar-po", json=po_payload, headers=headers)
        assert po_resp.status_code == 200, f"Informar P.O. failed: {po_resp.text}"
        
        updated_proposal = po_resp.json()
        assert updated_proposal.get("status") == "aprovada", "Proposal should be approved"
        assert updated_proposal.get("os_id"), "Proposal should have os_id"
        os_id = updated_proposal.get("os_id")
        os_number = updated_proposal.get("os_number")
        print(f"Proposal approved: os_id={os_id}, os_number={os_number}")
        
        # Get the created Service Order and verify field mapping
        os_resp = requests.get(f"{BASE_URL}/api/service-orders/{os_id}", headers=headers)
        assert os_resp.status_code == 200, f"Get Service Order failed: {os_resp.text}"
        service_order = os_resp.json()
        
        # CRITICAL ASSERTIONS - Field mapping verification
        assert service_order.get("location") == "TEST_Local_ForOS", \
            f"OS.location should be '{proposal_payload['local']}' but got '{service_order.get('location')}'"
        
        assert service_order.get("embarcacao") == "TEST_Embarcacao_ForOS", \
            f"OS.embarcacao should be '{proposal_payload['embarcacao']}' but got '{service_order.get('embarcacao')}'"
        
        assert service_order.get("service") == "TEST_Servico_ForOS", \
            f"OS.service should be '{proposal_payload['servico']}' but got '{service_order.get('service')}'"
        
        print(f"PASS: Service Order created with correct field mapping:")
        print(f"  - OS.location = '{service_order.get('location')}' (from proposal.local)")
        print(f"  - OS.embarcacao = '{service_order.get('embarcacao')}' (from proposal.embarcacao)")
        print(f"  - OS.service = '{service_order.get('service')}' (from proposal.servico)")
        
        return os_id
    
    def test_informar_po_with_empty_local(self, admin_token):
        """Test Informar P.O. when local is empty - should still work"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create proposal without local
        proposal_payload = {
            "empresa": "TEST_Empresa NoLocal",
            "contato": "TEST_Contato NoLocal",
            "embarcacao": "TEST_Embarcacao_NoLocal",
            "local": "",  # Empty local
            "servico": "TEST_Servico_NoLocal",
            "itens": [{"id": "item1", "titulo": "Secao", "descricao": "Desc", "valor": 1000}]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=proposal_payload, headers=headers)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        
        # Submit Informar P.O.
        po_resp = requests.put(f"{BASE_URL}/api/proposals/{proposal_id}/informar-po", 
                               json={"po_number": "TEST_PO-NOLOCAL"}, headers=headers)
        assert po_resp.status_code == 200, f"Informar P.O. failed: {po_resp.text}"
        
        os_id = po_resp.json().get("os_id")
        os_resp = requests.get(f"{BASE_URL}/api/service-orders/{os_id}", headers=headers)
        service_order = os_resp.json()
        
        # Location should be empty string
        assert service_order.get("location") == "", f"OS.location should be empty but got '{service_order.get('location')}'"
        print(f"PASS: Service Order created with empty location when proposal.local is empty")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_cleanup_test_proposals(self, admin_token):
        """Delete TEST_ prefixed proposals"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all proposals
        response = requests.get(f"{BASE_URL}/api/proposals", headers=headers)
        if response.status_code == 200:
            proposals = response.json()
            deleted = 0
            for p in proposals:
                if p.get("empresa", "").startswith("TEST_"):
                    del_resp = requests.delete(f"{BASE_URL}/api/proposals/{p['id']}", headers=headers)
                    if del_resp.status_code in [200, 204]:
                        deleted += 1
            print(f"Cleaned up {deleted} test proposals")
    
    def test_cleanup_test_service_orders(self, admin_token):
        """Delete TEST_ prefixed service orders"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all service orders
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        if response.status_code == 200:
            orders = response.json()
            deleted = 0
            for o in orders:
                if o.get("client", "").startswith("TEST_") or o.get("po_number", "").startswith("TEST_"):
                    del_resp = requests.delete(f"{BASE_URL}/api/service-orders/{o['id']}", headers=headers)
                    if del_resp.status_code in [200, 204]:
                        deleted += 1
            print(f"Cleaned up {deleted} test service orders")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
