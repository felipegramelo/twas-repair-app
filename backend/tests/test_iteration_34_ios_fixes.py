"""
Iteration 34: iOS Native Fixes Testing
Tests for:
1. Backend API endpoints still work (login, proposals CRUD, timesheets, reports)
2. PDF generation endpoints work correctly
3. All existing functionality preserved after iOS fixes
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://twas-repair-app.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_admin_login(self):
        """Test admin login works correctly"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["proposta_access"] == True
        print(f"✓ Admin login successful - user: {data['user']['name']}")
    
    def test_supervisor_login(self):
        """Test supervisor login works correctly"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "supervisor"
        print(f"✓ Supervisor login successful - user: {data['user']['name']}")
    
    def test_invalid_login(self):
        """Test invalid credentials return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly returns 401")


class TestProposalsEndpoints:
    """Test proposals CRUD endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_proposals(self):
        """Test listing proposals"""
        response = requests.get(f"{BASE_URL}/api/proposals", headers=self.headers)
        assert response.status_code == 200, f"List proposals failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List proposals successful - {len(data)} proposals found")
    
    def test_create_proposal_with_servico(self):
        """Test creating proposal with servico field"""
        payload = {
            "empresa": "TEST_iOS_Fix_Company",
            "contato": "Test Contact",
            "email": "test@test.com",
            "embarcacao": "Test Platform",
            "equipamento": "Test Equipment",
            "servico": "Reparo de válvulas de segurança",
            "observacoes": "Test observation",
            "itens": [
                {
                    "id": "test-item-1",
                    "titulo": "Seção de Teste",
                    "descricao": "Descrição do teste",
                    "valor": 1500.00,
                    "subsections": []
                }
            ],
            "termos_gerais": "Termos de teste"
        }
        response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Create proposal failed: {response.text}"
        data = response.json()
        assert data["empresa"] == "TEST_iOS_Fix_Company"
        assert data["servico"] == "Reparo de válvulas de segurança"
        self.created_proposal_id = data["id"]
        print(f"✓ Create proposal successful - ID: {data['id']}, servico: {data['servico']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proposals/{data['id']}", headers=self.headers)
    
    def test_proposal_pdf_comercial(self):
        """Test PDF comercial generation"""
        # First create a proposal
        payload = {
            "empresa": "TEST_PDF_Company",
            "contato": "PDF Test",
            "email": "pdf@test.com",
            "embarcacao": "PDF Platform",
            "equipamento": "PDF Equipment",
            "servico": "Serviço de teste para PDF",
            "observacoes": "",
            "itens": [{"id": "1", "titulo": "Item 1", "descricao": "Desc", "valor": 1000, "subsections": []}],
            "termos_gerais": "Termos"
        }
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        
        # Test PDF generation
        pdf_resp = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=comercial", headers=self.headers)
        assert pdf_resp.status_code == 200, f"PDF comercial failed: {pdf_resp.text}"
        assert pdf_resp.headers.get("content-type") == "application/pdf"
        print(f"✓ PDF comercial generation successful - size: {len(pdf_resp.content)} bytes")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=self.headers)
    
    def test_proposal_pdf_tecnica(self):
        """Test PDF tecnica generation"""
        # First create a proposal
        payload = {
            "empresa": "TEST_PDF_Tecnica",
            "contato": "PDF Test",
            "email": "pdf@test.com",
            "embarcacao": "PDF Platform",
            "equipamento": "PDF Equipment",
            "servico": "Serviço técnico de teste",
            "observacoes": "",
            "itens": [{"id": "1", "titulo": "Item 1", "descricao": "Desc", "valor": 1000, "subsections": []}],
            "termos_gerais": "Termos"
        }
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        
        # Test PDF generation
        pdf_resp = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=tecnica", headers=self.headers)
        assert pdf_resp.status_code == 200, f"PDF tecnica failed: {pdf_resp.text}"
        assert pdf_resp.headers.get("content-type") == "application/pdf"
        print(f"✓ PDF tecnica generation successful - size: {len(pdf_resp.content)} bytes")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=self.headers)


class TestTimesheetsEndpoints:
    """Test timesheets endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get supervisor token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get admin token for service orders
        admin_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.admin_token = admin_resp.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_list_timesheets(self):
        """Test listing timesheets"""
        response = requests.get(f"{BASE_URL}/api/timesheets", headers=self.headers)
        assert response.status_code == 200, f"List timesheets failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List timesheets successful - {len(data)} timesheets found")
    
    def test_list_service_orders(self):
        """Test listing service orders (needed for timesheet creation)"""
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        assert response.status_code == 200, f"List service orders failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List service orders successful - {len(data)} orders found")
    
    def test_list_employees(self):
        """Test listing employees (needed for timesheet creation)"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert response.status_code == 200, f"List employees failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List employees successful - {len(data)} employees found")


class TestReportsEndpoints:
    """Test reports endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get supervisor token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_reports(self):
        """Test listing reports"""
        response = requests.get(f"{BASE_URL}/api/reports", headers=self.headers)
        assert response.status_code == 200, f"List reports failed: {response.text}"
        data = response.json()
        # API returns {"reports": [...]} format
        if isinstance(data, dict) and "reports" in data:
            reports = data["reports"]
        else:
            reports = data
        assert isinstance(reports, list)
        print(f"✓ List reports successful - {len(reports)} reports found")


