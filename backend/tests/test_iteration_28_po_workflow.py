"""
Iteration 28 Tests: P.O. Workflow and Month/Year Filters
Tests:
- PUT /api/proposals/{id}/informar-po - Accept po_number, change status to aprovada, create O.S. automatically
- Auto-generated O.S. number format: SEQ - PROPOSTA_NUMBER (yearly sequential)
- PUT /api/proposals/{id}/informar-po - Reject if proposal already approved (400)
- GET /api/proposals?month=3&year=2026 - Filter proposals by month/year
- GET /api/proposals?year=2026 - Filter proposals by year only
- GET /api/service-orders?month=3&year=2026 - Filter service orders by month/year
- Proposal status field returned in list/get responses (pendente or aprovada)
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


class TestAuthSetup:
    """Authentication setup tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get admin headers with auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_admin_login(self):
        """Test admin login returns proposta_access"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data.get("user", {}).get("proposta_access") == True


class TestProposalFilters:
    """Test proposal month/year filters"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_proposals_with_year_filter(self, admin_headers):
        """GET /api/proposals?year=2026 - Filter proposals by year only"""
        response = requests.get(f"{BASE_URL}/api/proposals?year=2026", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # All proposals should have status field
        for proposal in data:
            assert "status" in proposal, f"Proposal missing status field: {proposal}"
            assert proposal["status"] in ["pendente", "aprovada"], f"Invalid status: {proposal['status']}"
    
    def test_get_proposals_with_month_year_filter(self, admin_headers):
        """GET /api/proposals?month=1&year=2026 - Filter proposals by month/year"""
        response = requests.get(f"{BASE_URL}/api/proposals?month=1&year=2026", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
    
    def test_proposals_return_status_field(self, admin_headers):
        """Verify proposal status field is returned in list responses"""
        response = requests.get(f"{BASE_URL}/api/proposals?year=2026", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            proposal = data[0]
            assert "status" in proposal, "status field missing"
            assert "po_number" in proposal, "po_number field missing"
            assert "os_id" in proposal, "os_id field missing"
            assert "os_number" in proposal, "os_number field missing"


class TestServiceOrderFilters:
    """Test service order month/year filters"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_service_orders_with_year_filter(self, admin_headers):
        """GET /api/service-orders?year=2026 - Filter service orders by year"""
        response = requests.get(f"{BASE_URL}/api/service-orders?year=2026", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
    
    def test_get_service_orders_with_month_year_filter(self, admin_headers):
        """GET /api/service-orders?month=1&year=2026 - Filter service orders by month/year"""
        response = requests.get(f"{BASE_URL}/api/service-orders?month=1&year=2026", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"


class TestInformarPOWorkflow:
    """Test the Informar P.O. workflow"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_create_pending_proposal_for_po_test(self, admin_headers):
        """Create a new pending proposal for P.O. testing"""
        payload = {
            "empresa": "TEST_PO_Company",
            "contato": "Test Contact",
            "email": "test@po.com",
            "embarcacao": "Test Platform",
            "equipamento": "Test Equipment",
            "observacoes": "Test for P.O. workflow",
            "itens": [
                {"titulo": "Test Item 1", "descricao": "Description 1", "valor": 1000.0}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create proposal: {response.text}"
        data = response.json()
        assert data["status"] == "pendente", "New proposal should be pendente"
        assert data["po_number"] == "", "New proposal should have empty po_number"
        assert data["os_id"] == "", "New proposal should have empty os_id"
        assert data["os_number"] == "", "New proposal should have empty os_number"
        # Store for later tests
        TestInformarPOWorkflow.test_proposal_id = data["id"]
        TestInformarPOWorkflow.test_proposal_number = data["numero_proposta"]
        print(f"Created test proposal: {data['numero_proposta']} with id: {data['id']}")
    
    def test_informar_po_success(self, admin_headers):
        """PUT /api/proposals/{id}/informar-po - Accept po_number, change status to aprovada, create O.S."""
        proposal_id = getattr(TestInformarPOWorkflow, 'test_proposal_id', None)
        if not proposal_id:
            pytest.skip("No test proposal created")
        
        po_number = "TEST-PO-2026-001"
        response = requests.put(
            f"{BASE_URL}/api/proposals/{proposal_id}/informar-po",
            json={"po_number": po_number},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to inform P.O.: {response.text}"
        data = response.json()
        
        # Verify proposal status changed
        assert data["status"] == "aprovada", f"Status should be aprovada, got: {data['status']}"
        assert data["po_number"] == po_number, f"P.O. number mismatch: {data['po_number']}"
        
        # Verify O.S. was created
        assert data["os_id"] != "", "os_id should be set"
        assert data["os_number"] != "", "os_number should be set"
        
        # Verify O.S. number format: SEQ - PROPOSTA_NUMBER
        os_number = data["os_number"]
        proposal_number = data["numero_proposta"]
        assert proposal_number in os_number, f"O.S. number should contain proposal number. OS: {os_number}, Proposal: {proposal_number}"
        
        # Store for verification
        TestInformarPOWorkflow.created_os_id = data["os_id"]
        TestInformarPOWorkflow.created_os_number = data["os_number"]
        print(f"P.O. informed successfully. O.S. created: {data['os_number']}")
    
    def test_verify_os_created(self, admin_headers):
        """Verify the O.S. was actually created in the database"""
        os_id = getattr(TestInformarPOWorkflow, 'created_os_id', None)
        if not os_id:
            pytest.skip("No O.S. created")
        
        response = requests.get(f"{BASE_URL}/api/service-orders/{os_id}", headers=admin_headers)
        assert response.status_code == 200, f"O.S. not found: {response.text}"
        data = response.json()
        
        # Verify O.S. data
        assert data["os_number"] == TestInformarPOWorkflow.created_os_number
        assert data["po_number"] == "TEST-PO-2026-001"
        assert data["client"] == "TEST_PO_Company"
        print(f"O.S. verified: {data['os_number']}")
    
    def test_informar_po_already_approved_fails(self, admin_headers):
        """PUT /api/proposals/{id}/informar-po - Reject if proposal already approved (400)"""
        proposal_id = getattr(TestInformarPOWorkflow, 'test_proposal_id', None)
        if not proposal_id:
            pytest.skip("No test proposal created")
        
        response = requests.put(
            f"{BASE_URL}/api/proposals/{proposal_id}/informar-po",
            json={"po_number": "ANOTHER-PO"},
            headers=admin_headers
        )
        assert response.status_code == 400, f"Should reject already approved proposal, got: {response.status_code}"
        data = response.json()
        assert "já aprovada" in data.get("detail", "").lower() or "already" in data.get("detail", "").lower(), f"Error message should mention already approved: {data}"
    
    def test_informar_po_empty_po_number_fails(self, admin_headers):
        """PUT /api/proposals/{id}/informar-po - Reject empty P.O. number"""
        # First create another pending proposal
        payload = {
            "empresa": "TEST_Empty_PO_Company",
            "contato": "Test Contact",
            "email": "test@empty.com",
            "embarcacao": "Test Platform",
            "equipamento": "Test Equipment",
            "observacoes": "Test for empty P.O.",
            "itens": [
                {"titulo": "Test Item", "descricao": "Description", "valor": 500.0}
            ]
        }
        create_response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=admin_headers)
        assert create_response.status_code == 200
        proposal_id = create_response.json()["id"]
        
        # Try to inform with empty P.O.
        response = requests.put(
            f"{BASE_URL}/api/proposals/{proposal_id}/informar-po",
            json={"po_number": "   "},
            headers=admin_headers
        )
        assert response.status_code == 400, f"Should reject empty P.O., got: {response.status_code}"
        
        # Cleanup - delete the test proposal
        requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=admin_headers)
    
    def test_informar_po_nonexistent_proposal(self, admin_headers):
        """PUT /api/proposals/{id}/informar-po - 404 for non-existent proposal"""
        fake_id = "000000000000000000000000"
        response = requests.put(
            f"{BASE_URL}/api/proposals/{fake_id}/informar-po",
            json={"po_number": "TEST-PO"},
            headers=admin_headers
        )
        assert response.status_code == 404, f"Should return 404, got: {response.status_code}"


class TestApprovedProposalFields:
    """Test that approved proposals show correct fields"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_approved_proposal_has_all_fields(self, admin_headers):
        """Verify approved proposal shows P.O. number and O.S. number"""
        proposal_id = getattr(TestInformarPOWorkflow, 'test_proposal_id', None)
        if not proposal_id:
            pytest.skip("No test proposal created")
        
        response = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "aprovada"
        assert data["po_number"] != ""
        assert data["os_id"] != ""
        assert data["os_number"] != ""
        print(f"Approved proposal fields verified: status={data['status']}, po={data['po_number']}, os={data['os_number']}")


class TestOSNumberFormat:
    """Test O.S. number format: SEQ - PROPOSTA_NUMBER"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_os_number_format(self, admin_headers):
        """Verify O.S. number format is SEQ - PROPOSTA_NUMBER"""
        os_number = getattr(TestInformarPOWorkflow, 'created_os_number', None)
        proposal_number = getattr(TestInformarPOWorkflow, 'test_proposal_number', None)
        
        if not os_number or not proposal_number:
            pytest.skip("No O.S. created from previous tests")
        
        # Format should be like "01 - 2603 - 01" where 01 is seq and 2603 - 01 is proposal number
        parts = os_number.split(" - ", 1)
        assert len(parts) >= 2, f"O.S. number should have format 'SEQ - PROPOSTA_NUMBER', got: {os_number}"
        
        seq_part = parts[0]
        assert seq_part.isdigit() or (len(seq_part) == 2 and seq_part[0] == '0'), f"First part should be sequence number: {seq_part}"
        
        # The rest should contain the proposal number
        rest = " - ".join(parts[1:]) if len(parts) > 1 else parts[1]
        assert proposal_number in os_number, f"O.S. should contain proposal number. OS: {os_number}, Proposal: {proposal_number}"
        print(f"O.S. number format verified: {os_number}")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_cleanup_test_data(self, admin_headers):
        """Clean up test proposals and service orders"""
        # Delete test proposal
        proposal_id = getattr(TestInformarPOWorkflow, 'test_proposal_id', None)
        if proposal_id:
            response = requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=admin_headers)
            print(f"Deleted test proposal: {response.status_code}")
        
        # Delete test O.S.
        os_id = getattr(TestInformarPOWorkflow, 'created_os_id', None)
        if os_id:
            response = requests.delete(f"{BASE_URL}/api/service-orders/{os_id}", headers=admin_headers)
            print(f"Deleted test O.S.: {response.status_code}")
        
        # Clean up any TEST_ prefixed proposals
        response = requests.get(f"{BASE_URL}/api/proposals?year=2026", headers=admin_headers)
        if response.status_code == 200:
            proposals = response.json()
            for p in proposals:
                if p.get("empresa", "").startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/proposals/{p['id']}", headers=admin_headers)
                    print(f"Cleaned up test proposal: {p['empresa']}")
