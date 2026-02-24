#!/usr/bin/env python3
"""
Backend API Testing for Timesheet PDF Generation
Tests the PDF generation endpoint with focus on legend table formatting
"""

import requests
import json
from datetime import datetime
import io
import PyPDF2
import sys

# API Configuration
API_BASE_URL = "https://shift-docs-staging.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"

class TimesheetAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_results = []
        
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
            
    def get_or_create_employee(self):
        """Get existing employees or create one if none exist"""
        try:
            # Get existing employees
            response = self.session.get(f"{API_BASE_URL}/employees")
            if response.status_code == 200:
                employees = response.json()
                if employees:
                    emp_id = employees[0]["id"]
                    emp_name = employees[0]["name"]
                    self.log_result("Get Employees", True, f"Found {len(employees)} employee(s), using {emp_name}")
                    return emp_id, emp_name
                    
                # No employees found, create one
                employee_data = {
                    "name": "Test Worker",
                    "function": "T"
                }
                response = self.session.post(f"{API_BASE_URL}/employees", json=employee_data)
                if response.status_code == 200:
                    employee = response.json()
                    emp_id = employee["_id"]  # Create response uses _id
                    self.log_result("Create Employee", True, f"Created employee with ID: {emp_id}")
                    return emp_id, "Test Worker"
                else:
                    self.log_result("Create Employee", False, f"Failed with status {response.status_code}: {response.text}")
                    return None, None
            else:
                self.log_result("Get Employees", False, f"Failed with status {response.status_code}: {response.text}")
                return None, None
                
        except Exception as e:
            self.log_result("Employee Operations", False, f"Exception: {str(e)}")
            return None, None
            
    def get_or_create_service_order(self):
        """Get existing service orders or create one if none exist"""
        try:
            # Get existing service orders
            response = self.session.get(f"{API_BASE_URL}/service-orders")
            if response.status_code == 200:
                service_orders = response.json()
                if service_orders:
                    so_id = service_orders[0]["id"]
                    so_number = service_orders[0]["os_number"]
                    self.log_result("Get Service Orders", True, f"Found {len(service_orders)} service order(s), using {so_number}")
                    return so_id
                    
                # No service orders found, create one
                so_data = {
                    "os_number": "OS-TEST",
                    "client": "TestClient",
                    "location": "TestLocation",
                    "service": "TestService"
                }
                response = self.session.post(f"{API_BASE_URL}/service-orders", json=so_data)
                if response.status_code == 200:
                    service_order = response.json()
                    so_id = service_order["_id"]  # Create response uses _id
                    self.log_result("Create Service Order", True, f"Created service order with ID: {so_id}")
                    return so_id
                else:
                    self.log_result("Create Service Order", False, f"Failed with status {response.status_code}: {response.text}")
                    return None
            else:
                self.log_result("Get Service Orders", False, f"Failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Service Order Operations", False, f"Exception: {str(e)}")
            return None
            
    def get_or_create_timesheet(self, so_id, emp_id, emp_name):
        """Get existing timesheets or create one if none exist"""
        try:
            # Get existing timesheets
            response = self.session.get(f"{API_BASE_URL}/timesheets")
            if response.status_code == 200:
                timesheets = response.json()
                if timesheets:
                    ts_id = timesheets[0]["id"]
                    self.log_result("Get Timesheets", True, f"Found {len(timesheets)} timesheet(s), using first one")
                    return ts_id
                    
                # No timesheets found, create one
                ts_data = {
                    "os_id": so_id,
                    "entries": [{
                        "date": "10/02/2026",
                        "employee_id": emp_id,
                        "employee_name": emp_name,
                        "employee_function": "T",
                        "service_start": "08:00",
                        "service_end": "17:00",
                        "travel_start": "07:00",
                        "travel_end": "07:30"
                    }],
                    "observations": "Test PDF generation"
                }
                response = self.session.post(f"{API_BASE_URL}/timesheets", json=ts_data)
                if response.status_code == 200:
                    timesheet = response.json()
                    ts_id = timesheet["id"]  # List response uses id
                    self.log_result("Create Timesheet", True, f"Created timesheet with ID: {ts_id}")
                    return ts_id
                else:
                    self.log_result("Create Timesheet", False, f"Failed with status {response.status_code}: {response.text}")
                    return None
            else:
                self.log_result("Get Timesheets", False, f"Failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Timesheet Operations", False, f"Exception: {str(e)}")
            return None
            
    def test_pdf_generation(self, ts_id):
        """Test PDF generation and verify content"""
        try:
            # Download PDF
            response = self.session.get(f"{API_BASE_URL}/timesheets/{ts_id}/pdf")
            
            if response.status_code != 200:
                self.log_result("PDF Download", False, f"Failed with status {response.status_code}: {response.text}")
                return False
                
            # Verify content type
            content_type = response.headers.get('content-type', '')
            if 'application/pdf' not in content_type:
                self.log_result("PDF Content Type", False, f"Wrong content type: {content_type}")
                return False
            else:
                self.log_result("PDF Content Type", True, "Correct content-type: application/pdf")
                
            # Parse PDF content
            pdf_buffer = io.BytesIO(response.content)
            try:
                pdf_reader = PyPDF2.PdfReader(pdf_buffer)
                
                # Extract text from all pages
                pdf_text = ""
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text()
                    
                self.log_result("PDF Text Extraction", True, f"Successfully extracted text from {len(pdf_reader.pages)} page(s)")
                
                # Verify legend table content
                required_legend_items = [
                    "LEGENDA",
                    "Português", 
                    "English",
                    "Engenheiro",
                    "Engineer", 
                    "Encarregado",
                    "Foreman",
                    "Supervisor",
                    "Técnico", 
                    "Technician",
                    "Mecânico",
                    "Mechanic",
                    "Segurança",  # Note: this is from "Téc. Segurança" but "Segurança" should be in text
                    "Safety"
                ]
                
                missing_items = []
                found_items = []
                
                for item in required_legend_items:
                    if item in pdf_text:
                        found_items.append(item)
                    else:
                        missing_items.append(item)
                        
                if missing_items:
                    self.log_result("Legend Content Verification", False, 
                        f"Missing items: {missing_items}. Found items: {found_items}")
                else:
                    self.log_result("Legend Content Verification", True, 
                        f"All required legend items found: {found_items}")
                    
                # Check for table structure indicators
                table_indicators = ["CAPTION", "LEGENDA"]
                table_found = any(indicator in pdf_text for indicator in table_indicators)
                
                if table_found:
                    self.log_result("Legend Table Structure", True, "Found legend table structure indicators")
                else:
                    self.log_result("Legend Table Structure", False, "Legend table structure indicators not found")
                    
                return True
                
            except Exception as e:
                self.log_result("PDF Parsing", False, f"Failed to parse PDF: {str(e)}")
                return False
                
        except Exception as e:
            self.log_result("PDF Generation Test", False, f"Exception: {str(e)}")
            return False
            
    def run_all_tests(self):
        """Run all API tests"""
        print("🧪 Starting Timesheet API Tests")
        print("=" * 50)
        
        # Step 1: Login
        if not self.login_admin():
            print("❌ Cannot proceed without authentication")
            return False
            
        # Step 2: Get/Create Employee
        emp_id, emp_name = self.get_or_create_employee()
        if not emp_id:
            print("❌ Cannot proceed without employee")
            return False
            
        # Step 3: Get/Create Service Order
        so_id = self.get_or_create_service_order()
        if not so_id:
            print("❌ Cannot proceed without service order")
            return False
            
        # Step 4: Get/Create Timesheet
        ts_id = self.get_or_create_timesheet(so_id, emp_id, emp_name)
        if not ts_id:
            print("❌ Cannot proceed without timesheet")
            return False
            
        # Step 5: Test PDF Generation
        self.test_pdf_generation(ts_id)
        
        print("\n" + "=" * 50)
        print("🏁 Test Summary")
        print("=" * 50)
        
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
    # Install required packages if not available
    try:
        import PyPDF2
    except ImportError:
        print("Installing PyPDF2...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
        import PyPDF2
        
    tester = TimesheetAPITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)