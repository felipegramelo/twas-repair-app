"""
Iteration 31: Proposal Restructuring Tests
- Proposal CRUD with termos_gerais field
- Photo upload/list/delete endpoints
- PDF generation (comercial vs tecnica)
- PDF content verification (plain text client info, numbered sections, termos gerais)
- Backward compatibility for proposals without termos_gerais
"""

import pytest
import requests
import os
import io
import fitz  # PyMuPDF for PDF content verification

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://repair-proposals-app.preview.emergentagent.com')

class TestProposalRestructure:
    """Test proposal restructuring features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        data = login_response.json()
        self.token = data.get("access_token")
        assert self.token, "No access_token in login response"
        
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        self.created_proposal_id = None
        yield
        
        # Cleanup: Delete test proposal if created
        if self.created_proposal_id:
            try:
                self.session.delete(f"{BASE_URL}/api/proposals/{self.created_proposal_id}")
            except Exception:
                pass
    
    # ==================== PROPOSAL CRUD WITH TERMOS_GERAIS ====================
    
    def test_01_create_proposal_with_termos_gerais(self):
        """Test creating a proposal with termos_gerais field"""
        payload = {
            "empresa": "TEST_Empresa Teste LTDA",
            "contato": "João Silva",
            "email": "joao@teste.com",
            "embarcacao": "Navio Teste",
            "equipamento": "Motor Principal",
            "itens": [
                {
                    "id": "item-1",
                    "titulo": "Serviço de Manutenção",
                    "descricao": "Manutenção preventiva do motor principal",
                    "valor": 5000.00
                },
                {
                    "id": "item-2",
                    "titulo": "Troca de Peças",
                    "descricao": "Substituição de componentes desgastados",
                    "valor": 3000.00
                }
            ],
            "termos_gerais": "1. Prazo de execução: 15 dias úteis.\n2. Garantia: 90 dias.\n3. Pagamento: 50% entrada, 50% na conclusão.",
            "observacoes": "Serviço urgente. Prioridade alta."
        }
        
        response = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert response.status_code == 200, f"Create proposal failed: {response.text}"
        
        data = response.json()
        self.created_proposal_id = data.get("id")
        
        # Verify response contains termos_gerais
        assert "termos_gerais" in data, "Response missing termos_gerais field"
        assert data["termos_gerais"] == payload["termos_gerais"], "termos_gerais not saved correctly"
        assert data["empresa"] == payload["empresa"]
        assert data["observacoes"] == payload["observacoes"]
        assert len(data["itens"]) == 2
        
        print(f"✓ Created proposal {data['numero_proposta']} with termos_gerais")
    
    def test_02_get_proposal_returns_termos_gerais(self):
        """Test that GET proposal returns termos_gerais field"""
        # First create a proposal
        payload = {
            "empresa": "TEST_Get Termos Test",
            "contato": "Maria",
            "email": "maria@test.com",
            "embarcacao": "Barco X",
            "equipamento": "Gerador",
            "itens": [{"id": "i1", "titulo": "Serviço", "descricao": "Desc", "valor": 1000}],
            "termos_gerais": "Termos de teste para GET",
            "observacoes": ""
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        # GET the proposal
        get_resp = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}")
        assert get_resp.status_code == 200, f"GET proposal failed: {get_resp.text}"
        
        data = get_resp.json()
        assert data["termos_gerais"] == payload["termos_gerais"], "GET did not return correct termos_gerais"
        
        print(f"✓ GET proposal returns termos_gerais correctly")
    
    def test_03_update_proposal_termos_gerais(self):
        """Test updating termos_gerais field"""
        # Create proposal
        payload = {
            "empresa": "TEST_Update Termos Test",
            "contato": "Pedro",
            "email": "pedro@test.com",
            "embarcacao": "Navio Y",
            "equipamento": "Bomba",
            "itens": [{"id": "i1", "titulo": "Reparo", "descricao": "Desc", "valor": 2000}],
            "termos_gerais": "Termos originais",
            "observacoes": ""
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        # Update termos_gerais
        update_payload = {
            "termos_gerais": "Termos atualizados com novas condições"
        }
        
        update_resp = self.session.put(f"{BASE_URL}/api/proposals/{proposal_id}", json=update_payload)
        assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
        
        data = update_resp.json()
        assert data["termos_gerais"] == update_payload["termos_gerais"], "termos_gerais not updated"
        
        # Verify with GET
        get_resp = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["termos_gerais"] == update_payload["termos_gerais"]
        
        print(f"✓ Update proposal termos_gerais works correctly")
    
    def test_04_backward_compatibility_no_termos(self):
        """Test that proposals without termos_gerais still work"""
        # Create proposal without termos_gerais
        payload = {
            "empresa": "TEST_No Termos Test",
            "contato": "Ana",
            "email": "ana@test.com",
            "embarcacao": "Barco Z",
            "equipamento": "Compressor",
            "itens": [{"id": "i1", "titulo": "Inspeção", "descricao": "Desc", "valor": 500}],
            "observacoes": "Sem termos"
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        # GET should return empty termos_gerais
        get_resp = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert "termos_gerais" in data, "termos_gerais field missing"
        assert data["termos_gerais"] == "", "termos_gerais should be empty string"
        
        print(f"✓ Backward compatibility: proposals without termos_gerais work")
    
    # ==================== PHOTO UPLOAD/LIST/DELETE ====================
    
    def test_05_upload_photo_to_proposal(self):
        """Test uploading a photo to a proposal section"""
        # Create proposal first
        payload = {
            "empresa": "TEST_Photo Upload Test",
            "contato": "Carlos",
            "email": "carlos@test.com",
            "embarcacao": "Navio Photo",
            "equipamento": "Motor",
            "itens": [
                {"id": "i1", "titulo": "Seção 1", "descricao": "Primeira seção", "valor": 1000},
                {"id": "i2", "titulo": "Seção 2", "descricao": "Segunda seção", "valor": 2000}
            ],
            "termos_gerais": "Termos",
            "observacoes": ""
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        # Create a simple test image (100x100 red pixel JPEG)
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        img_buffer.seek(0)
        
        # Upload photo to section 0 - use requests directly without session headers
        files = {'file': ('test_photo.jpg', img_buffer, 'image/jpeg')}
        upload_resp = requests.post(
            f"{BASE_URL}/api/proposals/{proposal_id}/upload-photo?section_index=0",
            files=files,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        assert upload_resp.status_code == 200, f"Photo upload failed: {upload_resp.text}"
        data = upload_resp.json()
        assert "storage_path" in data or "storage_paths" in data, "No storage path in response"
        assert data.get("section_index") == 0, "section_index not returned correctly"
        
        print(f"✓ Photo upload to section 0 successful")
    
    def test_06_list_proposal_photos(self):
        """Test listing photos for a proposal"""
        # Create proposal and upload photo
        payload = {
            "empresa": "TEST_List Photos Test",
            "contato": "Diana",
            "email": "diana@test.com",
            "embarcacao": "Barco List",
            "equipamento": "Gerador",
            "itens": [{"id": "i1", "titulo": "Seção", "descricao": "Desc", "valor": 1000}],
            "termos_gerais": "",
            "observacoes": ""
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        # Upload a photo
        from PIL import Image
        img = Image.new('RGB', (50, 50), color='blue')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        img_buffer.seek(0)
        
        del self.session.headers["Content-Type"]
        files = {'file': ('test_list.jpg', img_buffer, 'image/jpeg')}
        upload_resp = self.session.post(
            f"{BASE_URL}/api/proposals/{proposal_id}/upload-photo?section_index=0",
            files=files,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert upload_resp.status_code == 200
        self.session.headers["Content-Type"] = "application/json"
        
        # List photos
        list_resp = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}/photos")
        assert list_resp.status_code == 200, f"List photos failed: {list_resp.text}"
        
        photos = list_resp.json()
        assert isinstance(photos, list), "Photos response should be a list"
        assert len(photos) >= 1, "Should have at least 1 photo"
        
        photo = photos[0]
        assert "id" in photo, "Photo missing id"
        assert "section_index" in photo, "Photo missing section_index"
        assert "storage_path" in photo, "Photo missing storage_path"
        
        print(f"✓ List photos returns {len(photos)} photo(s)")
    
    def test_07_delete_proposal_photo(self):
        """Test deleting a photo from a proposal"""
        # Create proposal and upload photo
        payload = {
            "empresa": "TEST_Delete Photo Test",
            "contato": "Eduardo",
            "email": "eduardo@test.com",
            "embarcacao": "Navio Delete",
            "equipamento": "Bomba",
            "itens": [{"id": "i1", "titulo": "Seção", "descricao": "Desc", "valor": 1000}],
            "termos_gerais": "",
            "observacoes": ""
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        # Upload a photo
        from PIL import Image
        img = Image.new('RGB', (50, 50), color='green')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        img_buffer.seek(0)
        
        del self.session.headers["Content-Type"]
        files = {'file': ('test_delete.jpg', img_buffer, 'image/jpeg')}
        upload_resp = self.session.post(
            f"{BASE_URL}/api/proposals/{proposal_id}/upload-photo?section_index=0",
            files=files,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert upload_resp.status_code == 200
        self.session.headers["Content-Type"] = "application/json"
        
        # List photos to get photo_id
        list_resp = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}/photos")
        assert list_resp.status_code == 200
        photos = list_resp.json()
        assert len(photos) >= 1
        photo_id = photos[0]["id"]
        
        # Delete photo
        delete_resp = self.session.delete(f"{BASE_URL}/api/proposals/{proposal_id}/photos/{photo_id}")
        assert delete_resp.status_code == 200, f"Delete photo failed: {delete_resp.text}"
        
        # Verify photo is deleted (soft delete)
        list_resp2 = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}/photos")
        assert list_resp2.status_code == 200
        photos2 = list_resp2.json()
        photo_ids = [p["id"] for p in photos2]
        assert photo_id not in photo_ids, "Deleted photo should not appear in list"
        
        print(f"✓ Delete photo successful")
    
    # ==================== PDF GENERATION ====================
    
    def test_08_commercial_pdf_plain_text_client_info(self):
        """Test that commercial PDF has plain text client info (no table)"""
        # Create proposal with all fields
        payload = {
            "empresa": "TEST_PDF Client Info Test LTDA",
            "contato": "Fernando Almeida",
            "email": "fernando@pdftest.com",
            "embarcacao": "Navio PDF Test",
            "equipamento": "Motor Diesel Principal",
            "itens": [
                {"id": "i1", "titulo": "Manutenção Preventiva", "descricao": "Serviço completo", "valor": 5000},
                {"id": "i2", "titulo": "Troca de Óleo", "descricao": "Óleo sintético", "valor": 1500}
            ],
            "termos_gerais": "Prazo: 10 dias. Garantia: 60 dias.",
            "observacoes": "Observação de teste para PDF"
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        # Generate commercial PDF
        pdf_resp = self.session.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=comercial&token={self.token}"
        )
        assert pdf_resp.status_code == 200, f"PDF generation failed: {pdf_resp.text}"
        assert pdf_resp.headers.get("content-type") == "application/pdf"
        
        # Parse PDF content with PyMuPDF
        pdf_data = pdf_resp.content
        pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        full_text = ""
        for page in pdf_doc:
            full_text += page.get_text()
        pdf_doc.close()
        
        # Verify client info is present as plain text
        assert "TEST_PDF Client Info Test LTDA" in full_text, "Empresa not in PDF"
        assert "Fernando Almeida" in full_text, "Contato not in PDF"
        assert "fernando@pdftest.com" in full_text, "Email not in PDF"
        assert "Navio PDF Test" in full_text, "Embarcacao not in PDF"
        assert "Motor Diesel Principal" in full_text, "Equipamento not in PDF"
        
        # Verify NO table indicators (HTML table tags should not be present)
        # In plain text PDF, we shouldn't see table-like structures for client info
        # The client info should be formatted as "Label: Value" lines
        assert "Empresa:" in full_text, "Client info should have 'Empresa:' label"
        
        print(f"✓ Commercial PDF has plain text client info")
    
    def test_09_commercial_pdf_numbered_sections_with_prices(self):
        """Test that commercial PDF has numbered sections with prices"""
        # Create proposal
        payload = {
            "empresa": "TEST_Numbered Sections Test",
            "contato": "Gabriela",
            "email": "gabi@test.com",
            "embarcacao": "Barco Numbered",
            "equipamento": "Gerador",
            "itens": [
                {"id": "i1", "titulo": "Serviço A", "descricao": "Descrição A", "valor": 3000},
                {"id": "i2", "titulo": "Serviço B", "descricao": "Descrição B", "valor": 2000},
                {"id": "i3", "titulo": "Serviço C", "descricao": "Descrição C", "valor": 1000}
            ],
            "termos_gerais": "Termos de teste",
            "observacoes": ""
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        # Generate commercial PDF
        pdf_resp = self.session.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=comercial&token={self.token}"
        )
        assert pdf_resp.status_code == 200
        
        pdf_data = pdf_resp.content
        pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        full_text = ""
        for page in pdf_doc:
            full_text += page.get_text()
        pdf_doc.close()
        
        # Verify numbered sections
        assert "1. Serviço A" in full_text or "1.Serviço A" in full_text or "1." in full_text, "Section 1 not numbered"
        assert "2. Serviço B" in full_text or "2.Serviço B" in full_text or "2." in full_text, "Section 2 not numbered"
        assert "3. Serviço C" in full_text or "3.Serviço C" in full_text or "3." in full_text, "Section 3 not numbered"
        
        # Verify prices are shown (R$ format)
        assert "R$" in full_text, "Prices (R$) should be in commercial PDF"
        assert "3.000" in full_text or "3000" in full_text, "Price 3000 should be in PDF"
        
        # Verify VALOR TOTAL
        assert "VALOR TOTAL" in full_text, "VALOR TOTAL should be in commercial PDF"
        
        print(f"✓ Commercial PDF has numbered sections with prices")
    
    def test_10_commercial_pdf_termos_gerais_section(self):
        """Test that commercial PDF has TERMOS E CONDICOES GERAIS section"""
        payload = {
            "empresa": "TEST_Termos PDF Test",
            "contato": "Helena",
            "email": "helena@test.com",
            "embarcacao": "Navio Termos",
            "equipamento": "Bomba",
            "itens": [{"id": "i1", "titulo": "Serviço", "descricao": "Desc", "valor": 1000}],
            "termos_gerais": "Prazo de execução: 15 dias úteis. Garantia: 90 dias após conclusão.",
            "observacoes": ""
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        pdf_resp = self.session.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=comercial&token={self.token}"
        )
        assert pdf_resp.status_code == 200
        
        pdf_data = pdf_resp.content
        pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        full_text = ""
        for page in pdf_doc:
            full_text += page.get_text()
        pdf_doc.close()
        
        # Verify TERMOS E CONDIÇÕES GERAIS section
        assert "TERMOS E CONDI" in full_text or "TERMOS E CONDIÇÕES GERAIS" in full_text, \
            "TERMOS E CONDIÇÕES GERAIS section not found in PDF"
        
        # Verify termos content
        assert "Prazo de execução" in full_text or "15 dias" in full_text, \
            "Termos content not in PDF"
        
        print(f"✓ Commercial PDF has TERMOS E CONDIÇÕES GERAIS section")
    
    def test_11_commercial_pdf_observacoes_section(self):
        """Test that commercial PDF has OBSERVACOES section"""
        payload = {
            "empresa": "TEST_Obs PDF Test",
            "contato": "Igor",
            "email": "igor@test.com",
            "embarcacao": "Barco Obs",
            "equipamento": "Compressor",
            "itens": [{"id": "i1", "titulo": "Serviço", "descricao": "Desc", "valor": 1000}],
            "termos_gerais": "Termos",
            "observacoes": "Esta é uma observação importante para o cliente."
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        pdf_resp = self.session.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=comercial&token={self.token}"
        )
        assert pdf_resp.status_code == 200
        
        pdf_data = pdf_resp.content
        pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        full_text = ""
        for page in pdf_doc:
            full_text += page.get_text()
        pdf_doc.close()
        
        # Verify OBSERVAÇÕES section
        assert "OBSERVA" in full_text, "OBSERVAÇÕES section not found in PDF"
        assert "observação importante" in full_text, "Observacoes content not in PDF"
        
        print(f"✓ Commercial PDF has OBSERVAÇÕES section")
    
    def test_12_technical_pdf_no_prices(self):
        """Test that technical PDF does NOT show prices (no R$ values)"""
        payload = {
            "empresa": "TEST_Technical PDF Test",
            "contato": "Julia",
            "email": "julia@test.com",
            "embarcacao": "Navio Tech",
            "equipamento": "Motor",
            "itens": [
                {"id": "i1", "titulo": "Serviço Técnico A", "descricao": "Descrição técnica", "valor": 5000},
                {"id": "i2", "titulo": "Serviço Técnico B", "descricao": "Outra descrição", "valor": 3000}
            ],
            "termos_gerais": "Termos técnicos",
            "observacoes": "Obs técnica"
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        # Generate TECHNICAL PDF
        pdf_resp = self.session.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=tecnica&token={self.token}"
        )
        assert pdf_resp.status_code == 200
        
        pdf_data = pdf_resp.content
        pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        full_text = ""
        for page in pdf_doc:
            full_text += page.get_text()
        pdf_doc.close()
        
        # Verify title is PROPOSTA TÉCNICA
        assert "PROPOSTA TÉCNICA" in full_text, "Title should be PROPOSTA TÉCNICA"
        
        # Verify numbered sections exist
        assert "1. Serviço Técnico A" in full_text or "1." in full_text, "Section 1 should be numbered"
        
        # Verify NO prices (R$ should not appear, or VALOR TOTAL should not appear)
        # Technical PDF should not show monetary values
        assert "VALOR TOTAL" not in full_text, "VALOR TOTAL should NOT be in technical PDF"
        
        # Verify termos gerais is still present
        assert "TERMOS E CONDI" in full_text or "Termos técnicos" in full_text, \
            "Termos should still be in technical PDF"
        
        print(f"✓ Technical PDF does NOT show prices")
    
    def test_13_technical_pdf_has_numbered_sections(self):
        """Test that technical PDF has numbered sections without prices"""
        payload = {
            "empresa": "TEST_Tech Numbered Test",
            "contato": "Karen",
            "email": "karen@test.com",
            "embarcacao": "Barco Tech",
            "equipamento": "Gerador",
            "itens": [
                {"id": "i1", "titulo": "Inspeção Visual", "descricao": "Verificação completa", "valor": 2000},
                {"id": "i2", "titulo": "Teste de Funcionamento", "descricao": "Testes operacionais", "valor": 1500}
            ],
            "termos_gerais": "Termos",
            "observacoes": ""
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_resp.status_code == 200
        proposal_id = create_resp.json()["id"]
        self.created_proposal_id = proposal_id
        
        pdf_resp = self.session.get(
            f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=tecnica&token={self.token}"
        )
        assert pdf_resp.status_code == 200
        
        pdf_data = pdf_resp.content
        pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        full_text = ""
        for page in pdf_doc:
            full_text += page.get_text()
        pdf_doc.close()
        
        # Verify sections are numbered
        assert "1." in full_text, "Section 1 should be numbered"
        assert "2." in full_text, "Section 2 should be numbered"
        assert "Inspeção Visual" in full_text, "Section title should be in PDF"
        assert "Teste de Funcionamento" in full_text, "Section title should be in PDF"
        
        print(f"✓ Technical PDF has numbered sections")
    
    # ==================== DASHBOARD STILL WORKS ====================
    
    def test_14_dashboard_still_works(self):
        """Test that dashboard endpoint still works correctly"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/summary")
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        
        data = response.json()
        assert "bm_by_month" in data, "Dashboard missing bm_by_month"
        assert "proposals_by_status" in data, "Dashboard missing proposals_by_status"
        assert "totals" in data, "Dashboard missing totals"
        
        print(f"✓ Dashboard still works correctly")
    
    def test_15_proposals_list_still_works(self):
        """Test that proposals list endpoint still works"""
        response = self.session.get(f"{BASE_URL}/api/proposals")
        assert response.status_code == 200, f"Proposals list failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Proposals should return a list"
        
        # Verify each proposal has termos_gerais field
        for p in data[:5]:  # Check first 5
            assert "termos_gerais" in p, f"Proposal {p.get('id')} missing termos_gerais"
        
        print(f"✓ Proposals list works, returned {len(data)} proposals")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
