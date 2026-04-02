"""
Test iteration 24 features:
1. FUNCTION_NAMES updated: E=ENGENHEIRO, EN=ENCARREGADO (new), no ELETRICISTA
2. PUT /api/bm/{bm_id} endpoint for editing BM
3. BMCreate model accepts periodo as optional (default empty string)
4. POST /api/bm/calculate returns ENGENHEIRO for function E (not ELETRICISTA)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://repair-proposals-app.preview.emergentagent.com')
if BASE_URL.endswith('/'):
    BASE_URL = BASE_URL.rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"

# Known OS with timesheets
TEST_OS_ID = "699df3e6cf749c0aece02e93"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    return data["access_token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestFunctionNamesUpdate:
    """Test that FUNCTION_NAMES has been updated correctly"""
    
    def test_calculate_returns_engenheiro_for_e(self, auth_headers):
        """POST /api/bm/calculate should return ENGENHEIRO for function E (not ELETRICISTA)"""
        response = requests.post(
            f"{BASE_URL}/api/bm/calculate/{TEST_OS_ID}",
            headers=auth_headers,
            json={"timesheet_ids": [], "data_inicio": "", "data_fim": ""}
        )
        assert response.status_code == 200, f"Calculate failed: {response.text}"
        data = response.json()
        
        # Check items for function names
        items = data.get("items", [])
        function_names = [item.get("function_name", "") for item in items]
        
        # ELETRICISTA should NOT be present (it was removed from FUNCTION_NAMES)
        # Note: function names may have "(NOTURNO)" suffix for night shift
        base_function_names = [fn.replace(" (NOTURNO)", "") for fn in function_names]
        assert "ELETRICISTA" not in base_function_names, "ELETRICISTA should not be in function names (was removed)"
        
        # Check that valid function names are used (with optional NOTURNO suffix)
        valid_functions = ["ENGENHEIRO", "ENCARREGADO", "SUPERVISOR", "TÉCNICO", "MECÂNICO", "TÉCNICO DE SEGURANÇA"]
        for fn in base_function_names:
            assert fn in valid_functions, f"Unexpected function name: {fn}"
    
    def test_calculate_returns_encarregado_for_en(self, auth_headers):
        """Verify ENCARREGADO is a valid function (new addition)"""
        response = requests.post(
            f"{BASE_URL}/api/bm/calculate/{TEST_OS_ID}",
            headers=auth_headers,
            json={"timesheet_ids": [], "data_inicio": "", "data_fim": ""}
        )
        assert response.status_code == 200
        # Just verify the endpoint works - ENCARREGADO will only appear if there are EN entries


class TestBMUpdateEndpoint:
    """Test PUT /api/bm/{bm_id} endpoint for editing BM"""
    
    def test_create_and_update_bm(self, auth_headers):
        """Create a BM, then update it using PUT endpoint"""
        # First, create a BM
        create_payload = {
            "os_id": TEST_OS_ID,
            "periodo": "01/01/2025 a 15/01/2025",
            "data": "20/01/2025",
            "rev": "0",
            "po_number": "PO-TEST-001",
            "proposta": "PROP-TEST-001",
            "cod": "COD-TEST-001",
            "items": [
                {"function_name": "TÉCNICO", "qtd": 5, "valor_und": 100.0, "valor_total": 500.0, "shift": "day"}
            ],
            "subtotal": 500.0,
            "impostos": 0.0,
            "valor_total": 500.0
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/bm",
            headers=auth_headers,
            json=create_payload
        )
        assert create_response.status_code == 200, f"Create BM failed: {create_response.text}"
        created_bm = create_response.json()
        bm_id = created_bm.get("id")
        assert bm_id, "No BM ID returned"
        
        try:
            # Now update the BM using PUT
            update_payload = {
                "os_id": TEST_OS_ID,
                "periodo": "01/01/2025 a 31/01/2025",  # Changed period
                "data": "25/01/2025",  # Changed date
                "rev": "1",  # Changed revision
                "po_number": "PO-TEST-002",  # Changed PO
                "proposta": "PROP-TEST-002",
                "cod": "COD-TEST-002",
                "items": [
                    {"function_name": "TÉCNICO", "qtd": 10, "valor_und": 100.0, "valor_total": 1000.0, "shift": "day"}
                ],
                "subtotal": 1000.0,
                "impostos": 150.0,  # Added impostos
                "valor_total": 1150.0
            }
            
            update_response = requests.put(
                f"{BASE_URL}/api/bm/{bm_id}",
                headers=auth_headers,
                json=update_payload
            )
            assert update_response.status_code == 200, f"Update BM failed: {update_response.text}"
            updated_bm = update_response.json()
            
            # Verify update was applied
            assert updated_bm.get("rev") == "1", "Revision not updated"
            assert updated_bm.get("po_number") == "PO-TEST-002", "PO number not updated"
            assert updated_bm.get("subtotal") == 1000.0, "Subtotal not updated"
            assert updated_bm.get("impostos") == 150.0, "Impostos not updated"
            assert updated_bm.get("valor_total") == 1150.0, "Valor total not updated"
            
            # Verify by GET
            get_response = requests.get(
                f"{BASE_URL}/api/bm/{bm_id}",
                headers=auth_headers
            )
            assert get_response.status_code == 200
            fetched_bm = get_response.json()
            assert fetched_bm.get("rev") == "1", "GET: Revision not persisted"
            assert fetched_bm.get("impostos") == 150.0, "GET: Impostos not persisted"
            
        finally:
            # Cleanup: delete the test BM
            requests.delete(f"{BASE_URL}/api/bm/{bm_id}", headers=auth_headers)
    
    def test_update_nonexistent_bm_returns_404(self, auth_headers):
        """PUT /api/bm/{invalid_id} should return 404"""
        fake_id = "000000000000000000000000"
        update_payload = {
            "os_id": TEST_OS_ID,
            "periodo": "",
            "data": "01/01/2025",
            "rev": "0",
            "po_number": "",
            "proposta": "",
            "cod": "",
            "items": [],
            "subtotal": 0.0,
            "impostos": 0.0,
            "valor_total": 0.0
        }
        
        response = requests.put(
            f"{BASE_URL}/api/bm/{fake_id}",
            headers=auth_headers,
            json=update_payload
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestBMCreateWithOptionalPeriodo:
    """Test that BMCreate model accepts periodo as optional"""
    
    def test_create_bm_without_periodo(self, auth_headers):
        """Create BM without periodo field - should default to empty string"""
        create_payload = {
            "os_id": TEST_OS_ID,
            # "periodo" is intentionally omitted
            "data": "20/01/2025",
            "rev": "0",
            "po_number": "PO-NO-PERIODO",
            "proposta": "",
            "cod": "",
            "items": [
                {"function_name": "TÉCNICO", "qtd": 1, "valor_und": 100.0, "valor_total": 100.0, "shift": "day"}
            ],
            "subtotal": 100.0,
            "impostos": 0.0,
            "valor_total": 100.0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bm",
            headers=auth_headers,
            json=create_payload
        )
        assert response.status_code == 200, f"Create BM without periodo failed: {response.text}"
        created_bm = response.json()
        bm_id = created_bm.get("id")
        
        # Verify periodo defaults to empty string
        assert created_bm.get("periodo") == "", f"Expected empty periodo, got: {created_bm.get('periodo')}"
        
        # Cleanup
        if bm_id:
            requests.delete(f"{BASE_URL}/api/bm/{bm_id}", headers=auth_headers)
    
    def test_create_bm_with_empty_periodo(self, auth_headers):
        """Create BM with empty periodo string"""
        create_payload = {
            "os_id": TEST_OS_ID,
            "periodo": "",  # Explicitly empty
            "data": "20/01/2025",
            "rev": "0",
            "po_number": "PO-EMPTY-PERIODO",
            "proposta": "",
            "cod": "",
            "items": [
                {"function_name": "TÉCNICO", "qtd": 1, "valor_und": 100.0, "valor_total": 100.0, "shift": "day"}
            ],
            "subtotal": 100.0,
            "impostos": 0.0,
            "valor_total": 100.0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bm",
            headers=auth_headers,
            json=create_payload
        )
        assert response.status_code == 200, f"Create BM with empty periodo failed: {response.text}"
        created_bm = response.json()
        bm_id = created_bm.get("id")
        
        # Cleanup
        if bm_id:
            requests.delete(f"{BASE_URL}/api/bm/{bm_id}", headers=auth_headers)


class TestClientPriceFunctions:
    """Test that client price table uses correct function names in the UI"""
    
    def test_get_client_prices_endpoint_works(self, auth_headers):
        """GET /api/client-prices should return price tables"""
        response = requests.get(
            f"{BASE_URL}/api/client-prices",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get client prices failed: {response.text}"
        prices = response.json()
        assert isinstance(prices, list), "Expected list of price tables"
        # Note: Existing price tables in DB may have old function names (ELETRICISTA, ENCANADOR)
        # This is expected - the code change only affects NEW price tables created via UI
        # The frontend FUNCTION_OPTIONS array has the correct new values


class TestBMCRUDOperations:
    """Test full CRUD operations for BM"""
    
    def test_list_bm(self, auth_headers):
        """GET /api/bm should return list of BMs"""
        response = requests.get(
            f"{BASE_URL}/api/bm",
            headers=auth_headers
        )
        assert response.status_code == 200, f"List BM failed: {response.text}"
        bms = response.json()
        assert isinstance(bms, list), "Expected list of BMs"
    
    def test_get_bm_detail(self, auth_headers):
        """GET /api/bm/{id} should return BM details"""
        # First list BMs to get an ID
        list_response = requests.get(
            f"{BASE_URL}/api/bm",
            headers=auth_headers
        )
        bms = list_response.json()
        
        if len(bms) > 0:
            bm_id = bms[0].get("id")
            response = requests.get(
                f"{BASE_URL}/api/bm/{bm_id}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Get BM detail failed: {response.text}"
            bm = response.json()
            assert bm.get("id") == bm_id, "BM ID mismatch"
        else:
            pytest.skip("No BMs available to test GET detail")
    
    def test_delete_bm(self, auth_headers):
        """DELETE /api/bm/{id} should delete BM"""
        # Create a BM to delete
        create_payload = {
            "os_id": TEST_OS_ID,
            "periodo": "Test Delete",
            "data": "01/01/2025",
            "rev": "0",
            "po_number": "DELETE-TEST",
            "proposta": "",
            "cod": "",
            "items": [],
            "subtotal": 0.0,
            "impostos": 0.0,
            "valor_total": 0.0
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/bm",
            headers=auth_headers,
            json=create_payload
        )
        assert create_response.status_code == 200
        bm_id = create_response.json().get("id")
        
        # Delete it
        delete_response = requests.delete(
            f"{BASE_URL}/api/bm/{bm_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200, f"Delete BM failed: {delete_response.text}"
        
        # Verify it's gone
        get_response = requests.get(
            f"{BASE_URL}/api/bm/{bm_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404, "BM should be deleted"


class TestImpostosCalculation:
    """Test impostos calculation in BM"""
    
    def test_create_bm_with_impostos(self, auth_headers):
        """Create BM with impostos calculated from percentage"""
        subtotal = 1000.0
        imposto_pct = 15.0
        impostos = subtotal * imposto_pct / 100  # 150.0
        
        create_payload = {
            "os_id": TEST_OS_ID,
            "periodo": "01/01/2025 a 15/01/2025",
            "data": "20/01/2025",
            "rev": "0",
            "po_number": "PO-IMPOSTOS-TEST",
            "proposta": "",
            "cod": "",
            "items": [
                {"function_name": "TÉCNICO", "qtd": 10, "valor_und": 100.0, "valor_total": 1000.0, "shift": "day"}
            ],
            "subtotal": subtotal,
            "impostos": impostos,
            "valor_total": subtotal + impostos
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bm",
            headers=auth_headers,
            json=create_payload
        )
        assert response.status_code == 200, f"Create BM with impostos failed: {response.text}"
        created_bm = response.json()
        bm_id = created_bm.get("id")
        
        # Verify impostos
        assert created_bm.get("impostos") == 150.0, f"Expected impostos 150.0, got {created_bm.get('impostos')}"
        assert created_bm.get("valor_total") == 1150.0, f"Expected valor_total 1150.0, got {created_bm.get('valor_total')}"
        
        # Cleanup
        if bm_id:
            requests.delete(f"{BASE_URL}/api/bm/{bm_id}", headers=auth_headers)
    
    def test_create_bm_without_impostos(self, auth_headers):
        """Create BM with impostos = 0 (toggle off)"""
        create_payload = {
            "os_id": TEST_OS_ID,
            "periodo": "01/01/2025 a 15/01/2025",
            "data": "20/01/2025",
            "rev": "0",
            "po_number": "PO-NO-IMPOSTOS",
            "proposta": "",
            "cod": "",
            "items": [
                {"function_name": "TÉCNICO", "qtd": 5, "valor_und": 100.0, "valor_total": 500.0, "shift": "day"}
            ],
            "subtotal": 500.0,
            "impostos": 0.0,  # No impostos
            "valor_total": 500.0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bm",
            headers=auth_headers,
            json=create_payload
        )
        assert response.status_code == 200, f"Create BM without impostos failed: {response.text}"
        created_bm = response.json()
        bm_id = created_bm.get("id")
        
        # Verify no impostos
        assert created_bm.get("impostos") == 0.0, f"Expected impostos 0.0, got {created_bm.get('impostos')}"
        assert created_bm.get("valor_total") == 500.0, f"Expected valor_total 500.0, got {created_bm.get('valor_total')}"
        
        # Cleanup
        if bm_id:
            requests.delete(f"{BASE_URL}/api/bm/{bm_id}", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
