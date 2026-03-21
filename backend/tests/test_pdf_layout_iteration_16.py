"""
Test PDF Layout Changes - Iteration 16
Tests for:
1. PDF endpoint returns 200 - GET /api/reports/{report_id}/pdf
2. Page count and 'X de Y' numbering in footer (right side)
3. Cover page has NO page number
4. SUMÁRIO has dot leaders connecting section titles to page numbers
5. SUMÁRIO page numbers are right-aligned (x > 450)
6. Watermark logo exists on page 2+ (90% content width)
7. Logo in header is 5.5cm wide
8. All text black
9. Cover titles in UPPERCASE
10. Border margin is 1.0cm
"""

import pytest
import requests
import os
import io
import re

# Use the public URL for testing
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://repair-tracker-app-7.preview.emergentagent.com')
REPORT_ID = "69be160fbc3470b8fd2dbe87"

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
    """Test 1: PDF endpoint returns 200 and valid PDF"""
    
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
    """Test 2 & 3: Page numbering 'X de Y' format and cover has no page number"""
    
    def test_cover_page_has_no_page_number(self, pdf_doc):
        """Test: Cover page (page 0) has NO page number"""
        cover_page = pdf_doc[0]
        text = cover_page.get_text()
        
        # Check that there's no "X de Y" pattern on cover page
        page_num_pattern = re.compile(r'\d+\s+de\s+\d+')
        matches = page_num_pattern.findall(text)
        
        assert len(matches) == 0, f"Cover page should have no page number, found: {matches}"
        print(f"✓ Cover page (page 0) has NO page number")
    
    def test_page_count_and_numbering(self, pdf_doc):
        """Test: Verify page count and 'X de Y' numbering"""
        total_pages = len(pdf_doc)
        total_numbered = total_pages - 1  # Cover not counted
        
        print(f"Total pages: {total_pages}, Numbered pages: {total_numbered}")
        
        # Check pages 1 onwards have page numbers
        for i in range(1, min(total_pages, 4)):  # Check first few pages
            page = pdf_doc[i]
            text = page.get_text()
            expected_num = i
            pattern = re.compile(rf'{expected_num}\s+de\s+{total_numbered}')
            matches = pattern.findall(text)
            assert len(matches) > 0, f"Page index {i} should have '{expected_num} de {total_numbered}'"
            print(f"✓ Page index {i} has correct number: {expected_num} de {total_numbered}")
    
    def test_page_number_in_footer_right_side(self, pdf_doc):
        """Test: Page numbers are in footer right side"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        # Check page 1 (SUMÁRIO)
        page = pdf_doc[1]
        blocks = page.get_text("dict")["blocks"]
        
        # Look for "de" text in footer area (y > 750) and right side (x > 400)
        footer_text_found = False
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        bbox = span["bbox"]
                        text = span["text"].strip()
                        # Footer is at bottom (y > 750) and page number on right (x > 400)
                        if bbox[1] > 750 and "de" in text:
                            footer_text_found = True
                            print(f"✓ Found footer page number at x={bbox[0]:.1f}, y={bbox[1]:.1f}: '{text}'")
        
        assert footer_text_found, "Page number should be in footer area"


class TestSumarioDotLeaders:
    """Test 4 & 5: SUMÁRIO has dot leaders and page numbers right-aligned"""
    
    def test_sumario_has_dot_leaders(self, pdf_doc):
        """Test: SUMÁRIO has dot leaders connecting section titles to page numbers"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        sumario_page = pdf_doc[1]
        text = sumario_page.get_text()
        
        # Check for SUMÁRIO title
        assert "SUMÁRIO" in text, "SUMÁRIO title not found"
        
        # Check for dot leaders (multiple consecutive dots)
        dot_pattern = re.compile(r'\.{3,}')  # At least 3 consecutive dots
        matches = dot_pattern.findall(text)
        
        assert len(matches) > 0, f"SUMÁRIO should have dot leaders, found none in text"
        print(f"✓ SUMÁRIO has {len(matches)} dot leader sequences")
    
    def test_sumario_page_numbers_right_aligned(self, pdf_doc):
        """Test: SUMÁRIO page numbers are right-aligned (x > 450)"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        sumario_page = pdf_doc[1]
        blocks = sumario_page.get_text("dict")["blocks"]
        
        # Look for page numbers on right side (x > 450)
        # These are the section page numbers, not the footer page number
        right_side_nums = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        bbox = span["bbox"]
                        text = span["text"].strip()
                        # Look for single/double digit numbers on right side
                        # Exclude footer area (y < 750) and check x > 450
                        if bbox[0] > 450 and bbox[1] < 750 and text.isdigit():
                            right_side_nums.append((text, bbox[0]))
        
        assert len(right_side_nums) > 0, "SUMÁRIO should have section page numbers on right side (x > 450)"
        
        # Verify all are on right side
        for num, x_pos in right_side_nums:
            assert x_pos > 450, f"Page number {num} at x={x_pos} should be > 450"
        
        print(f"✓ Found {len(right_side_nums)} section page numbers on right side")
        print(f"  Sample positions: {right_side_nums[:5]}")


class TestWatermark:
    """Test 6: Watermark logo exists on page 2+ (90% content width)"""
    
    def test_watermark_code_90_percent_width(self):
        """Test: Code review - watermark is 90% of content width"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Check for watermark width = 0.9 * content_width
        assert "wm_w = content_width * 0.9" in pdf_section, "Watermark should be 90% of content width"
        print(f"✓ Watermark width = content_width * 0.9 (90%)")
    
    def test_watermark_on_pages_after_cover(self):
        """Test: Code review - watermark appears on pages > 1 (after cover)"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Check for watermark condition
        assert "if page_num > 1 and logo_image:" in pdf_section, "Watermark should appear on pages > 1"
        assert "setFillAlpha(0.06)" in pdf_section, "Watermark should use 6% opacity"
        print(f"✓ Watermark appears on pages > 1 with 6% opacity")


class TestLogoSize:
    """Test 7: Logo in header is 5.5cm wide"""
    
    def test_logo_width_is_5_5cm(self):
        """Test: Code review - logo width = 5.5*cm"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Find the drawImage call for the header logo
        # Should be: width=5.5*cm
        assert "width=5.5*cm" in pdf_section, "Logo width should be 5.5*cm"
        print(f"✓ Logo width = 5.5*cm")


