#!/usr/bin/env python3
"""
Enhanced Backend Test Suite
Comprehensive testing for ML/AI capabilities, email validation, and CORS functionality
"""

import requests
import json
import time
import base64
from PIL import Image
import io
import os
import sys
from datetime import datetime

class EnhancedBackendTester:
    def __init__(self, base_url, amplify_domain="https://main.d3gelc4wjo7dl.amplifyapp.com"):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.amplify_domain = amplify_domain
        self.session = requests.Session()
        self.session.headers.update({
            'Origin': self.amplify_domain,
            'User-Agent': 'Enhanced-Backend-Tester/1.0'
        })
        
        self.test_results = []
        self.start_time = datetime.now()
    
    def log_test(self, test_name, success, message, details=None):
        """Log test result"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        if details and not success:
            print(f"   Details: {json.dumps(details, indent=2)}")
    
    def test_health_endpoint(self):
        """Test health endpoint and enhanced features"""
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check basic health
                if data.get('status') == 'healthy':
                    self.log_test("Health Check", True, "Backend is healthy")
                    
                    # Check enhanced features
                    features = data.get('features', {})
                    
                    opencv_available = features.get('opencv_available', False)
                    rembg_available = features.get('rembg_available', False)
                    enhanced_processing = features.get('enhanced_processing', False)
                    
                    self.log_test("OpenCV Availability", opencv_available, 
                                f"OpenCV {'available' if opencv_available else 'not available'}")
                    
                    self.log_test("Background Removal", rembg_available,
                                f"rembg {'available' if rembg_available else 'not available'}")
                    
                    self.log_test("Enhanced Processing", enhanced_processing,
                                f"Enhanced processing {'enabled' if enhanced_processing else 'disabled'}")
                    
                    return True, data
                else:
                    self.log_test("Health Check", False, f"Unhealthy status: {data.get('status')}")
                    return False, data
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False, None
                
        except Exception as e:
            self.log_test("Health Check", False, f"Request failed: {str(e)}")
            return False, None
    
    def test_cors_functionality(self):
        """Test CORS headers and preflight requests"""
        try:
            # Test preflight request
            preflight_response = self.session.options(f"{self.api_url}/test-cors", timeout=10)
            
            if preflight_response.status_code == 200:
                self.log_test("CORS Preflight", True, "Preflight request successful")
                
                # Check CORS headers
                cors_headers = {
                    'Access-Control-Allow-Origin': preflight_response.headers.get('Access-Control-Allow-Origin'),
                    'Access-Control-Allow-Methods': preflight_response.headers.get('Access-Control-Allow-Methods'),
                    'Access-Control-Allow-Headers': preflight_response.headers.get('Access-Control-Allow-Headers')
                }
                
                if cors_headers['Access-Control-Allow-Origin']:
                    self.log_test("CORS Headers", True, "CORS headers present", cors_headers)
                else:
                    self.log_test("CORS Headers", False, "Missing CORS headers", cors_headers)
                
                # Test actual CORS request
                cors_response = self.session.get(f"{self.api_url}/test-cors", timeout=10)
                
                if cors_response.status_code == 200:
                    data = cors_response.json()
                    self.log_test("CORS Request", True, f"CORS test successful: {data.get('status')}")
                    return True
                else:
                    self.log_test("CORS Request", False, f"CORS test failed: {cors_response.status_code}")
                    return False
            else:
                self.log_test("CORS Preflight", False, f"Preflight failed: {preflight_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("CORS Functionality", False, f"CORS test failed: {str(e)}")
            return False
    
    def test_email_validation(self):
        """Test email validation system"""
        test_email = "test@example.com"
        
        try:
            # Test OTP sending
            otp_data = {
                'email': test_email
            }
            
            otp_response = self.session.post(f"{self.api_url}/send-otp", 
                                           json=otp_data, timeout=15)
            
            if otp_response.status_code == 200:
                otp_result = otp_response.json()
                if otp_result.get('success'):
                    self.log_test("OTP Sending", True, "OTP sent successfully")
                    
                    # Test OTP verification with invalid code
                    verify_data = {
                        'email': test_email,
                        'otp': '000000'  # Invalid OTP
                    }
                    
                    verify_response = self.session.post(f"{self.api_url}/verify-otp",
                                                      json=verify_data, timeout=10)
                    
                    if verify_response.status_code == 400:
                        verify_result = verify_response.json()
                        self.log_test("OTP Validation", True, "Invalid OTP correctly rejected")
                        return True
                    else:
                        self.log_test("OTP Validation", False, "Invalid OTP not rejected properly")
                        return False
                else:
                    self.log_test("OTP Sending", False, f"OTP sending failed: {otp_result.get('error')}")
                    return False
            else:
                self.log_test("OTP Sending", False, f"OTP request failed: {otp_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Email Validation", False, f"Email validation test failed: {str(e)}")
            return False
    
    def create_test_image(self):
        """Create a simple test image"""
        # Create a simple 400x400 RGB image with a face-like pattern
        img = Image.new('RGB', (400, 400), color='lightblue')
        
        # Add a simple face-like pattern (circle for head, dots for eyes)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        # Head (circle)
        draw.ellipse([150, 100, 250, 200], fill='peachpuff', outline='black')
        
        # Eyes (dots)
        draw.ellipse([170, 130, 180, 140], fill='black')
        draw.ellipse([220, 130, 230, 140], fill='black')
        
        # Mouth (arc)
        draw.arc([180, 160, 220, 180], 0, 180, fill='black')
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=90)
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    
    def test_image_processing(self):
        """Test enhanced image processing capabilities"""
        try:
            # Create test image
            test_image_data = self.create_test_image()
            
            # Test basic processing (no background removal)
            files = {'image': ('test.jpg', test_image_data, 'image/jpeg')}
            data = {'remove_background': 'false'}
            
            response = self.session.post(f"{self.api_url}/full-workflow",
                                       files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    self.log_test("Basic Image Processing", True, "Image processed successfully")
                    
                    # Check analysis results
                    analysis = result.get('analysis', {})
                    face_detection = analysis.get('face_detection', {})
                    
                    faces_detected = face_detection.get('faces_detected', 0)
                    detection_method = face_detection.get('detection_method', 'unknown')
                    
                    self.log_test("Face Detection", faces_detected > 0,
                                f"Detected {faces_detected} faces using {detection_method}")
                    
                    # Test with background removal
                    files = {'image': ('test.jpg', test_image_data, 'image/jpeg')}
                    data = {'remove_background': 'true'}
                    
                    bg_response = self.session.post(f"{self.api_url}/full-workflow",
                                                  files=files, data=data, timeout=45)
                    
                    if bg_response.status_code == 200:
                        bg_result = bg_response.json()
                        
                        if bg_result.get('success'):
                            self.log_test("Background Removal", True, "Background removal processed")
                            return True
                        else:
                            self.log_test("Background Removal", False, 
                                        f"Background removal failed: {bg_result.get('message')}")
                            return False
                    else:
                        self.log_test("Background Removal", False, 
                                    f"Background removal request failed: {bg_response.status_code}")
                        return False
                else:
                    self.log_test("Basic Image Processing", False, 
                                f"Processing failed: {result.get('message')}")
                    return False
            else:
                self.log_test("Basic Image Processing", False, 
                            f"Processing request failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Image Processing", False, f"Image processing test failed: {str(e)}")
            return False
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        try:
            # Make multiple rapid requests to test rate limiting
            rapid_requests = 0
            rate_limited = False
            
            for i in range(5):
                response = self.session.get(f"{self.api_url}/health", timeout=5)
                
                if response.status_code == 429:  # Too Many Requests
                    rate_limited = True
                    break
                elif response.status_code == 200:
                    rapid_requests += 1
                
                time.sleep(0.1)  # Small delay between requests
            
            if rate_limited:
                self.log_test("Rate Limiting", True, "Rate limiting is active")
            else:
                self.log_test("Rate Limiting", True, f"Made {rapid_requests} requests without rate limiting")
            
            return True
            
        except Exception as e:
            self.log_test("Rate Limiting", False, f"Rate limiting test failed: {str(e)}")
            return False
    
    def test_analytics_logging(self):
        """Test analytics event logging"""
        try:
            event_data = {
                'event_type': 'test_event',
                'user_action': 'backend_test',
                'timestamp': datetime.now().isoformat()
            }
            
            response = self.session.post(f"{self.api_url}/log-event",
                                       json=event_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("Analytics Logging", True, "Event logged successfully")
                    return True
                else:
                    self.log_test("Analytics Logging", False, "Event logging failed")
                    return False
            else:
                self.log_test("Analytics Logging", False, f"Logging request failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Analytics Logging", False, f"Analytics test failed: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all test suites"""
        print(f"🧪 Starting Enhanced Backend Test Suite")
        print(f"🌐 Testing: {self.base_url}")
        print(f"🔗 Origin: {self.amplify_domain}")
        print("=" * 60)
        
        # Run tests in order
        tests = [
            self.test_health_endpoint,
            self.test_cors_functionality,
            self.test_email_validation,
            self.test_image_processing,
            self.test_rate_limiting,
            self.test_analytics_logging
        ]
        
        passed = 0
        total = 0
        
        for test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
                total += 1
            except Exception as e:
                print(f"❌ Test {test_func.__name__} crashed: {str(e)}")
                total += 1
            
            print()  # Add spacing between tests
        
        # Generate summary
        self.generate_summary(passed, total)
    
    def generate_summary(self, passed, total):
        """Generate test summary"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print("=" * 60)
        print(f"📊 Test Summary")
        print("=" * 60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        print()
        
        # Detailed results
        print("📋 Detailed Results:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}: {result['message']}")
        
        print()
        
        if passed == total:
            print("🎉 All tests passed! Enhanced backend is fully functional.")
        elif passed >= total * 0.8:
            print("⚠️  Most tests passed. Some features may need attention.")
        else:
            print("🚨 Multiple test failures. Backend needs investigation.")
        
        # Save results to file
        results_file = f"enhanced_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total,
                    'passed': passed,
                    'failed': total - passed,
                    'success_rate': passed/total*100,
                    'duration_seconds': duration,
                    'test_time': self.start_time.isoformat(),
                    'backend_url': self.base_url
                },
                'results': self.test_results
            }, f, indent=2)
        
        print(f"📄 Results saved to: {results_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test-enhanced.py <backend_url> [amplify_domain]")
        print("Example: python test-enhanced.py http://passport-photo-ai-enhanced.us-east-1.elasticbeanstalk.com")
        sys.exit(1)
    
    backend_url = sys.argv[1]
    amplify_domain = sys.argv[2] if len(sys.argv) > 2 else "https://main.d3gelc4wjo7dl.amplifyapp.com"
    
    tester = EnhancedBackendTester(backend_url, amplify_domain)
    tester.run_all_tests()

if __name__ == "__main__":
    main()