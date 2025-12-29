#!/usr/bin/env python3
"""
Local Testing Automation Script
Starts Flask application locally and runs comprehensive tests
"""

import os
import sys
import time
import requests
import subprocess
import threading
import json
from pathlib import Path
from typing import Dict, List, Optional
import signal

class LocalTestRunner:
    """Runs local tests for the Passport Photo AI backend"""
    
    def __init__(self, app_file: str = 'application.py', port: int = 5000):
        self.app_file = app_file
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self.api_url = f"{self.base_url}/api"
        self.app_process = None
        self.test_results = {
            'success': True,
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'results': []
        }
    
    def start_application(self) -> bool:
        """Start the Flask application locally"""
        print("🚀 Starting Flask application locally...")
        
        if not Path(self.app_file).exists():
            print(f"❌ Application file not found: {self.app_file}")
            return False
        
        try:
            # Set environment variables for local testing
            env = os.environ.copy()
            env.update({
                'FLASK_ENV': 'development',
                'FLASK_DEBUG': 'false',
                'ALLOWED_ORIGINS': 'http://localhost:3000,https://main.d3gelc4wjo7dl.amplifyapp.com',
                'ENABLE_OPENCV': 'true',
                'ENABLE_REMBG': 'true',
                'ENABLE_ENHANCED_PROCESSING': 'true'
            })
            
            # Start the application
            self.app_process = subprocess.Popen(
                [sys.executable, self.app_file],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for application to start
            print("⏳ Waiting for application to start...")
            for attempt in range(30):  # 30 seconds timeout
                try:
                    response = requests.get(f"{self.base_url}/", timeout=2)
                    if response.status_code == 200:
                        print(f"✅ Application started successfully on port {self.port}")
                        return True
                except requests.exceptions.RequestException:
                    time.sleep(1)
            
            print("❌ Application failed to start within timeout")
            return False
            
        except Exception as e:
            print(f"❌ Error starting application: {str(e)}")
            return False
    
    def stop_application(self):
        """Stop the Flask application"""
        if self.app_process:
            print("🛑 Stopping Flask application...")
            self.app_process.terminate()
            try:
                self.app_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.app_process.kill()
                self.app_process.wait()
            print("✅ Application stopped")
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and record results"""
        self.test_results['tests_run'] += 1
        
        try:
            print(f"🧪 Running {test_name}...")
            success, message, details = test_func()
            
            result = {
                'test': test_name,
                'success': success,
                'message': message,
                'details': details or {}
            }
            
            self.test_results['results'].append(result)
            
            if success:
                self.test_results['tests_passed'] += 1
                print(f"✅ {test_name}: {message}")
            else:
                self.test_results['tests_failed'] += 1
                self.test_results['success'] = False
                print(f"❌ {test_name}: {message}")
                if details:
                    print(f"   Details: {details}")
            
            return success
            
        except Exception as e:
            self.test_results['tests_failed'] += 1
            self.test_results['success'] = False
            error_result = {
                'test': test_name,
                'success': False,
                'message': f"Test crashed: {str(e)}",
                'details': {'exception': str(e)}
            }
            self.test_results['results'].append(error_result)
            print(f"💥 {test_name}: Test crashed - {str(e)}")
            return False
    
    def test_health_endpoint(self) -> tuple:
        """Test the health endpoint"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'healthy':
                    features = data.get('features', {})
                    return True, "Health endpoint responding correctly", {
                        'opencv_available': features.get('opencv_available', False),
                        'rembg_available': features.get('rembg_available', False),
                        'enhanced_processing': features.get('enhanced_processing', False)
                    }
                else:
                    return False, f"Unhealthy status: {data.get('status')}", data
            else:
                return False, f"HTTP {response.status_code}", {'response': response.text}
                
        except Exception as e:
            return False, f"Request failed: {str(e)}", {}
    
    def test_cors_configuration(self) -> tuple:
        """Test CORS configuration"""
        try:
            # Test preflight request
            headers = {
                'Origin': 'https://main.d3gelc4wjo7dl.amplifyapp.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = requests.options(f"{self.api_url}/test-cors", headers=headers, timeout=10)
            
            if response.status_code == 200:
                cors_headers = {
                    'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                    'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                    'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
                }
                
                if cors_headers['Access-Control-Allow-Origin']:
                    return True, "CORS headers present and valid", cors_headers
                else:
                    return False, "Missing CORS headers", cors_headers
            else:
                return False, f"CORS preflight failed: {response.status_code}", {}
                
        except Exception as e:
            return False, f"CORS test failed: {str(e)}", {}
    
    def test_api_endpoints(self) -> tuple:
        """Test core API endpoints"""
        endpoints = [
            ('GET', '/', 'Root endpoint'),
            ('GET', '/api/health', 'Health endpoint'),
            ('GET', '/api/test-cors', 'CORS test endpoint'),
            ('OPTIONS', '/api/test-cors', 'CORS preflight'),
        ]
        
        results = {}
        all_passed = True
        
        for method, path, description in endpoints:
            try:
                url = f"{self.base_url}{path}"
                response = requests.request(method, url, timeout=10)
                
                if response.status_code in [200, 204]:
                    results[description] = {'status': 'PASS', 'code': response.status_code}
                else:
                    results[description] = {'status': 'FAIL', 'code': response.status_code}
                    all_passed = False
                    
            except Exception as e:
                results[description] = {'status': 'ERROR', 'error': str(e)}
                all_passed = False
        
        if all_passed:
            return True, "All API endpoints responding", results
        else:
            return False, "Some API endpoints failed", results
    
    def test_email_validation_endpoints(self) -> tuple:
        """Test email validation endpoints (without actually sending emails)"""
        try:
            # Test send-otp endpoint with invalid data
            response = requests.post(
                f"{self.api_url}/send-otp",
                json={'email': 'invalid-email'},
                timeout=10
            )
            
            if response.status_code == 400:
                # Test verify-otp endpoint with missing data
                response2 = requests.post(
                    f"{self.api_url}/verify-otp",
                    json={},
                    timeout=10
                )
                
                if response2.status_code == 400:
                    return True, "Email validation endpoints responding to invalid input correctly", {
                        'send_otp_validation': 'PASS',
                        'verify_otp_validation': 'PASS'
                    }
                else:
                    return False, "verify-otp endpoint not validating input", {
                        'verify_otp_status': response2.status_code
                    }
            else:
                return False, "send-otp endpoint not validating input", {
                    'send_otp_status': response.status_code
                }
                
        except Exception as e:
            return False, f"Email validation test failed: {str(e)}", {}
    
    def test_application_startup(self) -> tuple:
        """Test that application started with correct configuration"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', {})
                
                # Check that enhanced features are enabled
                checks = {
                    'cors_enabled': features.get('cors_enabled', False),
                    'origins_configured': features.get('origins_configured', 0) > 0,
                    'opencv_available': features.get('opencv_available', False),
                    'rembg_available': features.get('rembg_available', False)
                }
                
                passed_checks = sum(1 for v in checks.values() if v)
                total_checks = len(checks)
                
                if passed_checks >= total_checks * 0.75:  # At least 75% of checks pass
                    return True, f"Application configuration valid ({passed_checks}/{total_checks} checks passed)", checks
                else:
                    return False, f"Application configuration issues ({passed_checks}/{total_checks} checks passed)", checks
            else:
                return False, f"Cannot verify application configuration: HTTP {response.status_code}", {}
                
        except Exception as e:
            return False, f"Configuration test failed: {str(e)}", {}
    
    def run_all_tests(self) -> bool:
        """Run all local tests"""
        print("🧪 Starting local test suite...")
        print("="*60)
        
        # Start application
        if not self.start_application():
            return False
        
        try:
            # Run tests
            tests = [
                ("Health Endpoint", self.test_health_endpoint),
                ("CORS Configuration", self.test_cors_configuration),
                ("API Endpoints", self.test_api_endpoints),
                ("Email Validation Endpoints", self.test_email_validation_endpoints),
                ("Application Startup", self.test_application_startup)
            ]
            
            for test_name, test_func in tests:
                self.run_test(test_name, test_func)
                time.sleep(0.5)  # Brief pause between tests
            
            return self.test_results['success']
            
        finally:
            self.stop_application()
    
    def print_results(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("LOCAL TEST RESULTS")
        print("="*60)
        
        if self.test_results['success']:
            print("✅ Overall Status: PASSED")
        else:
            print("❌ Overall Status: FAILED")
        
        print(f"📊 Tests Run: {self.test_results['tests_run']}")
        print(f"✅ Passed: {self.test_results['tests_passed']}")
        print(f"❌ Failed: {self.test_results['tests_failed']}")
        
        if self.test_results['tests_failed'] > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results['results']:
                if not result['success']:
                    print(f"  • {result['test']}: {result['message']}")
    
    def save_results(self, output_file: str = 'local-test-results.json'):
        """Save test results to JSON file"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        with open(output_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"Results saved to: {output_path}")

def main():
    """Main function"""
    runner = LocalTestRunner()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n🛑 Interrupted by user")
        runner.stop_application()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        success = runner.run_all_tests()
        runner.print_results()
        runner.save_results()
        
        if not success:
            print("\n❌ Local tests failed!")
            sys.exit(1)
        else:
            print("\n✅ All local tests passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Test runner error: {str(e)}")
        runner.stop_application()
        sys.exit(1)

if __name__ == '__main__':
    main()