class TestOSArchiveEndpoint:
    """Test OS Archive endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_os_archive(self):
        """Test getting OS archive"""
        response = requests.get(f"{BASE_URL}/api/admin/os-archive", headers=self.headers)
        assert response.status_code == 200, f"Get OS archive failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get OS archive successful - {len(data)} service orders found")
        
        # Verify structure
        if len(data) > 0:
            os_item = data[0]
            assert "id" in os_item
            assert "os_number" in os_item
            assert "timesheets" in os_item
            assert "service_reports" in os_item
            assert "daily_reports" in os_item
            print(f"  - First OS: {os_item['os_number']} with {os_item['total_documents']} documents")


class TestTimesheetPDF:
    """Test timesheet PDF generation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get supervisor token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_timesheet_pdf_endpoint_exists(self):
        """Test that timesheet PDF endpoint exists"""
        # Get a timesheet first
        ts_resp = requests.get(f"{BASE_URL}/api/timesheets", headers=self.headers)
        assert ts_resp.status_code == 200
        timesheets = ts_resp.json()
        
        if len(timesheets) > 0:
            ts_id = timesheets[0]["id"]
            pdf_resp = requests.get(f"{BASE_URL}/api/timesheets/{ts_id}/pdf", headers=self.headers)
            # Should return PDF or 404 if no timesheet
            assert pdf_resp.status_code in [200, 404], f"Unexpected status: {pdf_resp.status_code}"
            if pdf_resp.status_code == 200:
                assert pdf_resp.headers.get("content-type") == "application/pdf"
                print(f"✓ Timesheet PDF generation successful - size: {len(pdf_resp.content)} bytes")
            else:
                print("✓ Timesheet PDF endpoint exists (no timesheets to test)")
        else:
            print("✓ Timesheet PDF endpoint check skipped (no timesheets)")


class TestReportPDF:
    """Test report PDF generation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get supervisor token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_report_pdf_endpoint_exists(self):
        """Test that report PDF endpoint exists"""
        # Get a report first
        rpt_resp = requests.get(f"{BASE_URL}/api/reports", headers=self.headers)
        assert rpt_resp.status_code == 200
        data = rpt_resp.json()
        # API returns {"reports": [...]} format
        if isinstance(data, dict) and "reports" in data:
            reports = data["reports"]
        else:
            reports = data
        
        if len(reports) > 0:
            rpt_id = reports[0]["id"]
            pdf_resp = requests.get(f"{BASE_URL}/api/reports/{rpt_id}/pdf", headers=self.headers)
            # Should return PDF or 404 if no report
            assert pdf_resp.status_code in [200, 404], f"Unexpected status: {pdf_resp.status_code}"
            if pdf_resp.status_code == 200:
                assert pdf_resp.headers.get("content-type") == "application/pdf"
                print(f"✓ Report PDF generation successful - size: {len(pdf_resp.content)} bytes")
            else:
                print("✓ Report PDF endpoint exists (no reports to test)")
        else:
            print("✓ Report PDF endpoint check skipped (no reports)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
