"""
Tier management service - quota tracking and enforcement
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any
from datetime import datetime, timedelta
import json

from persistence.models.core import Tenant, TierConfiguration, TierEnum
from shared.utils.redis_client import RedisClient


class TierService:
    """Service for managing tier limits and quotas"""
    
    def __init__(self, redis: RedisClient):
        self.redis = redis
    
    async def get_tier_config(self, db: AsyncSession, tier: TierEnum) -> Dict[str, Any]:
        """Get tier configuration — cached in Redis for 5 minutes to avoid DB hit on every join."""
        cache_key = f"tier_config:{tier.value}"
        cached = await self.redis.get_json(cache_key)
        if cached:
            return cached

        result = await db.execute(
            select(TierConfiguration).filter(TierConfiguration.tier == tier)
        )
        config = result.scalar_one_or_none()

        if not config:
            data = self._get_default_limits(tier)
        else:
            features = None
            if config.features:
                try:
                    features = json.loads(config.features)
                except Exception:
                    features = config.features
            data = {
                "tier": config.tier.value,
                "max_participants": config.max_participants,
                "max_questions": config.max_questions,
                "max_concurrent_events": config.max_concurrent_events,
                "features": features,
            }

        await self.redis.set_json(cache_key, data, expire=300)  # 5-minute TTL
        return data
    
    def _get_default_limits(self, tier: TierEnum) -> Dict[str, Any]:
        """Get default limits for tier"""
        limits = {
            TierEnum.FREE: {
                "max_participants": 50,
                "max_questions": 10,
                "max_concurrent_events": 1
            },
            TierEnum.BASIC: {
                "max_participants": 200,
                "max_questions": 30,
                "max_concurrent_events": 2
            },
            TierEnum.PRO: {
                "max_participants": 2000,
                "max_questions": 100,
                "max_concurrent_events": 5
            },
            TierEnum.ENTERPRISE: {
                "max_participants": 10000,
                "max_questions": 1000,
                "max_concurrent_events": 50
            }
        }
        
        return {
            "tier": tier.value,
            **limits.get(tier, limits[TierEnum.FREE]),
            "features": None
        }

    async def _resolve_limits(self, db: AsyncSession, tier: TierEnum) -> Dict[str, Any]:
        """Resolve effective limits from DB config with fallback defaults."""
        return await self.get_tier_config(db, tier)
    
    async def check_participant_limit(
        self,
        db: AsyncSession,
        tenant_id: int,
        session_id: int,
        tier: TierEnum
    ) -> bool:
        """Check if tenant can add more participants to session"""
        config = await self._resolve_limits(db, tier)
        max_participants = config["max_participants"]
        
        # Get current participant count from Redis
        key = f"session:{session_id}:participants:count"
        count = await self.redis.get(key)
        current_count = int(count) if count else 0
        
        return current_count < max_participants
    
    async def check_question_limit(
        self,
        db: AsyncSession,
        tenant_id: int,
        quiz_id: int,
        tier: TierEnum,
        question_count: int
    ) -> bool:
        """Check if quiz can have more questions"""
        config = await self._resolve_limits(db, tier)
        max_questions = config["max_questions"]
        
        return question_count < max_questions
    
    async def check_concurrent_events_limit(
        self,
        db: AsyncSession,
        tenant_id: int,
        tier: TierEnum
    ) -> bool:
        """Check if tenant can create more concurrent events"""
        from persistence.models.quiz import QuizSession, QuizSessionStatus
        
        config = await self._resolve_limits(db, tier)
        max_concurrent = config["max_concurrent_events"]
        
        # Count only currently open sessions.
        # Using session status is more reliable than Event.join_code, which may linger.
        result = await db.execute(
            select(func.count(QuizSession.id)).filter(
                QuizSession.tenant_id == tenant_id,
                QuizSession.status.in_([QuizSessionStatus.CREATED, QuizSessionStatus.ACTIVE])
            )
        )
        active_count = result.scalar()
        
        return active_count < max_concurrent
    
    async def increment_participant_count(self, session_id: int):
        """Increment participant count for session"""
        key = f"session:{session_id}:participants:count"
        await self.redis.increment(key)
        await self.redis.expire(key, 86400)  # 24 hours
    
    async def decrement_participant_count(self, session_id: int):
        """Decrement participant count for session"""
        key = f"session:{session_id}:participants:count"
        count = await self.redis.get(key)
        if count and int(count) > 0:
            await self.redis.client.decr(key)


async def seed_tier_configurations(db: AsyncSession):
    """Seed default tier configurations"""
    from sqlalchemy.ext.asyncio import AsyncSession
    
    tiers = [
        TierConfiguration(
            tier=TierEnum.FREE,
            max_participants=50,
            max_questions=10,
            max_concurrent_events=1,
            features=None
        ),
        TierConfiguration(
            tier=TierEnum.BASIC,
            max_participants=200,
            max_questions=30,
            max_concurrent_events=2,
            features=None
        ),
        TierConfiguration(
            tier=TierEnum.PRO,
            max_participants=1000,
            max_questions=100,
            max_concurrent_events=5,
            features=None
        ),
        TierConfiguration(
            tier=TierEnum.ENTERPRISE,
            max_participants=10000,
            max_questions=1000,
            max_concurrent_events=50,
            features=None
        )
    ]
    
    for tier_config in tiers:
        result = await db.execute(
            select(TierConfiguration).filter(
                TierConfiguration.tier == tier_config.tier
            )
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            db.add(tier_config)
    
    await db.commit()
