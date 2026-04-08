#!/usr/bin/env python3
"""
Backend API Testing for Timesheet PDF Generation and Delete Functionality
Tests as per review requirements:
- PDF generation with content validation  
- Delete functionality verification
- Multiple timesheet PDF consistency testing
"""

import requests
import json
from datetime import datetime
import io
import sys
import time

# Install PyPDF2 if not available
try:
    import PyPDF2
except ImportError:
    print("Installing PyPDF2...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
    import PyPDF2

# API Configuration  
API_BASE_URL = "https://twas-repair-preview.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"
SUPERVISOR_EMAIL = "supervisor@twasrepair.com"
SUPERVISOR_PASSWORD = "super123"

class TimesheetAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_results = []
        self.timesheets_to_cleanup = []
        
    def log_result(self, test_name, success, message):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} {test_name}: {message}"
        print(result)
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
        
    def login_admin(self):
        """Login as admin and get authentication token"""
        try:
            response = self.session.post(f"{API_BASE_URL}/auth/login", 
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                self.log_result("Admin Login", True, f"Successfully logged in as {ADMIN_EMAIL}")
                return True
            else:
                self.log_result("Admin Login", False, f"Failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Admin Login", False, f"Exception: {str(e)}")
            return False
    
    def list_timesheets(self):
        """List all timesheets"""
        try:
            response = self.session.get(f"{API_BASE_URL}/timesheets")
            
            if response.status_code == 200:
                timesheets = response.json()
                self.log_result("List Timesheets", True, f"Found {len(timesheets)} timesheets")
                return timesheets
            else:
                self.log_result("List Timesheets", False, f"Failed with status {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            self.log_result("List Timesheets", False, f"Exception: {str(e)}")
            return []
    
    def download_pdf(self, timesheet_id, test_name="PDF Download"):
        """Download PDF for a timesheet with timestamp parameter"""
        try:
            timestamp = int(time.time())
            response = self.session.get(f"{API_BASE_URL}/timesheets/{timesheet_id}/pdf?t={timestamp}")
            
            if response.status_code != 200:
                self.log_result(test_name, False, f"HTTP {response.status_code}: {response.text}")
                return None
                
            # Verify content type
            content_type = response.headers.get('content-type', '')
            if 'application/pdf' not in content_type:
                self.log_result(f"{test_name} Content-Type", False, f"Expected application/pdf, got: {content_type}")
                return None
            else:
                self.log_result(f"{test_name} Content-Type", True, "Correct application/pdf content-type")
                
            # Verify Cache-Control headers
            cache_control = response.headers.get('cache-control', '')
            if 'no-cache' in cache_control:
                self.log_result(f"{test_name} Cache-Control", True, f"Correct cache headers: {cache_control}")
            else:
                self.log_result(f"{test_name} Cache-Control", False, f"Expected no-cache, got: {cache_control}")
                
            self.log_result(test_name, True, f"Successfully downloaded PDF for timesheet {timesheet_id}")
            return response.content
            
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            return None
    
    def verify_pdf_content(self, pdf_content, test_name="PDF Content Verification"):
        """Parse and verify PDF content according to review requirements"""
        try:
            pdf_buffer = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_buffer)
            
            # Verify exactly 1 page
            page_count = len(pdf_reader.pages)
            if page_count == 1:
                self.log_result(f"{test_name} Page Count", True, f"Exactly 1 page as required")
            else:
                self.log_result(f"{test_name} Page Count", False, f"Expected 1 page, got {page_count}")
                
            # Extract text from all pages
            pdf_text = ""
            for page in pdf_reader.pages:
                pdf_text += page.extract_text()
                
            self.log_result(f"{test_name} Text Extraction", True, f"Extracted text from {page_count} page(s)")
            
            # Required legend content as per review requirements
            required_items = [
                ("Legenda", "Legend title check"),
                ("Caption", "Caption title check"), 
                ("Engenheiro", "Engineer Portuguese check"),
                ("Engineer", "Engineer English check"),
                ("Encarregado", "Foreman Portuguese check"),
                ("Foreman", "Foreman English check"),
                ("Supervisor", "Supervisor check"),
                ("Técnico", "Technician Portuguese check"),
                ("Technician", "Technician English check"),
                ("Mecânico", "Mechanic Portuguese check"),
                ("Mechanic", "Mechanic English check")
            ]
            
            legend_pass = True
            found_items = []
            missing_items = []
            
            for item, description in required_items:
                # Handle special cases for accent variations
                if item == "Técnico" and "Tecnico" in pdf_text:
                    found_items.append(f"{item} (as Tecnico)")
                elif item == "Mecânico" and "Mecanico" in pdf_text:
                    found_items.append(f"{item} (as Mecanico)")
                elif item in pdf_text:
                    found_items.append(item)
                else:
                    missing_items.append(item)
                    legend_pass = False
                    
            if legend_pass:
                self.log_result(f"{test_name} Legend Content", True, f"All required legend items found: {found_items}")
            else:
                self.log_result(f"{test_name} Legend Content", False, f"Missing items: {missing_items}. Found: {found_items}")
                
            # Check for observations title (separate from table content)
            obs_variations = ["Observações", "Observacoes"]
            obs_found = False
            for obs in obs_variations:
                if obs in pdf_text:
                    obs_found = True
                    self.log_result(f"{test_name} Observations Title", True, f"Found '{obs}' as separate text")
                    break
                    
            if not obs_found:
                self.log_result(f"{test_name} Observations Title", False, "Observations title not found as separate text")
                
            # Verify footer content
            footer_items = ["TWAS REPAIR", "Página 1 de 1"]
            footer_pass = True
            footer_found = []
            footer_missing = []
            
            for item in footer_items:
                if item in pdf_text:
                    footer_found.append(item)
                else:
                    footer_missing.append(item)
                    footer_pass = False
                    
            if footer_pass:
                self.log_result(f"{test_name} Footer Content", True, f"All required footer items found: {footer_found}")
            else:
                self.log_result(f"{test_name} Footer Content", False, f"Missing footer items: {footer_missing}. Found: {footer_found}")
                
            return True
            
        except Exception as e:
            self.log_result(f"{test_name} PDF Parsing", False, f"Failed to parse PDF: {str(e)}")
            return False
    
    def delete_timesheet(self, timesheet_id):
        """Delete a timesheet"""
        try:
            response = self.session.delete(f"{API_BASE_URL}/timesheets/{timesheet_id}")
            
            if response.status_code == 200:
                self.log_result("Delete Timesheet", True, f"Successfully deleted timesheet {timesheet_id}")
                return True
            else:
                self.log_result("Delete Timesheet", False, f"Failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Delete Timesheet", False, f"Exception: {str(e)}")
            return False
    
    def verify_timesheet_deleted(self, deleted_id):
        """Verify timesheet is actually removed from the list"""
        try:
            timesheets = self.list_timesheets()
            remaining_ids = [ts["id"] for ts in timesheets]
            
            if deleted_id not in remaining_ids:
                self.log_result("Verify Delete", True, f"Timesheet {deleted_id} successfully removed from list")
                return True
            else:
                self.log_result("Verify Delete", False, f"Timesheet {deleted_id} still exists in list")
                return False
                
        except Exception as e:
            self.log_result("Verify Delete", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run comprehensive tests as per review requirements"""
        print("🧪 Starting Timesheet API Comprehensive Tests")
        print("=" * 60)
        
        # Step 1: Login as admin
        if not self.login_admin():
            print("❌ Cannot proceed without admin authentication")
            return False
            
        # Step 2: List timesheets
        timesheets = self.list_timesheets()
        if not timesheets:
            print("⚠️ No timesheets found - cannot test PDF download and delete")
            return False
            
        print(f"\n📋 Found {len(timesheets)} timesheets to test")
        
        # Step 3: Download PDF for first timesheet
        first_timesheet = timesheets[0]
        first_id = first_timesheet["id"]
        
        print(f"\n🔍 Testing PDF generation for first timesheet: {first_id}")
        pdf_content = self.download_pdf(first_id, "First PDF Download")
        
        if pdf_content:
            # Step 4: Verify PDF content
            self.verify_pdf_content(pdf_content, "First PDF Content")
        
        # Step 5: Test PDF with another timesheet for consistency
        if len(timesheets) > 1:
            second_timesheet = timesheets[1] 
            second_id = second_timesheet["id"]
            
            print(f"\n🔍 Testing PDF consistency with second timesheet: {second_id}")
            second_pdf_content = self.download_pdf(second_id, "Second PDF Download")
            
            if second_pdf_content:
                self.verify_pdf_content(second_pdf_content, "Second PDF Content")
        else:
            print("\n⚠️ Only one timesheet available - skipping consistency test")
            
        # Step 6: Delete timesheet test
        # Use the last timesheet for deletion to be safe
        if len(timesheets) > 0:
            timesheet_to_delete = timesheets[-1]
            delete_id = timesheet_to_delete["id"]
            
            print(f"\n🗑️ Testing delete functionality with timesheet: {delete_id}")
            
            if self.delete_timesheet(delete_id):
                # Step 7: Verify deletion
                self.verify_timesheet_deleted(delete_id)
            
        print("\n" + "=" * 60)
        print("🏁 Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
                    
        return failed_tests == 0

if __name__ == "__main__":        
    tester = TimesheetAPITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)