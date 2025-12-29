#!/usr/bin/env python3
"""
Comprehensive Health Check Script
Tests all API endpoints and validates deployed application health
"""

import os
import sys
import json
import time
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import concurrent.futures
from urllib.parse import urljoin

class HealthChecker:
    """Comprehensive health checker for deployed application"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CI-CD-Pipeline-Health-Checker/1.0',
            'Origin': 'https://main.d3gelc4wjo7dl.amplifyapp.com'
        })
        
        self.health_results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'base_url': base_url,
            'checks_run': 0,
            'checks_passed': 0,
            'checks_failed': 0,
            'results': [],
            'overall_health': 'unknown'
        }
    
    def run_check(self, check_name: str, check_func) -> bool:
        """Run a single health check and record results"""
        self.health_results['checks_run'] += 1
        
        try:
            print(f"🔍 Running {check_name}...")
            success, message, details = check_func()
            
            result = {
                'check': check_name,
                'success': success,
                'message': message,
                'details': details or {},
                'timestamp': datetime.now().isoformat()
            }
            
            self.health_results['results'].append(result)
            
            if success:
                self.health_results['checks_passed'] += 1
                print(f"✅ {check_name}: {message}")
            else:
                self.health_results['checks_failed'] += 1
                self.health_results['success'] = False
                print(f"❌ {check_name}: {message}")
                if details:
                    print(f"   Details: {json.dumps(details, indent=2)}")
            
            return success
            
        except Exception as e:
            self.health_results['checks_failed'] += 1
            self.health_results['success'] = False
            error_result = {
                'check': check_name,
                'success': False,
                'message': f"Check crashed: {str(e)}",
                'details': {'exception': str(e)},
                'timestamp': datetime.now().isoformat()
            }
            self.health_results['results'].append(error_result)
            print(f"💥 {check_name}: Check crashed - {str(e)}")
            return False
    
    def check_basic_connectivity(self) -> Tuple[bool, str, Dict]:
        """Test basic connectivity to the application"""
        try:
            response = self.session.get(self.base_url, timeout=self.timeout)
            
            if response.status_code == 200:
                return True, f"Application responding (HTTP {response.status_code})", {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'content_length': len(response.content)
                }
            else:
                return False, f"HTTP {response.status_code}", {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
                
        except requests.exceptions.Timeout:
            return False, f"Connection timeout (>{self.timeout}s)", {'timeout': True}
        except requests.exceptions.ConnectionError:
            return False, "Connection refused", {'connection_error': True}
        except Exception as e:
            return False, f"Connection failed: {str(e)}", {'error': str(e)}
    
    def check_health_endpoint(self) -> Tuple[bool, str, Dict]:
        """Test the /api/health endpoint"""
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'healthy':
                    features = data.get('features', {})
                    return True, "Health endpoint reports healthy", {
                        'status': data.get('status'),
                        'features': features,
                        'response_time': response.elapsed.total_seconds()
                    }
                else:
                    return False, f"Unhealthy status: {data.get('status')}", data
            else:
                return False, f"Health endpoint HTTP {response.status_code}", {
                    'status_code': response.status_code,
                    'response': response.text[:200]
                }
                
        except Exception as e:
            return False, f"Health endpoint failed: {str(e)}", {'error': str(e)}
    
    def check_cors_headers(self) -> Tuple[bool, str, Dict]:
        """Test CORS headers are properly configured"""
        try:
            # Test preflight request
            headers = {
                'Origin': 'https://main.d3gelc4wjo7dl.amplifyapp.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = self.session.options(f"{self.api_url}/test-cors", headers=headers, timeout=self.timeout)
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }
            
            if response.status_code == 200 and cors_headers['Access-Control-Allow-Origin']:
                return True, "CORS headers properly configured", cors_headers
            else:
                return False, f"CORS configuration issue (HTTP {response.status_code})", cors_headers
                
        except Exception as e:
            return False, f"CORS check failed: {str(e)}", {'error': str(e)}
    
    def check_api_endpoints(self) -> Tuple[bool, str, Dict]:
        """Test all API endpoints for basic functionality"""
        endpoints = [
            ('GET', '/api/health', 'Health endpoint'),
            ('GET', '/api/test-cors', 'CORS test endpoint'),
            ('OPTIONS', '/api/test-cors', 'CORS preflight'),
            ('POST', '/api/send-otp', 'Send OTP endpoint', {'email': 'invalid'}),
            ('POST', '/api/verify-otp', 'Verify OTP endpoint', {}),
            ('POST', '/api/log-event', 'Log event endpoint', {'event': 'test'})
        ]
        
        results = {}
        total_endpoints = len(endpoints)
        working_endpoints = 0
        
        for endpoint_info in endpoints:
            method = endpoint_info[0]
            path = endpoint_info[1]
            description = endpoint_info[2]
            data = endpoint_info[3] if len(endpoint_info) > 3 else None
            
            try:
                url = f"{self.base_url}{path}"
                
                if method == 'GET':
                    response = self.session.get(url, timeout=self.timeout)
                elif method == 'OPTIONS':
                    response = self.session.options(url, timeout=self.timeout)
                elif method == 'POST':
                    response = self.session.post(url, json=data, timeout=self.timeout)
                else:
                    response = self.session.request(method, url, timeout=self.timeout)
                
                # Consider 2xx, 4xx as working (4xx means endpoint exists but validates input)
                if 200 <= response.status_code < 500:
                    results[description] = {
                        'status': 'WORKING',
                        'code': response.status_code,
                        'response_time': response.elapsed.total_seconds()
                    }
                    working_endpoints += 1
                else:
                    results[description] = {
                        'status': 'ERROR',
                        'code': response.status_code,
                        'response_time': response.elapsed.total_seconds()
                    }
                    
            except Exception as e:
                results[description] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
        
        success_rate = working_endpoints / total_endpoints
        
        if success_rate >= 0.8:  # 80% of endpoints working
            return True, f"API endpoints healthy ({working_endpoints}/{total_endpoints} working)", results
        else:
            return False, f"API endpoints issues ({working_endpoints}/{total_endpoints} working)", results
    
    def check_ml_features_availability(self) -> Tuple[bool, str, Dict]:
        """Check if ML/AI features are available"""
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', {})
                
                ml_features = {
                    'opencv_available': features.get('opencv_available', False),
                    'rembg_available': features.get('rembg_available', False),
                    'enhanced_processing': features.get('enhanced_processing', False),
                    'numpy_available': features.get('numpy_available', False)
                }
                
                available_count = sum(1 for v in ml_features.values() if v)
                total_features = len(ml_features)
                
                if available_count >= total_features * 0.5:  # At least 50% available
                    return True, f"ML/AI features available ({available_count}/{total_features})", ml_features
                else:
                    return False, f"Limited ML/AI features ({available_count}/{total_features})", ml_features
            else:
                return False, f"Cannot check ML features (HTTP {response.status_code})", {}
                
        except Exception as e:
            return False, f"ML features check failed: {str(e)}", {'error': str(e)}
    
    def check_database_connectivity(self) -> Tuple[bool, str, Dict]:
        """Test database connectivity through API"""
        try:
            # Try to send an OTP (which uses DynamoDB)
            response = self.session.post(
                f"{self.api_url}/send-otp",
                json={'email': 'test@example.com'},
                timeout=self.timeout
            )
            
            # We expect either success or a specific error (not a 500 server error)
            if response.status_code in [200, 400, 429]:
                return True, "Database connectivity working", {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
            elif response.status_code == 500:
                return False, "Database connectivity issues (HTTP 500)", {
                    'status_code': response.status_code,
                    'response': response.text[:200]
                }
            else:
                return True, f"Database accessible (HTTP {response.status_code})", {
                    'status_code': response.status_code
                }
                
        except Exception as e:
            return False, f"Database check failed: {str(e)}", {'error': str(e)}
    
    def check_response_times(self) -> Tuple[bool, str, Dict]:
        """Check API response times"""
        endpoints = [
            f"{self.base_url}/",
            f"{self.api_url}/health",
            f"{self.api_url}/test-cors"
        ]
        
        response_times = {}
        total_time = 0
        successful_requests = 0
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = self.session.get(endpoint, timeout=self.timeout)
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times[endpoint] = {
                    'response_time': response_time,
                    'status_code': response.status_code
                }
                
                if response.status_code == 200:
                    total_time += response_time
                    successful_requests += 1
                    
            except Exception as e:
                response_times[endpoint] = {
                    'error': str(e)
                }
        
        if successful_requests > 0:
            avg_response_time = total_time / successful_requests
            
            if avg_response_time < 2.0:  # Under 2 seconds average
                return True, f"Response times good (avg: {avg_response_time:.2f}s)", response_times
            elif avg_response_time < 5.0:  # Under 5 seconds
                return True, f"Response times acceptable (avg: {avg_response_time:.2f}s)", response_times
            else:
                return False, f"Response times slow (avg: {avg_response_time:.2f}s)", response_times
        else:
            return False, "No successful requests for response time measurement", response_times
    
    def check_error_handling(self) -> Tuple[bool, str, Dict]:
        """Test error handling by sending invalid requests"""
        error_tests = [
            ('POST', '/api/send-otp', {'email': 'invalid-email'}, 'Invalid email format'),
            ('POST', '/api/verify-otp', {}, 'Missing required fields'),
            ('POST', '/api/full-workflow', {}, 'Missing image file'),
            ('GET', '/api/nonexistent', {}, 'Non-existent endpoint')
        ]
        
        results = {}
        proper_errors = 0
        
        for method, path, data, test_name in error_tests:
            try:
                url = f"{self.base_url}{path}"
                
                if method == 'POST':
                    response = self.session.post(url, json=data, timeout=self.timeout)
                else:
                    response = self.session.get(url, timeout=self.timeout)
                
                # Proper error handling should return 4xx status codes
                if 400 <= response.status_code < 500:
                    results[test_name] = {
                        'status': 'PROPER_ERROR',
                        'code': response.status_code
                    }
                    proper_errors += 1
                elif response.status_code == 500:
                    results[test_name] = {
                        'status': 'SERVER_ERROR',
                        'code': response.status_code
                    }
                else:
                    results[test_name] = {
                        'status': 'UNEXPECTED',
                        'code': response.status_code
                    }
                    
            except Exception as e:
                results[test_name] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
        
        total_tests = len(error_tests)
        if proper_errors >= total_tests * 0.75:  # 75% proper error handling
            return True, f"Error handling working ({proper_errors}/{total_tests} proper)", results
        else:
            return False, f"Error handling issues ({proper_errors}/{total_tests} proper)", results
    
    def run_all_checks(self) -> bool:
        """Run all health checks"""
        print("🏥 Starting comprehensive health checks...")
        print(f"🌐 Target URL: {self.base_url}")
        print("="*60)
        
        # Define all health checks
        checks = [
            ("Basic Connectivity", self.check_basic_connectivity),
            ("Health Endpoint", self.check_health_endpoint),
            ("CORS Headers", self.check_cors_headers),
            ("API Endpoints", self.check_api_endpoints),
            ("ML/AI Features", self.check_ml_features_availability),
            ("Database Connectivity", self.check_database_connectivity),
            ("Response Times", self.check_response_times),
            ("Error Handling", self.check_error_handling)
        ]
        
        # Run checks sequentially
        for check_name, check_func in checks:
            self.run_check(check_name, check_func)
            time.sleep(0.5)  # Brief pause between checks
        
        # Determine overall health
        if self.health_results['checks_passed'] == self.health_results['checks_run']:
            self.health_results['overall_health'] = 'excellent'
        elif self.health_results['checks_passed'] >= self.health_results['checks_run'] * 0.8:
            self.health_results['overall_health'] = 'good'
        elif self.health_results['checks_passed'] >= self.health_results['checks_run'] * 0.6:
            self.health_results['overall_health'] = 'fair'
        else:
            self.health_results['overall_health'] = 'poor'
        
        return self.health_results['success']
    
    def print_results(self):
        """Print health check results"""
        print("\n" + "="*60)
        print("HEALTH CHECK RESULTS")
        print("="*60)
        
        overall_health = self.health_results['overall_health']
        health_emoji = {
            'excellent': '🟢',
            'good': '🟡',
            'fair': '🟠',
            'poor': '🔴'
        }.get(overall_health, '⚪')
        
        print(f"{health_emoji} Overall Health: {overall_health.upper()}")
        print(f"📊 Checks Run: {self.health_results['checks_run']}")
        print(f"✅ Passed: {self.health_results['checks_passed']}")
        print(f"❌ Failed: {self.health_results['checks_failed']}")
        print(f"📈 Success Rate: {(self.health_results['checks_passed']/self.health_results['checks_run']*100):.1f}%")
        
        if self.health_results['checks_failed'] > 0:
            print("\n❌ Failed Checks:")
            for result in self.health_results['results']:
                if not result['success']:
                    print(f"  • {result['check']}: {result['message']}")
    
    def save_results(self, output_file: str = 'health-check-results.json'):
        """Save health check results to JSON file"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        with open(output_path, 'w') as f:
            json.dump(self.health_results, f, indent=2)
        print(f"Results saved to: {output_path}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python run_health_checks.py <base_url>")
        print("Example: python run_health_checks.py http://passport-photo-ai-enhanced.us-east-1.elasticbeanstalk.com")
        sys.exit(1)
    
    base_url = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    checker = HealthChecker(base_url, timeout)
    
    try:
        success = checker.run_all_checks()
        checker.print_results()
        checker.save_results()
        
        if not success:
            print("\n❌ Health checks failed!")
            sys.exit(1)
        else:
            print("\n✅ All health checks passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()