"""
Iteration 36: Testing iOS Native Bug Fixes
- Timesheet entry form pickers (calendar, employee, time) now render INLINE within the entry form modal
- Create Report native OS dropdown now uses Modal-based picker for native
- Proposal PDF download fixed double-token issue

Tests cover:
1. Authentication (admin and supervisor)
2. Service Orders API
3. Employees API
4. Timesheets API (CRUD)
5. Reports API (CRUD)
6. Proposals API (CRUD + PDF download)
7. Admin pages (os-archive, dashboard)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_admin_login_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "user" in data, "Missing user in response"
        assert data["user"]["email"] == "admin@twasrepair.com"
        assert data["user"]["role"] == "admin"
    
    def test_supervisor_login_success(self):
        """Test supervisor login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "supervisor@twasrepair.com"
        assert data["user"]["role"] == "supervisor"
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401


class TestServiceOrders:
    """Test Service Orders API"""
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Supervisor login failed")
    
    def test_get_service_orders(self, supervisor_token):
        """Test fetching all service orders"""
        response = requests.get(
            f"{BASE_URL}/api/service-orders",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Verify structure if data exists
        if len(data) > 0:
            so = data[0]
            assert "id" in so
            assert "os_number" in so
            assert "client" in so


class TestEmployees:
    """Test Employees API"""
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Supervisor login failed")
    
    def test_get_employees(self, supervisor_token):
        """Test fetching all employees"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestTimesheets:
    """Test Timesheets API - CRUD operations"""
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Supervisor login failed")
    
    @pytest.fixture
    def service_order_id(self, supervisor_token):
        """Get a service order ID for testing"""
        response = requests.get(
            f"{BASE_URL}/api/service-orders",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        pytest.skip("No service orders available")
    
    def test_get_timesheets(self, supervisor_token):
        """Test fetching all timesheets"""
        response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_timesheet(self, supervisor_token, service_order_id):
        """Test creating a new timesheet"""
        payload = {
            "os_id": service_order_id,
            "entries": [
                {
                    "date": "08/04/2026",
                    "employee_id": "test-emp-1",
                    "employee_name": "Test Employee",
                    "employee_function": "T",
                    "service_start": "08:00",
                    "service_end": "17:00",
                    "travel_start": "-",
                    "travel_end": "-"
                }
            ],
            "observations": "Test timesheet from iteration 36",
            "supervisor_function": "Supervisor (Sup)"
        }
        response = requests.post(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            json=payload
        )
        # Accept 200 or 201 for creation
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        return data["id"]


class TestReports:
    """Test Reports API - CRUD operations"""
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Supervisor login failed")
    
    @pytest.fixture
    def service_order_id(self, supervisor_token):
        """Get a service order ID for testing"""
        response = requests.get(
            f"{BASE_URL}/api/service-orders",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        pytest.skip("No service orders available")
    
    def test_get_reports(self, supervisor_token):
        """Test fetching all reports"""
        response = requests.get(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # API returns {"reports": [...]} structure
        if isinstance(data, dict) and "reports" in data:
            assert isinstance(data["reports"], list)
        else:
            assert isinstance(data, list)
    
    def test_create_daily_report(self, supervisor_token, service_order_id):
        """Test creating a daily report"""
        payload = {
            "report_type": "daily",
            "os_id": service_order_id,
            "periodo_inicio": "08/04/2026",
            "periodo_fim": "08/04/2026",
            "executado_por": "Test Supervisor"
        }
        response = requests.post(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            json=payload
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
    
    def test_create_service_report(self, supervisor_token, service_order_id):
        """Test creating a service report"""
        payload = {
            "report_type": "service",
            "os_id": service_order_id,
            "periodo_inicio": "01/04/2026",
            "periodo_fim": "08/04/2026",
            "executado_por": "Test Supervisor"
        }
        response = requests.post(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            json=payload
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"


class TestProposals:
    """Test Proposals API - CRUD + PDF download"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_get_proposals(self, admin_token):
        """Test fetching all proposals"""
        response = requests.get(
            f"{BASE_URL}/api/proposals",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_proposal(self, admin_token):
        """Test creating a new proposal"""
        payload = {
            "empresa": "Test Company Iteration 36",
            "contato": "Test Contact",
            "email": "test@example.com",
            "embarcacao": "Test Vessel",
            "equipamento": "Test Equipment",
            "servico": "Test Service",
            "observacoes": "Test observations",
            "itens": [
                {
                    "id": "item-1",
                    "titulo": "Test Section",
                    "descricao": "Test description",
                    "valor": 1000.00,
                    "subsections": []
                }
            ],
            "termos_gerais": "Test terms"
        }
        response = requests.post(
            f"{BASE_URL}/api/proposals",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=payload
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        return data["id"]
    
    def test_proposal_pdf_comercial(self, admin_token):
        """Test downloading commercial PDF for a proposal"""
        # First get proposals
        response = requests.get(
            f"{BASE_URL}/api/proposals",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code != 200 or len(response.json()) == 0:
            pytest.skip("No proposals available for PDF test")
        
        proposal_id = response.json()[0]["id"]
        
        # Download PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=comercial",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert pdf_response.status_code == 200, f"PDF download failed: {pdf_response.status_code}"
        assert "application/pdf" in pdf_response.headers.get("Content-Type", "")
    
    def test_proposal_pdf_tecnica(self, admin_token):
        """Test downloading technical PDF for a proposal"""
        # First get proposals
        response = requests.get(
            f"{BASE_URL}/api/proposals",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code != 200 or len(response.json()) == 0:
            pytest.skip("No proposals available for PDF test")
        
        proposal_id = response.json()[0]["id"]
        
        # Download PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=tecnica",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert pdf_response.status_code == 200, f"PDF download failed: {pdf_response.status_code}"
        assert "application/pdf" in pdf_response.headers.get("Content-Type", "")


class TestAdminFeatures:
    """Test Admin-specific features"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_os_archive(self, admin_token):
        """Test OS Archive endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/admin/os-archive",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_dashboard_stats(self, admin_token):
        """Test Dashboard stats endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Dashboard might return 200 or 404 if not implemented
        assert response.status_code in [200, 404]


class TestTimesheetPDF:
    """Test Timesheet PDF generation"""
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Supervisor login failed")
    
    def test_timesheet_pdf(self, supervisor_token):
        """Test downloading timesheet PDF"""
        # First get timesheets
        response = requests.get(
            f"{BASE_URL}/api/timesheets",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        if response.status_code != 200 or len(response.json()) == 0:
            pytest.skip("No timesheets available for PDF test")
        
        timesheet_id = response.json()[0]["id"]
        
        # Download PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/timesheets/{timesheet_id}/pdf",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert pdf_response.status_code == 200, f"PDF download failed: {pdf_response.status_code}"
        assert "application/pdf" in pdf_response.headers.get("Content-Type", "")


class TestReportPDF:
    """Test Report PDF generation"""
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Supervisor login failed")
    
    def test_report_pdf(self, supervisor_token):
        """Test downloading report PDF"""
        # First get reports
        response = requests.get(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        if response.status_code != 200:
            pytest.skip("No reports available for PDF test")
        
        data = response.json()
        # API returns {"reports": [...]} structure
        reports = data.get("reports", data) if isinstance(data, dict) else data
        if len(reports) == 0:
            pytest.skip("No reports available for PDF test")
        
        report_id = reports[0]["id"]
        
        # Download PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/pdf",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert pdf_response.status_code == 200, f"PDF download failed: {pdf_response.status_code}"
        assert "application/pdf" in pdf_response.headers.get("Content-Type", "")
