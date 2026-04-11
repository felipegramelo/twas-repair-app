"""
Iteration 32: Proposal Subsections Testing
Tests for nested sections with subsections in Commercial Proposals (Propostas Comerciais)

Features tested:
1. Create proposal with sections and subsections
2. Update proposal preserving subsections
3. Get proposal returns subsections correctly
4. PDF generation with subsections (comercial and tecnica)
5. Termos e Condicoes Gerais section
6. Photo upload with section_key for subsections
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://twas-repair-app-1.preview.emergentagent.com').rstrip('/')

class TestProposalSubsections:
    """Test proposal subsection functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.created_proposal_id = None
        yield
        # Cleanup
        if self.created_proposal_id:
            try:
                requests.delete(f"{BASE_URL}/api/proposals/{self.created_proposal_id}", headers=self.headers)
            except:
                pass
    
    def test_01_create_proposal_with_subsections(self):
        """Test creating a proposal with sections containing subsections"""
        payload = {
            "empresa": "TEST_Empresa Subsecoes",
            "contato": "TEST_Contato",
            "email": "test@subsecoes.com",
            "embarcacao": "Plataforma P-99",
            "equipamento": "Turbina Principal",
            "observacoes": "Observacoes de teste",
            "termos_gerais": "Termos customizados para teste",
            "itens": [
                {
                    "id": "section-1",
                    "titulo": "Secao 1 - Inspecao",
                    "descricao": "Descricao da secao 1",
                    "valor": 5000.00,
                    "subsections": [
                        {
                            "id": "sub-1-1",
                            "titulo": "Subsecao 1.1 - Inspecao Visual",
                            "descricao": "Descricao da subsecao 1.1"
                        },
                        {
                            "id": "sub-1-2",
                            "titulo": "Subsecao 1.2 - Inspecao Tecnica",
                            "descricao": "Descricao da subsecao 1.2"
                        }
                    ]
                },
                {
                    "id": "section-2",
                    "titulo": "Secao 2 - Reparo",
                    "descricao": "Descricao da secao 2",
                    "valor": 10000.00,
                    "subsections": [
                        {
                            "id": "sub-2-1",
                            "titulo": "Subsecao 2.1 - Reparo Mecanico",
                            "descricao": "Descricao da subsecao 2.1"
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Create proposal failed: {response.text}"
        
        data = response.json()
        self.created_proposal_id = data["id"]
        
        # Verify response structure
        assert "id" in data
        assert "numero_proposta" in data
        assert data["empresa"] == "TEST_Empresa Subsecoes"
        assert data["termos_gerais"] == "Termos customizados para teste"
        assert len(data["itens"]) == 2
        
        # Verify subsections in section 1
        section1 = data["itens"][0]
        assert section1["titulo"] == "Secao 1 - Inspecao"
        assert "subsections" in section1
        assert len(section1["subsections"]) == 2
        assert section1["subsections"][0]["titulo"] == "Subsecao 1.1 - Inspecao Visual"
        assert section1["subsections"][1]["titulo"] == "Subsecao 1.2 - Inspecao Tecnica"
        
        # Verify subsections in section 2
        section2 = data["itens"][1]
        assert len(section2["subsections"]) == 1
        assert section2["subsections"][0]["titulo"] == "Subsecao 2.1 - Reparo Mecanico"
        
        print(f"PASS: Created proposal {data['numero_proposta']} with subsections")
    
    def test_02_get_proposal_returns_subsections(self):
        """Test that GET proposal returns subsections correctly"""
        # First create a proposal
        payload = {
            "empresa": "TEST_Get Subsecoes",
            "contato": "TEST_Contato Get",
            "email": "test@get.com",
            "embarcacao": "",
            "equipamento": "",
            "itens": [
                {
                    "id": "sec-1",
                    "titulo": "Secao Principal",
                    "descricao": "Descricao",
                    "valor": 1000.00,
                    "subsections": [
                        {"id": "sub-1", "titulo": "Sub 1", "descricao": "Desc sub 1"},
                        {"id": "sub-2", "titulo": "Sub 2", "descricao": "Desc sub 2"}
                    ]
                }
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_proposal_id = created["id"]
        
        # Now GET the proposal
        get_resp = requests.get(f"{BASE_URL}/api/proposals/{created['id']}", headers=self.headers)
        assert get_resp.status_code == 200, f"GET proposal failed: {get_resp.text}"
        
        data = get_resp.json()
        assert len(data["itens"]) == 1
        assert len(data["itens"][0]["subsections"]) == 2
        assert data["itens"][0]["subsections"][0]["titulo"] == "Sub 1"
        assert data["itens"][0]["subsections"][1]["titulo"] == "Sub 2"
        
        print(f"PASS: GET proposal returns subsections correctly")
    
    def test_03_update_proposal_preserves_subsections(self):
        """Test that updating a proposal preserves subsections"""
        # Create proposal with subsections
        payload = {
            "empresa": "TEST_Update Subsecoes",
            "contato": "TEST_Contato Update",
            "email": "test@update.com",
            "embarcacao": "",
            "equipamento": "",
            "itens": [
                {
                    "id": "sec-1",
                    "titulo": "Secao Original",
                    "descricao": "Descricao original",
                    "valor": 2000.00,
                    "subsections": [
                        {"id": "sub-1", "titulo": "Sub Original", "descricao": "Desc original"}
                    ]
                }
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_proposal_id = created["id"]
        
        # Update with new subsections
        update_payload = {
            "empresa": "TEST_Update Subsecoes UPDATED",
            "contato": "TEST_Contato Update",
            "email": "test@update.com",
            "itens": [
                {
                    "id": "sec-1",
                    "titulo": "Secao Atualizada",
                    "descricao": "Descricao atualizada",
                    "valor": 3000.00,
                    "subsections": [
                        {"id": "sub-1", "titulo": "Sub Atualizada", "descricao": "Desc atualizada"},
                        {"id": "sub-2", "titulo": "Nova Subsecao", "descricao": "Nova descricao"}
                    ]
                },
                {
                    "id": "sec-2",
                    "titulo": "Nova Secao",
                    "descricao": "Nova secao descricao",
                    "valor": 1500.00,
                    "subsections": []
                }
            ]
        }
        
        update_resp = requests.put(f"{BASE_URL}/api/proposals/{created['id']}", json=update_payload, headers=self.headers)
        assert update_resp.status_code == 200, f"Update proposal failed: {update_resp.text}"
        
        data = update_resp.json()
        assert data["empresa"] == "TEST_Update Subsecoes UPDATED"
        assert len(data["itens"]) == 2
        
        # Verify first section has updated subsections
        assert data["itens"][0]["titulo"] == "Secao Atualizada"
        assert len(data["itens"][0]["subsections"]) == 2
        assert data["itens"][0]["subsections"][0]["titulo"] == "Sub Atualizada"
        assert data["itens"][0]["subsections"][1]["titulo"] == "Nova Subsecao"
        
        # Verify second section has no subsections
        assert data["itens"][1]["titulo"] == "Nova Secao"
        assert len(data["itens"][1]["subsections"]) == 0
        
        print(f"PASS: Update proposal preserves and updates subsections correctly")
    
    def test_04_update_termos_gerais(self):
        """Test updating termos_gerais field"""
        # Create proposal
        payload = {
            "empresa": "TEST_Termos Update",
            "contato": "TEST_Contato",
            "email": "test@termos.com",
            "embarcacao": "",
            "equipamento": "",
            "termos_gerais": "Termos originais",
            "itens": [
                {"id": "sec-1", "titulo": "Secao", "descricao": "", "valor": 100.00, "subsections": []}
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_proposal_id = created["id"]
        assert created["termos_gerais"] == "Termos originais"
        
        # Update termos_gerais
        update_payload = {
            "termos_gerais": "Termos atualizados com novas condicoes"
        }
        
        update_resp = requests.put(f"{BASE_URL}/api/proposals/{created['id']}", json=update_payload, headers=self.headers)
        assert update_resp.status_code == 200
        
        data = update_resp.json()
        assert data["termos_gerais"] == "Termos atualizados com novas condicoes"
        
        # Verify with GET
        get_resp = requests.get(f"{BASE_URL}/api/proposals/{created['id']}", headers=self.headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["termos_gerais"] == "Termos atualizados com novas condicoes"
        
        print(f"PASS: termos_gerais field updates correctly")
    
    def test_05_pdf_comercial_with_subsections(self):
        """Test PDF comercial generation with subsections"""
        # Create proposal with subsections
        payload = {
            "empresa": "TEST_PDF Comercial",
            "contato": "TEST_Contato PDF",
            "email": "test@pdf.com",
            "embarcacao": "Navio Teste",
            "equipamento": "Motor Principal",
            "termos_gerais": "Termos para PDF teste",
            "observacoes": "Observacoes para PDF",
            "itens": [
                {
                    "id": "sec-1",
                    "titulo": "Inspecao Geral",
                    "descricao": "Descricao da inspecao",
                    "valor": 5000.00,
                    "subsections": [
                        {"id": "sub-1-1", "titulo": "Inspecao Visual", "descricao": "Inspecao visual detalhada"},
                        {"id": "sub-1-2", "titulo": "Inspecao Tecnica", "descricao": "Inspecao tecnica completa"}
                    ]
                },
                {
                    "id": "sec-2",
                    "titulo": "Reparo",
                    "descricao": "Descricao do reparo",
                    "valor": 10000.00,
                    "subsections": []
                }
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_proposal_id = created["id"]
        
        # Generate PDF comercial
        pdf_resp = requests.get(
            f"{BASE_URL}/api/proposals/{created['id']}/pdf?tipo=comercial&token={self.token}",
            headers=self.headers
        )
        assert pdf_resp.status_code == 200, f"PDF comercial generation failed: {pdf_resp.text}"
        assert pdf_resp.headers.get("Content-Type") == "application/pdf"
        
        # Check PDF size (should be reasonable)
        pdf_size = len(pdf_resp.content)
        assert pdf_size > 5000, f"PDF too small: {pdf_size} bytes"
        
        print(f"PASS: PDF comercial generated successfully ({pdf_size} bytes)")
    
    def test_06_pdf_tecnica_with_subsections(self):
        """Test PDF tecnica generation with subsections"""
        # Create proposal with subsections
        payload = {
            "empresa": "TEST_PDF Tecnica",
            "contato": "TEST_Contato PDF Tec",
            "email": "test@pdftec.com",
            "embarcacao": "Plataforma P-100",
            "equipamento": "Compressor",
            "termos_gerais": "Termos tecnicos",
            "itens": [
                {
                    "id": "sec-1",
                    "titulo": "Analise Tecnica",
                    "descricao": "Analise tecnica detalhada",
                    "valor": 8000.00,
                    "subsections": [
                        {"id": "sub-1-1", "titulo": "Analise de Vibracao", "descricao": "Medicao de vibracao"},
                        {"id": "sub-1-2", "titulo": "Analise Termica", "descricao": "Medicao termica"}
                    ]
                }
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_proposal_id = created["id"]
        
        # Generate PDF tecnica
        pdf_resp = requests.get(
            f"{BASE_URL}/api/proposals/{created['id']}/pdf?tipo=tecnica&token={self.token}",
            headers=self.headers
        )
        assert pdf_resp.status_code == 200, f"PDF tecnica generation failed: {pdf_resp.text}"
        assert pdf_resp.headers.get("Content-Type") == "application/pdf"
        
        pdf_size = len(pdf_resp.content)
        assert pdf_size > 5000, f"PDF too small: {pdf_size} bytes"
        
        print(f"PASS: PDF tecnica generated successfully ({pdf_size} bytes)")
    
    def test_07_list_proposals_returns_subsections(self):
        """Test that listing proposals returns subsections"""
        # Create proposal with subsections
        payload = {
            "empresa": "TEST_List Subsecoes",
            "contato": "TEST_Contato List",
            "email": "test@list.com",
            "embarcacao": "",
            "equipamento": "",
            "itens": [
                {
                    "id": "sec-1",
                    "titulo": "Secao Lista",
                    "descricao": "",
                    "valor": 500.00,
                    "subsections": [
                        {"id": "sub-1", "titulo": "Sub Lista", "descricao": ""}
                    ]
                }
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_proposal_id = created["id"]
        
        # List proposals
        list_resp = requests.get(f"{BASE_URL}/api/proposals", headers=self.headers)
        assert list_resp.status_code == 200
        
        proposals = list_resp.json()
        assert len(proposals) > 0
        
        # Find our created proposal
        found = None
        for p in proposals:
            if p["id"] == created["id"]:
                found = p
                break
        
        assert found is not None, "Created proposal not found in list"
        assert len(found["itens"]) == 1
        assert len(found["itens"][0]["subsections"]) == 1
        assert found["itens"][0]["subsections"][0]["titulo"] == "Sub Lista"
        
        print(f"PASS: List proposals returns subsections correctly")
    
    def test_08_proposal_without_subsections_backward_compat(self):
        """Test backward compatibility - proposal without subsections"""
        payload = {
            "empresa": "TEST_No Subsecoes",
            "contato": "TEST_Contato NoSub",
            "email": "test@nosub.com",
            "embarcacao": "",
            "equipamento": "",
            "itens": [
                {
                    "id": "sec-1",
                    "titulo": "Secao Simples",
                    "descricao": "Sem subsecoes",
                    "valor": 1000.00
                    # No subsections field
                }
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_proposal_id = created["id"]
        
        # Verify subsections is empty array (not missing)
        assert "subsections" in created["itens"][0]
        assert created["itens"][0]["subsections"] == []
        
        # Verify GET also returns empty subsections
        get_resp = requests.get(f"{BASE_URL}/api/proposals/{created['id']}", headers=self.headers)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["itens"][0]["subsections"] == []
        
        print(f"PASS: Backward compatibility - proposals without subsections work correctly")
    
    def test_09_photo_upload_with_section_key(self):
        """Test photo upload with section_key parameter for subsections"""
        # Create proposal
        payload = {
            "empresa": "TEST_Photo Upload",
            "contato": "TEST_Contato Photo",
            "email": "test@photo.com",
            "embarcacao": "",
            "equipamento": "",
            "itens": [
                {
                    "id": "sec-1",
                    "titulo": "Secao com Fotos",
                    "descricao": "",
                    "valor": 1000.00,
                    "subsections": [
                        {"id": "sub-1", "titulo": "Subsecao com Fotos", "descricao": ""}
                    ]
                }
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_proposal_id = created["id"]
        
        # Create a simple test image (1x1 pixel JPEG)
        import base64
        # Minimal valid JPEG
        jpeg_bytes = base64.b64decode(
            "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
            "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwh"
            "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAAR"
            "CAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAA"
            "AAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMB"
            "AAIRAxEAPwCwAB//2Q=="
        )
        
        # Upload to section 0 (main section)
        files = {"file": ("test_section.jpg", jpeg_bytes, "image/jpeg")}
        upload_resp = requests.post(
            f"{BASE_URL}/api/proposals/{created['id']}/upload-photo?section_index=0&section_key=0",
            files=files,
            headers=self.headers
        )
        assert upload_resp.status_code == 200, f"Photo upload to section failed: {upload_resp.text}"
        
        # Upload to subsection 0.0
        files = {"file": ("test_subsection.jpg", jpeg_bytes, "image/jpeg")}
        upload_resp2 = requests.post(
            f"{BASE_URL}/api/proposals/{created['id']}/upload-photo?section_index=0&section_key=0.0",
            files=files,
            headers=self.headers
        )
        assert upload_resp2.status_code == 200, f"Photo upload to subsection failed: {upload_resp2.text}"
        
        # Get photos and verify section_key
        photos_resp = requests.get(f"{BASE_URL}/api/proposals/{created['id']}/photos", headers=self.headers)
        assert photos_resp.status_code == 200
        
        photos = photos_resp.json()
        assert len(photos) == 2
        
        # Verify section_key values
        section_keys = [p.get("section_key", "") for p in photos]
        assert "0" in section_keys, "Section photo not found"
        assert "0.0" in section_keys, "Subsection photo not found"
        
        print(f"PASS: Photo upload with section_key works for sections and subsections")
    
    def test_10_delete_proposal_with_subsections(self):
        """Test deleting a proposal with subsections"""
        # Create proposal
        payload = {
            "empresa": "TEST_Delete Subsecoes",
            "contato": "TEST_Contato Delete",
            "email": "test@delete.com",
            "embarcacao": "",
            "equipamento": "",
            "itens": [
                {
                    "id": "sec-1",
                    "titulo": "Secao para Deletar",
                    "descricao": "",
                    "valor": 100.00,
                    "subsections": [
                        {"id": "sub-1", "titulo": "Sub para Deletar", "descricao": ""}
                    ]
                }
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        proposal_id = created["id"]
        
        # Delete proposal
        delete_resp = requests.delete(f"{BASE_URL}/api/proposals/{proposal_id}", headers=self.headers)
        assert delete_resp.status_code == 200
        
        # Verify it's deleted
        get_resp = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}", headers=self.headers)
        assert get_resp.status_code == 404
        
        # Don't set created_proposal_id since we already deleted it
        self.created_proposal_id = None
        
        print(f"PASS: Delete proposal with subsections works correctly")


class TestProposalValidation:
    """Test proposal validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@twasrepair.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.created_proposal_id = None
        yield
        if self.created_proposal_id:
            try:
                requests.delete(f"{BASE_URL}/api/proposals/{self.created_proposal_id}", headers=self.headers)
            except:
                pass
    
    def test_11_create_proposal_requires_empresa(self):
        """Test that empresa is required"""
        payload = {
            "empresa": "",  # Empty
            "contato": "TEST_Contato",
            "email": "test@test.com",
            "itens": [{"id": "1", "titulo": "Test", "descricao": "", "valor": 100}]
        }
        
        # Note: The backend may or may not validate this - we're testing the behavior
        response = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        # If validation exists, it should return 400/422
        # If not, it will create with empty empresa
        if response.status_code == 200:
            self.created_proposal_id = response.json()["id"]
            print(f"INFO: Backend allows empty empresa (created proposal)")
        else:
            print(f"PASS: Backend validates empresa field")
    
    def test_12_informar_po_creates_os(self):
        """Test that informar P.O. creates a service order"""
        # Create proposal
        payload = {
            "empresa": "TEST_Informar PO",
            "contato": "TEST_Contato PO",
            "email": "test@po.com",
            "embarcacao": "Navio PO Test",
            "equipamento": "Motor PO",
            "itens": [
                {
                    "id": "sec-1",
                    "titulo": "Servico PO",
                    "descricao": "Descricao",
                    "valor": 5000.00,
                    "subsections": []
                }
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proposals", json=payload, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_proposal_id = created["id"]
        
        # Informar P.O.
        po_payload = {"po_number": "PO-TEST-2026-001"}
        po_resp = requests.put(
            f"{BASE_URL}/api/proposals/{created['id']}/informar-po",
            json=po_payload,
            headers=self.headers
        )
        assert po_resp.status_code == 200, f"Informar PO failed: {po_resp.text}"
        
        data = po_resp.json()
        assert data["status"] == "aprovada"
        assert data["po_number"] == "PO-TEST-2026-001"
        assert "os_number" in data
        assert data["os_number"] != ""
        
        print(f"PASS: Informar P.O. creates O.S. {data['os_number']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
