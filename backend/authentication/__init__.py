"""Authentication module for CHARACTER ENGINE backend.

This module contains authentication, credential, and session domain logic.
"""

from backend.authentication.password_service import PasswordService

__all__ = [
    "PasswordService"
]
