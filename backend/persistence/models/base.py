"""
Base model with common fields for all entities
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declared_attr


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TenantMixin:
    """Mixin for tenant isolation"""
    
    @declared_attr
    def tenant_id(cls):
        from sqlalchemy import Column, Integer, ForeignKey
        return Column(Integer, ForeignKey('tenants.id'), nullable=False, index=True)
