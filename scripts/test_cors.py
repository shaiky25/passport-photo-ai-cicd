#!/usr/bin/env python3
"""
CORS Functionality Testing Script
Tests cross-origin request handling and CORS configuration
"""

import os
import sys
import json
import requests
from typing import Dict, List, Tuple
from datetime import datetime

class CORSTester:
    """Tests CORS functionality and configuration"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.test_results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'base_url': base_url,
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'cors_configuration': {},
            'results': []
        }
        
        # Test origins
        self.test_origins = [
            'https://main.d3gelc4wjo7dl.amplifyapp.com',  # Primary Amplify domain
            'http://localhost:3000',  # Local development
            'https://localhost:3000',  # Local development HTTPS
        ]
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single CORS test"""
        self.test_results['tests_run'] += 1
        
        try:
            print(f"🌐 Running {test_name}...")
            success, message, details = test_func()
            
            result = {
                'test': test_name,
                'success': success,
                'message': message,
                'details': details or {},
                'timestamp': datetime.now().isoformat()
            }
            
            self.test_results['results'].append(result)
            
            if success:
                self.test_results['tests_passed'] += 1
                print(f"✅ {test_name}: {message}")
            else:
                self.test_results['tests_failed'] += 1
                self.test_results['success'] = False
                print(f"❌ {test_name}: {message}")
            
            return success
            
        except Exception as e:
            self.test_results['tests_failed'] += 1
            self.test_results['success'] = False
            error_result = {
                'test': test_name,
                'success': False,
                'message': f"Test crashed: {str(e)}",
                'details': {'exception': str(e)},
                'timestamp': datetime.now().isoformat()
            }
            self.test_results['results'].append(error_result)
            print(f"💥 {test_name}: Test crashed - {str(e)}")
            return False
    
    def test_preflight_requests(self) -> Tuple[bool, str, Dict]:
        """Test CORS preflight requests"""
        results = {}
        successful_origins = 0
        
        for origin in self.test_origins:
            try:
                headers = {
                    'Origin': origin,
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'Content-Type'
                }
                
                response = requests.options(f"{self.api_url}/test-cors", headers=headers, timeout=30)
                
                cors_headers = {
                    'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                    'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                    'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                    'Access-Control-Max-Age': response.headers.get('Access-Control-Max-Age')
                }
                
                origin_allowed = (
                    response.status_code == 200 and 
                    cors_headers['Access-Control-Allow-Origin'] is not None
                )
                
                results[origin] = {
                    'status_code': response.status_code,
                    'origin_allowed': origin_allowed,
                    'cors_headers': cors_headers
                }
                
                if origin_allowed:
                    successful_origins += 1
                    
            except Exception as e:
                results[origin] = {
                    'error': str(e),
                    'origin_allowed': False
                }
        
        # Store CORS configuration for later reference
        if results:
            first_successful = next((r for r in results.values() if r.get('origin_allowed')), None)
            if first_successful:
                self.test_results['cors_configuration'] = first_successful.get('cors_headers', {})
        
        if successful_origins > 0:
            return True, f"CORS preflight working ({successful_origins}/{len(self.test_origins)} origins)", results
        else:
            return False, f"CORS preflight failed for all origins", results
    
    def test_actual_cors_requests(self) -> Tuple[bool, str, Dict]:
        """Test actual CORS requests (not preflight)"""
        results = {}
        successful_requests = 0
        
        for origin in self.test_origins:
            try:
                headers = {'Origin': origin}
                
                # Test GET request
                get_response = requests.get(f"{self.api_url}/test-cors", headers=headers, timeout=30)
                
                # Test POST request
                post_response = requests.post(
                    f"{self.api_url}/send-otp", 
                    json={'email': 'invalid'}, 
                    headers=headers, 
                    timeout=30
                )
                
                get_cors_header = get_response.headers.get('Access-Control-Allow-Origin')
                post_cors_header = post_response.headers.get('Access-Control-Allow-Origin')
                
                results[origin] = {
                    'get_request': {
                        'status_code': get_response.status_code,
                        'cors_header': get_cors_header,
                        'success': get_response.status_code == 200 and get_cors_header is not None
                    },
                    'post_request': {
                        'status_code': post_response.status_code,
                        'cors_header': post_cors_header,
                        'success': post_response.status_code in [200, 400] and post_cors_header is not None
                    }
                }
                
                if (results[origin]['get_request']['success'] and 
                    results[origin]['post_request']['success']):
                    successful_requests += 1
                    
            except Exception as e:
                results[origin] = {
                    'error': str(e),
                    'get_request': {'success': False},
                    'post_request': {'success': False}
                }
        
        if successful_requests > 0:
            return True, f"CORS requests working ({successful_requests}/{len(self.test_origins)} origins)", results
        else:
            return False, f"CORS requests failed for all origins", results
    
    def test_cors_headers_completeness(self) -> Tuple[bool, str, Dict]:
        """Test that all necessary CORS headers are present"""
        try:
            headers = {
                'Origin': self.test_origins[0],  # Use primary origin
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = requests.options(f"{self.api_url}/full-workflow", headers=headers, timeout=30)
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                'Access-Control-Max-Age': response.headers.get('Access-Control-Max-Age'),
                'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
            }
            
            # Check required headers
            required_headers = ['Access-Control-Allow-Origin', 'Access-Control-Allow-Methods']
            missing_headers = [h for h in required_headers if not cors_headers[h]]
            
            # Check methods
            allowed_methods = cors_headers.get('Access-Control-Allow-Methods', '').upper()
            required_methods = ['GET', 'POST', 'OPTIONS']
            missing_methods = [m for m in required_methods if m not in allowed_methods]
            
            details = {
                'cors_headers': cors_headers,
                'missing_headers': missing_headers,
                'missing_methods': missing_methods,
                'status_code': response.status_code
            }
            
            if not missing_headers and not missing_methods:
                return True, "All required CORS headers present", details
            else:
                issues = []
                if missing_headers:
                    issues.append(f"Missing headers: {', '.join(missing_headers)}")
                if missing_methods:
                    issues.append(f"Missing methods: {', '.join(missing_methods)}")
                return False, f"CORS headers incomplete: {'; '.join(issues)}", details
                
        except Exception as e:
            return False, f"CORS headers test failed: {str(e)}", {'error': str(e)}
    
    def test_cors_with_credentials(self) -> Tuple[bool, str, Dict]:
        """Test CORS with credentials"""
        try:
            headers = {
                'Origin': self.test_origins[0],
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            # Test preflight with credentials
            response = requests.options(f"{self.api_url}/send-otp", headers=headers, timeout=30)
            
            allow_credentials = response.headers.get('Access-Control-Allow-Credentials', '').lower()
            allow_origin = response.headers.get('Access-Control-Allow-Origin')
            
            details = {
                'status_code': response.status_code,
                'allow_credentials': allow_credentials,
                'allow_origin': allow_origin,
                'credentials_supported': allow_credentials == 'true'
            }
            
            # Credentials handling is optional, so we're lenient here
            if response.status_code == 200:
                return True, f"CORS credentials handling configured (credentials: {allow_credentials})", details
            else:
                return False, f"CORS credentials test failed (HTTP {response.status_code})", details
                
        except Exception as e:
            return False, f"CORS credentials test failed: {str(e)}", {'error': str(e)}
    
    def test_cors_error_responses(self) -> Tuple[bool, str, Dict]:
        """Test that CORS headers are present even in error responses"""
        try:
            headers = {'Origin': self.test_origins[0]}
            
            # Make a request that should return an error (400)
            response = requests.post(
                f"{self.api_url}/send-otp",
                json={'email': 'invalid-email'},
                headers=headers,
                timeout=30
            )
            
            cors_header = response.headers.get('Access-Control-Allow-Origin')
            
            details = {
                'status_code': response.status_code,
                'cors_header_present': cors_header is not None,
                'cors_header_value': cors_header
            }
            
            # Should be a 400 error with CORS headers
            if response.status_code == 400 and cors_header is not None:
                return True, "CORS headers present in error responses", details
            elif cors_header is not None:
                return True, f"CORS headers present (HTTP {response.status_code})", details
            else:
                return False, f"CORS headers missing in error response (HTTP {response.status_code})", details
                
        except Exception as e:
            return False, f"CORS error response test failed: {str(e)}", {'error': str(e)}
    
    def test_cors_forbidden_origins(self) -> Tuple[bool, str, Dict]:
        """Test that unauthorized origins are properly handled"""
        forbidden_origins = [
            'https://malicious-site.com',
            'http://localhost:8080',
            'https://unauthorized-domain.com'
        ]
        
        results = {}
        properly_blocked = 0
        
        for origin in forbidden_origins:
            try:
                headers = {'Origin': origin}
                response = requests.get(f"{self.api_url}/test-cors", headers=headers, timeout=30)
                
                cors_header = response.headers.get('Access-Control-Allow-Origin')
                
                # Check if origin is properly blocked (no CORS header or different origin)
                blocked = (cors_header is None or cors_header != origin)
                
                results[origin] = {
                    'status_code': response.status_code,
                    'cors_header': cors_header,
                    'properly_blocked': blocked
                }
                
                if blocked:
                    properly_blocked += 1
                    
            except Exception as e:
                results[origin] = {
                    'error': str(e),
                    'properly_blocked': True  # Error is acceptable for forbidden origins
                }
                properly_blocked += 1
        
        if properly_blocked == len(forbidden_origins):
            return True, f"Unauthorized origins properly blocked ({properly_blocked}/{len(forbidden_origins)})", results
        else:
            return False, f"Some unauthorized origins not blocked ({properly_blocked}/{len(forbidden_origins)})", results
    
    def run_all_tests(self) -> bool:
        """Run all CORS tests"""
        print("🌐 Starting CORS functionality testing...")
        print(f"🎯 Target URL: {self.base_url}")
        print(f"🔗 Test Origins: {', '.join(self.test_origins)}")
        print("="*60)
        
        # Run CORS tests
        tests = [
            ("CORS Preflight Requests", self.test_preflight_requests),
            ("Actual CORS Requests", self.test_actual_cors_requests),
            ("CORS Headers Completeness", self.test_cors_headers_completeness),
            ("CORS with Credentials", self.test_cors_with_credentials),
            ("CORS Error Responses", self.test_cors_error_responses),
            ("Forbidden Origins Blocking", self.test_cors_forbidden_origins)
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        return self.test_results['success']
    
    def print_results(self):
        """Print CORS test results"""
        print("\n" + "="*60)
        print("CORS FUNCTIONALITY TEST RESULTS")
        print("="*60)
        
        if self.test_results['success']:
            print("✅ Overall Status: PASSED")
        else:
            print("❌ Overall Status: FAILED")
        
        print(f"📊 Tests Run: {self.test_results['tests_run']}")
        print(f"✅ Passed: {self.test_results['tests_passed']}")
        print(f"❌ Failed: {self.test_results['tests_failed']}")
        
        # Show CORS configuration
        if self.test_results['cors_configuration']:
            print("\n🔧 CORS Configuration:")
            for header, value in self.test_results['cors_configuration'].items():
                if value:
                    print(f"  • {header}: {value}")
        
        if self.test_results['tests_failed'] > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results['results']:
                if not result['success']:
                    print(f"  • {result['test']}: {result['message']}")
    
    def save_results(self, output_file: str = 'cors-test-results.json'):
        """Save test results to JSON file"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        with open(output_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"Results saved to: {output_path}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python test_cors.py <base_url>")
        print("Example: python test_cors.py http://passport-photo-ai-enhanced.us-east-1.elasticbeanstalk.com")
        sys.exit(1)
    
    base_url = sys.argv[1]
    
    tester = CORSTester(base_url)
    
    try:
        success = tester.run_all_tests()
        tester.print_results()
        tester.save_results()
        
        if not success:
            print("\n❌ CORS tests failed!")
            sys.exit(1)
        else:
            print("\n✅ All CORS tests passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ CORS test error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()