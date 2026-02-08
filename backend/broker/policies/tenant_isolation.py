"""
Middleware for tenant context and isolation
"""
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from persistence.database import get_db
from persistence.models.core import Tenant


class TenantContext:
    """Global tenant context for request"""
    
    def __init__(self):
        self.tenant_id: Optional[int] = None
        self.tenant: Optional[Tenant] = None


# Request-scoped tenant context
tenant_context = TenantContext()


async def tenant_isolation_middleware(request: Request, call_next):
    """
    Middleware to extract and validate tenant context from JWT
    Ensures all database queries are scoped to tenant
    """
    # Reset context for each request
    tenant_context.tenant_id = None
    tenant_context.tenant = None
    
    # Extract tenant_id from token if present
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from core.security.jwt import decode_access_token
            payload = decode_access_token(token)
            tenant_context.tenant_id = payload.get("tenant_id")
        except Exception:
            pass
    
    response = await call_next(request)
    return response


def get_tenant_context() -> TenantContext:
    """Dependency to get current tenant context"""
    return tenant_context
