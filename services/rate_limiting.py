"""
Rate Limiting Service
Handles IP-based and email-based rate limiting with exponential backoff
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import time
import hashlib

from database.dynamodb_client import get_db_client

class RateLimitingService:
    """
    Service for handling rate limiting including:
    - IP-based limits for unverified users
    - Email-based limits for verified users
    - Exponential backoff for failed attempts
    - Daily quota management
    """
    
    def __init__(self):
        """Initialize rate limiting service"""
        self.db = get_db_client()
        
        # Rate limit configurations
        self.limits = {
            'unverified_ip_hourly': 3,      # 3 requests per hour for unverified IPs
            'verified_email_daily': 20,     # 20 requests per day for verified emails
            'otp_generation_hourly': 3,     # 3 OTP generations per hour per email
            'otp_verification_attempts': 3,  # 3 verification attempts per OTP
            'failed_login_backoff': 5       # 5 failed attempts before exponential backoff
        }
    
    def check_ip_limit(self, ip_address: str, verified: bool = False) -> Dict[str, Any]:
        """
        Check IP-based rate limit for unverified users
        
        Args:
            ip_address: Client IP address
            verified: Whether user has verified email
            
        Returns:
            Dict with rate limit status
        """
        if verified:
            # Verified users don't have IP-based limits
            return {
                'allowed': True,
                'remaining': float('inf'),
                'limit_type': 'none'
            }
        
        # Check hourly IP limit for unverified users
        return self.db.check_rate_limit(
            identifier=ip_address,
            limit_type='IP_HOURLY',
            limit=self.limits['unverified_ip_hourly'],
            window_hours=1
        )
    
    def check_email_limit(self, email: str) -> Dict[str, Any]:
        """
        Check email-based daily rate limit for verified users
        
        Args:
            email: User email address
            
        Returns:
            Dict with rate limit status
        """
        return self.db.check_rate_limit(
            identifier=email.lower(),
            limit_type='EMAIL_DAILY',
            limit=self.limits['verified_email_daily'],
            window_hours=24
        )
    
    def check_combined_limits(self, ip_address: str, email: str = None, 
                            verified: bool = False) -> Dict[str, Any]:
        """
        Check both IP and email limits as applicable
        
        Args:
            ip_address: Client IP address
            email: User email address (if available)
            verified: Whether user has verified email
            
        Returns:
            Dict with combined rate limit status
        """
        # Check IP limit for unverified users
        if not verified:
            ip_check = self.check_ip_limit(ip_address, verified=False)
            if not ip_check['allowed']:
                return {
                    'allowed': False,
                    'reason': 'IP rate limit exceeded',
                    'limit_type': 'ip_hourly',
                    'remaining': ip_check['remaining'],
                    'reset_time': ip_check.get('reset_time')
                }
        
        # Check email limit for verified users
        if verified and email:
            email_check = self.check_email_limit(email)
            if not email_check['allowed']:
                return {
                    'allowed': False,
                    'reason': 'Daily quota exceeded',
                    'limit_type': 'email_daily',
                    'remaining': email_check['remaining'],
                    'reset_time': email_check.get('reset_time')
                }
        
        # Calculate remaining quota
        if verified and email:
            email_check = self.check_email_limit(email)
            remaining = email_check['remaining']
            limit_type = 'email_daily'
        else:
            ip_check = self.check_ip_limit(ip_address, verified=False)
            remaining = ip_check['remaining']
            limit_type = 'ip_hourly'
        
        return {
            'allowed': True,
            'remaining': remaining,
            'limit_type': limit_type
        }
    
    def record_request(self, ip_address: str, email: str = None, 
                      action: str = 'photo_process', verified: bool = False) -> bool:
        """
        Record a request for rate limiting
        
        Args:
            ip_address: Client IP address
            email: User email address (if available)
            action: Type of action being performed
            verified: Whether user has verified email
            
        Returns:
            bool: True if request recorded successfully
        """
        success = True
        
        # Record IP-based request for unverified users
        if not verified:
            ip_success = self.db.record_request(
                identifier=ip_address,
                limit_type='IP_HOURLY',
                action=action,
                window_hours=1
            )
            success = success and ip_success
        
        # Record email-based request for verified users
        if verified and email:
            email_success = self.db.record_request(
                identifier=email.lower(),
                limit_type='EMAIL_DAILY',
                action=action,
                window_hours=24
            )
            success = success and email_success
        
        # Log the request
        self.db.log_request(
            ip_address=ip_address,
            email=email,
            action=action,
            success=True
        )
        
        return success
    
    def get_remaining_quota(self, ip_address: str, email: str = None, 
                          verified: bool = False) -> Dict[str, Any]:
        """
        Get remaining quota for user
        
        Args:
            ip_address: Client IP address
            email: User email address (if available)
            verified: Whether user has verified email
            
        Returns:
            Dict with quota information
        """
        if verified and email:
            # Verified users have daily email-based quota
            email_check = self.check_email_limit(email)
            return {
                'remaining': email_check['remaining'],
                'limit': self.limits['verified_email_daily'],
                'window': 'daily',
                'type': 'verified_user',
                'reset_time': email_check.get('reset_time')
            }
        else:
            # Unverified users have hourly IP-based quota
            ip_check = self.check_ip_limit(ip_address, verified=False)
            return {
                'remaining': ip_check['remaining'],
                'limit': self.limits['unverified_ip_hourly'],
                'window': 'hourly',
                'type': 'unverified_user',
                'reset_time': ip_check.get('reset_time')
            }
    
    def reset_daily_limits(self) -> int:
        """
        Reset daily limits (called by scheduled job at midnight UTC)
        Note: DynamoDB TTL handles this automatically, but this method
        can be used for manual resets if needed
        
        Returns:
            int: Number of limits reset
        """
        # TTL handles automatic cleanup, but we can implement manual reset if needed
        print("Daily limits are automatically reset by DynamoDB TTL")
        return 0
    
    def implement_exponential_backoff(self, identifier: str, 
                                    failure_type: str = 'otp_verification') -> Dict[str, Any]:
        """
        Implement exponential backoff for repeated failures
        
        Args:
            identifier: User identifier (email or IP)
            failure_type: Type of failure (otp_verification, login, etc.)
            
        Returns:
            Dict with backoff information
        """
        # Get failure count from last hour
        failure_count = self._get_failure_count(identifier, failure_type)
        
        if failure_count < self.limits['failed_login_backoff']:
            return {
                'backoff_required': False,
                'failure_count': failure_count
            }
        
        # Calculate exponential backoff delay
        # 2^(failures-5) minutes, capped at 60 minutes
        backoff_minutes = min(2 ** (failure_count - 5), 60)
        backoff_seconds = backoff_minutes * 60
        
        # Check if still in backoff period
        last_failure_time = self._get_last_failure_time(identifier, failure_type)
        if last_failure_time:
            time_since_failure = (datetime.now(timezone.utc) - last_failure_time).total_seconds()
            
            if time_since_failure < backoff_seconds:
                remaining_backoff = backoff_seconds - time_since_failure
                return {
                    'backoff_required': True,
                    'failure_count': failure_count,
                    'backoff_seconds': int(remaining_backoff),
                    'retry_after': (datetime.now(timezone.utc) + 
                                  timedelta(seconds=remaining_backoff)).isoformat()
                }
        
        return {
            'backoff_required': False,
            'failure_count': failure_count
        }
    
    def record_failure(self, identifier: str, failure_type: str = 'otp_verification') -> bool:
        """
        Record a failure for exponential backoff calculation
        
        Args:
            identifier: User identifier (email or IP)
            failure_type: Type of failure
            
        Returns:
            bool: True if failure recorded successfully
        """
        return self.db.record_request(
            identifier=identifier,
            limit_type=f'FAILURE_{failure_type.upper()}',
            action=f'failure_{failure_type}',
            window_hours=1
        )
    
    def _get_failure_count(self, identifier: str, failure_type: str) -> int:
        """Get failure count for identifier in last hour"""
        try:
            check_result = self.db.check_rate_limit(
                identifier=identifier,
                limit_type=f'FAILURE_{failure_type.upper()}',
                limit=100,  # High limit, we just want the count
                window_hours=1
            )
            
            # Calculate actual count from remaining
            return 100 - check_result['remaining']
            
        except Exception as e:
            print(f"Error getting failure count: {e}")
            return 0
    
    def _get_last_failure_time(self, identifier: str, failure_type: str) -> Optional[datetime]:
        """Get timestamp of last failure"""
        # This would require querying the rate limit record
        # For now, we'll use a simplified approach
        # In a full implementation, we'd store the last failure timestamp
        return None
    
    def get_rate_limit_status(self, ip_address: str, email: str = None, 
                            verified: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive rate limit status
        
        Args:
            ip_address: Client IP address
            email: User email address (if available)
            verified: Whether user has verified email
            
        Returns:
            Dict with comprehensive rate limit status
        """
        # Check current limits
        limit_check = self.check_combined_limits(ip_address, email, verified)
        
        # Get quota information
        quota_info = self.get_remaining_quota(ip_address, email, verified)
        
        # Check for exponential backoff (if email available)
        backoff_info = {'backoff_required': False}
        if email:
            backoff_info = self.implement_exponential_backoff(email, 'otp_verification')
        
        return {
            'allowed': limit_check['allowed'] and not backoff_info['backoff_required'],
            'rate_limit': limit_check,
            'quota': quota_info,
            'backoff': backoff_info,
            'user_type': 'verified' if verified else 'unverified'
        }


# Global instance
rate_limiter = None

def get_rate_limiter() -> RateLimitingService:
    """Get global rate limiting service instance"""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = RateLimitingService()
    return rate_limiter