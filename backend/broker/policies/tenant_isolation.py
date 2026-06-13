"""
Middleware for tenant context and isolation
"""
from fastapi import Request
from typing import Optional
from contextvars import ContextVar

# ContextVar for thread-safe request-scoped tenant_id
_tenant_id_ctx: ContextVar[Optional[int]] = ContextVar('tenant_id', default=None)


class TenantContext:
    """Request-scoped tenant context for current request"""
    
    @property
    def tenant_id(self) -> Optional[int]:
        return _tenant_id_ctx.get()
    
    @tenant_id.setter
    def tenant_id(self, value: Optional[int]):
        _tenant_id_ctx.set(value)


# Global proxy for request-scoped context
tenant_context = TenantContext()


async def tenant_isolation_middleware(request: Request, call_next):
    """
    Middleware to extract and validate tenant context from JWT
    Ensures all database queries are scoped to tenant
    """
    # Reset context for each request (implicitly handled by ContextVar but explicit for clarity)
    _tenant_id_ctx.set(None)
    
    # Extract tenant_id from Bearer header or HttpOnly cookie
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    if not token:
        token = request.cookies.get("access_token")
    if token:
        try:
            from core.security.jwt import decode_access_token
            payload = decode_access_token(token)
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                _tenant_id_ctx.set(int(tenant_id))
        except Exception:
            pass
    
    response = await call_next(request)
    return response


def get_tenant_context() -> TenantContext:
    """Dependency to get current tenant context"""
    return tenant_context
