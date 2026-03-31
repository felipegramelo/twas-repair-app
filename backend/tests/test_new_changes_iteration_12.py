"""
Test new changes for iteration 12:
1. Bullet-free templates for introduction, equipment, objective sections
2. Período e Informações fields are optional (not removed from API, but frontend removed from edit screen)
3. Adicionar Subseção functionality (section update with new subsections)
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://proposal-builder-56.preview.emergentagent.com')

class TestSession:
    """Shared test session with authentication"""
    token = None
    headers = None
    
    @classmethod
    def get_auth_headers(cls):
        if cls.token:
            return cls.headers
        
        # Login as supervisor
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        cls.token = data["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}
        return cls.headers


class TestBulletFreeTemplates:
    """Test that new reports have bullet-free templates for introduction, equipment, objective"""
    
    def test_get_service_orders(self):
        """Get service orders to use for report creation"""
        headers = TestSession.get_auth_headers()
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        assert response.status_code == 200, f"Failed to get service orders: {response.text}"
        orders = response.json()
        assert len(orders) > 0, "No service orders found"
        print(f"Found {len(orders)} service orders")
        return orders[0]["id"]
    
    def test_create_new_service_report_has_bullet_free_templates(self):
        """Create a new service report and verify templates have NO bullet markers"""
        headers = TestSession.get_auth_headers()
        
        # First get an OS
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        os_id = response.json()[0]["id"]
        
        # Create a new report
        response = requests.post(f"{BASE_URL}/api/reports", headers=headers, json={
            "report_type": "service",
            "os_id": os_id
        })
        assert response.status_code == 200, f"Failed to create report: {response.text}"
        report_data = response.json()
        report_id = report_data["id"]
        print(f"Created report: {report_id}")
        
        # Get the full report to check sections
        response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        assert response.status_code == 200, f"Failed to get report: {response.text}"
        full_report = response.json()
        
        sections = full_report.get("sections", [])
        assert len(sections) > 0, "Report has no sections"
        
        # Check introduction section - should NOT have bullets (•)
        intro_section = next((s for s in sections if s["key"] == "introduction"), None)
        assert intro_section is not None, "Introduction section not found"
        intro_content = intro_section.get("content", "")
        assert "•" not in intro_content, f"Introduction should NOT have bullet markers. Content: {intro_content[:200]}"
        print(f"✅ Introduction section is bullet-free: {intro_content[:100]}...")
        
        # Check equipment section - should NOT have bullets (•)
        equip_section = next((s for s in sections if s["key"] == "equipment"), None)
        assert equip_section is not None, "Equipment section not found"
        equip_content = equip_section.get("content", "")
        assert "•" not in equip_content, f"Equipment should NOT have bullet markers. Content: {equip_content[:200]}"
        print(f"✅ Equipment section is bullet-free: {equip_content[:100]}...")
        
        # Check objective section - should NOT have bullets (•)
        obj_section = next((s for s in sections if s["key"] == "objective"), None)
        assert obj_section is not None, "Objective section not found"
        obj_content = obj_section.get("content", "")
        assert "•" not in obj_content, f"Objective should NOT have bullet markers. Content: {obj_content[:200]}"
        print(f"✅ Objective section is bullet-free: {obj_content[:100]}...")
        
        # Clean up - delete the test report
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        print(f"Cleaned up test report: {report_id}")
        
    def test_create_new_daily_report_has_bullet_free_templates(self):
        """Create a new daily report and verify templates have NO bullet markers"""
        headers = TestSession.get_auth_headers()
        
        # First get an OS
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        os_id = response.json()[0]["id"]
        
        # Create a new daily report
        response = requests.post(f"{BASE_URL}/api/reports", headers=headers, json={
            "report_type": "daily",
            "os_id": os_id
        })
        assert response.status_code == 200, f"Failed to create daily report: {response.text}"
        report_data = response.json()
        report_id = report_data["id"]
        print(f"Created daily report: {report_id}")
        
        # Get the full report to check sections
        response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        assert response.status_code == 200, f"Failed to get report: {response.text}"
        full_report = response.json()
        
        sections = full_report.get("sections", [])
        
        # Check introduction section - should NOT have bullets
        intro_section = next((s for s in sections if s["key"] == "introduction"), None)
        assert intro_section is not None, "Introduction section not found in daily report"
        intro_content = intro_section.get("content", "")
        assert "•" not in intro_content, f"Introduction should NOT have bullet markers"
        print(f"✅ Daily report introduction is bullet-free")
        
        # Check equipment section - should NOT have bullets
        equip_section = next((s for s in sections if s["key"] == "equipment"), None)
        assert equip_section is not None, "Equipment section not found in daily report"
        equip_content = equip_section.get("content", "")
        assert "•" not in equip_content, f"Equipment should NOT have bullet markers"
        print(f"✅ Daily report equipment is bullet-free")
        
        # Check objective section - should NOT have bullets
        obj_section = next((s for s in sections if s["key"] == "objective"), None)
        assert obj_section is not None, "Objective section not found in daily report"
        obj_content = obj_section.get("content", "")
        assert "•" not in obj_content, f"Objective should NOT have bullet markers"
        print(f"✅ Daily report objective is bullet-free")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        print(f"Cleaned up daily report: {report_id}")


class TestSubsectionAddition:
    """Test adding subsections to existing sections"""
    
    def test_update_report_with_new_subsection(self):
        """Test that we can add a new subsection to an existing section"""
        headers = TestSession.get_auth_headers()
        
        # First get an OS
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        os_id = response.json()[0]["id"]
        
        # Create a new report
        response = requests.post(f"{BASE_URL}/api/reports", headers=headers, json={
            "report_type": "service",
            "os_id": os_id
        })
        assert response.status_code == 200
        report_id = response.json()["id"]
        
        # Get the report
        response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        full_report = response.json()
        sections = full_report.get("sections", [])
        
        # Find the introduction section and add a subsection
        for i, section in enumerate(sections):
            if section["key"] == "introduction":
                # Add a new subsection
                new_subsection = {
                    "key": f"sub_{int(__import__('time').time() * 1000)}",
                    "number": "",
                    "title": "TEST SUBSECTION",
                    "content": "Test content for subsection",
                    "enabled": True,
                    "subsections": []
                }
                sections[i]["subsections"] = sections[i].get("subsections", []) + [new_subsection]
                break
        
        # Update the report with the new subsection
        response = requests.put(f"{BASE_URL}/api/reports/{report_id}", headers=headers, json={
            "sections": sections
        })
        assert response.status_code == 200, f"Failed to update report: {response.text}"
        print("✅ Successfully added subsection to report")
        
        # Verify the subsection was saved
        response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        updated_report = response.json()
        updated_sections = updated_report.get("sections", [])
        
        intro_section = next((s for s in updated_sections if s["key"] == "introduction"), None)
        assert intro_section is not None
        assert len(intro_section.get("subsections", [])) > 0, "Subsection was not saved"
        
        test_subsection = next((sub for sub in intro_section["subsections"] if sub["title"] == "TEST SUBSECTION"), None)
        assert test_subsection is not None, "Test subsection not found after update"
        print("✅ Subsection was persisted correctly")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=headers)


class TestSectionsModalFunctionality:
    """Test that section toggle (enable/disable) works correctly"""
    
    def test_toggle_section_enabled_state(self):
        """Test that we can enable/disable sections"""
        headers = TestSession.get_auth_headers()
        
        # Get an OS
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        os_id = response.json()[0]["id"]
        
        # Create a report
        response = requests.post(f"{BASE_URL}/api/reports", headers=headers, json={
            "report_type": "service",
            "os_id": os_id
        })
        assert response.status_code == 200
        report_id = response.json()["id"]
        
        # Get the report
        response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        full_report = response.json()
        sections = full_report.get("sections", [])
        
        # Disable the EQUIPAMENTOS section
        for i, section in enumerate(sections):
            if section["key"] == "equipment":
                sections[i]["enabled"] = False
                break
        
        # Update the report
        response = requests.put(f"{BASE_URL}/api/reports/{report_id}", headers=headers, json={
            "sections": sections
        })
        assert response.status_code == 200
        
        # Verify the change
        response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        updated_report = response.json()
        
        equip_section = next((s for s in updated_report["sections"] if s["key"] == "equipment"), None)
        assert equip_section is not None
        assert equip_section["enabled"] == False, "Equipment section should be disabled"
        print("✅ Section toggle works correctly")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=headers)


class TestPDFGeneration:
    """Test that PDF generation still works"""
    
    def test_pdf_endpoint_exists(self):
        """Test that PDF endpoint returns 200"""
        headers = TestSession.get_auth_headers()
        
        # Get reports list
        response = requests.get(f"{BASE_URL}/api/reports", headers=headers)
        assert response.status_code == 200
        reports = response.json().get("reports", [])
        
        if len(reports) > 0:
            report_id = reports[0]["id"]
            # Try to get PDF
            response = requests.get(f"{BASE_URL}/api/reports/{report_id}/pdf", headers=headers)
            assert response.status_code == 200, f"PDF generation failed: {response.status_code}"
            assert response.headers.get("content-type") == "application/pdf"
            print("✅ PDF generation endpoint works")
        else:
            pytest.skip("No reports to test PDF generation")


class TestSaveReport:
    """Test that saving a report works"""
    
    def test_save_report_without_errors(self):
        """Test that report update (save) works without errors"""
        headers = TestSession.get_auth_headers()
        
        # Get an OS
        response = requests.get(f"{BASE_URL}/api/service-orders", headers=headers)
        os_id = response.json()[0]["id"]
        
        # Create a report
        response = requests.post(f"{BASE_URL}/api/reports", headers=headers, json={
            "report_type": "service",
            "os_id": os_id
        })
        assert response.status_code == 200
        report_id = response.json()["id"]
        
        # Get the report
        response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        full_report = response.json()
        
        # Modify a section content
        sections = full_report.get("sections", [])
        for i, section in enumerate(sections):
            if section["key"] == "introduction":
                sections[i]["content"] = "Modified introduction content for test"
                break
        
        # Save (update) the report
        response = requests.put(f"{BASE_URL}/api/reports/{report_id}", headers=headers, json={
            "sections": sections
        })
        assert response.status_code == 200, f"Save failed: {response.text}"
        
        # Verify the change persisted
        response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)
        updated_report = response.json()
        
        intro_section = next((s for s in updated_report["sections"] if s["key"] == "introduction"), None)
        assert intro_section["content"] == "Modified introduction content for test"
        print("✅ Report save works correctly")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
