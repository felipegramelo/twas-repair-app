"""
Iteration 30: Dashboard Financeiro and Proposal Restructuring Tests
Tests for:
1. Dashboard API /api/dashboard/summary - returns bm_by_month, proposals_by_status, totals, top_clients
2. Dashboard requires dashboard_access permission (403 without it)
3. Dashboard toggle /api/users/admins/{id}/dashboard-access
4. Proposal CRUD with termos_gerais field
5. Proposal PDF generation (comercial and tecnica)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://timesheet-pro-75.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
ADMIN_ID = "699df05167a32342504627ba"

SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"


class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login returns access_token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        assert "user" in data, "Response should contain user"
        assert data["user"]["email"] == ADMIN_EMAIL
    
    def test_supervisor_login(self):
        """Test supervisor login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"


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


class TestDashboardAPI:
    """Dashboard API tests"""
    
    def test_dashboard_summary_returns_correct_structure(self, admin_token):
        """Test /api/dashboard/summary returns correct data structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/summary", headers=headers)
        
        assert response.status_code == 200, f"Dashboard summary failed: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "bm_by_month" in data, "Response should contain bm_by_month"
        assert "proposals_by_status" in data, "Response should contain proposals_by_status"
        assert "totals" in data, "Response should contain totals"
        assert "top_clients" in data, "Response should contain top_clients"
        
        # Check bm_by_month structure (should have 12 months)
        assert isinstance(data["bm_by_month"], list), "bm_by_month should be a list"
        assert len(data["bm_by_month"]) == 12, "bm_by_month should have 12 months"
        for month_data in data["bm_by_month"]:
            assert "month" in month_data, "Each month should have 'month' field"
            assert "total" in month_data, "Each month should have 'total' field"
            assert "count" in month_data, "Each month should have 'count' field"
        
        # Check totals structure
        totals = data["totals"]
        assert "bm_total_value" in totals, "totals should have bm_total_value"
        assert "bm_count" in totals, "totals should have bm_count"
        assert "proposals_count" in totals, "totals should have proposals_count"
        assert "os_count" in totals, "totals should have os_count"
        assert "timesheets_count" in totals, "totals should have timesheets_count"
        
        # Check proposals_by_status is a dict
        assert isinstance(data["proposals_by_status"], dict), "proposals_by_status should be a dict"
        
        # Check top_clients structure
        assert isinstance(data["top_clients"], list), "top_clients should be a list"
        for client in data["top_clients"]:
            assert "client" in client, "Each client should have 'client' field"
            assert "total" in client, "Each client should have 'total' field"
            assert "count" in client, "Each client should have 'count' field"
    
    def test_dashboard_requires_dashboard_access(self, supervisor_token):
        """Test dashboard returns 403 for users without dashboard_access"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/summary", headers=headers)
        
        # Supervisor doesn't have dashboard_access, should get 403
        assert response.status_code == 403, f"Expected 403 for supervisor, got {response.status_code}"
    
    def test_dashboard_requires_authentication(self):
        """Test dashboard returns 401/403 without token"""
        response = requests.get(f"{BASE_URL}/api/dashboard/summary")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestDashboardAccessToggle:
    """Dashboard access toggle tests"""
    
    def test_toggle_dashboard_access(self, admin_token):
        """Test toggling dashboard_access for an admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Toggle dashboard access
        response = requests.put(
            f"{BASE_URL}/api/users/admins/{ADMIN_ID}/dashboard-access",
            headers=headers
        )
        assert response.status_code == 200, f"Toggle failed: {response.text}"
        data = response.json()
        assert "dashboard_access" in data, "Response should contain dashboard_access"
        
        # Toggle back to original state
        response2 = requests.put(
            f"{BASE_URL}/api/users/admins/{ADMIN_ID}/dashboard-access",
            headers=headers
        )
        assert response2.status_code == 200
        data2 = response2.json()
        # Should be opposite of first toggle
        assert data2["dashboard_access"] != data["dashboard_access"]


class TestProposalCRUD:
    """Proposal CRUD tests with termos_gerais"""
    
    def test_create_proposal_with_termos_gerais(self, admin_token):
        """Test creating a proposal with termos_gerais field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        payload = {
            "empresa": "TEST_Empresa Teste",
            "contato": "Joao Silva",
            "email": "joao@teste.com",
            "embarcacao": "Plataforma P-99",
            "equipamento": "Turbina Principal",
            "itens": [
                {
                    "id": "item1",
                    "titulo": "Inspecao Visual",
                    "descricao": "Inspecao visual completa do equipamento",
                    "valor": 5000.00
                },
                {
                    "id": "item2",
                    "titulo": "Reparo Mecanico",
                    "descricao": "Reparo das partes mecanicas danificadas",
                    "valor": 15000.00
                }
            ],
            "termos_gerais": "Termos e condicoes customizados para este cliente.",
            "observacoes": "Urgente - prazo de 5 dias"
        }
        
        response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=headers)
        assert response.status_code in [200, 201], f"Create proposal failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain id"
        assert "numero_proposta" in data, "Response should contain numero_proposta"
        assert data["empresa"] == payload["empresa"]
        assert data["termos_gerais"] == payload["termos_gerais"]
        assert len(data["itens"]) == 2
        
        # Cleanup
        proposal_id = data["id"]
        requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=headers)
        
        return data
    
    def test_update_proposal_termos_gerais(self, admin_token):
        """Test updating termos_gerais field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a proposal first
        create_payload = {
            "empresa": "TEST_Update Termos",
            "contato": "Maria Santos",
            "email": "maria@teste.com",
            "itens": [{"id": "item1", "titulo": "Servico 1", "descricao": "Desc", "valor": 1000}],
            "termos_gerais": "Termos originais"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/proposals", json=create_payload, headers=headers)
        assert create_response.status_code in [200, 201]
        proposal_id = create_response.json()["id"]
        
        # Update termos_gerais
        update_payload = {
            "termos_gerais": "Termos atualizados com novas condicoes"
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/proposals/{proposal_id}",
            json=update_payload,
            headers=headers
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        updated_data = update_response.json()
        assert updated_data["termos_gerais"] == update_payload["termos_gerais"], "termos_gerais should be updated"
        
        # Verify with GET
        get_response = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["termos_gerais"] == update_payload["termos_gerais"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=headers)
    
    def test_list_proposals_with_filters(self, admin_token):
        """Test listing proposals with month/year filters"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # List all proposals for 2026
        response = requests.get(f"{BASE_URL}/api/proposals?year=2026", headers=headers)
        assert response.status_code == 200, f"List proposals failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Each proposal should have required fields
        for proposal in data:
            assert "id" in proposal
            assert "numero_proposta" in proposal
            assert "empresa" in proposal
            assert "status" in proposal
            assert "itens" in proposal
    
    def test_proposal_backward_compatibility(self, admin_token):
        """Test that proposals without termos_gerais return empty string"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # List proposals
        response = requests.get(f"{BASE_URL}/api/proposals?year=2026", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        for proposal in data:
            # termos_gerais should exist (even if empty string for old proposals)
            assert "termos_gerais" in proposal, f"Proposal {proposal['id']} missing termos_gerais"


class TestProposalPDF:
    """Proposal PDF generation tests"""
    
    def test_comercial_pdf_generation(self, admin_token):
        """Test commercial PDF generation with numbered sections"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a test proposal
        payload = {
            "empresa": "TEST_PDF Comercial",
            "contato": "Pedro Costa",
            "email": "pedro@teste.com",
            "embarcacao": "Navio Teste",
            "equipamento": "Motor Principal",
            "itens": [
                {"id": "s1", "titulo": "Secao 1 - Diagnostico", "descricao": "Diagnostico completo", "valor": 3000},
                {"id": "s2", "titulo": "Secao 2 - Reparo", "descricao": "Reparo do motor", "valor": 12000}
            ],
            "termos_gerais": "Termos e condicoes gerais para PDF comercial.",
            "observacoes": "Observacoes do servico"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=headers)
        assert create_response.status_code in [200, 201]
        proposal_id = create_response.json()["id"]
        
        # Generate commercial PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=comercial&token={admin_token}"
        )
        assert pdf_response.status_code == 200, f"PDF generation failed: {pdf_response.text}"
        assert pdf_response.headers.get("content-type") == "application/pdf"
        assert len(pdf_response.content) > 1000, "PDF should have content"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=headers)
    
    def test_tecnica_pdf_generation(self, admin_token):
        """Test technical PDF generation (no prices)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a test proposal
        payload = {
            "empresa": "TEST_PDF Tecnica",
            "contato": "Ana Lima",
            "email": "ana@teste.com",
            "itens": [
                {"id": "t1", "titulo": "Analise Tecnica", "descricao": "Analise detalhada", "valor": 5000},
                {"id": "t2", "titulo": "Relatorio", "descricao": "Relatorio tecnico", "valor": 2000}
            ],
            "termos_gerais": "Termos para proposta tecnica."
        }
        
        create_response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=headers)
        assert create_response.status_code in [200, 201]
        proposal_id = create_response.json()["id"]
        
        # Generate technical PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=tecnica&token={admin_token}"
        )
        assert pdf_response.status_code == 200, f"Technical PDF failed: {pdf_response.text}"
        assert pdf_response.headers.get("content-type") == "application/pdf"
        assert len(pdf_response.content) > 1000, "PDF should have content"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=headers)


class TestInformarPO:
    """Informar P.O. workflow tests"""
    
    def test_informar_po_creates_os(self, admin_token):
        """Test that informar P.O. creates an O.S. automatically"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a pending proposal
        payload = {
            "empresa": "TEST_PO Workflow",
            "contato": "Carlos Mendes",
            "email": "carlos@teste.com",
            "itens": [{"id": "po1", "titulo": "Servico PO", "descricao": "Teste PO", "valor": 8000}],
            "termos_gerais": "Termos PO"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=headers)
        assert create_response.status_code in [200, 201]
        proposal_id = create_response.json()["id"]
        
        # Informar P.O.
        po_response = requests.put(
            f"{BASE_URL}/api/proposals/{proposal_id}/informar-po",
            json={"po_number": "PO-TEST-001"},
            headers=headers
        )
        assert po_response.status_code == 200, f"Informar PO failed: {po_response.text}"
        
        po_data = po_response.json()
        assert po_data["status"] == "aprovada", "Status should be 'aprovada'"
        assert po_data["po_number"] == "PO-TEST-001"
        assert po_data["os_id"], "Should have os_id"
        assert po_data["os_number"], "Should have os_number"
        
        # Cleanup - delete the created O.S. and proposal
        if po_data.get("os_id"):
            requests.delete(f"{BASE_URL}/api/service-orders/{po_data['os_id']}", headers=headers)
        requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=headers)
    
    def test_informar_po_rejects_already_approved(self, admin_token):
        """Test that informar P.O. rejects already approved proposals"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create and approve a proposal
        payload = {
            "empresa": "TEST_Already Approved",
            "contato": "Test User",
            "itens": [{"id": "x1", "titulo": "Test", "descricao": "Test", "valor": 1000}]
        }
        
        create_response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=headers)
        proposal_id = create_response.json()["id"]
        
        # First informar P.O.
        requests.put(
            f"{BASE_URL}/api/proposals/{proposal_id}/informar-po",
            json={"po_number": "PO-FIRST"},
            headers=headers
        )
        
        # Try to informar P.O. again
        second_response = requests.put(
            f"{BASE_URL}/api/proposals/{proposal_id}/informar-po",
            json={"po_number": "PO-SECOND"},
            headers=headers
        )
        assert second_response.status_code == 400, "Should reject already approved proposal"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=headers)


class TestProposalPermissions:
    """Proposal permission tests"""
    
    def test_proposal_requires_proposta_access(self, supervisor_token):
        """Test that proposals require proposta_access permission"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        
        # Supervisor doesn't have proposta_access
        response = requests.get(f"{BASE_URL}/api/proposals?year=2026", headers=headers)
        assert response.status_code == 403, f"Expected 403 for supervisor, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
