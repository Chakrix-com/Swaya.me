"""
Proctoring context resolver — merges platform rules, tenant overrides, and quiz overrides.
"""
import hashlib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from persistence.models.proctoring import PlatformProctoringRule, TenantProctoringPolicy
from features.proctoring.schemas import ProctoringContext, ResolvedRule, ResolvedRuleSet

TIER_ORDER = {"free": 0, "basic": 1, "pro": 2, "enterprise": 3}

DEFAULT_ESCALATION = {
    "lock_on_violation_count": 3,
    "auto_submit_on_lock": False,
}


def _tier_gte(tenant_tier: str, rule_tier: str) -> bool:
    return TIER_ORDER.get(tenant_tier, 0) >= TIER_ORDER.get(rule_tier, 0)


def _context_hash(context: ProctoringContext) -> str:
    key = f"{context.quiz_type}:{context.tier}:{context.host_enabled}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


class ProctoringContextResolver:

    async def resolve(
        self,
        context: ProctoringContext,
        quiz_proctoring_policy: dict | None,
        db: AsyncSession,
        redis: "RedisClient",
    ) -> ResolvedRuleSet:
        if not context.host_enabled:
            return ResolvedRuleSet(
                enabled=False,
                rules=[],
                escalation=DEFAULT_ESCALATION,
                webcam_required=False,
            )

        policy_hash = hashlib.md5(
            json.dumps(quiz_proctoring_policy or {}, sort_keys=True).encode()
        ).hexdigest()[:8]
        cache_key = f"proctor:rules:{context.quiz_id}:{_context_hash(context)}:{policy_hash}"
        try:
            cached = await redis.get(cache_key)
            if cached:
                return ResolvedRuleSet.model_validate_json(cached)
        except Exception:
            pass

        platform_rules = await self._load_platform_rules(context, db)
        tenant_overrides = await self._load_tenant_policy(context.tenant_id, db)
        quiz_policy = quiz_proctoring_policy or {}

        merged = self._merge(platform_rules, tenant_overrides, quiz_policy, context)

        try:
            await redis.set(cache_key, merged.model_dump_json(), expire=3600)
        except Exception:
            pass

        return merged

    async def _load_platform_rules(
        self, context: ProctoringContext, db: AsyncSession
    ) -> list[PlatformProctoringRule]:
        result = await db.execute(
            select(PlatformProctoringRule).where(PlatformProctoringRule.is_active == True)
        )
        return result.scalars().all()

    async def _load_tenant_policy(
        self, tenant_id: int, db: AsyncSession
    ) -> dict[str, TenantProctoringPolicy]:
        result = await db.execute(
            select(TenantProctoringPolicy).where(TenantProctoringPolicy.tenant_id == tenant_id)
        )
        policies = result.scalars().all()
        return {p.rule_id: p for p in policies}

    def _merge(
        self,
        platform_rules: list[PlatformProctoringRule],
        tenant_overrides: dict,
        quiz_policy: dict,
        context: ProctoringContext,
    ) -> ResolvedRuleSet:
        result = []
        rules_policy = quiz_policy.get("rules", {})
        escalation = {**DEFAULT_ESCALATION, **quiz_policy.get("escalation", {})}

        for rule in platform_rules:
            if not _tier_gte(context.tier, rule.tier_minimum):
                continue

            applies_quiz_types = rule.applies_to.get("quiz_types", [])
            if context.quiz_type not in applies_quiz_types and "all" not in applies_quiz_types:
                continue

            tenant_policy = tenant_overrides.get(rule.rule_id)
            if tenant_policy and not tenant_policy.is_enabled:
                continue

            quiz_rule = rules_policy.get(rule.rule_id, {})
            if not quiz_rule.get("enabled", True):
                continue

            config = {**rule.default_config}
            if tenant_policy and tenant_policy.config_override:
                config.update(tenant_policy.config_override)
            config.update({k: v for k, v in quiz_rule.items() if k != "enabled"})

            result.append(ResolvedRule(
                rule_id=rule.rule_id,
                display_name=rule.display_name,
                severity=rule.severity,
                is_silent=rule.is_silent,
                config=config,
            ))

        webcam_required = any(r.rule_id == "webcam_monitoring" for r in result)

        return ResolvedRuleSet(
            enabled=True,
            rules=result,
            escalation=escalation,
            webcam_required=webcam_required,
        )
