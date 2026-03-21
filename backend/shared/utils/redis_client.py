"""
Redis connection and utilities for caching and live state
"""
import redis.asyncio as aioredis
from typing import Optional
import json

from core.config.settings import settings


class RedisClient:
    """Redis client wrapper with connection pooling"""
    
    def __init__(self):
        self.pool: Optional[aioredis.ConnectionPool] = None
        self.client: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection pool"""
        self.pool = aioredis.ConnectionPool.from_url(
            settings.redis.url,
            max_connections=settings.redis.pool_size,
            decode_responses=True
        )
        self.client = aioredis.Redis(connection_pool=self.pool)
    
    async def disconnect(self):
        """Close Redis connections"""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self.client:
            await self.connect()
        return await self.client.get(key)
    
    async def set(self, key: str, value: str, expire: Optional[int] = None):
        """Set key-value pair with optional expiration (seconds)"""
        if not self.client:
            await self.connect()
        await self.client.set(key, value, ex=expire)
    
    async def delete(self, key: str):
        """Delete key"""
        if not self.client:
            await self.connect()
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            await self.connect()
        return await self.client.exists(key) > 0
    
    async def increment(self, key: str) -> int:
        """Increment counter"""
        if not self.client:
            await self.connect()
        return await self.client.incr(key)
    
    async def expire(self, key: str, seconds: int):
        """Set expiration on key"""
        if not self.client:
            await self.connect()
        await self.client.expire(key, seconds)
    
    async def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value"""
        value = await self.get(key)
        return json.loads(value) if value else None
    
    async def set_json(self, key: str, value: dict, expire: Optional[int] = None):
        """Set JSON value"""
        await self.set(key, json.dumps(value), expire)


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency for getting Redis client"""
    if not redis_client.client:
        await redis_client.connect()
    return redis_client
