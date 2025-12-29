#!/usr/bin/env python3
"""
Performance Testing Script
Tests API response times and performance thresholds
"""

import os
import sys
import json
import time
import requests
import statistics
import concurrent.futures
from typing import Dict, List, Tuple
from datetime import datetime

class PerformanceTester:
    """Tests application performance and response times"""
    
    def __init__(self, base_url: str, max_response_time: float = 5.0):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.max_response_time = max_response_time
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CI-CD-Pipeline-Performance-Tester/1.0',
            'Origin': 'https://main.d3gelc4wjo7dl.amplifyapp.com'
        })
        
        self.test_results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'base_url': base_url,
            'max_response_time': max_response_time,
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'performance_metrics': {},
            'results': []
        }
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single performance test"""
        self.test_results['tests_run'] += 1
        
        try:
            print(f"⚡ Running {test_name}...")
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
    
    def test_endpoint_response_time(self, endpoint: str, method: str = 'GET', 
                                  data: Dict = None, iterations: int = 5) -> Tuple[bool, str, Dict]:
        """Test response time for a specific endpoint"""
        response_times = []
        successful_requests = 0
        
        for i in range(iterations):
            try:
                start_time = time.time()
                
                if method == 'GET':
                    response = self.session.get(endpoint, timeout=30)
                elif method == 'POST':
                    response = self.session.post(endpoint, json=data, timeout=30)
                else:
                    response = self.session.request(method, endpoint, timeout=30)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status_code < 500:  # Accept 2xx, 3xx, 4xx as successful
                    response_times.append(response_time)
                    successful_requests += 1
                
                time.sleep(0.1)  # Brief pause between requests
                
            except Exception as e:
                print(f"   Request {i+1} failed: {str(e)}")
        
        if not response_times:
            return False, f"No successful requests to {endpoint}", {}
        
        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        details = {
            'avg_response_time': avg_time,
            'min_response_time': min_time,
            'max_response_time': max_time,
            'successful_requests': successful_requests,
            'total_requests': iterations,
            'success_rate': successful_requests / iterations
        }
        
        if avg_time <= self.max_response_time:
            return True, f"Response time good (avg: {avg_time:.2f}s)", details
        else:
            return False, f"Response time slow (avg: {avg_time:.2f}s > {self.max_response_time}s)", details
    
    def test_concurrent_requests(self, endpoint: str, concurrent_users: int = 5) -> Tuple[bool, str, Dict]:
        """Test concurrent request handling"""
        def make_request():
            try:
                start_time = time.time()
                response = self.session.get(endpoint, timeout=30)
                end_time = time.time()
                return {
                    'success': response.status_code < 500,
                    'response_time': end_time - start_time,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'response_time': 30.0  # Timeout
                }
        
        print(f"   Testing with {concurrent_users} concurrent users...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrent_users)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        successful_requests = sum(1 for r in results if r['success'])
        response_times = [r['response_time'] for r in results if r['success']]
        
        if response_times:
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
        else:
            avg_time = 0
            max_time = 0
        
        details = {
            'concurrent_users': concurrent_users,
            'successful_requests': successful_requests,
            'total_requests': len(results),
            'success_rate': successful_requests / len(results),
            'avg_response_time': avg_time,
            'max_response_time': max_time
        }
        
        success_rate = successful_requests / len(results)
        
        if success_rate >= 0.8 and avg_time <= self.max_response_time * 2:  # Allow 2x time for concurrent
            return True, f"Concurrent handling good ({successful_requests}/{len(results)} success, avg: {avg_time:.2f}s)", details
        else:
            return False, f"Concurrent handling issues ({successful_requests}/{len(results)} success, avg: {avg_time:.2f}s)", details
    
    def test_api_endpoints_performance(self) -> Tuple[bool, str, Dict]:
        """Test performance of all API endpoints"""
        endpoints = [
            (f"{self.base_url}/", 'GET', None, 'Root endpoint'),
            (f"{self.api_url}/health", 'GET', None, 'Health endpoint'),
            (f"{self.api_url}/test-cors", 'GET', None, 'CORS test endpoint'),
            (f"{self.api_url}/send-otp", 'POST', {'email': 'invalid'}, 'Send OTP endpoint'),
            (f"{self.api_url}/verify-otp", 'POST', {}, 'Verify OTP endpoint')
        ]
        
        endpoint_results = {}
        all_passed = True
        
        for endpoint, method, data, description in endpoints:
            success, message, details = self.test_endpoint_response_time(endpoint, method, data, 3)
            endpoint_results[description] = {
                'success': success,
                'message': message,
                'details': details
            }
            
            if not success:
                all_passed = False
        
        if all_passed:
            return True, "All API endpoints meet performance requirements", endpoint_results
        else:
            return False, "Some API endpoints have performance issues", endpoint_results
    
    def test_memory_usage_indicators(self) -> Tuple[bool, str, Dict]:
        """Test for memory usage indicators through response patterns"""
        try:
            # Make multiple requests to see if response times degrade (memory leak indicator)
            response_times = []
            
            for i in range(10):
                start_time = time.time()
                response = self.session.get(f"{self.api_url}/health", timeout=30)
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
                
                time.sleep(0.5)
            
            if len(response_times) < 5:
                return False, "Insufficient successful requests for memory analysis", {}
            
            # Check if response times are increasing (potential memory leak)
            first_half = response_times[:len(response_times)//2]
            second_half = response_times[len(response_times)//2:]
            
            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            
            degradation = (second_avg - first_avg) / first_avg if first_avg > 0 else 0
            
            details = {
                'first_half_avg': first_avg,
                'second_half_avg': second_avg,
                'degradation_percent': degradation * 100,
                'total_requests': len(response_times)
            }
            
            if degradation < 0.5:  # Less than 50% degradation
                return True, f"Memory usage stable (degradation: {degradation*100:.1f}%)", details
            else:
                return False, f"Potential memory issues (degradation: {degradation*100:.1f}%)", details
                
        except Exception as e:
            return False, f"Memory usage test failed: {str(e)}", {'error': str(e)}
    
    def test_error_rate_under_load(self) -> Tuple[bool, str, Dict]:
        """Test error rate under moderate load"""
        try:
            total_requests = 20
            error_count = 0
            response_times = []
            
            for i in range(total_requests):
                try:
                    start_time = time.time()
                    response = self.session.get(f"{self.api_url}/health", timeout=30)
                    end_time = time.time()
                    
                    response_times.append(end_time - start_time)
                    
                    if response.status_code >= 500:
                        error_count += 1
                        
                except Exception:
                    error_count += 1
                
                time.sleep(0.1)  # Brief pause
            
            error_rate = error_count / total_requests
            avg_response_time = statistics.mean(response_times) if response_times else 0
            
            details = {
                'total_requests': total_requests,
                'error_count': error_count,
                'error_rate': error_rate,
                'avg_response_time': avg_response_time
            }
            
            if error_rate <= 0.05:  # Less than 5% error rate
                return True, f"Error rate acceptable ({error_rate*100:.1f}%)", details
            else:
                return False, f"High error rate ({error_rate*100:.1f}%)", details
                
        except Exception as e:
            return False, f"Error rate test failed: {str(e)}", {'error': str(e)}
    
    def run_all_tests(self) -> bool:
        """Run all performance tests"""
        print("⚡ Starting performance testing...")
        print(f"🌐 Target URL: {self.base_url}")
        print(f"⏱️  Max Response Time: {self.max_response_time}s")
        print("="*60)
        
        # Run performance tests
        tests = [
            ("API Endpoints Performance", self.test_api_endpoints_performance),
            ("Concurrent Request Handling", lambda: self.test_concurrent_requests(f"{self.api_url}/health", 5)),
            ("Memory Usage Indicators", self.test_memory_usage_indicators),
            ("Error Rate Under Load", self.test_error_rate_under_load)
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
            time.sleep(1)  # Pause between tests
        
        return self.test_results['success']
    
    def print_results(self):
        """Print performance test results"""
        print("\n" + "="*60)
        print("PERFORMANCE TEST RESULTS")
        print("="*60)
        
        if self.test_results['success']:
            print("✅ Overall Status: PASSED")
        else:
            print("❌ Overall Status: FAILED")
        
        print(f"📊 Tests Run: {self.test_results['tests_run']}")
        print(f"✅ Passed: {self.test_results['tests_passed']}")
        print(f"❌ Failed: {self.test_results['tests_failed']}")
        print(f"⏱️  Max Response Time: {self.test_results['max_response_time']}s")
        
        if self.test_results['tests_failed'] > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results['results']:
                if not result['success']:
                    print(f"  • {result['test']}: {result['message']}")
    
    def save_results(self, output_file: str = 'performance-test-results.json'):
        """Save test results to JSON file"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        with open(output_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"Results saved to: {output_path}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python test_performance.py <base_url> [max_response_time]")
        print("Example: python test_performance.py http://passport-photo-ai-enhanced.us-east-1.elasticbeanstalk.com 5.0")
        sys.exit(1)
    
    base_url = sys.argv[1]
    max_response_time = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    
    tester = PerformanceTester(base_url, max_response_time)
    
    try:
        success = tester.run_all_tests()
        tester.print_results()
        tester.save_results()
        
        if not success:
            print("\n❌ Performance tests failed!")
            sys.exit(1)
        else:
            print("\n✅ All performance tests passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Performance test error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()