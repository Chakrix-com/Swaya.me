"""
Tier configuration management APIs (Super Admin only)
"""
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import require_super_admin
from persistence.database_async import get_async_db
from persistence.models.core import TierConfiguration, TierEnum

router = APIRouter()


class TierConfigResponse(BaseModel):
    tier: str
    max_participants: int
    max_questions: int
    max_concurrent_events: int
    features: List[str] = []


class TierConfigUpdateRequest(BaseModel):
    max_participants: int = Field(..., ge=1, le=1000000)
    max_questions: int = Field(..., ge=1, le=100000)
    max_concurrent_events: int = Field(..., ge=1, le=10000)
    features: List[str] = []


DEFAULTS = {
    TierEnum.FREE: {"max_participants": 50, "max_questions": 10, "max_concurrent_events": 1},
    TierEnum.BASIC: {"max_participants": 200, "max_questions": 30, "max_concurrent_events": 2},
    TierEnum.PRO: {"max_participants": 1000, "max_questions": 100, "max_concurrent_events": 5},
    TierEnum.ENTERPRISE: {"max_participants": 10000, "max_questions": 1000, "max_concurrent_events": 50},
}


def _parse_features(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        pass
    return []


@router.get("/tier-configs", response_model=List[TierConfigResponse])
async def list_tier_configs(
    _: object = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(TierConfiguration))
    existing = {row.tier: row for row in result.scalars().all()}

    payload: List[TierConfigResponse] = []
    for tier in TierEnum:
        config = existing.get(tier)
        if config:
            payload.append(
                TierConfigResponse(
                    tier=tier.value,
                    max_participants=config.max_participants,
                    max_questions=config.max_questions,
                    max_concurrent_events=config.max_concurrent_events,
                    features=_parse_features(config.features),
                )
            )
        else:
            defaults = DEFAULTS.get(tier, DEFAULTS[TierEnum.FREE])
            payload.append(
                TierConfigResponse(
                    tier=tier.value,
                    max_participants=defaults["max_participants"],
                    max_questions=defaults["max_questions"],
                    max_concurrent_events=defaults["max_concurrent_events"],
                    features=[],
                )
            )
    return payload


@router.put("/tier-configs/{tier}", response_model=TierConfigResponse)
async def update_tier_config(
    tier: str,
    request: TierConfigUpdateRequest,
    _: object = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        tier_enum = TierEnum(tier.lower())
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tier")

    result = await db.execute(select(TierConfiguration).filter(TierConfiguration.tier == tier_enum))
    config = result.scalar_one_or_none()

    if not config:
        config = TierConfiguration(
            tier=tier_enum,
            max_participants=request.max_participants,
            max_questions=request.max_questions,
            max_concurrent_events=request.max_concurrent_events,
            features=json.dumps(request.features or []),
        )
        db.add(config)
    else:
        config.max_participants = request.max_participants
        config.max_questions = request.max_questions
        config.max_concurrent_events = request.max_concurrent_events
        config.features = json.dumps(request.features or [])

    await db.commit()
    await db.refresh(config)

    return TierConfigResponse(
        tier=tier_enum.value,
        max_participants=config.max_participants,
        max_questions=config.max_questions,
        max_concurrent_events=config.max_concurrent_events,
        features=_parse_features(config.features),
    )
