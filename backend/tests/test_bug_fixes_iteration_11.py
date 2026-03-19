"""
Test suite for bug fixes in iteration 11:
1. Service orders visible in create report dropdown
2. Report creation with periodo_inicio and periodo_fim
3. Report GET returns all data correctly
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://report-hub-local.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')


class TestServiceOrdersAPI:
    """Test that service orders are accessible for dropdown population"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as supervisor and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_service_orders_returns_all(self):
        """Verify GET /api/service-orders returns all service orders"""
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1, "Should have at least one service order"
        
        # Verify structure
        for so in data:
            assert "id" in so
            assert "os_number" in so
            assert "client" in so
            assert "location" in so
            assert "service" in so
            
        print(f"Found {len(data)} service orders")
        

class TestReportCreationWithPeriod:
    """Test report creation with periodo_inicio and periodo_fim"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get service order ID"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get first service order
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        assert so_response.status_code == 200
        self.service_orders = so_response.json()
        assert len(self.service_orders) > 0
        self.os_id = self.service_orders[0]["id"]
        
        # Track created report for cleanup
        self.created_report_id = None
        
    def teardown_method(self):
        """Cleanup created reports"""
        if self.created_report_id:
            requests.delete(f"{BASE_URL}/api/reports/{self.created_report_id}", headers=self.headers)
    
    def test_create_service_report_with_dates(self):
        """Test creating a service report with period dates"""
        response = requests.post(f"{BASE_URL}/api/reports", headers=self.headers, json={
            "report_type": "service",
            "os_id": self.os_id,
            "periodo_inicio": "10/03/2026",
            "periodo_fim": "20/03/2026",
            "executado_por": "Test User"
        })
        
        assert response.status_code == 200, f"Failed to create report: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["report_type"] == "service"
        assert data["status"] == "draft"
        
        self.created_report_id = data["id"]
        print(f"Created report with ID: {self.created_report_id}")
        
        # Verify the report was created with correct dates
        get_response = requests.get(f"{BASE_URL}/api/reports/{self.created_report_id}", headers=self.headers)
        assert get_response.status_code == 200
        
        report_data = get_response.json()
        assert report_data["periodo_inicio"] == "10/03/2026"
        assert report_data["periodo_fim"] == "20/03/2026"
        assert report_data["executado_por"] == "Test User"
        
    def test_create_daily_report_with_dates(self):
        """Test creating a daily report with period dates"""
        response = requests.post(f"{BASE_URL}/api/reports", headers=self.headers, json={
            "report_type": "daily",
            "os_id": self.os_id,
            "periodo_inicio": "15/03/2026",
            "periodo_fim": "15/03/2026",
            "executado_por": "Daily Test User"
        })
        
        assert response.status_code == 200, f"Failed to create report: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["report_type"] == "daily"
        
        self.created_report_id = data["id"]
        
        # Verify
        get_response = requests.get(f"{BASE_URL}/api/reports/{self.created_report_id}", headers=self.headers)
        assert get_response.status_code == 200
        report_data = get_response.json()
        assert report_data["periodo_inicio"] == "15/03/2026"


class TestReportSectionsStructure:
    """Test that report sections have correct structure for dynamic numbering"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and create a test report"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get first service order
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        self.os_id = so_response.json()[0]["id"]
        
        # Create test report
        create_response = requests.post(f"{BASE_URL}/api/reports", headers=self.headers, json={
            "report_type": "service",
            "os_id": self.os_id,
            "periodo_inicio": "01/01/2026",
            "periodo_fim": "31/01/2026"
        })
        assert create_response.status_code == 200
        self.report_id = create_response.json()["id"]
        
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'report_id') and self.report_id:
            requests.delete(f"{BASE_URL}/api/reports/{self.report_id}", headers=self.headers)
    
    def test_service_report_has_correct_sections(self):
        """Verify service report has expected sections structure"""
        response = requests.get(f"{BASE_URL}/api/reports/{self.report_id}", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        sections = data.get("sections", [])
        
        # Service reports should have these main sections
        expected_keys = ["introduction", "equipment", "objective", "service_description"]
        section_keys = [s["key"] for s in sections]
        
        for key in expected_keys:
            assert key in section_keys, f"Missing section: {key}"
            
        # Check service_description has subsections with FOTOS
        service_desc = next((s for s in sections if s["key"] == "service_description"), None)
        assert service_desc is not None
        assert "subsections" in service_desc
        
        subsections = service_desc["subsections"]
        assert len(subsections) >= 2, "Should have DESMONTAGEM and MONTAGEM"
        
        # Check for FOTOS subsections
        for sub in subsections:
            if sub["key"] in ["disassembly", "assembly"]:
                assert "subsections" in sub
                fotos_sub = next((ss for ss in sub.get("subsections", []) if "photos" in ss["key"] or "fotos" in ss["key"].lower()), None)
                assert fotos_sub is not None, f"FOTOS subsection missing in {sub['key']}"
                
        print("Service report sections structure verified")
        
    def test_section_enabled_field(self):
        """Verify sections have enabled field for dynamic numbering"""
        response = requests.get(f"{BASE_URL}/api/reports/{self.report_id}", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        sections = data.get("sections", [])
        
        # All sections should have enabled field
        for section in sections:
            assert "enabled" in section, f"Section {section.get('key')} missing 'enabled' field"
            assert isinstance(section["enabled"], bool)
            
        # Check that some sections are enabled by default and some disabled
        enabled_count = sum(1 for s in sections if s["enabled"])
        disabled_count = sum(1 for s in sections if not s["enabled"])
        
        assert enabled_count >= 4, "Should have at least 4 enabled sections by default"
        print(f"Sections: {enabled_count} enabled, {disabled_count} disabled")


class TestReportUpdate:
    """Test report update functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and create test report"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        self.os_id = so_response.json()[0]["id"]
        
        create_response = requests.post(f"{BASE_URL}/api/reports", headers=self.headers, json={
            "report_type": "service",
            "os_id": self.os_id,
            "periodo_inicio": "01/01/2026",
            "periodo_fim": "31/01/2026"
        })
        self.report_id = create_response.json()["id"]
        
    def teardown_method(self):
        if hasattr(self, 'report_id') and self.report_id:
            requests.delete(f"{BASE_URL}/api/reports/{self.report_id}", headers=self.headers)
    
    def test_update_sections_enabled_state(self):
        """Test toggling section enabled state"""
        # Get current sections
        get_response = requests.get(f"{BASE_URL}/api/reports/{self.report_id}", headers=self.headers)
        sections = get_response.json()["sections"]
        
        # Disable the second section (EQUIPAMENTOS)
        for i, section in enumerate(sections):
            if section["key"] == "equipment":
                sections[i]["enabled"] = False
                break
                
        # Update report
        update_response = requests.put(f"{BASE_URL}/api/reports/{self.report_id}", 
            headers=self.headers, json={"sections": sections})
        assert update_response.status_code == 200
        
        # Verify update
        verify_response = requests.get(f"{BASE_URL}/api/reports/{self.report_id}", headers=self.headers)
        updated_sections = verify_response.json()["sections"]
        
        equipment_section = next(s for s in updated_sections if s["key"] == "equipment")
        assert equipment_section["enabled"] == False, "Equipment section should be disabled"
        
        print("Section enabled state update verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
