"""Password hashing service for CHARACTER ENGINE backend.

This module implements secure password hashing using Argon2id.

Hashing parameters are selected per environment:

- PRODUCTION / DEVELOPMENT: OWASP-recommended Argon2id parameters
  (time_cost=3, memory_cost=256 MiB, parallelism=4).
- TEST: reduced-cost parameters so the test suite runs in seconds instead of
  minutes. The algorithm (Argon2id), hash length and salt length are identical,
  so every security property under test is preserved; only work factor differs.

The test profile is NEVER selected implicitly: it requires
``CHARACTER_ENGINE_ENV=test``.
"""

from typing import Dict

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from backend.config.config import Environment, get_config

# OWASP recommended parameters (production grade).
_PRODUCTION_PARAMS: Dict[str, int] = dict(
    time_cost=3,           # Number of iterations
    memory_cost=262144,    # 256 MiB memory
    parallelism=4,         # Number of parallel threads
    hash_len=32,           # Hash length in bytes
    salt_len=16,           # Salt length in bytes
)

# Reduced work factor for automated tests only. Same algorithm and output shape.
_TEST_PARAMS: Dict[str, int] = dict(
    time_cost=1,
    memory_cost=8192,      # 8 MiB memory
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


class PasswordService:
    """Password hashing and verification service."""

    _hashers: Dict[Environment, PasswordHasher] = {}

    @classmethod
    def _get_hasher(cls) -> PasswordHasher:
        """Return the Argon2id hasher for the current environment (cached)."""
        environment = get_config().environment
        hasher = cls._hashers.get(environment)
        if hasher is None:
            params = _TEST_PARAMS if environment == Environment.TEST else _PRODUCTION_PARAMS
            hasher = PasswordHasher(encoding="utf-8", **params)
            cls._hashers[environment] = hasher
        return hasher

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
        return PasswordService._get_hasher().hash(password)

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: Plain text password
            password_hash: Hashed password

        Returns:
            True if password matches hash, False otherwise

        Note:
            Argon2 verification is constant-time with respect to the hash and
            reads its parameters from the encoded hash, so hashes produced with
            any work factor verify correctly.
        """
        try:
            PasswordService._get_hasher().verify(password_hash, password)
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
        return PasswordService._get_hasher().check_needs_rehash(password_hash)
