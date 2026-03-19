"""
Tests for new features: Duplicate report, Photo upload/download/delete
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://repair-tracker-app-7.preview.emergentagent.com')

class TestNewFeatures:
    """Tests for new duplicate report and photo features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login and get token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "supervisor@twasrepair.com", "password": "super123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield
    
    def test_duplicate_report_with_different_os_and_period(self):
        """Test POST /api/reports/{id}/duplicate - duplicate with different OS and period"""
        # Get reports to find one to duplicate
        response = requests.get(f"{BASE_URL}/api/reports", headers=self.headers)
        assert response.status_code == 200
        reports = response.json().get("reports", [])
        assert len(reports) > 0, "No reports found to duplicate"
        
        # Find a service report to duplicate
        source_report = next((r for r in reports if r["report_type"] == "service"), reports[0])
        
        # Get service orders for a different OS
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        assert so_response.status_code == 200
        service_orders = so_response.json()
        assert len(service_orders) > 0, "No service orders found"
        
        # Find different OS if possible
        different_os = next((so for so in service_orders if so["id"] != source_report["os_id"]), service_orders[0])
        
        # Duplicate the report
        dup_response = requests.post(
            f"{BASE_URL}/api/reports/{source_report['id']}/duplicate",
            json={
                "os_id": different_os["id"],
                "periodo_inicio": "10/03/2026",
                "periodo_fim": "20/03/2026"
            },
            headers=self.headers
        )
        assert dup_response.status_code == 200, f"Duplicate failed: {dup_response.text}"
        
        dup_data = dup_response.json()
        assert "id" in dup_data, "Duplicate response missing 'id'"
        assert dup_data["os_number"] == different_os["os_number"], "OS number mismatch"
        assert dup_data["status"] == "draft", "Duplicated report should be draft"
        
        # Verify duplicated report has new period
        verify_response = requests.get(f"{BASE_URL}/api/reports/{dup_data['id']}", headers=self.headers)
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["periodo_inicio"] == "10/03/2026"
        assert verify_data["periodo_fim"] == "20/03/2026"
        
        # Cleanup: delete duplicated report
        requests.delete(f"{BASE_URL}/api/reports/{dup_data['id']}", headers=self.headers)
        print(f"TEST PASSED: Duplicated report {source_report['id']} to new OS {different_os['os_number']}")
    
    def test_duplicate_report_keep_same_os(self):
        """Test duplicate report keeping same OS but changing period"""
        response = requests.get(f"{BASE_URL}/api/reports", headers=self.headers)
        reports = response.json().get("reports", [])
        assert len(reports) > 0
        source_report = reports[0]
        
        # Duplicate keeping same OS
        dup_response = requests.post(
            f"{BASE_URL}/api/reports/{source_report['id']}/duplicate",
            json={
                "periodo_inicio": "01/04/2026",
                "periodo_fim": "30/04/2026"
            },
            headers=self.headers
        )
        assert dup_response.status_code == 200
        dup_data = dup_response.json()
        assert dup_data["os_number"] == source_report["os_number"], "OS should be same"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reports/{dup_data['id']}", headers=self.headers)
        print("TEST PASSED: Duplicate with same OS")
    
    def test_photo_upload_cover(self):
        """Test POST /api/reports/{id}/upload-photo?section_key=cover"""
        # Create a new report for testing photos
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        service_orders = so_response.json()
        os_id = service_orders[0]["id"]
        
        create_response = requests.post(
            f"{BASE_URL}/api/reports",
            json={"report_type": "service", "os_id": os_id},
            headers=self.headers
        )
        assert create_response.status_code == 200
        report_id = create_response.json()["id"]
        
        # Create a simple test image (1x1 PNG)
        import base64
        png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        
        # Upload cover photo
        files = {"file": ("test_cover.png", io.BytesIO(png_data), "image/png")}
        upload_response = requests.post(
            f"{BASE_URL}/api/reports/{report_id}/upload-photo?section_key=cover",
            files=files,
            headers=self.headers
        )
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        upload_data = upload_response.json()
        assert "storage_path" in upload_data
        assert upload_data["section_key"] == "cover"
        
        # Verify cover_photo field is set in report
        report_response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=self.headers)
        report_data = report_response.json()
        assert report_data["cover_photo"] == upload_data["storage_path"], "Cover photo path not set"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=self.headers)
        print("TEST PASSED: Cover photo upload")
    
    def test_photo_upload_section(self):
        """Test photo upload to a section (e.g., ndt)"""
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        service_orders = so_response.json()
        os_id = service_orders[0]["id"]
        
        create_response = requests.post(
            f"{BASE_URL}/api/reports",
            json={"report_type": "service", "os_id": os_id},
            headers=self.headers
        )
        report_id = create_response.json()["id"]
        
        import base64
        png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        
        # Upload to section 'ndt'
        files = {"file": ("test_ndt.png", io.BytesIO(png_data), "image/png")}
        upload_response = requests.post(
            f"{BASE_URL}/api/reports/{report_id}/upload-photo?section_key=ndt",
            files=files,
            headers=self.headers
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["section_key"] == "ndt"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=self.headers)
        print("TEST PASSED: Section photo upload")
    
    def test_get_photos(self):
        """Test GET /api/reports/{id}/photos"""
        # Create report and upload photo first
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        os_id = so_response.json()[0]["id"]
        
        create_response = requests.post(
            f"{BASE_URL}/api/reports",
            json={"report_type": "service", "os_id": os_id},
            headers=self.headers
        )
        report_id = create_response.json()["id"]
        
        import base64
        png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        files = {"file": ("test.png", io.BytesIO(png_data), "image/png")}
        requests.post(
            f"{BASE_URL}/api/reports/{report_id}/upload-photo?section_key=cover",
            files=files,
            headers=self.headers
        )
        
        # Get photos
        photos_response = requests.get(
            f"{BASE_URL}/api/reports/{report_id}/photos",
            headers=self.headers
        )
        assert photos_response.status_code == 200
        photos_data = photos_response.json()
        assert "photos" in photos_data
        assert len(photos_data["photos"]) == 1
        assert photos_data["photos"][0]["section_key"] == "cover"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=self.headers)
        print("TEST PASSED: Get photos")
    
    def test_download_photo_with_auth(self):
        """Test GET /api/photos/{path} with auth token"""
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        os_id = so_response.json()[0]["id"]
        
        create_response = requests.post(
            f"{BASE_URL}/api/reports",
            json={"report_type": "service", "os_id": os_id},
            headers=self.headers
        )
        report_id = create_response.json()["id"]
        
        import base64
        png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        files = {"file": ("test.png", io.BytesIO(png_data), "image/png")}
        upload_response = requests.post(
            f"{BASE_URL}/api/reports/{report_id}/upload-photo?section_key=cover",
            files=files,
            headers=self.headers
        )
        storage_path = upload_response.json()["storage_path"]
        
        # Download with auth query param
        download_response = requests.get(
            f"{BASE_URL}/api/photos/{storage_path}?auth={self.token}"
        )
        assert download_response.status_code == 200, f"Download failed: {download_response.status_code}"
        assert "image" in download_response.headers.get("content-type", "")
        
        # Download with Authorization header
        download_response2 = requests.get(
            f"{BASE_URL}/api/photos/{storage_path}",
            headers=self.headers
        )
        assert download_response2.status_code == 200
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=self.headers)
        print("TEST PASSED: Download photo with auth")
    
    def test_download_photo_without_auth_fails(self):
        """Test that photo download without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/photos/some/path")
        assert response.status_code == 401
        print("TEST PASSED: Unauthorized photo access rejected")
    
    def test_delete_photo(self):
        """Test DELETE /api/reports/{id}/photos/{photo_id}"""
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        os_id = so_response.json()[0]["id"]
        
        create_response = requests.post(
            f"{BASE_URL}/api/reports",
            json={"report_type": "service", "os_id": os_id},
            headers=self.headers
        )
        report_id = create_response.json()["id"]
        
        import base64
        png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        files = {"file": ("test.png", io.BytesIO(png_data), "image/png")}
        upload_response = requests.post(
            f"{BASE_URL}/api/reports/{report_id}/upload-photo?section_key=cover",
            files=files,
            headers=self.headers
        )
        
        # Get photo ID
        photos_response = requests.get(f"{BASE_URL}/api/reports/{report_id}/photos", headers=self.headers)
        photo_id = photos_response.json()["photos"][0]["id"]
        
        # Delete photo
        delete_response = requests.delete(
            f"{BASE_URL}/api/reports/{report_id}/photos/{photo_id}",
            headers=self.headers
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] == True
        
        # Verify photo is deleted (soft delete)
        photos_response2 = requests.get(f"{BASE_URL}/api/reports/{report_id}/photos", headers=self.headers)
        assert len(photos_response2.json()["photos"]) == 0
        
        # Verify cover_photo field is cleared
        report_response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=self.headers)
        assert report_response.json()["cover_photo"] == ""
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=self.headers)
        print("TEST PASSED: Delete photo")
    
    def test_invalid_file_format_rejected(self):
        """Test that invalid file formats are rejected"""
        so_response = requests.get(f"{BASE_URL}/api/service-orders", headers=self.headers)
        os_id = so_response.json()[0]["id"]
        
        create_response = requests.post(
            f"{BASE_URL}/api/reports",
            json={"report_type": "service", "os_id": os_id},
            headers=self.headers
        )
        report_id = create_response.json()["id"]
        
        # Try to upload a .txt file
        files = {"file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")}
        upload_response = requests.post(
            f"{BASE_URL}/api/reports/{report_id}/upload-photo?section_key=cover",
            files=files,
            headers=self.headers
        )
        assert upload_response.status_code == 400
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reports/{report_id}", headers=self.headers)
        print("TEST PASSED: Invalid file format rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
