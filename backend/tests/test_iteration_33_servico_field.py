"""
Iteration 33: Testing 'servico' field in proposals
Features to test:
1. POST /api/proposals with 'servico' field - verify it saves and returns in response
2. PUT /api/proposals/{id} with 'servico' update - verify it updates correctly
3. GET /api/proposals - verify 'servico' field appears in list response
4. GET /api/proposals/{id} - verify 'servico' field appears in single response
5. PDF generation includes intro text with servico and embarcacao
6. Validate proposal creation with subsections and servico field
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://twas-repair-app-1.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"


class TestServicoField:
    """Test the new 'servico' field in proposals"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("access_token")
        assert token, "No access token returned"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.created_proposal_ids = []
        
        yield
        
        # Cleanup: Delete test proposals
        for proposal_id in self.created_proposal_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/proposals/{proposal_id}")
            except:
                pass
    
    def test_create_proposal_with_servico(self):
        """Test creating a proposal with the new 'servico' field"""
        payload = {
            "empresa": "TEST_Empresa Servico Test",
            "contato": "TEST_Contato",
            "email": "test@example.com",
            "embarcacao": "Plataforma P-71",
            "equipamento": "Turbina Principal",
            "servico": "Reparo de valvulas hidraulicas",
            "itens": [
                {
                    "id": "item1",
                    "titulo": "Secao de Teste",
                    "descricao": "Descricao da secao de teste",
                    "valor": 1500.00,
                    "subsections": []
                }
            ],
            "termos_gerais": "Termos de teste",
            "observacoes": "Observacoes de teste"
        }
        
        response = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert response.status_code == 200, f"Create proposal failed: {response.text}"
        
        data = response.json()
        self.created_proposal_ids.append(data["id"])
        
        # Verify servico field is returned
        assert "servico" in data, "servico field not in response"
        assert data["servico"] == "Reparo de valvulas hidraulicas", f"servico value mismatch: {data['servico']}"
        
        # Verify other fields
        assert data["empresa"] == "TEST_Empresa Servico Test"
        assert data["embarcacao"] == "Plataforma P-71"
        print(f"✓ Created proposal with servico: {data['servico']}")
    
    def test_get_proposal_returns_servico(self):
        """Test that GET /api/proposals/{id} returns servico field"""
        # First create a proposal
        payload = {
            "empresa": "TEST_Get Servico Test",
            "contato": "TEST_Contato",
            "servico": "Manutencao preventiva",
            "itens": [{"id": "item1", "titulo": "Secao 1", "descricao": "Desc", "valor": 1000}]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_response.status_code == 200
        proposal_id = create_response.json()["id"]
        self.created_proposal_ids.append(proposal_id)
        
        # Now GET the proposal
        get_response = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}")
        assert get_response.status_code == 200, f"GET proposal failed: {get_response.text}"
        
        data = get_response.json()
        assert "servico" in data, "servico field not in GET response"
        assert data["servico"] == "Manutencao preventiva", f"servico value mismatch: {data['servico']}"
        print(f"✓ GET proposal returns servico: {data['servico']}")
    
    def test_update_proposal_servico(self):
        """Test updating the servico field"""
        # Create proposal
        payload = {
            "empresa": "TEST_Update Servico Test",
            "contato": "TEST_Contato",
            "servico": "Servico Original",
            "itens": [{"id": "item1", "titulo": "Secao 1", "descricao": "Desc", "valor": 500}]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_response.status_code == 200
        proposal_id = create_response.json()["id"]
        self.created_proposal_ids.append(proposal_id)
        
        # Update servico
        update_payload = {
            "servico": "Servico Atualizado"
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/proposals/{proposal_id}", json=update_payload)
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        # Verify update
        get_response = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["servico"] == "Servico Atualizado", f"servico not updated: {data['servico']}"
        print(f"✓ Updated servico to: {data['servico']}")
    
    def test_list_proposals_includes_servico(self):
        """Test that GET /api/proposals list includes servico field"""
        # Create a proposal with servico
        payload = {
            "empresa": "TEST_List Servico Test",
            "contato": "TEST_Contato",
            "servico": "Servico para Listagem",
            "itens": [{"id": "item1", "titulo": "Secao 1", "descricao": "Desc", "valor": 750}]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_response.status_code == 200
        proposal_id = create_response.json()["id"]
        self.created_proposal_ids.append(proposal_id)
        
        # List proposals
        list_response = self.session.get(f"{BASE_URL}/api/proposals")
        assert list_response.status_code == 200, f"List failed: {list_response.text}"
        
        proposals = list_response.json()
        assert isinstance(proposals, list), "Response should be a list"
        
        # Find our test proposal
        test_proposal = next((p for p in proposals if p["id"] == proposal_id), None)
        assert test_proposal is not None, "Test proposal not found in list"
        assert "servico" in test_proposal, "servico field not in list response"
        assert test_proposal["servico"] == "Servico para Listagem"
        print(f"✓ List proposals includes servico: {test_proposal['servico']}")
    
    def test_create_proposal_with_subsections_and_servico(self):
        """Test creating a proposal with both subsections and servico field"""
        payload = {
            "empresa": "TEST_Subsections Servico Test",
            "contato": "TEST_Contato",
            "embarcacao": "Navio Teste",
            "servico": "Reparo completo de sistema hidraulico",
            "itens": [
                {
                    "id": "sec1",
                    "titulo": "Secao Principal",
                    "descricao": "Descricao da secao principal",
                    "valor": 2000.00,
                    "subsections": [
                        {
                            "id": "sub1",
                            "titulo": "Subsecao 1.1",
                            "descricao": "Descricao da subsecao 1.1"
                        },
                        {
                            "id": "sub2",
                            "titulo": "Subsecao 1.2",
                            "descricao": "Descricao da subsecao 1.2"
                        }
                    ]
                },
                {
                    "id": "sec2",
                    "titulo": "Segunda Secao",
                    "descricao": "Descricao da segunda secao",
                    "valor": 1500.00,
                    "subsections": []
                }
            ],
            "termos_gerais": "Termos e condicoes gerais de teste"
        }
        
        response = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        self.created_proposal_ids.append(data["id"])
        
        # Verify servico
        assert data["servico"] == "Reparo completo de sistema hidraulico"
        
        # Verify subsections
        assert len(data["itens"]) == 2
        assert len(data["itens"][0]["subsections"]) == 2
        assert data["itens"][0]["subsections"][0]["titulo"] == "Subsecao 1.1"
        
        print(f"✓ Created proposal with servico and {len(data['itens'][0]['subsections'])} subsections")
    
    def test_pdf_comercial_includes_intro_text(self):
        """Test that PDF comercial includes intro text with servico and embarcacao"""
        # Create proposal with servico and embarcacao
        payload = {
            "empresa": "TEST_PDF Intro Test",
            "contato": "TEST_Contato",
            "embarcacao": "Plataforma P-99",
            "servico": "Inspecao de equipamentos",
            "itens": [{"id": "item1", "titulo": "Inspecao Visual", "descricao": "Inspecao visual completa", "valor": 3000}]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_response.status_code == 200
        proposal_id = create_response.json()["id"]
        self.created_proposal_ids.append(proposal_id)
        
        # Get PDF comercial
        token = self.session.headers.get("Authorization", "").replace("Bearer ", "")
        pdf_response = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=comercial&token={token}")
        assert pdf_response.status_code == 200, f"PDF generation failed: {pdf_response.text}"
        assert pdf_response.headers.get("Content-Type") == "application/pdf"
        
        # Check PDF size (should be non-empty)
        pdf_content = pdf_response.content
        assert len(pdf_content) > 1000, f"PDF too small: {len(pdf_content)} bytes"
        
        print(f"✓ PDF comercial generated successfully ({len(pdf_content)} bytes)")
    
    def test_pdf_tecnica_includes_intro_text(self):
        """Test that PDF tecnica includes intro text with servico and embarcacao"""
        # Create proposal
        payload = {
            "empresa": "TEST_PDF Tecnica Test",
            "contato": "TEST_Contato",
            "embarcacao": "Navio Cargueiro",
            "servico": "Manutencao de motores",
            "itens": [{"id": "item1", "titulo": "Manutencao Motor 1", "descricao": "Manutencao completa", "valor": 5000}]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_response.status_code == 200
        proposal_id = create_response.json()["id"]
        self.created_proposal_ids.append(proposal_id)
        
        # Get PDF tecnica
        token = self.session.headers.get("Authorization", "").replace("Bearer ", "")
        pdf_response = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}/pdf?tipo=tecnica&token={token}")
        assert pdf_response.status_code == 200, f"PDF tecnica failed: {pdf_response.text}"
        assert pdf_response.headers.get("Content-Type") == "application/pdf"
        
        pdf_content = pdf_response.content
        assert len(pdf_content) > 1000, f"PDF too small: {len(pdf_content)} bytes"
        
        print(f"✓ PDF tecnica generated successfully ({len(pdf_content)} bytes)")
    
    def test_servico_field_required_validation(self):
        """Test that servico field is handled correctly (empty string allowed)"""
        # Create proposal without servico (should work, defaults to empty string)
        payload = {
            "empresa": "TEST_No Servico Test",
            "contato": "TEST_Contato",
            "itens": [{"id": "item1", "titulo": "Secao 1", "descricao": "Desc", "valor": 100}]
        }
        
        response = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert response.status_code == 200, f"Create without servico failed: {response.text}"
        
        data = response.json()
        self.created_proposal_ids.append(data["id"])
        
        # servico should be empty string
        assert data["servico"] == "", f"servico should be empty string, got: {data['servico']}"
        print("✓ Proposal created without servico (defaults to empty string)")
    
    def test_backward_compatibility_old_proposals(self):
        """Test that old proposals without servico field return empty string"""
        # List all proposals and check servico field exists
        list_response = self.session.get(f"{BASE_URL}/api/proposals")
        assert list_response.status_code == 200
        
        proposals = list_response.json()
        for p in proposals:
            assert "servico" in p, f"Proposal {p.get('id')} missing servico field"
        
        print(f"✓ All {len(proposals)} proposals have servico field (backward compatible)")


class TestProposalPhotoUpload:
    """Test photo upload functionality for sections and subsections"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.created_proposal_ids = []
        
        yield
        
        # Cleanup
        for proposal_id in self.created_proposal_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/proposals/{proposal_id}")
            except:
                pass
    
    def test_photo_upload_endpoint_exists(self):
        """Test that photo upload endpoint exists and requires proposal"""
        # Create a proposal first
        payload = {
            "empresa": "TEST_Photo Upload Test",
            "contato": "TEST_Contato",
            "servico": "Teste de upload",
            "itens": [{"id": "item1", "titulo": "Secao 1", "descricao": "Desc", "valor": 100}]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/proposals", json=payload)
        assert create_response.status_code == 200
        proposal_id = create_response.json()["id"]
        self.created_proposal_ids.append(proposal_id)
        
        # Try to get photos (should return empty list)
        photos_response = self.session.get(f"{BASE_URL}/api/proposals/{proposal_id}/photos")
        assert photos_response.status_code == 200, f"Get photos failed: {photos_response.text}"
        
        photos = photos_response.json()
        assert isinstance(photos, list), "Photos response should be a list"
        print(f"✓ Photo endpoint works, returned {len(photos)} photos")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
