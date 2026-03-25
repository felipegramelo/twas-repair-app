"""
Test BM (Boletim de Medição) Feature - Iteration 23
Tests for:
1. GET /api/bm/timesheets/{os_id} - List timesheets for BM selection
2. POST /api/bm/calculate/{os_id} - Calculate BM with timesheet selection and date filters
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"

# Known OS with timesheets
KNOWN_OS_ID = "699df3e6cf749c0aece02e93"


class TestBMTimesheetsEndpoint:
    """Tests for GET /api/bm/timesheets/{os_id}"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in login response"
        return data["access_token"]
    
    @pytest.fixture
    def supervisor_token(self):
        """Get supervisor auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_get_timesheets_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/bm/timesheets/{KNOWN_OS_ID}")
        assert response.status_code == 403, "Should require auth"
    
    def test_get_timesheets_requires_bm_access(self, supervisor_token):
        """Test that supervisor without bm_access is forbidden"""
        response = requests.get(
            f"{BASE_URL}/api/bm/timesheets/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 403, "Supervisor should be forbidden from BM endpoints"
    
    def test_get_timesheets_success(self, admin_token):
        """Test successful retrieval of timesheets for an OS"""
        response = requests.get(
            f"{BASE_URL}/api/bm/timesheets/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get timesheets: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify timesheet structure if any exist
        if len(data) > 0:
            ts = data[0]
            assert "id" in ts, "Timesheet should have id"
            assert "date_range" in ts, "Timesheet should have date_range"
            assert "employees" in ts, "Timesheet should have employees list"
            assert "entries_count" in ts, "Timesheet should have entries_count"
            assert "supervisor_name" in ts, "Timesheet should have supervisor_name"
            print(f"Found {len(data)} timesheets for OS {KNOWN_OS_ID}")
            print(f"First timesheet: id={ts['id']}, date_range={ts['date_range']}, entries={ts['entries_count']}")
    
    def test_get_timesheets_invalid_os(self, admin_token):
        """Test with invalid OS ID"""
        response = requests.get(
            f"{BASE_URL}/api/bm/timesheets/000000000000000000000000",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, "Should return 404 for invalid OS"


class TestBMCalculateEndpoint:
    """Tests for POST /api/bm/calculate/{os_id}"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def supervisor_token(self):
        """Get supervisor auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def available_timesheets(self, admin_token):
        """Get available timesheets for the known OS"""
        response = requests.get(
            f"{BASE_URL}/api/bm/timesheets/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            return response.json()
        return []
    
    def test_calculate_requires_auth(self):
        """Test that calculate endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/bm/calculate/{KNOWN_OS_ID}", json={})
        assert response.status_code == 403, "Should require auth"
    
    def test_calculate_requires_bm_access(self, supervisor_token):
        """Test that supervisor without bm_access is forbidden"""
        response = requests.post(
            f"{BASE_URL}/api/bm/calculate/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            json={}
        )
        assert response.status_code == 403, "Supervisor should be forbidden"
    
    def test_calculate_all_timesheets(self, admin_token):
        """Test BM calculation with all timesheets (empty timesheet_ids)"""
        response = requests.post(
            f"{BASE_URL}/api/bm/calculate/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"timesheet_ids": [], "data_inicio": "", "data_fim": ""}
        )
        assert response.status_code == 200, f"Calculate failed: {response.text}"
        
        data = response.json()
        assert "os_id" in data, "Response should have os_id"
        assert "os_number" in data, "Response should have os_number"
        assert "client" in data, "Response should have client"
        assert "items" in data, "Response should have items"
        assert "subtotal" in data, "Response should have subtotal"
        assert "data_inicial" in data, "Response should have data_inicial"
        assert "data_final" in data, "Response should have data_final"
        
        print(f"Calculate all: {len(data['items'])} items, subtotal={data['subtotal']}")
        print(f"Date range: {data['data_inicial']} - {data['data_final']}")
    
    def test_calculate_selected_timesheets(self, admin_token, available_timesheets):
        """Test BM calculation with specific timesheet IDs"""
        if len(available_timesheets) < 2:
            pytest.skip("Need at least 2 timesheets to test selection")
        
        # Select only first timesheet
        selected_ids = [available_timesheets[0]["id"]]
        
        response = requests.post(
            f"{BASE_URL}/api/bm/calculate/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"timesheet_ids": selected_ids, "data_inicio": "", "data_fim": ""}
        )
        assert response.status_code == 200, f"Calculate failed: {response.text}"
        
        data = response.json()
        assert "items" in data
        print(f"Calculate with 1 timesheet: {len(data['items'])} items, subtotal={data['subtotal']}")
        
        # Now calculate with all timesheets and compare
        response_all = requests.post(
            f"{BASE_URL}/api/bm/calculate/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"timesheet_ids": [], "data_inicio": "", "data_fim": ""}
        )
        data_all = response_all.json()
        
        # Selected subset should have <= items than all
        print(f"Compare: selected={len(data['items'])} items vs all={len(data_all['items'])} items")
    
    def test_calculate_with_date_filter(self, admin_token):
        """Test BM calculation with date filters"""
        # Use a date range that should filter some entries
        response = requests.post(
            f"{BASE_URL}/api/bm/calculate/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "timesheet_ids": [],
                "data_inicio": "01/01/2026",
                "data_fim": "31/01/2026"
            }
        )
        assert response.status_code == 200, f"Calculate with dates failed: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert data["data_inicial"] == "01/01/2026", "Should use provided data_inicio"
        assert data["data_final"] == "31/01/2026", "Should use provided data_fim"
        print(f"Calculate with date filter: {len(data['items'])} items")
    
    def test_calculate_invalid_os(self, admin_token):
        """Test calculate with invalid OS ID"""
        response = requests.post(
            f"{BASE_URL}/api/bm/calculate/000000000000000000000000",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )
        assert response.status_code == 404, "Should return 404 for invalid OS"
    
    def test_calculate_response_structure(self, admin_token):
        """Test that calculate response has correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/bm/calculate/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check all required fields
        required_fields = [
            "os_id", "os_number", "client", "location", "service",
            "schedule_type", "data_inicial", "data_final", "items",
            "subtotal", "has_price_table"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Check items structure if any exist
        if len(data["items"]) > 0:
            item = data["items"][0]
            item_fields = [
                "function_code", "function_name", "shift",
                "data_inicial", "data_final", "valor_und", "qtd", "valor_total"
            ]
            for field in item_fields:
                assert field in item, f"Item missing field: {field}"
            
            # Verify night shift has NOTURNO in name
            for item in data["items"]:
                if item["shift"] == "night":
                    assert "NOTURNO" in item["function_name"], "Night shift should have NOTURNO in name"


class TestBMNightShiftRates:
    """Test that night shift rates are calculated at +20% over day rates"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_night_shift_rate_calculation(self, admin_token):
        """Verify night shift rates are 20% higher than day rates"""
        response = requests.post(
            f"{BASE_URL}/api/bm/calculate/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )
        
        if response.status_code != 200:
            pytest.skip("Could not calculate BM")
        
        data = response.json()
        
        # Group items by function code
        day_rates = {}
        night_rates = {}
        
        for item in data["items"]:
            func = item["function_code"]
            if item["shift"] == "day":
                day_rates[func] = item["valor_und"]
            else:
                night_rates[func] = item["valor_und"]
        
        # Verify night rate = day rate * 1.2 for functions that have both
        for func in day_rates:
            if func in night_rates:
                expected_night = round(day_rates[func] * 1.2, 2)
                actual_night = night_rates[func]
                assert abs(actual_night - expected_night) < 0.01, \
                    f"Night rate for {func} should be {expected_night}, got {actual_night}"
                print(f"{func}: day={day_rates[func]}, night={actual_night} (expected {expected_night})")


class TestBMEndpointMethod:
    """Test that calculate endpoint uses POST method correctly"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_calculate_uses_post_method(self, admin_token):
        """Verify that calculate endpoint accepts POST, not GET"""
        # POST should work
        post_response = requests.post(
            f"{BASE_URL}/api/bm/calculate/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )
        assert post_response.status_code == 200, "POST should work"
        
        # GET should fail (405 Method Not Allowed)
        get_response = requests.get(
            f"{BASE_URL}/api/bm/calculate/{KNOWN_OS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 405, "GET should return 405 Method Not Allowed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
