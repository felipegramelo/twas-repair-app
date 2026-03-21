"""
Test PDF Layout Changes - Iteration 17
Tests for PDF layout matching reference file exactly:
1. PDF endpoint returns 200 for report 69be160fbc3470b8fd2dbe87
2. Page number '1 de 12' at position x=507, y=772 on page 1
3. Cover page (page 0) has NO page number text
4. SUMÁRIO page has section page numbers at x=532
5. Header has label:value format (Cliente:, Rig/Vessel:, Equipamento:, OS:, Rev:)
6. Footer text size is 8pt (matching reference)
7. Total pages > 1 (has content)
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


class TestPageNumberPosition:
    """Test 2: Page number '1 de Y' at position x=507, y=772 on page 1"""
    
    def test_page_number_at_correct_position(self, pdf_doc):
        """Test: Page number is at x=507, y=772"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        # Check page 1 (SUMÁRIO)
        page = pdf_doc[1]
        blocks = page.get_text("dict")["blocks"]
        
        # Look for page number text near x=507, y=772
        found_at_position = False
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        bbox = span["bbox"]
                        text = span["text"].strip()
                        # Check if text contains "de" and is near expected position
                        # Allow tolerance of ±10 points
                        if "de" in text and 497 <= bbox[0] <= 517 and 762 <= bbox[1] <= 782:
                            found_at_position = True
                            print(f"✓ Found page number '{text}' at x={bbox[0]:.1f}, y={bbox[1]:.1f}")
        
        assert found_at_position, "Page number should be at approximately x=507, y=772"
    
    def test_page_1_has_correct_format(self, pdf_doc):
        """Test: Page 1 has '1 de Y' format"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        page = pdf_doc[1]
        text = page.get_text()
        total_numbered = len(pdf_doc) - 1  # Cover not counted
        
        # Check for "1 de Y" pattern
        pattern = re.compile(rf'1\s+de\s+{total_numbered}')
        matches = pattern.findall(text)
        
        assert len(matches) > 0, f"Page 1 should have '1 de {total_numbered}'"
        print(f"✓ Page 1 has correct format: 1 de {total_numbered}")


class TestCoverNoPageNumber:
    """Test 3: Cover page (page 0) has NO page number text"""
    
    def test_cover_page_has_no_page_number(self, pdf_doc):
        """Test: Cover page (page 0) has NO page number"""
        cover_page = pdf_doc[0]
        text = cover_page.get_text()
        
        # Check that there's no "X de Y" pattern on cover page
        page_num_pattern = re.compile(r'\d+\s+de\s+\d+')
        matches = page_num_pattern.findall(text)
        
        assert len(matches) == 0, f"Cover page should have no page number, found: {matches}"
        print(f"✓ Cover page (page 0) has NO page number")
    
    def test_cover_page_no_page_number_at_footer_position(self, pdf_doc):
        """Test: Cover page has no text at footer page number position (x=507, y=772)"""
        cover_page = pdf_doc[0]
        blocks = cover_page.get_text("dict")["blocks"]
        
        # Check that there's no text at the page number position
        text_at_position = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        bbox = span["bbox"]
                        text = span["text"].strip()
                        # Check if any text is near the page number position
                        if 497 <= bbox[0] <= 517 and 762 <= bbox[1] <= 782 and text:
                            text_at_position.append(text)
        
        # Should be empty or not contain page number pattern
        for text in text_at_position:
            assert not re.match(r'\d+\s+de\s+\d+', text), f"Found page number at footer position: {text}"
        
        print(f"✓ Cover page has no page number at footer position")


class TestSumarioPageNumbers:
    """Test 4: SUMÁRIO page has section page numbers at x=532"""
    
    def test_sumario_section_page_numbers_at_x532(self, pdf_doc):
        """Test: SUMÁRIO has section page numbers at x=532"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        sumario_page = pdf_doc[1]
        blocks = sumario_page.get_text("dict")["blocks"]
        
        # Look for page numbers at x=532 (allow tolerance ±10)
        page_nums_at_532 = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        bbox = span["bbox"]
                        text = span["text"].strip()
                        # Check for single/double digit numbers at x≈532
                        # Exclude footer area (y < 750)
                        if 522 <= bbox[0] <= 542 and bbox[1] < 750 and text.isdigit():
                            page_nums_at_532.append((text, bbox[0], bbox[1]))
        
        assert len(page_nums_at_532) > 0, "SUMÁRIO should have section page numbers at x≈532"
        print(f"✓ Found {len(page_nums_at_532)} section page numbers at x≈532")
        for num, x, y in page_nums_at_532[:5]:
            print(f"  - Page {num} at x={x:.1f}, y={y:.1f}")
    
    def test_sumario_code_uses_x532(self):
        """Test: Code review - SUMÁRIO page numbers inserted at x=532"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for x=532 in SUMÁRIO page number insertion
        assert "fitz.Point(532," in content, "SUMÁRIO page numbers should be at x=532"
        print(f"✓ Code uses fitz.Point(532, ...) for SUMÁRIO page numbers")


class TestHeaderLabelValueFormat:
    """Test 5: Header has label:value format (Cliente:, Rig/Vessel:, Equipamento:, OS:, Rev:)"""
    
    def test_header_has_cliente_label(self, pdf_doc):
        """Test: Header has 'Cliente:' label"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        page = pdf_doc[1]
        text = page.get_text()
        
        assert "Cliente:" in text, "Header should have 'Cliente:' label"
        print(f"✓ Header has 'Cliente:' label")
    
    def test_header_has_rig_vessel_label(self, pdf_doc):
        """Test: Header has 'Rig/Vessel:' label"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        page = pdf_doc[1]
        text = page.get_text()
        
        assert "Rig/Vessel:" in text, "Header should have 'Rig/Vessel:' label"
        print(f"✓ Header has 'Rig/Vessel:' label")
    
    def test_header_has_equipamento_label(self, pdf_doc):
        """Test: Header has 'Equipamento:' label"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        page = pdf_doc[1]
        text = page.get_text()
        
        assert "Equipamento:" in text, "Header should have 'Equipamento:' label"
        print(f"✓ Header has 'Equipamento:' label")
    
    def test_header_has_os_label(self, pdf_doc):
        """Test: Header has 'OS:' label"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        page = pdf_doc[1]
        text = page.get_text()
        
        assert "OS:" in text, "Header should have 'OS:' label"
        print(f"✓ Header has 'OS:' label")
    
    def test_header_has_rev_label(self, pdf_doc):
        """Test: Header has 'Rev:' label"""
        if len(pdf_doc) < 2:
            pytest.skip("PDF has less than 2 pages")
        
        page = pdf_doc[1]
        text = page.get_text()
        
        assert "Rev:" in text, "Header should have 'Rev:' label"
        print(f"✓ Header has 'Rev:' label")
    
    def test_code_has_label_value_format(self):
        """Test: Code review - header uses label:value format"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for label:value format in code
        assert 'canvas_obj.drawString(lbl_x, detail_y, "Cliente:")' in content, "Code should have Cliente: label"
        assert 'canvas_obj.drawString(lbl_x, detail_y, "Rig/Vessel:")' in content, "Code should have Rig/Vessel: label"
        assert 'canvas_obj.drawString(lbl_x, detail_y, "Equipamento:")' in content, "Code should have Equipamento: label"
        assert 'canvas_obj.drawString(lbl_x, detail_y, "OS:")' in content, "Code should have OS: label"
        assert 'canvas_obj.drawString(lbl_x, detail_y, "Rev:")' in content, "Code should have Rev: label"
        
        print(f"✓ Code has all label:value pairs in header")


