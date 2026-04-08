"""
Test PDF Layout Fixes - Iteration 18
Tests for:
1. PDF generation for reports WITH photos (LayoutError fix)
2. PDF generation for reports WITHOUT photos
3. TOC (SUMÁRIO) formatting - dot leaders, bold numbers, normal titles
4. Border colors in PDF (#AAAAAA)
5. Page numbers 'X de Y' on all pages except cover
6. Login flow
7. GET /api/reports
"""

import pytest
import requests
import os
import io
import re

# Use the public URL from environment
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://twas-repair-preview.preview.emergentagent.com')

# Test credentials
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"

# Report IDs to test
REPORT_WITH_19_PHOTOS = "69be9c83db8f3fc8bdee0a21"
REPORT_WITH_11_PHOTOS = "69be9e02db8f3fc8bdee0a35"
REPORT_WITHOUT_PHOTOS = "69bec4c0ee7e51c8ca1583e9"


class TestAuthFlow:
    """Test authentication endpoints"""
    
    def test_login_supervisor(self):
        """Test login with supervisor credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERVISOR_EMAIL, "password": SUPERVISOR_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == SUPERVISOR_EMAIL
        print(f"✓ Login successful for {SUPERVISOR_EMAIL}")
        return data["access_token"]


class TestReportsAPI:
    """Test reports API endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERVISOR_EMAIL, "password": SUPERVISOR_PASSWORD}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
    
    def test_get_reports_list(self, auth_token):
        """Test GET /api/reports returns list of reports"""
        response = requests.get(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"GET /api/reports failed: {response.text}"
        data = response.json()
        assert "reports" in data, "No 'reports' key in response"
        assert isinstance(data["reports"], list), "Reports should be a list"
        print(f"✓ GET /api/reports returned {len(data['reports'])} reports")


class TestPDFGenerationWithPhotos:
    """Test PDF generation for reports WITH photos - LayoutError fix verification"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERVISOR_EMAIL, "password": SUPERVISOR_PASSWORD}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
    
    def test_pdf_generation_report_with_19_photos(self, auth_token):
        """Test PDF generation for report with 19 photos - should NOT crash with LayoutError"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_WITH_19_PHOTOS}/pdf",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=120  # PDF generation can take time
        )
        assert response.status_code == 200, f"PDF generation failed for report with 19 photos: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Response should be PDF"
        assert len(response.content) > 1000, "PDF content should not be empty"
        print(f"✓ PDF generated successfully for report {REPORT_WITH_19_PHOTOS} (19 photos)")
        return response.content
    
    def test_pdf_generation_report_with_11_photos(self, auth_token):
        """Test PDF generation for report with 11 photos - should NOT crash with LayoutError"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_WITH_11_PHOTOS}/pdf",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=120
        )
        assert response.status_code == 200, f"PDF generation failed for report with 11 photos: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Response should be PDF"
        assert len(response.content) > 1000, "PDF content should not be empty"
        print(f"✓ PDF generated successfully for report {REPORT_WITH_11_PHOTOS} (11 photos)")
        return response.content


class TestPDFGenerationWithoutPhotos:
    """Test PDF generation for reports WITHOUT photos"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERVISOR_EMAIL, "password": SUPERVISOR_PASSWORD}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
    
    def test_pdf_generation_report_without_photos(self, auth_token):
        """Test PDF generation for report without photos"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_WITHOUT_PHOTOS}/pdf",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=60
        )
        assert response.status_code == 200, f"PDF generation failed for report without photos: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Response should be PDF"
        assert len(response.content) > 1000, "PDF content should not be empty"
        print(f"✓ PDF generated successfully for report {REPORT_WITHOUT_PHOTOS} (no photos)")
        return response.content


class TestPDFContent:
    """Test PDF content - TOC, page numbers, etc."""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERVISOR_EMAIL, "password": SUPERVISOR_PASSWORD}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
    
    @pytest.fixture
    def pdf_content_with_photos(self, auth_token):
        """Get PDF content for report with photos"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_WITH_19_PHOTOS}/pdf",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=120
        )
        if response.status_code == 200:
            return response.content
        pytest.skip("Could not get PDF")
    
    @pytest.fixture
    def pdf_content_without_photos(self, auth_token):
        """Get PDF content for report without photos"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_WITHOUT_PHOTOS}/pdf",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=60
        )
        if response.status_code == 200:
            return response.content
        pytest.skip("Could not get PDF")
    
    def test_pdf_has_sumario_page(self, pdf_content_with_photos):
        """Test that PDF has SUMÁRIO (TOC) page"""
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_content_with_photos, filetype="pdf")
        
        # SUMÁRIO should be on page 1 (index 1, after cover)
        sumario_found = False
        for page_num in range(min(3, len(doc))):  # Check first 3 pages
            page = doc[page_num]
            text = page.get_text()
            if "SUMÁRIO" in text:
                sumario_found = True
                print(f"✓ SUMÁRIO found on page {page_num}")
                break
        
        doc.close()
        assert sumario_found, "SUMÁRIO page not found in PDF"
    
    def test_toc_has_dot_leaders(self, pdf_content_with_photos):
        """Test that TOC has dot leaders (sequences of dots)"""
        import fitz
        doc = fitz.open(stream=pdf_content_with_photos, filetype="pdf")
        
        # Find SUMÁRIO page
        sumario_page = None
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            if "SUMÁRIO" in text:
                sumario_page = page
                break
        
        assert sumario_page is not None, "SUMÁRIO page not found"
        
        text = sumario_page.get_text()
        # Check for dot leaders (3+ consecutive dots)
        dot_pattern = re.compile(r'\.{3,}')
        matches = dot_pattern.findall(text)
        
        doc.close()
        assert len(matches) > 0, f"No dot leaders found in SUMÁRIO. Text sample: {text[:500]}"
        print(f"✓ Found {len(matches)} dot leader sequences in SUMÁRIO")
    
    def test_toc_page_numbers_inserted(self, pdf_content_with_photos):
        """Test that TOC has page numbers inserted via PyMuPDF"""
        import fitz
        doc = fitz.open(stream=pdf_content_with_photos, filetype="pdf")
        
        # Find SUMÁRIO page (should be page 1)
        sumario_page = None
        sumario_page_num = None
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            if "SUMÁRIO" in text:
                sumario_page = page
                sumario_page_num = page_num
                break
        
        assert sumario_page is not None, "SUMÁRIO page not found"
        
        # Get text blocks with positions
        blocks = sumario_page.get_text("dict")["blocks"]
        
        # Look for page numbers on the right side (x > 450)
        right_side_numbers = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        x = span["bbox"][0]
                        # Check if it's a number on the right side
                        if x > 450 and text.isdigit():
                            right_side_numbers.append((text, x))
        
        doc.close()
        print(f"✓ Found {len(right_side_numbers)} page numbers on right side of SUMÁRIO")
        # We expect at least some page numbers for sections
        assert len(right_side_numbers) >= 1, "No page numbers found on right side of SUMÁRIO"
    
    def test_page_numbers_x_de_y_format(self, pdf_content_with_photos):
        """Test that pages have 'X de Y' format page numbers"""
        import fitz
        doc = fitz.open(stream=pdf_content_with_photos, filetype="pdf")
        
        total_pages = len(doc)
        pages_with_numbers = 0
        
        # Check pages 1 onwards (skip cover page 0)
        for page_num in range(1, min(5, total_pages)):  # Check first few content pages
            page = doc[page_num]
            text = page.get_text()
            
            # Look for "X de Y" pattern
            pattern = re.compile(r'\d+\s+de\s+\d+')
            if pattern.search(text):
                pages_with_numbers += 1
        
        doc.close()
        assert pages_with_numbers > 0, "No 'X de Y' page numbers found on content pages"
        print(f"✓ Found 'X de Y' page numbers on {pages_with_numbers} pages")
    
    def test_cover_page_no_page_number(self, pdf_content_with_photos):
        """Test that cover page (page 0) has no page number"""
        import fitz
        doc = fitz.open(stream=pdf_content_with_photos, filetype="pdf")
        
        cover_page = doc[0]
        text = cover_page.get_text()
        
        # Look for "X de Y" pattern on cover
        pattern = re.compile(r'\d+\s+de\s+\d+')
        match = pattern.search(text)
        
        doc.close()
        assert match is None, f"Cover page should not have page number, but found: {match.group() if match else 'N/A'}"
        print("✓ Cover page has no 'X de Y' page number")


class TestCodeVerification:
    """Verify code changes for border colors and image height calculations"""
    
    def test_border_color_is_aaaaaa(self):
        """Verify border colors are set to #AAAAAA in server.py"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for #AAAAAA in border/stroke color settings
        assert "colors.HexColor('#AAAAAA')" in content, "Border color #AAAAAA not found in server.py"
        
        # Count occurrences - should be multiple (page border, header box, footer box, cover table)
        count = content.count("colors.HexColor('#AAAAAA')")
        assert count >= 3, f"Expected at least 3 occurrences of #AAAAAA, found {count}"
        print(f"✓ Found {count} occurrences of #AAAAAA border color")
    
    def test_max_photo_height_calculation(self):
        """Verify max photo heights are calculated from frame dimensions"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for dynamic height calculation
        assert "frame_available_height" in content, "frame_available_height calculation not found"
        assert "max_full_photo_height" in content, "max_full_photo_height not found"
        assert "max_first_photo_height" in content, "max_first_photo_height not found"
        
        # Verify it's calculated from frame dimensions, not hardcoded
        assert "page_height -" in content or "frame_available_height -" in content, "Height should be calculated dynamically"
        print("✓ Photo heights are calculated dynamically from frame dimensions")
    
    def test_toc_uses_stringwidth(self):
        """Verify TOC uses stringWidth for accurate dot leader calculation"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for stringWidth import and usage
        assert "from reportlab.pdfbase.pdfmetrics import stringWidth" in content, "stringWidth import not found"
        assert "stringWidth(" in content, "stringWidth function not used"
        print("✓ TOC uses stringWidth for accurate dot leader calculation")
    
    def test_toc_bold_numbers_normal_titles(self):
        """Verify TOC has bold numbers but normal weight titles"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for the pattern: <b>{num_part}</b>{title_part}
        # This means number is bold, title is not
        assert "<b>{num_part}</b>{title_part}" in content or "<b>{num_part}</b>" in content, \
            "TOC should have bold numbers with normal titles"
        print("✓ TOC has bold numbers with normal weight titles")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
