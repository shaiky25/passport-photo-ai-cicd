"""
DynamoDB Client for Email Validation System
Handles all database operations using AWS DynamoDB with single-table design
"""

import boto3
import hashlib
import time
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from botocore.exceptions import ClientError
import json
import os

class DynamoDBClient:
    """
    DynamoDB client for email validation system using single-table design
    
    Table Structure:
    - PK (Partition Key): Entity identifier (USER#hash, RATE#ip, LOG#date)
    - SK (Sort Key): Entity type/timestamp (PROFILE, OTP#timestamp, IP#date)
    - GSI1PK/GSI1SK: Global Secondary Index for alternative access patterns
    - TTL: Time-to-live for automatic cleanup
    """
    
    def __init__(self, table_name: str = None, region: str = 'us-east-1'):
        """Initialize DynamoDB client"""
        self.region = region
        self.table_name = table_name or os.getenv('DYNAMODB_TABLE_NAME', 'email-validation')
        
        # Initialize DynamoDB client
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
            self.table = self.dynamodb.Table(self.table_name)
            print(f"✅ DynamoDB client initialized for table: {self.table_name}")
        except Exception as e:
            print(f"❌ Error initializing DynamoDB: {e}")
            self.dynamodb = None
            self.table = None
    
    def _hash_email(self, email: str) -> str:
        """Hash email address for privacy"""
        return hashlib.sha256(email.lower().encode()).hexdigest()
    
    def _get_ttl_timestamp(self, days: int) -> int:
        """Get TTL timestamp for automatic cleanup"""
        return int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp())
    
    def _is_healthy(self) -> bool:
        """Check if DynamoDB connection is healthy"""
        if not self.table:
            return False
        
        try:
            # Simple health check - describe table
            self.table.table_status
            return True
        except Exception:
            return False
    
    # User Management
    def create_user(self, email: str) -> Dict[str, Any]:
        """Create a new user record"""
        if not self._is_healthy():
            raise Exception("DynamoDB connection not available")
        
        email_hash = self._hash_email(email)
        now = datetime.now(timezone.utc).isoformat()
        
        user_item = {
            'PK': f'USER#{email_hash}',
            'SK': 'PROFILE',
            'GSI1PK': 'USER',
            'GSI1SK': now,
            'email_hash': email_hash,
            'verified': False,
            'created_at': now,
            'last_activity': now,
            'verification_count': 0,
            'TTL': self._get_ttl_timestamp(90)  # Auto-delete after 90 days
        }
        
        try:
            # Use condition to prevent overwriting existing user
            self.table.put_item(
                Item=user_item,
                ConditionExpression='attribute_not_exists(PK)'
            )
            return user_item
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # User already exists, return existing user
                return self.get_user(email)
            raise e
    
    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        if not self._is_healthy():
            return None
        
        email_hash = self._hash_email(email)
        
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'USER#{email_hash}',
                    'SK': 'PROFILE'
                }
            )
            return response.get('Item')
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def update_user_verification(self, email: str, verified: bool = True) -> bool:
        """Update user verification status"""
        if not self._is_healthy():
            return False
        
        email_hash = self._hash_email(email)
        now = datetime.now(timezone.utc).isoformat()
        
        try:
            self.table.update_item(
                Key={
                    'PK': f'USER#{email_hash}',
                    'SK': 'PROFILE'
                },
                UpdateExpression='SET verified = :verified, last_activity = :now, verification_count = verification_count + :inc',
                ExpressionAttributeValues={
                    ':verified': verified,
                    ':now': now,
                    ':inc': 1
                }
            )
            return True
        except Exception as e:
            print(f"Error updating user verification: {e}")
            return False
    
    def update_user_activity(self, email: str) -> bool:
        """Update user last activity timestamp"""
        if not self._is_healthy():
            return False
        
        email_hash = self._hash_email(email)
        now = datetime.now(timezone.utc).isoformat()
        
        try:
            self.table.update_item(
                Key={
                    'PK': f'USER#{email_hash}',
                    'SK': 'PROFILE'
                },
                UpdateExpression='SET last_activity = :now, #ttl = :ttl',
                ExpressionAttributeNames={
                    '#ttl': 'TTL'  # TTL is a reserved keyword
                },
                ExpressionAttributeValues={
                    ':now': now,
                    ':ttl': self._get_ttl_timestamp(90)  # Reset TTL
                }
            )
            return True
        except Exception as e:
            print(f"Error updating user activity: {e}")
            return False
    
    # OTP Management
    def store_otp(self, email: str, otp_code: str, expires_minutes: int = 10) -> bool:
        """Store OTP with expiration"""
        if not self._is_healthy():
            return False
        
        email_hash = self._hash_email(email)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expires_minutes)
        
        otp_item = {
            'PK': f'USER#{email_hash}',
            'SK': f'OTP#{now.isoformat()}',
            'otp_code': otp_code,
            'expires_at': expires_at.isoformat(),
            'created_at': now.isoformat(),
            'attempts': 0,
            'verified': False,
            'TTL': int(expires_at.timestamp())  # Auto-delete when expired
        }
        
        try:
            self.table.put_item(Item=otp_item)
            return True
        except Exception as e:
            print(f"Error storing OTP: {e}")
            return False
    
    def verify_otp(self, email: str, otp_code: str) -> Dict[str, Any]:
        """Verify OTP code"""
        if not self._is_healthy():
            return {'success': False, 'error': 'Database unavailable'}
        
        email_hash = self._hash_email(email)
        now = datetime.now(timezone.utc)
        
        try:
            # Get all OTPs for this user (most recent first)
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'USER#{email_hash}',
                    ':sk': 'OTP#'
                },
                ScanIndexForward=False,  # Most recent first
                Limit=5  # Only check last 5 OTPs
            )
            
            for item in response.get('Items', []):
                # Check if OTP matches and hasn't expired
                expires_at = datetime.fromisoformat(item['expires_at'].replace('Z', '+00:00'))
                
                if (item['otp_code'] == otp_code and 
                    now < expires_at and 
                    not item['verified'] and 
                    item['attempts'] < 3):
                    
                    # Mark OTP as verified
                    self.table.update_item(
                        Key={
                            'PK': item['PK'],
                            'SK': item['SK']
                        },
                        UpdateExpression='SET verified = :verified, attempts = attempts + :inc',
                        ExpressionAttributeValues={
                            ':verified': True,
                            ':inc': 1
                        }
                    )
                    
                    return {'success': True, 'message': 'OTP verified successfully'}
                
                elif item['otp_code'] == otp_code and now >= expires_at:
                    return {'success': False, 'error': 'OTP has expired'}
                
                elif item['otp_code'] == otp_code and item['attempts'] >= 3:
                    return {'success': False, 'error': 'Too many attempts'}
            
            return {'success': False, 'error': 'Invalid OTP'}
            
        except Exception as e:
            print(f"Error verifying OTP: {e}")
            return {'success': False, 'error': 'Verification failed'}
    
    def get_otp_attempts(self, email: str) -> int:
        """Get number of OTP generation attempts in last hour"""
        if not self._is_healthy():
            return 0
        
        email_hash = self._hash_email(email)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND SK >= :sk',
                ExpressionAttributeValues={
                    ':pk': f'USER#{email_hash}',
                    ':sk': f'OTP#{one_hour_ago.isoformat()}'
                }
            )
            
            return len(response.get('Items', []))
            
        except Exception as e:
            print(f"Error getting OTP attempts: {e}")
            return 0
    
    # Rate Limiting
    def check_rate_limit(self, identifier: str, limit_type: str, limit: int, window_hours: int = 1) -> Dict[str, Any]:
        """Check if identifier has exceeded rate limit"""
        if not self._is_healthy():
            return {'allowed': True, 'remaining': limit}  # Allow if DB unavailable
        
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'RATE#{identifier}',
                    'SK': f'{limit_type}#{today}'
                }
            )
            
            item = response.get('Item')
            if not item:
                return {'allowed': True, 'remaining': limit - 1}
            
            # Check if within time window
            last_request = datetime.fromisoformat(item['last_request'].replace('Z', '+00:00'))
            if last_request < window_start:
                # Reset counter for new window
                return {'allowed': True, 'remaining': limit - 1}
            
            current_count = item.get('request_count', 0)
            if current_count >= limit:
                return {
                    'allowed': False, 
                    'remaining': 0,
                    'reset_time': (last_request + timedelta(hours=window_hours)).isoformat()
                }
            
            return {'allowed': True, 'remaining': limit - current_count - 1}
            
        except Exception as e:
            print(f"Error checking rate limit: {e}")
            return {'allowed': True, 'remaining': limit}  # Allow if error
    
    def record_request(self, identifier: str, limit_type: str, action: str, window_hours: int = 1) -> bool:
        """Record a request for rate limiting"""
        if not self._is_healthy():
            return True  # Don't block if DB unavailable
        
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        now = datetime.now(timezone.utc).isoformat()
        
        try:
            # Update rate limit counter
            self.table.update_item(
                Key={
                    'PK': f'RATE#{identifier}',
                    'SK': f'{limit_type}#{today}'
                },
                UpdateExpression='ADD request_count :inc SET last_request = :now, request_action = :action, #ttl = :ttl',
                ExpressionAttributeNames={
                    '#ttl': 'TTL'  # TTL is a reserved keyword
                },
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':now': now,
                    ':action': action,
                    ':ttl': self._get_ttl_timestamp(1)  # Auto-delete after 1 day
                }
            )
            return True
            
        except Exception as e:
            print(f"Error recording request: {e}")
            return False
    
    # Request Logging
    def log_request(self, ip_address: str, email: str = None, action: str = 'unknown', 
                   success: bool = True, user_agent: str = None) -> bool:
        """Log request for analytics and debugging"""
        if not self._is_healthy():
            return False
        
        now = datetime.now(timezone.utc)
        today = now.strftime('%Y-%m-%d')
        
        log_item = {
            'PK': f'LOG#{today}',
            'SK': f'{now.isoformat()}#{secrets.token_hex(8)}',
            'GSI1PK': f'IP#{ip_address}',
            'GSI1SK': now.isoformat(),
            'ip_address': ip_address,
            'request_action': action,
            'success': success,
            'created_at': now.isoformat(),
            'TTL': self._get_ttl_timestamp(30)  # Auto-delete after 30 days
        }
        
        if email:
            log_item['email_hash'] = self._hash_email(email)
        
        if user_agent:
            log_item['user_agent'] = user_agent[:500]  # Truncate long user agents
        
        try:
            self.table.put_item(Item=log_item)
            return True
        except Exception as e:
            print(f"Error logging request: {e}")
            return False
    
    # Utility Methods
    def generate_otp(self) -> str:
        """Generate cryptographically secure 6-digit OTP"""
        return ''.join(secrets.choice('0123456789') for _ in range(6))
    
    def cleanup_expired_records(self) -> int:
        """Manual cleanup (TTL handles this automatically, but useful for testing)"""
        if not self._is_healthy():
            return 0
        
        # TTL handles cleanup automatically, this is just for manual cleanup if needed
        # In production, this method might not be necessary
        print("TTL handles automatic cleanup - no manual cleanup needed")
        return 0
    
    def get_user_stats(self, email: str) -> Dict[str, Any]:
        """Get user statistics"""
        if not self._is_healthy():
            return {}
        
        user = self.get_user(email)
        if not user:
            return {}
        
        email_hash = self._hash_email(email)
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        try:
            # Get today's request count
            rate_response = self.table.get_item(
                Key={
                    'PK': f'RATE#{email_hash}',
                    'SK': f'EMAIL#{today}'
                }
            )
            
            request_count = 0
            if rate_response.get('Item'):
                request_count = rate_response['Item'].get('request_count', 0)
            
            return {
                'verified': user.get('verified', False),
                'created_at': user.get('created_at'),
                'last_activity': user.get('last_activity'),
                'verification_count': user.get('verification_count', 0),
                'daily_requests': request_count,
                'daily_limit': 20 if user.get('verified') else 3
            }
            
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {
                'verified': user.get('verified', False),
                'created_at': user.get('created_at'),
                'last_activity': user.get('last_activity')
            }


# Global instance
db_client = None

def get_db_client() -> DynamoDBClient:
    """Get global DynamoDB client instance"""
    global db_client
    if db_client is None:
        db_client = DynamoDBClient()
    return db_client

def init_db_client(table_name: str = None, region: str = 'us-east-1') -> DynamoDBClient:
    """Initialize DynamoDB client with custom settings"""
    global db_client
    db_client = DynamoDBClient(table_name, region)
    return db_client