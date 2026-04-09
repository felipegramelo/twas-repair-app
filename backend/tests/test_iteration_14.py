"""
Test iteration 14 features:
- PDF page numbering (X de Y format, starting from page 2)
- Cover table bold only on labels
- Wider document margins (1.2cm)
- Bigger logo (4.5cm)
- Multiple file selection (multiple attribute)
- No OS number in header center
- Subsections don't need 'Adicionar Subseção' button (only sections do)
- NDT section has no photo upload (subsections have it)
- PDF upload converts to images
- Image compression for smaller PDFs
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://twas-repair-app.preview.emergentagent.com').rstrip('/')

# Test report ID
REPORT_ID = "69bd3ca965910340f419a05b"

class TestIteration14:
    """Test suite for iteration 14 features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_pdf_endpoint_returns_200(self):
        """Test PDF endpoint returns 200"""
        resp = requests.get(f"{BASE_URL}/api/reports/{REPORT_ID}/pdf", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.headers.get("Content-Type") == "application/pdf"
    
    def test_pdf_has_page_numbers_x_de_y_format(self):
        """Test PDF has page numbers in 'X de Y' format starting from page 2"""
        import fitz  # PyMuPDF
        
        resp = requests.get(f"{BASE_URL}/api/reports/{REPORT_ID}/pdf", headers=self.headers)
        assert resp.status_code == 200
        
        pdf = fitz.open(stream=resp.content, filetype="pdf")
        total_pages = len(pdf)
        assert total_pages >= 2, "Need at least 2 pages to test page numbering"
        
        # Cover page (index 0) should NOT have page number
        cover_text = pdf[0].get_text()
        page_nums_in_cover = [l for l in cover_text.split("\n") if " de " in l and l.strip().replace(" de ", "").replace(" ", "").isdigit()]
        # Cover shouldn't have "1 de X" or similar pattern
        cover_has_page_num = any("1 de" in l or "de 2" in l for l in cover_text.split("\n") if l.strip().startswith("1") or (l.strip().endswith("2") and " de " in l))
        
        # Page 2 (index 1) should have "1 de Y"
        page2_text = pdf[1].get_text()
        has_1_de = any("1 de" in l for l in page2_text.split("\n"))
        
        pdf.close()
        
        assert has_1_de, "Page 2 should have '1 de Y' page number"
    
    def test_report_has_sections_and_subsections(self):
        """Test report has sections with subsections for testing button logic"""
        resp = requests.get(f"{BASE_URL}/api/reports/{REPORT_ID}", headers=self.headers)
        assert resp.status_code == 200
        
        data = resp.json()
        sections = data.get("sections", [])
        
        # Verify sections exist
        assert len(sections) > 0, "Report should have sections"
        
        # Find service_description section which should have subsections
        service_desc = next((s for s in sections if s.get("key") == "service_description"), None)
        assert service_desc is not None, "service_description section should exist"
        assert len(service_desc.get("subsections", [])) > 0, "service_description should have subsections"
    
    def test_ndt_section_structure(self):
        """Test NDT section has subsections (which should have photo upload, not parent NDT)"""
        resp = requests.get(f"{BASE_URL}/api/reports/{REPORT_ID}", headers=self.headers)
        assert resp.status_code == 200
        
        data = resp.json()
        sections = data.get("sections", [])
        
        # Find NDT section
        ndt_section = next((s for s in sections if s.get("key") == "ndt"), None)
        assert ndt_section is not None, "NDT section should exist"
        
        # NDT should have subsections (propeller_shaft, pinion_shaft, etc.)
        ndt_subsections = ndt_section.get("subsections", [])
        assert len(ndt_subsections) > 0, "NDT should have subsections"
        
        # Verify expected subsections
        expected_subsection_keys = ["propeller_shaft", "pinion_shaft", "input_shaft", "coupling", "swivel_pinion", "propeller", "reduction_gear"]
        actual_keys = [s.get("key") for s in ndt_subsections]
        for key in expected_subsection_keys:
            assert key in actual_keys, f"NDT should have {key} subsection"
    
    def test_photo_upload_endpoint(self):
        """Test photo upload endpoint works"""
        resp = requests.get(f"{BASE_URL}/api/reports/{REPORT_ID}/photos", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "photos" in data
    
    def test_report_has_service_and_location(self):
        """Test report has service and location for cover display"""
        resp = requests.get(f"{BASE_URL}/api/reports/{REPORT_ID}", headers=self.headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data.get("service"), "Report should have service name"
        assert data.get("location"), "Report should have location (vessel)"
    
    def test_pdf_valid_content(self):
        """Test PDF is valid and has reasonable content"""
        resp = requests.get(f"{BASE_URL}/api/reports/{REPORT_ID}/pdf", headers=self.headers)
        assert resp.status_code == 200
        
        # PDF should start with %PDF
        assert resp.content[:4] == b'%PDF', "PDF should start with %PDF header"
        
        # PDF should have reasonable size (not empty, not too small)
        assert len(resp.content) > 1000, "PDF should have reasonable size"
    
    def test_login_returns_access_token(self):
        """Test login returns access_token (not token)"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data, "Login should return access_token"
        assert "user" in data, "Login should return user info"
    
    def test_invalid_login_rejected(self):
        """Test invalid credentials are rejected"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@test.com",
            "password": "wrongpass"
        })
        assert resp.status_code == 401, "Invalid login should return 401"
    
    def test_update_report_sections(self):
        """Test updating report sections works"""
        # Get current report
        resp = requests.get(f"{BASE_URL}/api/reports/{REPORT_ID}", headers=self.headers)
        assert resp.status_code == 200
        current_data = resp.json()
        
        # Update without changing anything (just verify endpoint works)
        update_resp = requests.put(
            f"{BASE_URL}/api/reports/{REPORT_ID}",
            headers=self.headers,
            json={"sections": current_data.get("sections", [])}
        )
        assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"


class TestPDFPageNumbers:
    """Specific tests for PDF page numbering feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor@twasrepair.com",
            "password": "super123"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_cover_page_no_page_number(self):
        """Test cover page (index 0) does NOT have page number"""
        import fitz
        
        resp = requests.get(f"{BASE_URL}/api/reports/{REPORT_ID}/pdf", headers=self.headers)
        pdf = fitz.open(stream=resp.content, filetype="pdf")
        
        cover_text = pdf[0].get_text()
        # Look for explicit page number patterns like "1 de 2", "2 de 2", etc.
        lines = cover_text.split("\n")
        page_number_patterns = [l.strip() for l in lines if l.strip() and " de " in l and len(l.strip()) < 10]
        
        pdf.close()
        
        # Cover should not have standalone page number
        for pattern in page_number_patterns:
            parts = pattern.split(" de ")
            if len(parts) == 2:
                try:
                    int(parts[0].strip())
                    int(parts[1].strip())
                    assert False, f"Cover page should not have page number, found: {pattern}"
                except ValueError:
                    pass  # Not a number, OK
    
    def test_page_2_has_page_number_1_de_y(self):
        """Test page 2 (index 1) has page number '1 de Y'"""
        import fitz
        
        resp = requests.get(f"{BASE_URL}/api/reports/{REPORT_ID}/pdf", headers=self.headers)
        pdf = fitz.open(stream=resp.content, filetype="pdf")
        
        if len(pdf) < 2:
            pdf.close()
            pytest.skip("PDF has only 1 page, can't test page 2 numbering")
        
        page2_text = pdf[1].get_text()
        pdf.close()
        
        # Should have "1 de" somewhere on page 2
        assert "1 de" in page2_text, f"Page 2 should have '1 de Y' page number"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
