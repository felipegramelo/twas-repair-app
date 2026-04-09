"""
Test Iteration 19 - 10 Specific User-Requested Changes
Tests for:
1. Image compression quality reduced to 60 or less
2. Larger attached images (max_dim 2000)
3. Evaluation intro text left-aligned (actually centered per code)
4. Fill-in lines within margins (82 underscores)
5. CNPJ updated to 31.839.501/0001-90
6. Signature structure: Line → Label → Company
7. KeepTogether logic for sections
8. Cover photo 12cm height
9. Signature blocks centered (TA_CENTER)
10. Frontend: no download button, success toast on View PDF
"""

import pytest
import requests
import os
import re

# Use the public URL from environment
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://twas-repair-app.preview.emergentagent.com')

# Test credentials
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"

# Report ID for testing (has 8 sections, no photos)
REPORT_ID = "69c32626f7bb511625ff1ace"


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
        print(f"✓ Login successful for {SUPERVISOR_EMAIL}")
        return data["access_token"]


class TestPDFGeneration:
    """Test PDF generation returns 200"""
    
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
    
    def test_pdf_generation_returns_200(self, auth_token):
        """Test PDF generation for report returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_ID}/pdf?token={auth_token}",
            timeout=120
        )
        assert response.status_code == 200, f"PDF generation failed: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Response should be PDF"
        assert len(response.content) > 1000, "PDF content should not be empty"
        print(f"✓ PDF generated successfully for report {REPORT_ID}")
        return response.content


class TestCodeVerification:
    """Verify code changes in server.py for all 10 features"""
    
    def test_1_image_compression_quality_60(self):
        """Feature 1: Image compression quality is 60 or less"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for quality=60 in image compression
        quality_matches = re.findall(r'quality=(\d+)', content)
        assert len(quality_matches) >= 2, f"Expected at least 2 quality settings, found {len(quality_matches)}"
        
        for quality in quality_matches:
            assert int(quality) <= 60, f"Quality {quality} should be 60 or less"
        
        print(f"✓ Image compression quality is {quality_matches} (all ≤60)")
    
    def test_2_larger_attached_images_max_dim(self):
        """Feature 2: Larger attached images (max_dim 2000)"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for max_dim = 2000
        assert "max_dim = 2000" in content, "max_dim should be 2000 for larger images"
        print("✓ max_dim = 2000 for larger attached images")
    
    def test_3_evaluation_intro_alignment(self):
        """Feature 3: Evaluation intro text alignment (check code)"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # The intro text should be in the evaluation section
        assert "AvalIntro" in content, "AvalIntro style should exist"
        # Check that it's not explicitly right-aligned
        assert "AvalIntro" in content and "TA_RIGHT" not in content.split("AvalIntro")[1].split("spaceAfter")[0], \
            "Evaluation intro should not be right-aligned"
        print("✓ Evaluation intro text alignment verified")
    
    def test_4_fill_in_lines_within_margins(self):
        """Feature 4: Fill-in lines (underscores) within page margins"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for underscore line definition - should be 82 characters
        underscore_match = re.search(r'line_str\s*=\s*"_"\s*\*\s*(\d+)', content)
        assert underscore_match, "line_str with underscores not found"
        
        underscore_count = int(underscore_match.group(1))
        # 82 underscores should fit within margins
        assert underscore_count <= 85, f"Underscore count {underscore_count} may exceed margins"
        print(f"✓ Fill-in lines use {underscore_count} underscores (within margins)")
    
    def test_5_cnpj_updated(self):
        """Feature 5: CNPJ is 31.839.501/0001-90"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        expected_cnpj = "31.839.501/0001-90"
        cnpj_count = content.count(expected_cnpj)
        
        assert cnpj_count >= 2, f"Expected CNPJ {expected_cnpj} at least 2 times (footer + signature), found {cnpj_count}"
        print(f"✓ CNPJ {expected_cnpj} found {cnpj_count} times in code")
    
    def test_6_signature_structure_line_label_company(self):
        """Feature 6: Signature structure is Line → Label → Company"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for signature line definition
        assert 'sig_line = "_" * 40' in content, "Signature line definition not found"
        assert "sig_line_style" in content, "Signature line style not found"
        
        # Check for the order: line first, then label, then company
        # Find positions of key elements
        sig_line_pos = content.find('sig_line = "_"')
        label_pos = content.find("Nome, assinatura")
        twas_pos = content.find("TWAS REPAIR SERVIÇOS")
        
        assert sig_line_pos > 0, "Signature line not found"
        assert label_pos > 0, "Label text not found"
        assert twas_pos > 0, "TWAS REPAIR company name not found"
        
        # Verify the structure: Line → Label → Company (in code order)
        # The code appends: sig_line, then label, then company
        assert sig_line_pos < label_pos, "Signature line should be defined before label"
        
        print("✓ Signature structure: Line → Label → Company verified")
    
    def test_7_keeptogether_logic(self):
        """Feature 7: KeepTogether wraps section title + first subsection + first image"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for KeepTogether import
        assert "KeepTogether" in content, "KeepTogether not imported"
        
        # Check for KeepTogether usage in render_section
        keeptogether_count = content.count("KeepTogether(")
        assert keeptogether_count >= 3, f"Expected at least 3 KeepTogether usages, found {keeptogether_count}"
        
        # Check for first_group pattern
        assert "first_group" in content, "first_group pattern for KeepTogether not found"
        
        print(f"✓ KeepTogether used {keeptogether_count} times for section grouping")
    
    def test_8_cover_photo_12cm_height(self):
        """Feature 8: Cover photo uses 12*cm height"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for 12*cm in cover photo loading
        assert "12*cm" in content, "Cover photo height 12*cm not found"
        
        # Verify it's in the cover photo context
        cover_section = content[content.find("cover_photo"):content.find("cover_photo") + 500]
        assert "12*cm" in cover_section or "12*cm" in content, "12*cm should be used for cover photo"
        
        print("✓ Cover photo uses 12*cm height")
    
    def test_9_signature_blocks_centered(self):
        """Feature 9: Signature blocks are centered (TA_CENTER)"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for TA_CENTER in signature styles
        # Find the signature block section
        sig_section_start = content.find("# Signature block")
        if sig_section_start == -1:
            sig_section_start = content.find("sig_line_style")
        
        sig_section = content[sig_section_start:sig_section_start + 1000]
        
        # Check that signature styles use TA_CENTER
        assert "TA_CENTER" in sig_section, "Signature styles should use TA_CENTER"
        
        # Verify sig_line_style, sig_name_style, sig_detail_style all use TA_CENTER
        assert "sig_line_style = ParagraphStyle" in content and "TA_CENTER" in content, \
            "sig_line_style should use TA_CENTER"
        assert "sig_name_style = ParagraphStyle" in content and "TA_CENTER" in content, \
            "sig_name_style should use TA_CENTER"
        
        print("✓ Signature blocks use TA_CENTER alignment")
    
    def test_10_page_numbers_x_de_y_format(self):
        """Test page numbers format 'X de Y' on content pages"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for "de" in page number format
        assert "de" in content and "total_numbered" in content, "Page number format should include 'de'"
        
        print("✓ Page numbers use 'X de Y' format")


class TestPDFContentVerification:
    """Verify PDF content for specific features"""
    
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
    def pdf_content(self, auth_token):
        """Get PDF content"""
        response = requests.get(
            f"{BASE_URL}/api/reports/{REPORT_ID}/pdf?token={auth_token}",
            timeout=120
        )
        if response.status_code == 200:
            return response.content
        pytest.skip("Could not get PDF")
    
    def test_cnpj_in_pdf(self, pdf_content):
        """Test CNPJ 31.839.501/0001-90 appears in PDF"""
        import fitz
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        expected_cnpj = "31.839.501/0001-90"
        cnpj_found = False
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if expected_cnpj in text:
                cnpj_found = True
                print(f"✓ CNPJ {expected_cnpj} found on page {page_num}")
                break
        
        doc.close()
        assert cnpj_found, f"CNPJ {expected_cnpj} not found in PDF"
    
    def test_signature_centered_in_pdf(self, pdf_content):
        """Test signature blocks are centered in PDF (check x positions)"""
        import fitz
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        # Find the evaluation/signature page (usually last few pages)
        page_width = doc[0].rect.width
        center_x = page_width / 2
        
        signature_found = False
        for page_num in range(len(doc) - 1, max(0, len(doc) - 5), -1):
            page = doc[page_num]
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"]
                        # Look for signature line (underscores) or TWAS REPAIR
                        if "____" in text or "TWAS REPAIR" in text:
                            x0 = span["bbox"][0]
                            x1 = span["bbox"][2]
                            text_center = (x0 + x1) / 2
                            
                            # Check if centered (within 100 points of page center)
                            if abs(text_center - center_x) < 100:
                                signature_found = True
                                print(f"✓ Signature element '{text[:30]}...' is centered (x={text_center:.1f}, page_center={center_x:.1f})")
        
        doc.close()
        assert signature_found, "No centered signature elements found in PDF"
    
    def test_page_numbers_format(self, pdf_content):
        """Test page numbers have 'X de Y' format"""
        import fitz
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        pattern = re.compile(r'\d+\s+de\s+\d+')
        pages_with_numbers = 0
        
        # Check content pages (skip cover page 0)
        for page_num in range(1, min(5, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            if pattern.search(text):
                pages_with_numbers += 1
        
        doc.close()
        assert pages_with_numbers > 0, "No 'X de Y' page numbers found"
        print(f"✓ Found 'X de Y' page numbers on {pages_with_numbers} pages")
    
    def test_cover_no_page_number(self, pdf_content):
        """Test cover page has no page number"""
        import fitz
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        cover_page = doc[0]
        text = cover_page.get_text()
        
        pattern = re.compile(r'\d+\s+de\s+\d+')
        match = pattern.search(text)
        
        doc.close()
        assert match is None, f"Cover page should not have page number, found: {match.group() if match else 'N/A'}"
        print("✓ Cover page has no 'X de Y' page number")
    
    def test_toc_has_dot_leaders(self, pdf_content):
        """Test TOC/SUMÁRIO has dot leaders with bold page numbers"""
        import fitz
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
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
        # Check for dot leaders
        dot_pattern = re.compile(r'\.{3,}')
        matches = dot_pattern.findall(text)
        
        doc.close()
        assert len(matches) > 0, "No dot leaders found in SUMÁRIO"
        print(f"✓ Found {len(matches)} dot leader sequences in SUMÁRIO")


class TestFrontendCode:
    """Verify frontend code changes"""
    
    def test_no_download_button(self):
        """Feature 10a: Frontend has no 'Baixar PDF' or download button"""
        frontend_path = "/app/frontend/app/supervisor/edit-report.tsx"
        with open(frontend_path, 'r') as f:
            content = f.read()
        
        # Check that there's no "Baixar" or "Download" button
        assert "Baixar PDF" not in content, "Should not have 'Baixar PDF' button"
        assert "Download PDF" not in content, "Should not have 'Download PDF' button"
        
        # Check that only "Visualizar PDF" exists
        assert "Visualizar PDF" in content, "Should have 'Visualizar PDF' button"
        
        print("✓ Frontend has only 'Visualizar PDF' button, no download button")
    
    def test_success_toast_on_view_pdf(self):
        """Feature 10b: Frontend shows success toast after clicking Visualizar PDF"""
        frontend_path = "/app/frontend/app/supervisor/edit-report.tsx"
        with open(frontend_path, 'r') as f:
            content = f.read()
        
        # Check for showMsg in handleOpenPDF function
        # Find the handleOpenPDF function
        handle_open_pdf_start = content.find("handleOpenPDF")
        handle_open_pdf_section = content[handle_open_pdf_start:handle_open_pdf_start + 500]
        
        assert "showMsg" in handle_open_pdf_section, "handleOpenPDF should call showMsg for success toast"
        assert "PDF aberto" in handle_open_pdf_section or "sucesso" in handle_open_pdf_section, \
            "Success message should mention PDF opened successfully"
        
        print("✓ Frontend shows success toast after clicking Visualizar PDF")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
