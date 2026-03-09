"""
Custom exception classes for authentication
"""


class AuthenticationError(Exception):
    """Base authentication error"""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password"""
    pass


class InvalidTokenError(AuthenticationError):
    """Invalid or malformed token"""
    pass


class ExpiredTokenError(AuthenticationError):
    """Token has expired"""
    pass


class InsufficientPermissionsError(AuthenticationError):
    """User lacks required permissions"""
    pass


class UserNotFoundError(AuthenticationError):
    """User not found"""
    pass


class TenantNotFoundError(AuthenticationError):
    """Tenant not found"""
    pass


class DuplicateUserError(Exception):
    """User with email already exists"""
    pass


class EmailNotVerifiedError(AuthenticationError):
    """Email address has not been verified"""
    pass
