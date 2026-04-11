"""
Test PDF Layout Changes - Iteration 15
Tests for:
1. PDF endpoint returns 200
2. Page numbering 'X de Y' starting from page 2 (page index 1)
3. Cover page (page 0) has NO page number
4. SUMÁRIO page has page numbers on the right side
5. All text in PDF is black (no colored sections)
6. Cover titles are in UPPERCASE
7. Border margins are 1.0cm
8. Logo width in header is 5.0cm
"""

import pytest
import requests
import os
import io
import re

# Use the public URL for testing
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://twas-repair-app-1.preview.emergentagent.com')
REPORT_ID = "69bd49d5d50559f19c945730"

# Test credentials
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for supervisor"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPERVISOR_EMAIL, "password": SUPERVISOR_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in login response"
    return data["access_token"]


@pytest.fixture(scope="module")
def pdf_content(auth_token):
    """Fetch PDF content once for all tests"""
    response = requests.get(
        f"{BASE_URL}/api/reports/{REPORT_ID}/pdf",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200, f"PDF endpoint failed: {response.status_code} - {response.text}"
    return response.content


@pytest.fixture(scope="module")
def pdf_doc(pdf_content):
    """Parse PDF with PyMuPDF for detailed analysis"""
    import fitz
    doc = fitz.open(stream=pdf_content, filetype="pdf")
    yield doc
    doc.close()


class TestPDFEndpoint:
    """Test PDF endpoint returns 200 and valid PDF"""
    
    def test_pdf_endpoint_returns_200(self, auth_token):
        """Test: GET /api/reports/{report_id}/pdf returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_ID}/pdf",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ PDF endpoint returns 200")
    
    def test_pdf_content_type(self, auth_token):
        """Test: PDF has correct content-type"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_ID}/pdf",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        print(f"✓ Content-Type is application/pdf")
    
    def test_pdf_valid_header(self, pdf_content):
        """Test: PDF starts with valid PDF header"""
        assert pdf_content[:4] == b'%PDF', "PDF does not start with %PDF header"
        print(f"✓ PDF has valid header")


class TestPageNumbering:
    """Test page numbering 'X de Y' format"""
    
    def test_cover_page_has_no_page_number(self, pdf_doc):
        """Test: Cover page (page 0) has NO page number"""
        cover_page = pdf_doc[0]
        text = cover_page.get_text()
        
        # Check that there's no "X de Y" pattern on cover page
        page_num_pattern = re.compile(r'\d+\s+de\s+\d+')
        matches = page_num_pattern.findall(text)
        
        assert len(matches) == 0, f"Cover page should have no page number, found: {matches}"
        print(f"✓ Cover page (page 0) has NO page number")
    
    def test_page_1_has_correct_number(self, pdf_doc):
        """Test: Page 1 (SUMÁRIO) has page number '1 de X'"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        page_1 = pdf_doc[1]
        text = page_1.get_text()
        
        # Look for "1 de X" pattern
        page_num_pattern = re.compile(r'1\s+de\s+\d+')
        matches = page_num_pattern.findall(text)
        
        assert len(matches) > 0, f"Page 1 should have '1 de X' page number, text: {text[-500:]}"
        print(f"✓ Page 1 has page number: {matches[0]}")
    
    def test_page_numbers_start_from_page_2(self, pdf_doc):
        """Test: Page numbers start from page index 1 (second page)"""
        total_pages = len(pdf_doc)
        total_numbered = total_pages - 1  # Cover not counted
        
        # Check pages 1 onwards have page numbers
        for i in range(1, min(total_pages, 4)):  # Check first few pages
            page = pdf_doc[i]
            text = page.get_text()
            expected_num = i
            pattern = re.compile(rf'{expected_num}\s+de\s+{total_numbered}')
            matches = pattern.findall(text)
            assert len(matches) > 0, f"Page index {i} should have '{expected_num} de {total_numbered}'"
            print(f"✓ Page index {i} has correct number: {expected_num} de {total_numbered}")
    
    def test_page_number_format_x_de_y(self, pdf_doc):
        """Test: Page numbers use 'X de Y' format (Portuguese)"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        page_1 = pdf_doc[1]
        text = page_1.get_text()
        
        # Should use "de" not "of"
        assert " de " in text.lower(), "Page numbers should use 'de' (Portuguese)"
        assert " of " not in text.lower(), "Page numbers should not use 'of' (English)"
        print(f"✓ Page numbers use 'X de Y' format")


class TestSumarioPageNumbers:
    """Test SUMÁRIO page has section page numbers"""
    
    def test_sumario_page_exists(self, pdf_doc):
        """Test: SUMÁRIO page exists (page index 1)"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        sumario_page = pdf_doc[1]
        text = sumario_page.get_text()
        
        assert "SUMÁRIO" in text, "SUMÁRIO title not found on page 1"
        print(f"✓ SUMÁRIO page exists at page index 1")
    
    def test_sumario_has_section_numbers(self, pdf_doc):
        """Test: SUMÁRIO has section entries with numbers"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        sumario_page = pdf_doc[1]
        text = sumario_page.get_text()
        
        # Check for section entries like "1. INTRODUÇÃO"
        section_pattern = re.compile(r'\d+\.\s+[A-ZÇÃÕÉÊÍÓÚÂ]+')
        matches = section_pattern.findall(text)
        
        assert len(matches) > 0, f"SUMÁRIO should have section entries, found: {text}"
        print(f"✓ SUMÁRIO has {len(matches)} section entries")
    
    def test_sumario_has_page_numbers_on_right(self, pdf_doc):
        """Test: SUMÁRIO entries have page numbers on the right side"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        sumario_page = pdf_doc[1]
        
        # Look for page numbers on the right side (x > 540)
        # The page numbers are injected by PyMuPDF at the right margin
        blocks = sumario_page.get_text("dict")["blocks"]
        section_page_nums = []
        
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        bbox = span["bbox"]
                        text = span["text"].strip()
                        # Look for single/double digits on the right side (x > 540)
                        # but not the footer page number (which contains "de")
                        if bbox[0] > 540 and text.isdigit():
                            section_page_nums.append(text)
        
        # We expect at least some page numbers for sections
        assert len(section_page_nums) > 0, "SUMÁRIO should have section page numbers on the right"
        print(f"✓ Found {len(section_page_nums)} section page numbers in SUMÁRIO: {section_page_nums[:5]}...")


class TestTextColors:
    """Test all text is black (no colored sections)"""
    
    def test_code_uses_black_text_colors(self):
        """Test: Code review - all styles use colors.black"""
        # Read server.py and check for color definitions
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Find all textColor definitions in the PDF generation section
        # Look for lines between generate_report_pdf and the end
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Check that textColor uses colors.black
        text_color_lines = re.findall(r'textColor\s*=\s*[^,\)]+', pdf_section)
        
        for line in text_color_lines:
            assert 'colors.black' in line or 'colors.gray' in line, f"Non-black text color found: {line}"
        
        print(f"✓ All {len(text_color_lines)} textColor definitions use colors.black (or gray for signature)")
    
    def test_no_colored_hex_text(self):
        """Test: No colored hex values for text in PDF styles"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Check for HexColor in textColor (should not exist)
        hex_text_colors = re.findall(r'textColor\s*=\s*colors\.HexColor', pdf_section)
        
        assert len(hex_text_colors) == 0, f"Found colored text: {hex_text_colors}"
        print(f"✓ No HexColor used for text colors")


class TestCoverTitles:
    """Test cover titles are in UPPERCASE"""
    
    def test_service_name_uppercase(self, pdf_doc):
        """Test: Service name on cover is UPPERCASE"""
        cover_page = pdf_doc[0]
        text = cover_page.get_text()
        
        # The service name should be uppercase (e.g., "TESTE HIDROSTATICO")
        # Check that there's uppercase text near the top
        lines = text.split('\n')
        
        # Find lines that are all uppercase (excluding numbers and punctuation)
        uppercase_lines = []
        for line in lines[:20]:  # Check first 20 lines
            stripped = line.strip()
            if stripped and len(stripped) > 3:
                # Check if alphabetic characters are uppercase
                alpha_chars = ''.join(c for c in stripped if c.isalpha())
                if alpha_chars and alpha_chars == alpha_chars.upper():
                    uppercase_lines.append(stripped)
        
        assert len(uppercase_lines) > 0, "No uppercase titles found on cover page"
        print(f"✓ Cover has uppercase titles: {uppercase_lines[:3]}")
    
    def test_code_uses_upper_for_cover(self):
        """Test: Code review - cover titles use .upper()"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for .upper() usage for service and vessel names
        assert 'service_name = report.get("service", "").upper()' in content, "Service name should use .upper()"
        assert 'vessel_name = report.get("location", "").upper()' in content, "Vessel name should use .upper()"
        
        print(f"✓ Code uses .upper() for cover titles")


class TestBorderMargins:
    """Test border margins are 1.0cm"""
    
    def test_border_margin_is_1cm(self):
        """Test: Code review - border_margin = 1.0*cm"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Find the generate_report_pdf function
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:pdf_section_start + 2000]
        
        # Check for border_margin = 1.0*cm
        assert "border_margin = 1.0*cm" in pdf_section, "border_margin should be 1.0*cm"
        print(f"✓ border_margin = 1.0*cm")
    
    def test_content_margins_are_1cm(self):
        """Test: Code review - content_left and content_right = 1.0*cm"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:pdf_section_start + 2000]
        
        assert "content_left = 1.0*cm" in pdf_section, "content_left should be 1.0*cm"
        assert "content_right = 1.0*cm" in pdf_section, "content_right should be 1.0*cm"
        print(f"✓ content_left = 1.0*cm, content_right = 1.0*cm")


class TestLogoSize:
    """Test logo width in header is 5.0cm"""
    
    def test_logo_width_is_5cm(self):
        """Test: Code review - logo width = 5.0*cm"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Find the drawImage call for the header logo
        # Should be: width=5.0*cm
        assert "width=5.0*cm" in pdf_section, "Logo width should be 5.0*cm"
        print(f"✓ Logo width = 5.0*cm")


