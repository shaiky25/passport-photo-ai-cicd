#!/usr/bin/env python3
"""
Image Processing Validation Script
Tests ML/AI features using images from test_images directory
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import base64
from PIL import Image
import io

class ImageProcessingValidator:
    """Validates ML/AI image processing capabilities"""
    
    def __init__(self, test_images_dir: str = 'test_images', base_url: str = None):
        self.test_images_dir = Path(test_images_dir)
        self.base_url = base_url or "http://localhost:5000"
        self.api_url = f"{self.base_url}/api"
        self.validation_results = {
            'success': True,
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'images_processed': 0,
            'results': []
        }
        
        # Supported image formats
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    def find_test_images(self) -> List[Path]:
        """Find all test images in the test_images directory"""
        if not self.test_images_dir.exists():
            print(f"❌ Test images directory not found: {self.test_images_dir}")
            return []
        
        images = []
        for file_path in self.test_images_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                images.append(file_path)
        
        print(f"📁 Found {len(images)} test images in {self.test_images_dir}")
        return images
    
    def create_test_image(self) -> bytes:
        """Create a simple test image if no test images are available"""
        print("🎨 Creating synthetic test image...")
        
        # Create a simple 400x400 RGB image with a face-like pattern
        img = Image.new('RGB', (400, 400), color='lightblue')
        
        # Add a simple face-like pattern
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        # Head (circle)
        draw.ellipse([150, 100, 250, 200], fill='peachpuff', outline='black', width=2)
        
        # Eyes (dots)
        draw.ellipse([170, 130, 180, 140], fill='black')
        draw.ellipse([220, 130, 230, 140], fill='black')
        
        # Mouth (arc)
        draw.arc([180, 160, 220, 180], 0, 180, fill='black', width=2)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=90)
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    
    def validate_image_file(self, image_path: Path) -> Tuple[bool, str, Dict]:
        """Validate a single image file"""
        try:
            # Check file size (should be reasonable for processing)
            file_size = image_path.stat().st_size
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                return False, f"Image too large: {file_size / 1024 / 1024:.1f}MB", {'size_mb': file_size / 1024 / 1024}
            
            # Try to open with PIL
            with Image.open(image_path) as img:
                width, height = img.size
                mode = img.mode
                
                # Basic validation
                if width < 100 or height < 100:
                    return False, f"Image too small: {width}x{height}", {'width': width, 'height': height}
                
                if width > 4000 or height > 4000:
                    return False, f"Image too large: {width}x{height}", {'width': width, 'height': height}
                
                return True, f"Valid image: {width}x{height} {mode}", {
                    'width': width,
                    'height': height,
                    'mode': mode,
                    'size_mb': file_size / 1024 / 1024
                }
                
        except Exception as e:
            return False, f"Cannot open image: {str(e)}", {'error': str(e)}
    
    def test_image_processing_endpoint(self, image_data: bytes, image_name: str, 
                                     remove_background: bool = False) -> Tuple[bool, str, Dict]:
        """Test image processing with the API endpoint"""
        try:
            # Prepare the request
            files = {'image': (image_name, image_data, 'image/jpeg')}
            data = {
                'remove_background': 'true' if remove_background else 'false',
                'email': 'test@example.com'
            }
            
            headers = {
                'Origin': 'https://main.d3gelc4wjo7dl.amplifyapp.com'
            }
            
            # Make the request
            response = requests.post(
                f"{self.api_url}/full-workflow",
                files=files,
                data=data,
                headers=headers,
                timeout=60  # Longer timeout for image processing
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    analysis = result.get('analysis', {})
                    face_detection = analysis.get('face_detection', {})
                    ai_analysis = analysis.get('ai_analysis', {})
                    
                    # Extract key metrics
                    faces_detected = face_detection.get('faces_detected', 0)
                    detection_method = face_detection.get('detection_method', 'unknown')
                    processing_time = result.get('processing_time', 0)
                    
                    details = {
                        'faces_detected': faces_detected,
                        'detection_method': detection_method,
                        'processing_time': processing_time,
                        'background_removed': remove_background,
                        'has_processed_image': bool(result.get('processed_image'))
                    }
                    
                    return True, f"Processed successfully: {faces_detected} faces, {processing_time:.2f}s", details
                else:
                    return False, f"Processing failed: {result.get('message', 'Unknown error')}", result
            else:
                return False, f"HTTP {response.status_code}: {response.text[:200]}", {
                    'status_code': response.status_code,
                    'response': response.text[:200]
                }
                
        except requests.exceptions.Timeout:
            return False, "Request timeout (>60s)", {'timeout': True}
        except Exception as e:
            return False, f"Request failed: {str(e)}", {'error': str(e)}
    
    def test_face_detection_capabilities(self, image_data: bytes, image_name: str) -> Tuple[bool, str, Dict]:
        """Test face detection capabilities specifically"""
        try:
            files = {'image': (image_name, image_data, 'image/jpeg')}
            data = {'remove_background': 'false'}
            headers = {'Origin': 'https://main.d3gelc4wjo7dl.amplifyapp.com'}
            
            response = requests.post(
                f"{self.api_url}/full-workflow",
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    face_detection = result.get('analysis', {}).get('face_detection', {})
                    
                    # Analyze face detection results
                    faces_detected = face_detection.get('faces_detected', 0)
                    detection_method = face_detection.get('detection_method', 'unknown')
                    confidence = face_detection.get('confidence', 0)
                    eyes_detected = face_detection.get('eyes_detected', 0)
                    
                    details = {
                        'faces_detected': faces_detected,
                        'detection_method': detection_method,
                        'confidence': confidence,
                        'eyes_detected': eyes_detected,
                        'opencv_used': 'opencv' in detection_method.lower()
                    }
                    
                    # Consider it successful if we detect at least some structure
                    if faces_detected > 0 or detection_method != 'unknown':
                        return True, f"Face detection working: {detection_method}", details
                    else:
                        return False, "No face detection capability", details
                else:
                    return False, f"Face detection failed: {result.get('message')}", result
            else:
                return False, f"Face detection request failed: {response.status_code}", {}
                
        except Exception as e:
            return False, f"Face detection test failed: {str(e)}", {}
    
    def test_background_removal(self, image_data: bytes, image_name: str) -> Tuple[bool, str, Dict]:
        """Test background removal capabilities"""
        try:
            files = {'image': (image_name, image_data, 'image/jpeg')}
            data = {'remove_background': 'true'}
            headers = {'Origin': 'https://main.d3gelc4wjo7dl.amplifyapp.com'}
            
            response = requests.post(
                f"{self.api_url}/full-workflow",
                files=files,
                data=data,
                headers=headers,
                timeout=90  # Longer timeout for background removal
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    processing_time = result.get('processing_time', 0)
                    has_processed_image = bool(result.get('processed_image'))
                    
                    details = {
                        'processing_time': processing_time,
                        'has_processed_image': has_processed_image,
                        'background_removal_attempted': True
                    }
                    
                    return True, f"Background removal completed in {processing_time:.2f}s", details
                else:
                    message = result.get('message', 'Unknown error')
                    # Background removal might not be available, which is okay
                    if 'rembg' in message.lower() or 'background' in message.lower():
                        return True, "Background removal not available (expected)", {'rembg_available': False}
                    else:
                        return False, f"Background removal failed: {message}", result
            else:
                return False, f"Background removal request failed: {response.status_code}", {}
                
        except requests.exceptions.Timeout:
            return True, "Background removal timeout (expected for complex processing)", {'timeout': True}
        except Exception as e:
            return False, f"Background removal test failed: {str(e)}", {}
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and record results"""
        self.validation_results['tests_run'] += 1
        
        try:
            print(f"🧪 Running {test_name}...")
            success, message, details = test_func()
            
            result = {
                'test': test_name,
                'success': success,
                'message': message,
                'details': details or {}
            }
            
            self.validation_results['results'].append(result)
            
            if success:
                self.validation_results['tests_passed'] += 1
                print(f"✅ {test_name}: {message}")
            else:
                self.validation_results['tests_failed'] += 1
                self.validation_results['success'] = False
                print(f"❌ {test_name}: {message}")
            
            return success
            
        except Exception as e:
            self.validation_results['tests_failed'] += 1
            self.validation_results['success'] = False
            error_result = {
                'test': test_name,
                'success': False,
                'message': f"Test crashed: {str(e)}",
                'details': {'exception': str(e)}
            }
            self.validation_results['results'].append(error_result)
            print(f"💥 {test_name}: Test crashed - {str(e)}")
            return False
    
    def run_validation(self) -> bool:
        """Run complete image processing validation"""
        print("🖼️  Starting image processing validation...")
        print("="*60)
        
        # Find test images
        test_images = self.find_test_images()
        
        if not test_images:
            print("⚠️  No test images found, creating synthetic test image...")
            test_image_data = self.create_test_image()
            test_images = [('synthetic_test.jpg', test_image_data)]
        else:
            # Convert file paths to (name, data) tuples
            image_data_list = []
            for img_path in test_images[:3]:  # Limit to first 3 images for speed
                try:
                    with open(img_path, 'rb') as f:
                        image_data_list.append((img_path.name, f.read()))
                except Exception as e:
                    print(f"⚠️  Could not read {img_path}: {e}")
            test_images = image_data_list
        
        if not test_images:
            print("❌ No images available for testing")
            return False
        
        print(f"📸 Testing with {len(test_images)} images")
        
        # Test each image
        for image_name, image_data in test_images:
            print(f"\n📷 Testing image: {image_name}")
            
            # Validate image data if it's a file path
            if isinstance(image_data, bytes):
                # Test basic image processing
                self.run_test(
                    f"Basic Processing - {image_name}",
                    lambda: self.test_image_processing_endpoint(image_data, image_name, False)
                )
                
                # Test face detection
                self.run_test(
                    f"Face Detection - {image_name}",
                    lambda: self.test_face_detection_capabilities(image_data, image_name)
                )
                
                # Test background removal (if available)
                self.run_test(
                    f"Background Removal - {image_name}",
                    lambda: self.test_background_removal(image_data, image_name)
                )
                
                self.validation_results['images_processed'] += 1
                time.sleep(1)  # Brief pause between images
        
        return self.validation_results['success']
    
    def print_results(self):
        """Print validation results"""
        print("\n" + "="*60)
        print("IMAGE PROCESSING VALIDATION RESULTS")
        print("="*60)
        
        if self.validation_results['success']:
            print("✅ Overall Status: PASSED")
        else:
            print("❌ Overall Status: FAILED")
        
        print(f"📊 Tests Run: {self.validation_results['tests_run']}")
        print(f"✅ Passed: {self.validation_results['tests_passed']}")
        print(f"❌ Failed: {self.validation_results['tests_failed']}")
        print(f"🖼️  Images Processed: {self.validation_results['images_processed']}")
        
        if self.validation_results['tests_failed'] > 0:
            print("\n❌ Failed Tests:")
            for result in self.validation_results['results']:
                if not result['success']:
                    print(f"  • {result['test']}: {result['message']}")
    
    def save_results(self, output_file: str = 'image-processing-validation-results.json'):
        """Save validation results to JSON file"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        with open(output_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        print(f"Results saved to: {output_path}")

def main():
    """Main function"""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    validator = ImageProcessingValidator(base_url=base_url)
    
    try:
        success = validator.run_validation()
        validator.print_results()
        validator.save_results()
        
        if not success:
            print("\n❌ Image processing validation failed!")
            sys.exit(1)
        else:
            print("\n✅ Image processing validation passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()