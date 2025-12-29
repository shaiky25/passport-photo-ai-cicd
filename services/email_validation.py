"""
Email Validation Service
Handles email format validation, OTP generation, and verification workflow
"""

import re
import secrets
import boto3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
import os

from database.dynamodb_client import get_db_client

class EmailValidationService:
    """
    Service for handling email validation workflow including:
    - Email format validation
    - OTP generation and sending
    - Email verification
    - Integration with SES for email delivery
    """
    
    def __init__(self, ses_region: str = 'us-east-1'):
        """Initialize email validation service"""
        self.ses_region = ses_region
        self.db = get_db_client()
        
        # Initialize SES client
        try:
            self.ses_client = boto3.client('ses', region_name=ses_region)
            print(f"✅ SES client initialized for region: {ses_region}")
        except Exception as e:
            print(f"❌ Error initializing SES: {e}")
            self.ses_client = None
        
        # Email validation regex (RFC 5322 compliant)
        self.email_regex = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        # Get sender email from environment
        self.sender_email = os.getenv('SES_SENDER_EMAIL', 'faiz.24365@gmail.com')
    
    def validate_email_format(self, email: str) -> bool:
        """
        Validate email format using RFC 5322 compliant regex
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if email format is valid
        """
        if not email or len(email) > 254:  # RFC 5321 limit
            return False
        
        return bool(self.email_regex.match(email.strip().lower()))
    
    def send_otp(self, email: str) -> Dict[str, Any]:
        """
        Send OTP to email address
        
        Args:
            email: Email address to send OTP to
            
        Returns:
            Dict with success status and message
        """
        # Validate email format
        if not self.validate_email_format(email):
            return {
                'success': False,
                'error': 'Please enter a valid email address'
            }
        
        # Exempt specific email from rate limiting (for testing/admin)
        exempt_emails = ['faiz.24365@gmail.com', 'faiz.undefined@gmail.com']
        is_exempt = email.lower() in [e.lower() for e in exempt_emails]
        
        # Check rate limiting for OTP generation (3 per hour) - skip for exempt emails
        if not is_exempt:
            rate_check = self.db.check_rate_limit(
                identifier=email.lower(),
                limit_type='OTP_GENERATION',
                limit=3,
                window_hours=1
            )
            
            if not rate_check['allowed']:
                # Calculate time until reset
                reset_time = rate_check.get('reset_time')
                if reset_time:
                    try:
                        from datetime import datetime
                        reset_dt = datetime.fromisoformat(reset_time.replace('Z', '+00:00'))
                        now = datetime.now(reset_dt.tzinfo)
                        minutes_left = max(1, int((reset_dt - now).total_seconds() / 60))
                        
                        return {
                            'success': False,
                            'error': f'Too many OTP requests. Please wait {minutes_left} minutes before trying again.',
                            'retry_after': reset_time,
                            'minutes_remaining': minutes_left
                        }
                    except:
                        return {
                            'success': False,
                            'error': 'Too many OTP requests. Please wait an hour before trying again.',
                            'retry_after': reset_time
                        }
                else:
                    return {
                        'success': False,
                        'error': 'Too many OTP requests. Please wait an hour before trying again.'
                    }
        
        # Generate OTP
        otp_code = self.db.generate_otp()
        
        # Store OTP in database
        if not self.db.store_otp(email, otp_code, expires_minutes=10):
            return {
                'success': False,
                'error': 'Unable to generate verification code. Please try again in a moment.'
            }
        
        # Send email via SES
        email_sent = self._send_otp_email(email, otp_code)
        
        if not email_sent:
            return {
                'success': False,
                'error': 'Unable to send verification email. Please check your email address and try again.'
            }
        
        # Record the request for rate limiting (only for non-exempt emails)
        if not is_exempt:
            self.db.record_request(
                identifier=email.lower(),
                limit_type='OTP_GENERATION',
                action='send_otp'
            )
        
        # Create user if doesn't exist
        try:
            self.db.create_user(email)
        except Exception as e:
            print(f"Warning: Could not create user record: {e}")
        
        return {
            'success': True,
            'message': 'OTP sent successfully',
            'expires_in': 600  # 10 minutes in seconds
        }
    
    def verify_otp(self, email: str, otp_code: str) -> Dict[str, Any]:
        """
        Verify OTP code
        
        Args:
            email: Email address
            otp_code: OTP code to verify
            
        Returns:
            Dict with verification result
        """
        # Validate email format
        if not self.validate_email_format(email):
            return {
                'success': False,
                'error': 'Invalid email format'
            }
        
        # Validate OTP format (6 digits)
        if not otp_code or not otp_code.isdigit() or len(otp_code) != 6:
            return {
                'success': False,
                'error': 'Invalid OTP format'
            }
        
        # Verify OTP
        verification_result = self.db.verify_otp(email, otp_code)
        
        if verification_result['success']:
            # Update user verification status
            self.db.update_user_verification(email, verified=True)
            
            # Log successful verification
            self.db.log_request(
                ip_address='unknown',  # Will be updated by caller
                email=email,
                action='otp_verified',
                success=True
            )
        else:
            # Log failed verification
            self.db.log_request(
                ip_address='unknown',  # Will be updated by caller
                email=email,
                action='otp_verification_failed',
                success=False
            )
        
        return verification_result
    
    def is_email_verified(self, email: str) -> bool:
        """
        Check if email is verified
        
        Args:
            email: Email address to check
            
        Returns:
            bool: True if email is verified
        """
        if not self.validate_email_format(email):
            return False
        
        user = self.db.get_user(email)
        return user and user.get('verified', False)
    
    def get_verification_status(self, email: str) -> Dict[str, Any]:
        """
        Get detailed verification status for email
        
        Args:
            email: Email address to check
            
        Returns:
            Dict with verification status and user stats
        """
        if not self.validate_email_format(email):
            return {
                'valid_email': False,
                'verified': False,
                'error': 'Invalid email format'
            }
        
        user_stats = self.db.get_user_stats(email)
        
        return {
            'valid_email': True,
            'verified': user_stats.get('verified', False),
            'created_at': user_stats.get('created_at'),
            'last_activity': user_stats.get('last_activity'),
            'verification_count': user_stats.get('verification_count', 0),
            'daily_requests': user_stats.get('daily_requests', 0),
            'daily_limit': user_stats.get('daily_limit', 3)
        }
    
    def _send_otp_email(self, email: str, otp_code: str) -> bool:
        """
        Send OTP email via AWS SES
        
        Args:
            email: Recipient email address
            otp_code: OTP code to send
            
        Returns:
            bool: True if email sent successfully
        """
        if not self.ses_client:
            print("SES client not available - cannot send email")
            return False
        
        # Professional email template
        subject = "Your Passport Photo AI Verification Code"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Verification Code</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">📸 PassportPhoto.AI</h1>
                <p style="color: white; margin: 10px 0 0 0; opacity: 0.9;">Professional passport photos powered by AI</p>
            </div>
            
            <div style="background: white; padding: 40px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">Your Verification Code</h2>
                
                <p>Hello! You requested a verification code to access watermark-free passport photos.</p>
                
                <div style="background: #f8f9fa; border: 2px solid #667eea; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
                    <p style="margin: 0; color: #666; font-size: 14px;">Your verification code is:</p>
                    <h1 style="margin: 10px 0; color: #667eea; font-size: 36px; letter-spacing: 8px; font-family: 'Courier New', monospace;">{otp_code}</h1>
                    <p style="margin: 0; color: #666; font-size: 14px;">This code expires in 10 minutes</p>
                </div>
                
                <div style="background: #e8f4fd; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0;">
                    <h3 style="margin: 0 0 10px 0; color: #1976D2;">🔒 Security Tips:</h3>
                    <ul style="margin: 0; padding-left: 20px; color: #555;">
                        <li>Never share this code with anyone</li>
                        <li>We will never ask for your code via phone or email</li>
                        <li>This code expires in 10 minutes for your security</li>
                    </ul>
                </div>
                
                <p style="margin-top: 30px;">If you didn't request this code, please ignore this email. Your account remains secure.</p>
                
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                
                <div style="text-align: center; color: #666; font-size: 14px;">
                    <p>Need help? Contact us at support@passportphoto.ai</p>
                    <p style="margin: 5px 0;">© 2024 PassportPhoto.AI - Professional AI-powered passport photos</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        PassportPhoto.AI - Verification Code
        
        Your verification code is: {otp_code}
        
        This code expires in 10 minutes.
        
        Enter this code on the website to access watermark-free passport photos.
        
        Security Tips:
        - Never share this code with anyone
        - We will never ask for your code via phone or email
        - This code expires in 10 minutes for your security
        
        If you didn't request this code, please ignore this email.
        
        Need help? Contact us at support@passportphoto.ai
        
        © 2024 PassportPhoto.AI
        """
        
        try:
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'}
                    }
                }
            )
            
            print(f"✅ OTP email sent to {email}, MessageId: {response['MessageId']}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            print(f"❌ SES Error ({error_code}): {error_message}")
            
            # Handle specific SES errors
            if error_code == 'MessageRejected':
                print("Email address may not be verified in SES")
            elif error_code == 'SendingPausedException':
                print("SES sending is paused for this account")
            elif error_code == 'MailFromDomainNotVerifiedException':
                print("Sender domain not verified in SES")
            
            return False
            
        except Exception as e:
            print(f"❌ Unexpected error sending email: {e}")
            return False


# Global instance
email_service = None

def get_email_service() -> EmailValidationService:
    """Get global email validation service instance"""
    global email_service
    if email_service is None:
        email_service = EmailValidationService()
    return email_service

def init_email_service(ses_region: str = 'us-east-1') -> EmailValidationService:
    """Initialize email validation service with custom settings"""
    global email_service
    email_service = EmailValidationService(ses_region)
    return email_service