class TestFooterTextSize:
    """Test 6: Footer text size is 8pt (matching reference)"""
    
    def test_footer_text_size_8pt_in_code(self):
        """Test: Code review - footer text uses 8pt font"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Find the footer section in generate_report_pdf
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Check for footer font size 8
        # The footer should use setFont with size 8
        assert 'setFont("Helvetica-Bold", 8)' in pdf_section, "Footer should use Helvetica-Bold 8pt"
        assert 'setFont("Helvetica", 8)' in pdf_section, "Footer should use Helvetica 8pt"
        assert 'setFont("Helvetica-BoldOblique", 8)' in pdf_section, "Footer should use Helvetica-BoldOblique 8pt"
        
        print(f"✓ Footer text uses 8pt font")
    
    def test_page_number_font_size_8pt(self):
        """Test: Code review - page numbers use fontsize=8"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for page number font size
        assert "fontsize=8," in content, "Page numbers should use fontsize=8"
        print(f"✓ Page numbers use fontsize=8")


class TestTotalPages:
    """Test 7: Total pages > 1 (has content)"""
    
    def test_pdf_has_multiple_pages(self, pdf_doc):
        """Test: PDF has more than 1 page"""
        total_pages = len(pdf_doc)
        assert total_pages > 1, f"PDF should have more than 1 page, has {total_pages}"
        print(f"✓ PDF has {total_pages} pages (> 1)")
    
    def test_pdf_has_content_pages(self, pdf_doc):
        """Test: PDF has content pages after cover and SUMÁRIO"""
        total_pages = len(pdf_doc)
        # Should have at least: cover (0), SUMÁRIO (1), content (2+)
        assert total_pages >= 3, f"PDF should have at least 3 pages (cover, SUMÁRIO, content), has {total_pages}"
        print(f"✓ PDF has content pages (total: {total_pages})")


class TestLogoSize:
    """Test: Logo in header is 5.2cm wide (matching reference)"""
    
    def test_logo_width_is_5_2cm(self):
        """Test: Code review - logo width = 5.2*cm"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Find the drawImage call for the header logo
        assert "width=5.2*cm" in pdf_section, "Logo width should be 5.2*cm"
        print(f"✓ Logo width = 5.2*cm")


class TestContentMargins:
    """Test: Content margins are 2.03cm (header/footer boxes ~2cm from edge)"""
    
    def test_content_margins_2_03cm(self):
        """Test: Code review - content_left and content_right = 2.03*cm"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:pdf_section_start + 700]
        
        assert "content_left = 2.03*cm" in pdf_section, "content_left should be 2.03*cm"
        assert "content_right = 2.03*cm" in pdf_section, "content_right should be 2.03*cm"
        print(f"✓ content_left = 2.03*cm, content_right = 2.03*cm")


class TestWatermark:
    """Test: Watermark is 95% width on content pages"""
    
    def test_watermark_95_percent_width(self):
        """Test: Code review - watermark is 95% of content width"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        pdf_section_start = content.find("async def generate_report_pdf")
        pdf_section = content[pdf_section_start:]
        
        # Check for watermark width = 0.95 * content_width
        assert "wm_w = content_width * 0.95" in pdf_section, "Watermark should be 95% of content width"
        print(f"✓ Watermark width = content_width * 0.95 (95%)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
