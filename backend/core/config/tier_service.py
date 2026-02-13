"""
Tier management service - quota tracking and enforcement
"""
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timedelta

from persistence.models.core import Tenant, TierConfiguration, TierEnum
from shared.utils.redis_client import RedisClient


class TierService:
    """Service for managing tier limits and quotas"""
    
    def __init__(self, redis: RedisClient):
        self.redis = redis
    
    async def get_tier_config(self, db: Session, tier: TierEnum) -> Dict[str, Any]:
        """Get tier configuration"""
        config = db.query(TierConfiguration).filter(
            TierConfiguration.tier == tier
        ).first()
        
        if not config:
            # Return default limits if not configured
            return self._get_default_limits(tier)
        
        return {
            "tier": config.tier.value,
            "max_participants": config.max_participants,
            "max_questions": config.max_questions,
            "max_concurrent_events": config.max_concurrent_events,
            "features": config.features
        }
    
    def _get_default_limits(self, tier: TierEnum) -> Dict[str, Any]:
        """Get default limits for tier"""
        limits = {
            TierEnum.FREE: {
                "max_participants": 50,
                "max_questions": 10,
                "max_concurrent_events": 1
            },
            TierEnum.PRO: {
                "max_participants": 1000,
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
    
    async def check_participant_limit(
        self,
        tenant_id: int,
        session_id: int,
        tier: TierEnum
    ) -> bool:
        """Check if tenant can add more participants to session"""
        config = self._get_default_limits(tier)
        max_participants = config["max_participants"]
        
        # Get current participant count from Redis
        key = f"session:{session_id}:participants:count"
        count = await self.redis.get(key)
        current_count = int(count) if count else 0
        
        return current_count < max_participants
    
    async def check_question_limit(
        self,
        tenant_id: int,
        quiz_id: int,
        tier: TierEnum,
        question_count: int
    ) -> bool:
        """Check if quiz can have more questions"""
        config = self._get_default_limits(tier)
        max_questions = config["max_questions"]
        
        return question_count < max_questions
    
    async def check_concurrent_events_limit(
        self,
        db: Session,
        tenant_id: int,
        tier: TierEnum
    ) -> bool:
        """Check if tenant can create more concurrent events"""
        from persistence.models.core import Event
        
        config = self._get_default_limits(tier)
        max_concurrent = config["max_concurrent_events"]
        
        # Count only ACTIVE events (events with a join_code indicate a running session)
        active_count = db.query(Event).filter(
            Event.tenant_id == tenant_id,
            Event.join_code.isnot(None)
        ).count()
        
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


async def seed_tier_configurations(db: Session):
    """Seed default tier configurations"""
    tiers = [
        TierConfiguration(
            tier=TierEnum.FREE,
            max_participants=50,
            max_questions=10,
            max_concurrent_events=1,
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
        existing = db.query(TierConfiguration).filter(
            TierConfiguration.tier == tier_config.tier
        ).first()
        
        if not existing:
            db.add(tier_config)
    
    db.commit()
