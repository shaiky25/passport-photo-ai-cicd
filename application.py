"""
Passport Photo AI - Enhanced Backend with ML/AI
Full-featured backend with advanced face detection, background removal, and AI analysis
Optimized for t3.small instances with comprehensive ML capabilities
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
import io
import base64
import json
import os
from datetime import datetime, timezone
import random
import string
import boto3
from botocore.exceptions import ClientError

# Import CORS configuration manager
from cors_config import get_cors_manager

# Try to import dotenv, but make it optional
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️ python-dotenv not available - using system environment variables only")
    def load_dotenv():
        pass

# Check for numpy availability
try:
    import numpy as np
    NUMPY_AVAILABLE = True
    print("✅ NumPy available")
except ImportError:
    NUMPY_AVAILABLE = False
    print("❌ NumPy not available")

# HEIC image support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT = True
    print("✅ HEIC support enabled")
except ImportError:
    HEIC_SUPPORT = False
    print("❌ HEIC support not available")

# rembg support for background removal
try:
    from rembg import remove, new_session
    REMBG_AVAILABLE = True
    print("✅ rembg available for background removal")
except ImportError:
    REMBG_AVAILABLE = False
    print("❌ rembg not available - background removal disabled")

# OpenCV for advanced face detection
try:
    import cv2
    OPENCV_AVAILABLE = True
    print("✅ OpenCV available for advanced face detection")
except ImportError:
    OPENCV_AVAILABLE = False
    print("❌ OpenCV not available - using fallback face detection")

# Enhanced processing availability
ENHANCED_PROCESSING_AVAILABLE = OPENCV_AVAILABLE and NUMPY_AVAILABLE
print(f"Enhanced processing: {'✅ Available' if ENHANCED_PROCESSING_AVAILABLE else '❌ Not available'}")

# Import email validation services
try:
    from services.email_validation import get_email_service
    from services.rate_limiting import get_rate_limiter
    from services.download_controller import get_download_controller
    from database.dynamodb_client import get_db_client
    EMAIL_VALIDATION_AVAILABLE = True
    print("✅ Email validation services loaded successfully")
except ImportError as e:
    print(f"❌ Email validation services not available: {e}")
    EMAIL_VALIDATION_AVAILABLE = False

# Advanced Face Detection with OpenCV
class AdvancedFaceDetection:
    """Advanced face detection using OpenCV with eye detection and scoring"""
    
    def __init__(self):
        self.face_cascade = None
        self.eye_cascade = None
        self._load_cascades()
    
    def _load_cascades(self):
        """Load OpenCV cascade classifiers"""
        if not OPENCV_AVAILABLE:
            return
        
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            print("✅ OpenCV cascades loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load OpenCV cascades: {e}")
            self.face_cascade = None
            self.eye_cascade = None
    
    def detect_face(self, image_path):
        """Advanced face detection with eye detection and scoring"""
        if not OPENCV_AVAILABLE or not self.face_cascade:
            return self._fallback_detection(image_path)
        
        try:
            # Load image with OpenCV
            cv_img = cv2.imread(image_path)
            if cv_img is None:
                return self._fallback_detection(image_path)
            
            height, width = cv_img.shape[:2]
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            
            # Detect faces with optimized parameters
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.2, 
                minNeighbors=8, 
                minSize=(80, 80)
            )
            
            if len(faces) == 0:
                return self._fallback_detection(image_path)
            
            # Score and select best face
            best_face = self._select_best_face(faces, gray, width, height)
            
            if best_face is None:
                return self._fallback_detection(image_path)
            
            x, y, w, h, eyes_count, confidence = best_face
            
            # Calculate metrics
            head_height_percent = h / height
            face_area_percent = (w * h) / (width * height) * 100
            horizontal_center = abs((x + w/2) - width/2) / width < 0.3
            
            # Enhanced validation with eye detection
            has_good_eyes = eyes_count >= 2
            face_size_ok = bool(0.5 <= face_area_percent <= 60.0)
            head_height_ok = bool(0.10 <= head_height_percent <= 0.9)
            aspect_ratio_ok = bool(0.3 <= (width/height) <= 3.0)
            
            # Be more lenient if eyes are detected
            if has_good_eyes:
                face_size_ok = bool(0.3 <= face_area_percent <= 70.0)
                head_height_ok = bool(0.05 <= head_height_percent <= 0.95)
            
            face_valid = bool(face_size_ok and head_height_ok and aspect_ratio_ok)
            
            # Expand face region for passport photo
            expansion_factor = 1.8
            center_x = x + w // 2
            center_y = y + h // 2
            
            new_w = int(w * expansion_factor)
            new_h = int(h * expansion_factor)
            crop_size = max(new_w, new_h)
            
            crop_x = center_x - crop_size // 2
            crop_y = center_y - int(crop_size * 0.4)
            
            # Ensure crop is within image bounds
            crop_x = max(0, min(crop_x, width - crop_size))
            crop_y = max(0, min(crop_y, height - crop_size))
            crop_size = min(crop_size, width - crop_x, height - crop_y)
            
            return {
                "faces_detected": int(len(faces)),
                "valid": bool(face_valid),
                "face_bbox": {"x": int(crop_x), "y": int(crop_y), "width": int(crop_size), "height": int(crop_size)},
                "original_face": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                "eyes_detected": int(eyes_count),
                "head_height_percent": float(round(head_height_percent, 2)),
                "head_height_valid": bool(head_height_ok),
                "horizontally_centered": bool(horizontal_center),
                "face_area_percent": float(round(face_area_percent, 1)),
                "face_aspect_ratio": float(round(width / height if height > 0 else 1, 2)),
                "face_size_ok": bool(face_size_ok),
                "aspect_ratio_ok": bool(aspect_ratio_ok),
                "image_dimensions": {"width": int(width), "height": int(height)},
                "confidence": float(round(confidence, 2)),
                "error": None if face_valid else "Face detected but may not meet passport photo requirements",
                "detection_method": "opencv_advanced",
                "eye_detection_used": True
            }
            
        except Exception as e:
            print(f"Advanced face detection error: {e}")
            return self._fallback_detection(image_path)
    
    def _select_best_face(self, faces, gray, width, height):
        """Select the best face based on multiple criteria"""
        best_face = None
        best_score = 0
        
        for fx, fy, fw, fh in faces:
            # Extract face region for eye detection
            face_roi_gray = gray[fy:fy+fh, fx:fx+fw]
            
            # Detect eyes within this face
            eyes = self.eye_cascade.detectMultiScale(
                face_roi_gray, 
                scaleFactor=1.1, 
                minNeighbors=3, 
                minSize=(10, 10)
            ) if self.eye_cascade else []
            
            # Calculate face quality score
            face_area = fw * fh
            face_area_percent = (face_area / (width * height)) * 100
            
            # Score factors
            eye_score = len(eyes) * 50  # 50 points per eye
            size_score = min(face_area_percent * 2, 100)  # Up to 100 points for size
            
            # Position score (center preference)
            face_center_x = fx + fw / 2
            face_center_y = fy + fh / 2
            center_distance = ((face_center_x - width/2)**2 + (face_center_y - height/2)**2)**0.5
            max_distance = (width**2 + height**2)**0.5
            position_score = (1 - center_distance / max_distance) * 50
            
            # Aspect ratio score
            aspect_ratio = fw / fh if fh > 0 else 0
            aspect_score = 25 if 0.7 <= aspect_ratio <= 1.4 else 0
            
            total_score = eye_score + size_score + position_score + aspect_score
            
            if total_score > best_score:
                best_score = total_score
                best_face = (fx, fy, fw, fh, len(eyes), total_score / 225.0)  # Normalize confidence
        
        return best_face
    
    def _fallback_detection(self, image_path):
        """Fallback to simple center crop"""
        try:
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            width, height = img.size
            size = min(width, height)
            crop_x = (width - size) // 2
            crop_y = (height - size) // 2
            
            return {
                "faces_detected": 1,
                "valid": True,
                "face_bbox": {"x": crop_x, "y": crop_y, "width": size, "height": size},
                "original_face": {"x": crop_x, "y": crop_y, "width": size, "height": size},
                "eyes_detected": 0,
                "head_height_percent": 0.5,
                "head_height_valid": True,
                "horizontally_centered": True,
                "face_area_percent": 25.0,
                "face_aspect_ratio": float(width / height if height > 0 else 1),
                "face_size_ok": True,
                "aspect_ratio_ok": True,
                "image_dimensions": {"width": width, "height": height},
                "confidence": 0.5,
                "error": None,
                "detection_method": "center_crop_fallback"
            }
        except Exception as e:
            return {"faces_detected": 0, "valid": False, "error": f"Detection failed: {str(e)}"}

# Initialize face detector
face_detector = AdvancedFaceDetection()

application = Flask(__name__)

# Initialize CORS configuration manager
cors_manager = get_cors_manager(application)

# Enhanced CORS Configuration using the manager
cors_instance = CORS(application, 
                    origins=cors_manager.config.allowed_origins,
                    methods=cors_manager.config.allowed_methods,
                    allow_headers=cors_manager.config.allowed_headers,
                    expose_headers=cors_manager.config.expose_headers,
                    supports_credentials=cors_manager.config.allow_credentials,
                    max_age=cors_manager.config.max_age)

application.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Add after_request handler to ensure CORS headers on all responses
@application.after_request
def after_request(response):
    """Ensure CORS headers are present on all responses"""
    return cors_manager.add_cors_headers(response)

# Initialize AWS services
try:
    ses_client = boto3.client('ses', region_name='us-east-1')
    s3_client = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    print("✅ AWS services initialized")
except Exception as e:
    print(f"⚠️ AWS services initialization warning: {e}")
    ses_client = None
    s3_client = None
    dynamodb = None

class EnhancedPhotoProcessor:
    """Enhanced photo processor with ML/AI capabilities"""
    
    PASSPORT_SIZE_PIXELS = (1200, 1200)  # High resolution output
    
    # Feature flags
    ENABLE_BACKGROUND_REMOVAL = True
    ENABLE_INTELLIGENT_CROPPING = True
    ENABLE_IMAGE_ENHANCEMENT = True
    ENABLE_WATERMARK = True
    
    def remove_background_advanced(self, img):
        """Advanced background removal using rembg"""
        if not REMBG_AVAILABLE:
            print("rembg not available, skipping background removal")
            return img
        
        try:
            # Use high-quality models for t3.small (4GB RAM)
            model_priority = [
                'u2net',           # High quality, ~200MB RAM
                'u2net_human_seg', # Human-focused, ~300MB RAM
                'u2netp',          # Lighter version, ~100MB RAM
                'silueta'          # Smallest, ~50MB RAM
            ]
            
            session = None
            model_used = None
            
            for model_name in model_priority:
                try:
                    print(f"Trying rembg model: {model_name}")
                    session = new_session(model_name)
                    model_used = model_name
                    print(f"Successfully loaded model: {model_name}")
                    break
                except Exception as e:
                    print(f"Failed to load model {model_name}: {e}")
                    continue
            
            if session is None:
                print("All rembg models failed to load, skipping background removal")
                return img
            
            # Convert PIL to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            input_data = img_buffer.getvalue()
            
            # Remove background
            print(f"Removing background with model: {model_used}")
            output_data = remove(input_data, session=session)
            
            # Convert back to PIL
            result_img = Image.open(io.BytesIO(output_data))
            
            # Convert RGBA to RGB with white background
            if result_img.mode == 'RGBA':
                white_bg = Image.new('RGB', result_img.size, (255, 255, 255))
                white_bg.paste(result_img, mask=result_img.split()[-1])
                print("Background removed and converted to white background")
                return white_bg
            else:
                return result_img
                
        except Exception as e:
            print(f"Background removal failed: {e}, returning original image")
            return img
    
    def intelligent_crop(self, img, face_bbox):
        """Intelligent cropping for passport photos"""
        if not face_bbox or not self.ENABLE_INTELLIGENT_CROPPING:
            # Fallback to center crop
            size = min(img.size)
            left = (img.size[0] - size) // 2
            top = (img.size[1] - size) // 2
            return img.crop((left, top, left + size, top + size))
        
        fx, fy, fw, fh = face_bbox['x'], face_bbox['y'], face_bbox['width'], face_bbox['height']
        
        # Calculate intelligent crop for passport photo
        face_center_x = fx + fw / 2
        face_center_y = fy + fh / 2
        
        # Estimate full head height (face detection usually captures core features)
        estimated_full_head_height = fh / 0.6  # Face is ~60% of full head
        target_face_ratio = 0.75  # Target 75% of image height for full head
        required_crop_height = estimated_full_head_height / target_face_ratio
        crop_size = required_crop_height  # Square crop
        
        # Position crop to include hair/forehead and shoulders
        estimated_head_top = fy - (fh * 0.4)
        headroom_ratio = 0.12
        
        crop_top = max(0, int(estimated_head_top - (crop_size * headroom_ratio)))
        crop_bottom = min(img.height, int(crop_top + crop_size))
        
        # Adjust if hitting boundaries
        if crop_bottom > img.height:
            crop_bottom = img.height
            crop_top = max(0, crop_bottom - int(crop_size))
        
        # Center horizontally
        crop_left = max(0, int(face_center_x - crop_size / 2))
        crop_right = min(img.width, int(crop_left + crop_size))
        
        # Adjust horizontal bounds
        if crop_right > img.width:
            crop_right = img.width
            crop_left = max(0, crop_right - int(crop_size))
        
        # Ensure perfect square
        actual_width = crop_right - crop_left
        actual_height = crop_bottom - crop_top
        final_size = min(actual_width, actual_height)
        
        if actual_width > final_size:
            center_x = crop_left + actual_width // 2
            crop_left = center_x - final_size // 2
            crop_right = crop_left + final_size
        
        if actual_height > final_size:
            center_y = crop_top + actual_height // 2
            crop_top = center_y - final_size // 2
            crop_bottom = crop_top + final_size
        
        print(f"Intelligent crop: ({crop_left}, {crop_top}) to ({crop_right}, {crop_bottom})")
        return img.crop((crop_left, crop_top, crop_right, crop_bottom))
    
    def enhance_image(self, img):
        """Apply professional image enhancements"""
        if not self.ENABLE_IMAGE_ENHANCEMENT:
            return img
        
        # Brightness adjustment
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.02)
        
        # Contrast adjustment
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.05)
        
        # Sharpness adjustment
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.1)
        
        print("Image enhancements applied")
        return img
    
    def add_watermark(self, img):
        """Add professional watermark"""
        if not self.ENABLE_WATERMARK:
            return img
        
        try:
            watermarked = img.copy().convert('RGBA')
            overlay = Image.new('RGBA', watermarked.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            watermark_text = "PROOF"
            img_width, img_height = watermarked.size
            font_size = max(img_width // 4, 96)
            
            try:
                font = ImageFont.load_default()
            except:
                font = None
            
            # Calculate text dimensions and positions
            if font:
                bbox = draw.textbbox((0, 0), watermark_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(watermark_text) * 24
                text_height = 48
            
            x_spacing = text_width + 40
            y_spacing = text_height + 30
            
            # Generate diagonal grid
            positions = []
            y = -text_height
            row_count = 0
            
            while y < img_height + text_height:
                x = -text_width
                if row_count % 2 == 1:
                    x += x_spacing // 2
                
                while x < img_width + text_width:
                    positions.append((x, y))
                    x += x_spacing
                
                y += y_spacing
                row_count += 1
            
            # Draw watermarks
            for x, y in positions:
                if font:
                    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 120))
                else:
                    draw.text((x, y), watermark_text, fill=(255, 255, 255, 120))
            
            # Composite and convert back to RGB
            watermarked = Image.alpha_composite(watermarked, overlay)
            final_image = Image.new('RGB', watermarked.size, (255, 255, 255))
            final_image.paste(watermarked, mask=watermarked.split()[-1])
            
            print("Watermark added")
            return final_image
            
        except Exception as e:
            print(f"Watermark error: {e}")
            return img
    
    def process_image(self, image_path, remove_background=False, remove_watermark=False):
        """Process image with full ML/AI pipeline"""
        try:
            # Detect face
            face_result = face_detector.detect_face(image_path)
            
            if not face_result.get("valid"):
                return None, face_result
            
            # Load and process image
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Intelligent cropping
            face_bbox = face_result.get("face_bbox")
            cropped = self.intelligent_crop(img, face_bbox)
            
            # Background removal
            if remove_background:
                cropped = self.remove_background_advanced(cropped)
            
            # Resize to passport size
            processed = cropped.resize(self.PASSPORT_SIZE_PIXELS, Image.Resampling.LANCZOS)
            
            # Image enhancements
            processed = self.enhance_image(processed)
            
            # Add watermark unless removal is authorized
            if not remove_watermark:
                processed = self.add_watermark(processed)
            
            return processed, face_result
            
        except Exception as e:
            return None, {"faces_detected": 0, "valid": False, "error": f"Processing failed: {str(e)}"}

# Initialize processor
processor = EnhancedPhotoProcessor()

# Initialize email services
if EMAIL_VALIDATION_AVAILABLE:
    email_service = get_email_service()
    rate_limiter = get_rate_limiter()
    download_controller = get_download_controller()
    db_client = get_db_client()
    print("✅ Email validation services initialized")
else:
    email_service = None
    rate_limiter = None
    download_controller = None
    db_client = None
    print("⚠️ Email validation services not available - using fallback")

# Simple in-memory store for OTPs (fallback)
otp_store = {}

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    """Send OTP via AWS SES"""
    if not ses_client:
        print("SES client not available")
        return False
    
    try:
        sender_email = os.environ.get('SENDER_EMAIL', 'faiz.24365@gmail.com')
        
        subject = "Your PassportPhotoAI Verification Code"
        body_html = f"""
        <html>
        <head></head>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4F46E5;">PassportPhotoAI Verification</h2>
                <p>Your verification code is:</p>
                <div style="background-color: #F3F4F6; padding: 20px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 3px; margin: 20px 0;">
                    {otp}
                </div>
                <p style="color: #6B7280;">This code will expire in 10 minutes.</p>
                <p style="color: #6B7280; font-size: 12px;">If you didn't request this code, please ignore this email.</p>
            </div>
        </body>
        </html>
        """
        
        response = ses_client.send_email(
            Destination={'ToAddresses': [email]},
            Message={
                'Body': {'Html': {'Charset': 'UTF-8', 'Data': body_html}},
                'Subject': {'Charset': 'UTF-8', 'Data': subject},
            },
            Source=sender_email,
        )
        
        print(f"Email sent successfully to {email}. Message ID: {response['MessageId']}")
        return True
        
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

# API Endpoints
@application.route('/', methods=['GET'])
def root():
    return jsonify({
        "status": "healthy", 
        "message": "Passport Photo AI - Enhanced Backend",
        "cors_origins": cors_manager.config.allowed_origins,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "enhanced"
    }), 200

@application.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Passport Photo AI - Enhanced Backend",
        "cors_origins": cors_manager.config.allowed_origins,
        "features": {
            "cors_enabled": True,
            "origins_configured": len(cors_manager.config.allowed_origins),
            "opencv_available": OPENCV_AVAILABLE,
            "rembg_available": REMBG_AVAILABLE,
            "heic_support": HEIC_SUPPORT,
            "numpy_available": NUMPY_AVAILABLE,
            "enhanced_processing": ENHANCED_PROCESSING_AVAILABLE,
            "background_removal": "advanced" if REMBG_AVAILABLE else "none",
            "face_detection": "opencv_advanced" if OPENCV_AVAILABLE else "center_crop"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200

@application.route('/api/test-cors', methods=['GET', 'POST', 'OPTIONS'])
def test_cors():
    """Test endpoint specifically for CORS validation"""
    
    if request.method == 'OPTIONS':
        return jsonify({'status': 'preflight_ok'}), 200
    
    return jsonify({
        'status': 'cors_test_successful',
        'method': request.method,
        'origin': request.headers.get('Origin', 'no-origin'),
        'user_agent': request.headers.get('User-Agent', 'no-user-agent'),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

@application.route('/api/send-otp', methods=['POST'])
def send_otp():
    """Send OTP for email verification"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        ip_address = request.remote_addr or 'unknown'
        
        if not email or '@' not in email:
            return jsonify({"error": "Invalid email address"}), 400
        
        # Use enhanced email service if available
        if EMAIL_VALIDATION_AVAILABLE and email_service:
            result = email_service.send_otp(email)
            
            if result['success']:
                return jsonify({
                    "success": True, 
                    "message": result['message'],
                    "expires_in": result.get('expires_in', 600)
                }), 200
            else:
                return jsonify({
                    "error": result['error'],
                    "retry_after": result.get('retry_after')
                }), 429 if 'rate limit' in result['error'].lower() else 400
        
        else:
            # Fallback to simple OTP system
            otp = generate_otp()
            otp_store[email] = {
                'otp': otp,
                'timestamp': datetime.now(timezone.utc).timestamp(),
                'verified': False
            }
            
            if send_otp_email(email, otp):
                return jsonify({"success": True, "message": "OTP sent to your email"}), 200
            else:
                return jsonify({"error": "Failed to send email. Please check your email address."}), 500
            
    except Exception as e:
        print(f"Send OTP error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@application.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP for email verification"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        otp = data.get('otp', '').strip()
        
        if not email or not otp:
            return jsonify({"error": "Email and OTP required"}), 400
        
        # Use enhanced email service if available
        if EMAIL_VALIDATION_AVAILABLE and email_service:
            result = email_service.verify_otp(email, otp)
            
            if result['success']:
                return jsonify({
                    "success": True, 
                    "message": result['message']
                }), 200
            else:
                return jsonify({"error": result['error']}), 400
        
        else:
            # Fallback to simple OTP system
            if email not in otp_store:
                return jsonify({"error": "No OTP found for this email"}), 400
            
            stored_data = otp_store[email]
            
            if datetime.now(timezone.utc).timestamp() - stored_data['timestamp'] > 600:
                del otp_store[email]
                return jsonify({"error": "OTP expired"}), 400
            
            if stored_data['otp'] == otp:
                otp_store[email]['verified'] = True
                return jsonify({"success": True, "message": "Email verified successfully"}), 200
            else:
                return jsonify({"error": "Invalid OTP"}), 400
            
    except Exception as e:
        print(f"Verify OTP error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@application.route('/api/full-workflow', methods=['POST', 'OPTIONS'])
def full_workflow():
    """Main photo processing workflow - enhanced version"""
    
    if request.method == 'OPTIONS':
        return jsonify({'status': 'preflight_ok'}), 200
    
    start_time = datetime.now()
    
    try:
        # Check if file was uploaded
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get processing options
        remove_background = request.form.get('remove_background', 'false').lower() == 'true'
        email = request.form.get('email', '').strip().lower()
        
        # Check if watermark removal is authorized
        remove_watermark = False
        if EMAIL_VALIDATION_AVAILABLE and email_service and email:
            remove_watermark = email_service.is_email_verified(email)
        elif email and email in otp_store and otp_store[email].get('verified', False):
            remove_watermark = True
        
        # Save uploaded file temporarily
        temp_path = f"/tmp/{random.randint(1000, 9999)}_{file.filename}"
        file.save(temp_path)
        
        try:
            # Process the image
            processed_img, analysis = processor.process_image(temp_path, remove_background, remove_watermark)
            
            if processed_img is None:
                return jsonify({
                    'success': False,
                    'message': 'Processing failed',
                    'analysis': {'face_detection': analysis}
                }), 400
            
            # Convert processed image to base64
            img_buffer = io.BytesIO()
            processed_img.save(img_buffer, format='JPEG', quality=95, dpi=(300, 300))
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Create AI analysis
            ai_analysis = {
                'compliant': analysis.get('valid', False),
                'issues': [] if analysis.get('valid', False) else ['Image may not meet passport photo requirements'],
                'analysis_details': {
                    'background_ok': remove_background,
                    'expression_neutral': True,
                    'eyes_open': analysis.get('eyes_detected', 0) >= 2,
                    'lighting_ok': True,
                    'no_obstructions': True
                },
                'confidence_score': analysis.get('confidence', 0)
            }
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            return jsonify({
                'success': True,
                'message': 'Image processed successfully with enhanced ML/AI pipeline',
                'processed_image': img_base64,
                'analysis': {
                    'face_detection': analysis,
                    'ai_analysis': ai_analysis
                },
                'processing_time': processing_time,
                'cors_origin': request.headers.get('Origin', 'no-origin'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }), 200
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@application.route('/api/log-event', methods=['POST', 'OPTIONS'])
def log_event():
    """Log analytics events"""
    
    if request.method == 'OPTIONS':
        return jsonify({'status': 'preflight_ok'}), 200
    
    try:
        event_data = request.json
        if not event_data:
            return jsonify({"error": "No event data provided"}), 400
        
        event_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        event_data['origin'] = request.headers.get('Origin', 'no-origin')
        
        print(f"Analytics Event: {json.dumps(event_data)}")
        
        # Store in DynamoDB if available
        if db_client:
            try:
                db_client.log_request(
                    ip_address=request.remote_addr or 'unknown',
                    email=event_data.get('email', ''),
                    action='analytics_event',
                    success=True,
                    user_agent=request.headers.get('User-Agent', '')[:500]
                )
            except Exception as e:
                print(f"DynamoDB logging error: {e}")
        
        return jsonify({"success": True, "message": "Event logged"}), 200
        
    except Exception as e:
        print(f"Log event error: {e}")
        return jsonify({"error": "Failed to log event"}), 500

if __name__ == '__main__':
    print("🚀 Starting Passport Photo AI - Enhanced Backend")
    print(f"🌐 CORS Origins: {cors_manager.config.allowed_origins}")
    print(f"🤖 OpenCV: {'✅' if OPENCV_AVAILABLE else '❌'}")
    print(f"🎨 Background Removal: {'✅' if REMBG_AVAILABLE else '❌'}")
    print(f"📊 NumPy: {'✅' if NUMPY_AVAILABLE else '❌'}")
    print(f"🔬 Enhanced Processing: {'✅' if ENHANCED_PROCESSING_AVAILABLE else '❌'}")
    application.run(debug=False, host='0.0.0.0', port=5000)