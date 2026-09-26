"""Password hashing service for CHARACTER ENGINE backend.

This module implements secure password hashing using Argon2id.
"""

from typing import Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from backend.config.config import get_config


class PasswordService:
    """Password hashing and verification service."""
    
    # Argon2id configuration - OWASP recommended parameters
    _HASHER = PasswordHasher(
        time_cost=3,           # Number of iterations
        memory_cost=262144,    # 256 MB memory
        parallelism=4,         # Number of parallel threads
        hash_len=32,           # Hash length in bytes
        salt_len=16,           # Salt length in bytes
        encoding='utf-8'
    )
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using Argon2id.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
            
        Raises:
            ValueError: If password is empty or too long
        """
        config = get_config()
        
        # Validate password length
        if not password:
            raise ValueError("Password cannot be empty")
        
        if len(password) < config.security.password_min_length:
            raise ValueError(
                f"Password must be at least {config.security.password_min_length} characters"
            )
        
        if len(password) > config.security.password_max_length:
            raise ValueError(
                f"Password cannot exceed {config.security.password_max_length} characters"
            )
        
        # Hash password using Argon2id
        return PasswordService._HASHER.hash(password)
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against a hash.
        
        Args:
            password: Plain text password
            password_hash: Hashed password
            
        Returns:
            True if password matches hash, False otherwise
            
        Note:
            This method uses constant-time comparison to prevent timing attacks.
        """
        try:
            PasswordService._HASHER.verify(password_hash, password)
            return True
        except VerifyMismatchError:
            return False
        except Exception:
            # Return False for any verification error to prevent information leakage
            return False
    
    @staticmethod
    def check_needs_rehash(password_hash: str) -> bool:
        """Check if a password hash needs to be rehashed.
        
        Args:
            password_hash: Hashed password
            
        Returns:
            True if hash needs rehashing, False otherwise
            
        Note:
            This is useful when upgrading password hashing parameters.
        """
        return PasswordService._HASHER.check_needs_rehash(password_hash)