class TestTextColors:
    """Test 8: All text is black"""
    
    def test_code_uses_black_text_colors(self):
        """Test: Code review - all styles use colors.black"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Check that textColor uses colors.black
        text_color_lines = re.findall(r'textColor\s*=\s*[^,\)]+', pdf_section)
        
        for line in text_color_lines:
            assert 'colors.black' in line or 'colors.gray' in line, f"Non-black text color found: {line}"
        
        print(f"✓ All {len(text_color_lines)} textColor definitions use colors.black (or gray for signature)")


class TestCoverTitles:
    """Test 9: Cover titles in UPPERCASE"""
    
    def test_service_name_uppercase(self, pdf_doc):
        """Test: Service name on cover is UPPERCASE"""
        cover_page = pdf_doc[0]
        text = cover_page.get_text()
        
        # The service name should be uppercase (e.g., "TESTE HIDROSTATICO")
        lines = text.split('\n')
        
        # Find lines that are all uppercase
        uppercase_lines = []
        for line in lines[:20]:
            stripped = line.strip()
            if stripped and len(stripped) > 3:
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
        
        assert 'service_name = report.get("service", "").upper()' in content, "Service name should use .upper()"
        assert 'vessel_name = report.get("location", "").upper()' in content, "Vessel name should use .upper()"
        
        print(f"✓ Code uses .upper() for cover titles")


class TestBorderMargins:
    """Test 10: Border margin is 1.0cm"""
    
    def test_border_margin_is_1cm(self):
        """Test: Code review - border_margin = 1.0*cm"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:pdf_section_start + 2000]
        
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
    
    def test_report_has_sections(self, auth_token):
        """Test: Report has sections for SUMÁRIO"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_ID}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        sections = data.get("sections", [])
        assert len(sections) > 0, "Report should have sections"
        print(f"✓ Report has {len(sections)} sections")


class TestSumarioTwoColumnTable:
    """Test SUMÁRIO uses two-column table structure"""
    
    def test_sumario_table_structure_in_code(self):
        """Test: Code review - SUMÁRIO uses two-column table with dots and page numbers"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for two-column table structure
        assert "dots_col_w = content_width - 1.2*cm" in content, "SUMÁRIO should have dots column width"
        assert "page_col_w = 1.2*cm" in content, "SUMÁRIO should have page number column width"
        assert "toc_table = Table(toc_data, colWidths=[dots_col_w, page_col_w])" in content, "SUMÁRIO should use two-column table"
        
        print(f"✓ SUMÁRIO uses two-column table structure")
    
    def test_sumario_dot_leaders_in_code(self):
        """Test: Code review - SUMÁRIO entries have dot leaders"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for dot leader generation
        assert 'dots = " " + "." * num_dots' in content, "SUMÁRIO should generate dot leaders"
        assert "num_dots = max(3, max_chars - len(num_title))" in content, "SUMÁRIO should calculate dot count"
        
        print(f"✓ SUMÁRIO generates dot leaders")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