class TestWatermark:
    """Test watermark logo on every page except cover"""
    
    def test_watermark_code_exists(self):
        """Test: Code review - watermark is added to pages > 1"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Check for watermark code
        assert "WATERMARK LOGO" in pdf_section, "Watermark section should exist"
        assert "if page_num > 1" in pdf_section, "Watermark should only appear on pages > 1"
        assert "setFillAlpha(0.06)" in pdf_section, "Watermark should use 6% opacity"
        print(f"✓ Watermark code exists with correct conditions")
    
    def test_watermark_not_on_cover(self):
        """Test: Watermark condition excludes cover page"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # The condition "if page_num > 1" means:
        # - page_num 1 = cover (no watermark)
        # - page_num 2+ = content pages (has watermark)
        assert "if page_num > 1 and logo_image:" in content, "Watermark should skip cover (page_num > 1)"
        print(f"✓ Watermark skips cover page (page_num > 1)")


class TestReportData:
    """Test report data is accessible"""
    
    def test_report_exists(self, auth_token):
        """Test: Report with ID exists"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_ID}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Report not found: {response.status_code}"
        data = response.json()
        assert "id" in data, "Report should have id"
        print(f"✓ Report {REPORT_ID} exists")
    
    def test_report_has_photos(self, auth_token):
        """Test: Report has photos for PDF generation"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_ID}/photos",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Photos endpoint failed: {response.status_code}"
        data = response.json()
        photos = data.get("photos", [])
        print(f"✓ Report has {len(photos)} photos")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
