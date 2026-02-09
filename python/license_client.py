"""
License Client for Suno Studio Pro
Handles communication with the payment/license server
"""

import json
import requests
import uuid
import hashlib
import platform
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class LicenseInfo:
    """License information structure"""
    license_key: str
    tier: str  # 'free', 'pro', 'lifetime', 'studio'
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    price_paid: float = 0.0
    currency: str = 'USD'
    status: str = 'active'  # 'active', 'pending', 'expired', 'revoked'
    activated: bool = False
    activation_date: Optional[str] = None
    expires_at: Optional[str] = None
    max_activations: int = 1
    current_activations: int = 0
    machine_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LicenseInfo':
        """Create from dictionary"""
        return cls(**data)
    
    def is_valid(self) -> bool:
        """Check if license is valid for current machine"""
        if self.status != 'active':
            return False
        
        if self.expires_at:
            from datetime import datetime
            expires = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            if datetime.now(expires.tzinfo) > expires:
                return False
        
        if self.activated and self.machine_id:
            # Check if this machine is activated
            current_machine_id = get_machine_id()
            return current_machine_id == self.machine_id
        
        return True
    
    def can_process_track(self) -> bool:
        """Check if license can process another track"""
        if self.tier == 'free':
            # Free tier limited to 5 tracks per month
            # This should be checked against usage tracking
            return True  # Actual check done elsewhere
        return True

@dataclass
class VerificationResult:
    """License verification result"""
    valid: bool
    license: Optional[LicenseInfo] = None
    message: str = ''
    error_code: Optional[str] = None
    server_response: Optional[Dict[str, Any]] = None

