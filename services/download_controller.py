"""
Download Controller Service
Manages download permissions based on verification status and quota
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from database.dynamodb_client import get_db_client
from services.email_validation import get_email_service
from services.rate_limiting import get_rate_limiter

class DownloadController:
    """
    Service for managing download permissions including:
    - Watermarked downloads for unverified users
    - Clean downloads for verified users
    - Quota tracking and enforcement
    - Download permission checking
    """
    
    def __init__(self):
        """Initialize download controller"""
        self.db = get_db_client()
        self.email_service = get_email_service()
        self.rate_limiter = get_rate_limiter()
    
    def can_download_watermarked(self, ip_address: str) -> Dict[str, Any]:
        """
        Check if user can download watermarked photos
        
        Args:
            ip_address: Client IP address
            
        Returns:
            Dict with permission result
        """
        # Check IP-based rate limit for unverified users
        rate_status = self.rate_limiter.check_ip_limit(ip_address, verified=False)
        
        if not rate_status['allowed']:
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
                'retry_after': rate_status.get('reset_time'),
                'download_type': 'watermarked'
            }
        
        return {
            'allowed': True,
            'download_type': 'watermarked',
            'remaining_quota': rate_status['remaining'],
            'message': 'Watermarked download allowed'
        }
    
    def can_download_clean(self, email: str, ip_address: str) -> Dict[str, Any]:
        """
        Check if user can download clean (watermark-free) photos
        
        Args:
            email: User email address
            ip_address: Client IP address
            
        Returns:
            Dict with permission result
        """
        # Check if email is verified
        if not self.email_service.is_email_verified(email):
            return {
                'allowed': False,
                'reason': 'Email not verified',
                'message': 'Please verify your email address to download watermark-free photos.',
                'download_type': 'clean',
                'verification_required': True
            }
        
        # Check email-based daily quota for verified users
        rate_status = self.rate_limiter.check_email_limit(email)
        
        if not rate_status['allowed']:
            return {
                'allowed': False,
                'reason': 'Daily quota exceeded',
                'message': 'Daily download quota exceeded. Quota resets at midnight UTC.',
                'retry_after': rate_status.get('reset_time'),
                'download_type': 'clean'
            }
        
        # Check for exponential backoff
        backoff_info = self.rate_limiter.implement_exponential_backoff(email, 'download')
        
        if backoff_info['backoff_required']:
            return {
                'allowed': False,
                'reason': 'Temporary restriction',
                'message': f'Please wait {backoff_info["backoff_seconds"]} seconds before downloading.',
                'retry_after': backoff_info['retry_after'],
                'download_type': 'clean'
            }
        
        return {
            'allowed': True,
            'download_type': 'clean',
            'remaining_quota': rate_status['remaining'],
            'message': 'Clean download allowed'
        }
    
    def can_download_print_sheet(self, email: str, ip_address: str) -> Dict[str, Any]:
        """
        Check if user can download print sheets
        
        Args:
            email: User email address
            ip_address: Client IP address
            
        Returns:
            Dict with permission result
        """
        # Print sheets require email verification (same as clean downloads)
        return self.can_download_clean(email, ip_address)
    
    def record_download(self, identifier: str, download_type: str, 
                       email: str = None, ip_address: str = None) -> bool:
        """
        Record a download for quota tracking
        
        Args:
            identifier: User identifier (email for verified, IP for unverified)
            download_type: Type of download (watermarked, clean, print_sheet)
            email: User email address (if available)
            ip_address: Client IP address
            
        Returns:
            bool: True if download recorded successfully
        """
        verified = email and self.email_service.is_email_verified(email)
        
        # Record the download request
        success = self.rate_limiter.record_request(
            ip_address=ip_address or 'unknown',
            email=email,
            action=f'download_{download_type}',
            verified=verified
        )
        
        # Update user activity if email provided
        if email and verified:
            self.db.update_user_activity(email)
        
        return success
    
    def get_download_quota(self, email: str = None, ip_address: str = None) -> Dict[str, Any]:
        """
        Get download quota information
        
        Args:
            email: User email address (if available)
            ip_address: Client IP address
            
        Returns:
            Dict with quota information
        """
        verified = email and self.email_service.is_email_verified(email)
        
        if verified:
            # Get email-based quota for verified users
            quota_info = self.rate_limiter.get_remaining_quota(
                ip_address=ip_address or 'unknown',
                email=email,
                verified=True
            )
            
            return {
                'user_type': 'verified',
                'download_type': 'clean',
                'remaining': quota_info['remaining'],
                'limit': quota_info['limit'],
                'window': quota_info['window'],
                'reset_time': quota_info.get('reset_time'),
                'email_verified': True
            }
        else:
            # Get IP-based quota for unverified users
            quota_info = self.rate_limiter.get_remaining_quota(
                ip_address=ip_address or 'unknown',
                email=None,
                verified=False
            )
            
            return {
                'user_type': 'unverified',
                'download_type': 'watermarked',
                'remaining': quota_info['remaining'],
                'limit': quota_info['limit'],
                'window': quota_info['window'],
                'reset_time': quota_info.get('reset_time'),
                'email_verified': False,
                'verification_message': 'Verify your email to access watermark-free downloads and higher quota'
            }
    
    def get_download_permissions(self, email: str = None, ip_address: str = None) -> Dict[str, Any]:
        """
        Get comprehensive download permissions for user
        
        Args:
            email: User email address (if available)
            ip_address: Client IP address
            
        Returns:
            Dict with all download permissions
        """
        verified = email and self.email_service.is_email_verified(email)
        
        # Check watermarked download permission
        watermarked_permission = self.can_download_watermarked(ip_address or 'unknown')
        
        # Check clean download permission
        clean_permission = {'allowed': False, 'reason': 'Email verification required'}
        print_permission = {'allowed': False, 'reason': 'Email verification required'}
        
        if email:
            clean_permission = self.can_download_clean(email, ip_address or 'unknown')
            print_permission = self.can_download_print_sheet(email, ip_address or 'unknown')
        
        # Get quota information
        quota_info = self.get_download_quota(email, ip_address)
        
        return {
            'verified': verified,
            'permissions': {
                'watermarked': watermarked_permission,
                'clean': clean_permission,
                'print_sheet': print_permission
            },
            'quota': quota_info,
            'recommendations': self._get_recommendations(verified, watermarked_permission, clean_permission)
        }
    
    def _get_recommendations(self, verified: bool, watermarked_perm: Dict, clean_perm: Dict) -> List[str]:
        """Get user recommendations based on current status"""
        recommendations = []
        
        if not verified:
            recommendations.append("Verify your email to access watermark-free downloads")
            recommendations.append("Verified users get 20 downloads per day vs 3 per hour")
        
        if not watermarked_perm['allowed']:
            recommendations.append("Rate limit exceeded. Please wait before downloading again")
        
        if verified and not clean_perm['allowed']:
            if clean_perm.get('reason') == 'Daily quota exceeded':
                recommendations.append("Daily quota exceeded. Quota resets at midnight UTC")
            elif clean_perm.get('reason') == 'Temporary restriction':
                recommendations.append("Temporary restriction active. Please wait before downloading")
        
        if not recommendations:
            recommendations.append("All download options are available")
        
        return recommendations
    
    def should_add_watermark(self, email: str = None, ip_address: str = None) -> bool:
        """
        Determine if watermark should be added to processed image
        
        Args:
            email: User email address (if available)
            ip_address: Client IP address
            
        Returns:
            bool: True if watermark should be added
        """
        # Add watermark if email is not verified
        if not email:
            return True
        
        return not self.email_service.is_email_verified(email)
    
    def get_watermark_message(self, email: str = None) -> str:
        """
        Get appropriate watermark message
        
        Args:
            email: User email address (if available)
            
        Returns:
            str: Watermark message
        """
        if not email:
            return "Verify email to remove watermark"
        
        if not self.email_service.validate_email_format(email):
            return "Invalid email - verify to remove watermark"
        
        if not self.email_service.is_email_verified(email):
            return "Verify email to remove watermark"
        
        return ""  # No watermark needed


# Global instance
download_controller = None

def get_download_controller() -> DownloadController:
    """Get global download controller instance"""
    global download_controller
    if download_controller is None:
        download_controller = DownloadController()
    return download_controller