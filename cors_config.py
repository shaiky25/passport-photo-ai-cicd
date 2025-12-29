"""
CORS Configuration Manager for Passport Photo AI - Enhanced Backend
Handles environment-specific CORS settings with advanced validation
"""
import os
from dataclasses import dataclass
from typing import List

@dataclass
class CORSConfig:
    allowed_origins: List[str]
    allowed_methods: List[str]
    allowed_headers: List[str]
    expose_headers: List[str]
    allow_credentials: bool
    max_age: int

class CORSConfigManager:
    def __init__(self, app):
        self.app = app
        self.config = self._create_config()
        print(f"✅ Enhanced CORS configured for origins: {self.config.allowed_origins}")
    
    def _get_allowed_origins(self):
        """Get allowed origins from environment or use defaults"""
        env_origins = os.environ.get('ALLOWED_ORIGINS', '')
        
        if env_origins:
            origins = [origin.strip() for origin in env_origins.split(',')]
            print(f"🌐 Using CORS origins from environment: {origins}")
            return origins
        
        # Default origins for production
        default_origins = [
            'https://main.d3gelc4wjo7dl.amplifyapp.com',  # Amplify frontend
            'http://localhost:3000',  # Local development
            'http://localhost:3001',  # Alternative local port
            'http://localhost:5173',  # Vite dev server
        ]
        
        print(f"🌐 Using default CORS origins: {default_origins}")
        return default_origins
    
    def _create_config(self):
        """Create enhanced CORS configuration"""
        return CORSConfig(
            allowed_origins=self._get_allowed_origins(),
            allowed_methods=['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'],
            allowed_headers=[
                'Content-Type', 
                'Authorization', 
                'X-Requested-With',
                'Accept',
                'Origin',
                'Cache-Control',
                'X-File-Name'
            ],
            expose_headers=['Content-Type', 'Content-Length', 'X-Request-ID'],
            allow_credentials=False,
            max_age=86400  # 24 hours preflight cache
        )
    
    def validate_configuration(self):
        """Validate CORS configuration"""
        issues = []
        warnings = []
        
        # Check for wildcard in production
        if '*' in self.config.allowed_origins:
            env = os.environ.get('FLASK_ENV', 'production')
            if env == 'production':
                issues.append("Wildcard origin (*) should not be used in production")
            else:
                warnings.append("Wildcard origin (*) detected in non-production environment")
        
        # Check for localhost in production
        localhost_origins = [o for o in self.config.allowed_origins if 'localhost' in o or '127.0.0.1' in o]
        if localhost_origins:
            env = os.environ.get('FLASK_ENV', 'production')
            if env == 'production':
                warnings.append(f"Localhost origins detected in production: {localhost_origins}")
        
        # Check for HTTP origins with HTTPS frontend
        http_origins = [o for o in self.config.allowed_origins if o.startswith('http://')]
        https_origins = [o for o in self.config.allowed_origins if o.startswith('https://')]
        
        if http_origins and https_origins:
            warnings.append("Mixed HTTP/HTTPS origins may cause issues with some browsers")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'environment': os.environ.get('FLASK_ENV', 'production')
        }
    
    def add_cors_headers(self, response):
        """Add CORS headers to response with enhanced logic"""
        # Get the request origin
        request_origin = None
        if hasattr(response, 'request') and response.request:
            request_origin = response.request.headers.get('Origin')
        
        # Set appropriate origin header
        if request_origin and request_origin in self.config.allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = request_origin
        elif '*' in self.config.allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = '*'
        elif self.config.allowed_origins:
            # Fallback to first allowed origin
            response.headers['Access-Control-Allow-Origin'] = self.config.allowed_origins[0]
        
        # Add other CORS headers if not present
        if 'Access-Control-Allow-Methods' not in response.headers:
            response.headers['Access-Control-Allow-Methods'] = ', '.join(self.config.allowed_methods)
        
        if 'Access-Control-Allow-Headers' not in response.headers:
            response.headers['Access-Control-Allow-Headers'] = ', '.join(self.config.allowed_headers)
        
        if 'Access-Control-Expose-Headers' not in response.headers:
            response.headers['Access-Control-Expose-Headers'] = ', '.join(self.config.expose_headers)
        
        if 'Access-Control-Max-Age' not in response.headers:
            response.headers['Access-Control-Max-Age'] = str(self.config.max_age)
        
        # Add request ID for debugging
        if 'X-Request-ID' not in response.headers:
            import uuid
            response.headers['X-Request-ID'] = str(uuid.uuid4())[:8]
        
        return response

def get_cors_manager(app):
    """Factory function to create enhanced CORS manager"""
    return CORSConfigManager(app)