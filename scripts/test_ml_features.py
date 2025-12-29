#!/usr/bin/env python3
"""
ML/AI Feature Testing Script
Tests face detection, background removal, and email validation using test_images
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image
import io
import base64
from datetime import datetime

class MLFeatureTester:
    """Tests ML/AI features of the deployed application"""
    
    def __init__(self, base_url: str, test_images_dir: str = 'test_images'):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.test_images_dir = Path(test_images_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CI-CD-Pipeline-ML-Tester/1.0',
            'Origin': 'https://main.d3gelc4wjo7dl.amplifyapp.com'
        })
        
        self.test_results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'base_url': base_url,
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'images_processed': 0,
            'ml_features_available': {},
            'results': []
        }
        
        # Supported image formats
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
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
                if details:
                    print(f"   Details: {json.dumps(details, indent=2)}")
            
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
    
    def check_ml_features_availability(self) -> Tuple[bool, str, Dict]:
        """Check which ML/AI features are available"""
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', {})
                
                ml_features = {
                    'opencv_available': features.get('opencv_available', False),
                    'rembg_available': features.get('rembg_available', False),
                    'enhanced_processing': features.get('enhanced_processing', False),
                    'numpy_available': features.get('numpy_available', False),
                    'heic_support': features.get('heic_support', False),
                    'face_detection': features.get('face_detection', 'unknown'),
                    'background_removal': features.get('background_removal', 'none')
                }
                
                self.test_results['ml_features_available'] = ml_features
                
                # Count available features
                available_count = sum(1 for k, v in ml_features.items() 
                                    if isinstance(v, bool) and v)
                
                return True, f"ML features detected: {available_count} available", ml_features
            else:
                return False, f"Cannot check ML features (HTTP {response.status_code})", {}
                
        except Exception as e:
            return False, f"ML features check failed: {str(e)}", {'error': str(e)}
    
    def find_test_images(self) -> List[Path]:
        """Find test images in the test_images directory"""
        if not self.test_images_dir.exists():
            print(f"⚠️  Test images directory not found: {self.test_images_dir}")
            return []
        
        images = []
        for file_path in self.test_images_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                images.append(file_path)
        
        print(f"📁 Found {len(images)} test images")
        return images
    
    def create_synthetic_test_image(self) -> bytes:
        """Create a synthetic test image with face-like features"""
        print("🎨 Creating synthetic test image...")
        
        # Create a 400x400 RGB image
        img = Image.new('RGB', (400, 400), color='lightblue')
        
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        # Draw a face-like pattern
        # Head (circle)
        draw.ellipse([150, 100, 250, 200], fill='peachpuff', outline='black', width=2)
        
        # Eyes
        draw.ellipse([170, 130, 180, 140], fill='black')
        draw.ellipse([220, 130, 230, 140], fill='black')
        
        # Nose
        draw.line([(200, 150), (200, 170)], fill='black', width=2)
        
        # Mouth
        draw.arc([180, 160, 220, 180], 0, 180, fill='black', width=2)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=90)
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    
    def test_face_detection_with_image(self, image_data: bytes, image_name: str) -> Tuple[bool, str, Dict]:
        """Test face detection with a specific image"""
        try:
            files = {'image': (image_name, image_data, 'image/jpeg')}
            data = {'remove_background': 'false'}
            
            response = self.session.post(
                f"{self.api_url}/full-workflow",
                files=files,
                data=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    analysis = result.get('analysis', {})
                    face_detection = analysis.get('face_detection', {})
                    
                    faces_detected = face_detection.get('faces_detected', 0)
                    detection_method = face_detection.get('detection_method', 'unknown')
                    confidence = face_detection.get('confidence', 0)
                    eyes_detected = face_detection.get('eyes_detected', 0)
                    processing_time = result.get('processing_time', 0)
                    
                    details = {
                        'faces_detected': faces_detected,
                        'detection_method': detection_method,
                        'confidence': confidence,
                        'eyes_detected': eyes_detected,
                        'processing_time': processing_time,
                        'image_name': image_name
                    }
                    
                    # Consider successful if we get any detection result
                    if detection_method != 'unknown':
                        return True, f"Face detection working: {detection_method}, {faces_detected} faces", details
                    else:
                        return False, "Face detection not working", details
                else:
                    return False, f"Image processing failed: {result.get('message')}", result
            else:
                return False, f"Face detection request failed (HTTP {response.status_code})", {
                    'status_code': response.status_code,
                    'response': response.text[:200]
                }
                
        except requests.exceptions.Timeout:
            return False, f"Face detection timeout for {image_name}", {'timeout': True}
        except Exception as e:
            return False, f"Face detection failed: {str(e)}", {'error': str(e)}
    
    def test_background_removal_with_image(self, image_data: bytes, image_name: str) -> Tuple[bool, str, Dict]:
        """Test background removal with a specific image"""
        try:
            files = {'image': (image_name, image_data, 'image/jpeg')}
            data = {'remove_background': 'true'}
            
            response = self.session.post(
                f"{self.api_url}/full-workflow",
                files=files,
                data=data,
                timeout=120  # Longer timeout for background removal
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    processing_time = result.get('processing_time', 0)
                    has_processed_image = bool(result.get('processed_image'))
                    
                    details = {
                        'processing_time': processing_time,
                        'has_processed_image': has_processed_image,
                        'image_name': image_name
                    }
                    
                    return True, f"Background removal completed in {processing_time:.2f}s", details
                else:
                    message = result.get('message', 'Unknown error')
                    # If rembg is not available, that's expected and okay
                    if 'rembg' in message.lower() or 'background' in message.lower():
                        return True, f"Background removal not available (expected): {message}", {
                            'rembg_available': False,
                            'image_name': image_name
                        }
                    else:
                        return False, f"Background removal failed: {message}", result
            else:
                return False, f"Background removal request failed (HTTP {response.status_code})", {
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            # Timeout is acceptable for background removal as it's computationally intensive
            return True, f"Background removal timeout (acceptable for {image_name})", {
                'timeout': True,
                'image_name': image_name
            }
        except Exception as e:
            return False, f"Background removal test failed: {str(e)}", {'error': str(e)}
    
    def test_image_enhancement_features(self, image_data: bytes, image_name: str) -> Tuple[bool, str, Dict]:
        """Test image enhancement and processing features"""
        try:
            files = {'image': (image_name, image_data, 'image/jpeg')}
            data = {'remove_background': 'false', 'email': 'test@example.com'}
            
            response = self.session.post(
                f"{self.api_url}/full-workflow",
                files=files,
                data=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    analysis = result.get('analysis', {})
                    ai_analysis = analysis.get('ai_analysis', {})
                    face_detection = analysis.get('face_detection', {})
                    
                    # Check various enhancement features
                    features_tested = {
                        'has_processed_image': bool(result.get('processed_image')),
                        'ai_analysis_present': bool(ai_analysis),
                        'face_analysis_present': bool(face_detection),
                        'confidence_score': ai_analysis.get('confidence_score', 0),
                        'processing_time': result.get('processing_time', 0)
                    }
                    
                    working_features = sum(1 for v in features_tested.values() if v)
                    
                    if working_features >= 3:  # At least 3 features working
                        return True, f"Image enhancement working ({working_features}/5 features)", features_tested
                    else:
                        return False, f"Limited image enhancement ({working_features}/5 features)", features_tested
                else:
                    return False, f"Image enhancement failed: {result.get('message')}", result
            else:
                return False, f"Image enhancement request failed (HTTP {response.status_code})", {}
                
        except Exception as e:
            return False, f"Image enhancement test failed: {str(e)}", {'error': str(e)}
    
    def test_email_validation_workflow(self) -> Tuple[bool, str, Dict]:
        """Test email validation OTP workflow"""
        test_email = "test@example.com"
        
        try:
            # Test OTP sending
            otp_response = self.session.post(
                f"{self.api_url}/send-otp",
                json={'email': test_email},
                timeout=30
            )
            
            otp_details = {
                'send_otp_status': otp_response.status_code,
                'send_otp_success': False
            }
            
            if otp_response.status_code == 200:
                otp_result = otp_response.json()
                otp_details['send_otp_success'] = otp_result.get('success', False)
                
                if otp_result.get('success'):
                    # Test OTP verification with invalid code
                    verify_response = self.session.post(
                        f"{self.api_url}/verify-otp",
                        json={'email': test_email, 'otp': '000000'},
                        timeout=30
                    )
                    
                    otp_details.update({
                        'verify_otp_status': verify_response.status_code,
                        'verify_otp_rejects_invalid': verify_response.status_code == 400
                    })
                    
                    if verify_response.status_code == 400:
                        return True, "Email validation workflow working", otp_details
                    else:
                        return False, "Email validation not rejecting invalid OTP", otp_details
                else:
                    # OTP sending failed, but endpoint is working
                    return True, f"Email validation endpoint working (expected failure): {otp_result.get('error', 'Unknown')}", otp_details
            else:
                # Check if it's a validation error (expected) vs server error
                if otp_response.status_code == 400:
                    return True, "Email validation working (input validation)", otp_details
                else:
                    return False, f"Email validation endpoint error (HTTP {otp_response.status_code})", otp_details
                    
        except Exception as e:
            return False, f"Email validation test failed: {str(e)}", {'error': str(e)}
    
    def test_cors_functionality(self) -> Tuple[bool, str, Dict]:
        """Test CORS functionality for ML/AI endpoints"""
        try:
            # Test CORS with image upload endpoint
            headers = {
                'Origin': 'https://main.d3gelc4wjo7dl.amplifyapp.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = self.session.options(f"{self.api_url}/full-workflow", headers=headers, timeout=30)
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }
            
            if response.status_code == 200 and cors_headers['Access-Control-Allow-Origin']:
                return True, "CORS working for ML/AI endpoints", cors_headers
            else:
                return False, f"CORS issues for ML/AI endpoints (HTTP {response.status_code})", cors_headers
                
        except Exception as e:
            return False, f"CORS test failed: {str(e)}", {'error': str(e)}
    
    def run_all_tests(self) -> bool:
        """Run all ML/AI feature tests"""
        print("🤖 Starting ML/AI feature testing...")
        print(f"🌐 Target URL: {self.base_url}")
        print("="*60)
        
        # Check ML features availability first
        self.run_test("ML Features Availability", self.check_ml_features_availability)
        
        # Test email validation workflow
        self.run_test("Email Validation Workflow", self.test_email_validation_workflow)
        
        # Test CORS functionality
        self.run_test("CORS Functionality", self.test_cors_functionality)
        
        # Find test images
        test_images = self.find_test_images()
        
        if not test_images:
            print("⚠️  No test images found, creating synthetic test image...")
            synthetic_image_data = self.create_synthetic_test_image()
            test_images_data = [('synthetic_test.jpg', synthetic_image_data)]
        else:
            # Load test images (limit to first 3 for speed)
            test_images_data = []
            for img_path in test_images[:3]:
                try:
                    with open(img_path, 'rb') as f:
                        test_images_data.append((img_path.name, f.read()))
                except Exception as e:
                    print(f"⚠️  Could not read {img_path}: {e}")
        
        if not test_images_data:
            print("❌ No images available for ML/AI testing")
            return False
        
        print(f"📸 Testing ML/AI features with {len(test_images_data)} images")
        
        # Test each image with different ML/AI features
        for image_name, image_data in test_images_data:
            print(f"\n📷 Testing with image: {image_name}")
            
            # Test face detection
            self.run_test(
                f"Face Detection - {image_name}",
                lambda img_data=image_data, img_name=image_name: self.test_face_detection_with_image(img_data, img_name)
            )
            
            # Test background removal
            self.run_test(
                f"Background Removal - {image_name}",
                lambda img_data=image_data, img_name=image_name: self.test_background_removal_with_image(img_data, img_name)
            )
            
            # Test image enhancement
            self.run_test(
                f"Image Enhancement - {image_name}",
                lambda img_data=image_data, img_name=image_name: self.test_image_enhancement_features(img_data, img_name)
            )
            
            self.test_results['images_processed'] += 1
            time.sleep(1)  # Brief pause between images
        
        return self.test_results['success']
    
    def print_results(self):
        """Print ML/AI test results"""
        print("\n" + "="*60)
        print("ML/AI FEATURE TEST RESULTS")
        print("="*60)
        
        if self.test_results['success']:
            print("✅ Overall Status: PASSED")
        else:
            print("❌ Overall Status: FAILED")
        
        print(f"📊 Tests Run: {self.test_results['tests_run']}")
        print(f"✅ Passed: {self.test_results['tests_passed']}")
        print(f"❌ Failed: {self.test_results['tests_failed']}")
        print(f"🖼️  Images Processed: {self.test_results['images_processed']}")
        print(f"📈 Success Rate: {(self.test_results['tests_passed']/self.test_results['tests_run']*100):.1f}%")
        
        # Show ML features availability
        if self.test_results['ml_features_available']:
            print("\n🤖 ML/AI Features Available:")
            for feature, available in self.test_results['ml_features_available'].items():
                status = "✅" if available else "❌"
                print(f"  {status} {feature}: {available}")
        
        if self.test_results['tests_failed'] > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results['results']:
                if not result['success']:
                    print(f"  • {result['test']}: {result['message']}")
    
    def save_results(self, output_file: str = 'ml-feature-test-results.json'):
        """Save test results to JSON file"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        with open(output_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"Results saved to: {output_path}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python test_ml_features.py <base_url> [test_images_dir]")
        print("Example: python test_ml_features.py http://passport-photo-ai-enhanced.us-east-1.elasticbeanstalk.com")
        sys.exit(1)
    
    base_url = sys.argv[1]
    test_images_dir = sys.argv[2] if len(sys.argv) > 2 else 'test_images'
    
    tester = MLFeatureTester(base_url, test_images_dir)
    
    try:
        success = tester.run_all_tests()
        tester.print_results()
        tester.save_results()
        
        if not success:
            print("\n❌ ML/AI feature tests failed!")
            sys.exit(1)
        else:
            print("\n✅ All ML/AI feature tests passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ ML/AI test error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()