class LicenseClient:
    """Client for license server communication"""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.environ.get('LICENSE_SERVER_URL', 'http://localhost:3000')
        self.api_key = api_key or os.environ.get('LICENSE_API_KEY', '')
        self.machine_id = get_machine_id()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'SunoStudioPro/1.0 ({platform.system()})',
            'Content-Type': 'application/json'
        })
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def verify_license(self, license_key: str) -> VerificationResult:
        """
        Verify a license key with the server
        
        Args:
            license_key: The license key to verify
            
        Returns:
            VerificationResult with validity and license info
        """
        try:
            response = self.session.post(
                f'{self.base_url}/api/verify',
                json={
                    'license_key': license_key,
                    'machine_id': self.machine_id
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('valid'):
                    # License is valid
                    license_data = data.get('license', {})
                    license_info = LicenseInfo.from_dict({
                        'license_key': license_key,
                        'tier': license_data.get('tier', 'pro'),
                        'customer_email': license_data.get('customer_email'),
                        'customer_name': license_data.get('customer_name'),
                        'price_paid': license_data.get('price_paid', 0),
                        'currency': license_data.get('currency', 'USD'),
                        'status': license_data.get('status', 'active'),
                        'activated': True,
                        'activation_date': license_data.get('activation_date'),
                        'expires_at': license_data.get('expires_at'),
                        'max_activations': license_data.get('max_activations', 1),
                        'current_activations': license_data.get('current_activations', 0),
                        'machine_id': self.machine_id,
                        'metadata': license_data.get('metadata', {})
                    })
                    
                    return VerificationResult(
                        valid=True,
                        license=license_info,
                        message='License is valid',
                        server_response=data
                    )
                else:
                    # License invalid
                    return VerificationResult(
                        valid=False,
                        message=data.get('message', 'License verification failed'),
                        error_code=data.get('error_code'),
                        server_response=data
                    )
            else:
                # Server error
                error_msg = f'Server error: {response.status_code}'
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except:
                    pass
                
                return VerificationResult(
                    valid=False,
                    message=error_msg,
                    error_code=f'HTTP_{response.status_code}',
                    server_response=None
                )
                
        except requests.exceptions.Timeout:
            return VerificationResult(
                valid=False,
                message='Connection timeout',
                error_code='CONNECTION_TIMEOUT'
            )
        except requests.exceptions.ConnectionError:
            return VerificationResult(
                valid=False,
                message='Cannot connect to license server',
                error_code='CONNECTION_ERROR'
            )
        except Exception as e:
            logger.error(f'License verification error: {e}')
            return VerificationResult(
                valid=False,
                message=f'Verification error: {str(e)}',
                error_code='UNKNOWN_ERROR'
            )
    
    def activate_license(self, license_key: str, machine_name: str = None) -> Dict[str, Any]:
        """
        Activate a license on this machine
        
        Args:
            license_key: The license key to activate
            machine_name: Optional human-readable machine name
            
        Returns:
            Activation result
        """
        try:
            if not machine_name:
                machine_name = f'{platform.system()} {platform.release()}'
            
            response = self.session.post(
                f'{self.base_url}/api/activate',
                json={
                    'license_key': license_key,
                    'machine_id': self.machine_id,
                    'machine_name': machine_name
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    **response.json()
                }
            else:
                error_msg = f'Activation failed: {response.status_code}'
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except:
                    pass
                
                return {
                    'success': False,
                    'message': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f'License activation error: {e}')
            return {
                'success': False,
                'message': f'Activation error: {str(e)}'
            }
    
    def deactivate_license(self, license_key: str) -> Dict[str, Any]:
        """
        Deactivate a license on this machine
        
        Args:
            license_key: The license key to deactivate
            
        Returns:
            Deactivation result
        """
        try:
            response = self.session.post(
                f'{self.base_url}/api/deactivate',
                json={
                    'license_key': license_key,
                    'machine_id': self.machine_id
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    **response.json()
                }
            else:
                error_msg = f'Deactivation failed: {response.status_code}'
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except:
                    pass
                
                return {
                    'success': False,
                    'message': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f'License deactivation error: {e}')
            return {
                'success': False,
                'message': f'Deactivation error: {str(e)}'
            }
    
    def check_license_status(self, license_key: str) -> Dict[str, Any]:
        """
        Check license status without activation
        
        Args:
            license_key: The license key to check
            
        Returns:
            Status information
        """
        try:
            response = self.session.get(
                f'{self.base_url}/api/licenses/{license_key}',
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'license': response.json()
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'message': f'License not found or server error'
                }
                
        except Exception as e:
            logger.error(f'License status check error: {e}')
            return {
                'success': False,
                'message': f'Status check error: {str(e)}'
            }
    
    def create_checkout(self, tier: str, email: str, name: str = None) -> Dict[str, Any]:
        """
        Create a checkout for license purchase
        
        Args:
            tier: License tier ('pro', 'lifetime', 'studio')
            email: Customer email
            name: Customer name
            
        Returns:
            Checkout information with payment URL
        """
        try:
            response = self.session.post(
                f'{self.base_url}/api/checkout',
                json={
                    'tier': tier,
                    'email': email,
                    'name': name
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    **response.json()
                }
            else:
                error_msg = f'Checkout failed: {response.status_code}'
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except:
                    pass
                
                return {
                    'success': False,
                    'message': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f'Checkout creation error: {e}')
            return {
                'success': False,
                'message': f'Checkout error: {str(e)}'
            }
    
    def test_connection(self) -> bool:
        """Test connection to license server"""
        try:
            response = self.session.get(
                f'{self.base_url}/health',
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

def get_machine_id() -> str:
    """Generate a unique machine ID"""
    # Use platform-specific information to generate a machine ID
    # This is a simple implementation - in production you might want something more robust
    machine_info = {
        'node': platform.node(),
        'system': platform.system(),
        'release': platform.release(),
        'machine': platform.machine(),
        'processor': platform.processor()
    }
    
    # Create a hash of machine info
    machine_str = json.dumps(machine_info, sort_keys=True)
    machine_hash = hashlib.sha256(machine_str.encode()).hexdigest()[:32]
    
    return f'machine_{machine_hash}'

def save_license_locally(license_info: LicenseInfo, file_path: str) -> bool:
    """Save license information to local file"""
    try:
        license_dir = os.path.dirname(file_path)
        if license_dir and not os.path.exists(license_dir):
            os.makedirs(license_dir)
        
        with open(file_path, 'w') as f:
            json.dump(license_info.to_dict(), f, indent=2)
        
        logger.info(f'License saved to {file_path}')
        return True
    except Exception as e:
        logger.error(f'Error saving license: {e}')
        return False

def load_license_locally(file_path: str) -> Optional[LicenseInfo]:
    """Load license information from local file"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
            return LicenseInfo.from_dict(data)
    except Exception as e:
        logger.error(f'Error loading license: {e}')
    return None

def check_license_limits(license_info: LicenseInfo, usage_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Check if license usage is within limits
    
    Args:
        license_info: License information
        usage_data: Usage tracking data
        
    Returns:
        Tuple of (is_valid, message)
    """
    if license_info.tier == 'free':
        # Free tier: 5 tracks per month
        tracks_this_month = usage_data.get('tracks_this_month', 0)
        if tracks_this_month >= 5:
            return False, 'Free tier limit reached (5 tracks per month). Please upgrade.'
    
    # Other tiers have no limits
    return True, ''

# Default client instance
_default_client = None

def get_default_client() -> LicenseClient:
    """Get default license client instance"""
    global _default_client
    if _default_client is None:
        _default_client = LicenseClient()
    return _default_client

if __name__ == '__main__':
    # Test the license client
    client = LicenseClient()
    print(f'Machine ID: {client.machine_id}')
    print(f'Server connection: {client.test_connection()}')
    
    # Example usage
    if len(sys.argv) > 1:
        if sys.argv[1] == 'verify':
            if len(sys.argv) > 2:
                result = client.verify_license(sys.argv[2])
                print(f'Verification result: {result}')
        elif sys.argv[1] == 'activate':
            if len(sys.argv) > 2:
                result = client.activate_license(sys.argv[2])
                print(f'Activation result: {result}')