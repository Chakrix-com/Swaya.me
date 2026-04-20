"""
Platform proctoring rule definitions — seeded once on startup.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from persistence.models.proctoring import PlatformProctoringRule

PLATFORM_RULES = [
    {
        "rule_id": "fullscreen_enforce",
        "display_name": "Fullscreen Enforcement",
        "description": "Forces participant to stay in fullscreen mode during the exam.",
        "tier_minimum": "free",
        "applies_to": {"quiz_types": ["exam", "offline_poll", "quiz"], "question_types": ["all"]},
        "config_schema": {"type": "object", "properties": {"re_prompt_interval_sec": {"type": "integer"}}},
        "default_config": {"re_prompt_interval_sec": 30},
        "severity": "warn",
        "is_silent": False,
    },
    {
        "rule_id": "tab_switch_detect",
        "display_name": "Tab Switch Detection",
        "description": "Detects when participant switches away from the exam tab.",
        "tier_minimum": "free",
        "applies_to": {"quiz_types": ["exam", "offline_poll", "quiz"], "question_types": ["all"]},
        "config_schema": {"type": "object", "properties": {"max_switches": {"type": "integer"}}},
        "default_config": {"max_switches": 3},
        "severity": "warn",
        "is_silent": False,
    },
    {
        "rule_id": "copy_paste_block",
        "display_name": "Copy-Paste Block",
        "description": "Prevents copy and paste in text answer fields.",
        "tier_minimum": "free",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["paragraph", "single_line", "one_word"]},
        "config_schema": {},
        "default_config": {},
        "severity": "warn",
        "is_silent": False,
    },
    {
        "rule_id": "multi_tab_detect",
        "display_name": "Multi-Tab Detection",
        "description": "Silently locks session if exam is opened in multiple tabs.",
        "tier_minimum": "free",
        "applies_to": {"quiz_types": ["exam", "offline_poll", "quiz"], "question_types": ["all"]},
        "config_schema": {},
        "default_config": {},
        "severity": "lock",
        "is_silent": True,
    },
    {
        "rule_id": "right_click_block",
        "display_name": "Right-Click Block",
        "description": "Disables right-click context menu during exam.",
        "tier_minimum": "free",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["all"]},
        "config_schema": {},
        "default_config": {},
        "severity": "warn",
        "is_silent": False,
    },
    {
        "rule_id": "bot_signal_detect",
        "display_name": "Bot Signal Detection",
        "description": "Detects WebDriver/automation tools and silently locks session.",
        "tier_minimum": "free",
        "applies_to": {"quiz_types": ["exam", "offline_poll", "quiz"], "question_types": ["all"]},
        "config_schema": {"type": "object", "properties": {"block_on_detect": {"type": "boolean"}}},
        "default_config": {"block_on_detect": True},
        "severity": "lock",
        "is_silent": True,
    },
    {
        "rule_id": "honeypot_traps",
        "display_name": "Honeypot Traps",
        "description": "Invisible traps that catch AI-assisted or automated submissions.",
        "tier_minimum": "free",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["mcq", "paragraph", "single_line", "one_word"]},
        "config_schema": {},
        "default_config": {},
        "severity": "lock",
        "is_silent": True,
    },
    {
        "rule_id": "question_randomization",
        "display_name": "Question Randomization",
        "description": "Shuffles question order per participant to prevent sharing.",
        "tier_minimum": "basic",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["all"]},
        "config_schema": {},
        "default_config": {},
        "severity": "warn",
        "is_silent": False,
    },
    {
        "rule_id": "option_randomization",
        "display_name": "Option Randomization",
        "description": "Shuffles MCQ option order per participant.",
        "tier_minimum": "basic",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["mcq"]},
        "config_schema": {},
        "default_config": {},
        "severity": "warn",
        "is_silent": False,
    },
    {
        "rule_id": "answer_timing_enforce",
        "display_name": "Minimum Answer Time",
        "description": "Flags answers submitted suspiciously quickly.",
        "tier_minimum": "basic",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["mcq", "paragraph", "single_line", "one_word", "word_cloud"]},
        "config_schema": {"type": "object", "properties": {"min_ms_per_word": {"type": "integer"}}},
        "default_config": {"min_ms_per_word": 150},
        "severity": "warn",
        "is_silent": True,
    },
    {
        "rule_id": "behavioral_biometrics",
        "display_name": "Behavioral Biometrics",
        "description": "Analyzes mouse, keystroke, and scroll patterns to detect bots.",
        "tier_minimum": "pro",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["paragraph", "single_line", "one_word"]},
        "config_schema": {},
        "default_config": {"sample_interval_ms": 500, "batch_interval_sec": 10, "flag_threshold": 40, "lock_threshold": 20},
        "severity": "warn",
        "is_silent": True,
    },
    {
        "rule_id": "browser_fingerprint_bind",
        "display_name": "Browser Fingerprint Binding",
        "description": "Locks session if browser fingerprint changes mid-exam.",
        "tier_minimum": "pro",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["all"]},
        "config_schema": {},
        "default_config": {},
        "severity": "lock",
        "is_silent": True,
    },
    {
        "rule_id": "ip_bind",
        "display_name": "IP Address Binding",
        "description": "Locks session if IP address changes mid-exam.",
        "tier_minimum": "pro",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["all"]},
        "config_schema": {},
        "default_config": {},
        "severity": "lock",
        "is_silent": True,
    },
    {
        "rule_id": "steg_watermark",
        "display_name": "Steganographic Watermark",
        "description": "Embeds invisible participant ID in question text for leak tracing.",
        "tier_minimum": "pro",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["all"]},
        "config_schema": {},
        "default_config": {},
        "severity": "warn",
        "is_silent": True,
    },
    {
        "rule_id": "devtools_detect",
        "display_name": "DevTools Detection",
        "description": "Detects open browser developer tools.",
        "tier_minimum": "pro",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["all"]},
        "config_schema": {"type": "object", "properties": {"size_threshold_px": {"type": "integer"}}},
        "default_config": {"size_threshold_px": 160},
        "severity": "warn",
        "is_silent": True,
    },
    {
        "rule_id": "webcam_monitoring",
        "display_name": "Webcam Monitoring",
        "description": "Requires webcam access; monitors face presence and gaze.",
        "tier_minimum": "pro",
        "applies_to": {"quiz_types": ["exam", "offline_poll"], "question_types": ["all"]},
        "config_schema": {},
        "default_config": {
            "snapshot_interval_sec": 30,
            "face_absent_warn_sec": 10,
            "gaze_away_warn_sec": 5,
            "require_photo_id": False,
        },
        "severity": "warn",
        "is_silent": False,
    },
    {
        "rule_id": "canvas_rendering",
        "display_name": "Canvas Question Rendering",
        "description": "Renders questions on HTML canvas to prevent DOM scraping.",
        "tier_minimum": "enterprise",
        "applies_to": {"quiz_types": ["exam"], "question_types": ["mcq"]},
        "config_schema": {},
        "default_config": {},
        "severity": "warn",
        "is_silent": False,
    },
]


async def seed_platform_rules(db: AsyncSession) -> None:
    """Idempotent upsert of all platform proctoring rules."""
    for rule_data in PLATFORM_RULES:
        result = await db.execute(
            select(PlatformProctoringRule).where(PlatformProctoringRule.rule_id == rule_data["rule_id"])
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            db.add(PlatformProctoringRule(
                rule_id=rule_data["rule_id"],
                display_name=rule_data["display_name"],
                description=rule_data.get("description"),
                applies_to=rule_data["applies_to"],
                tier_minimum=rule_data["tier_minimum"],
                config_schema=rule_data.get("config_schema", {}),
                default_config=rule_data["default_config"],
                severity=rule_data["severity"],
                is_silent=rule_data["is_silent"],
                is_active=True,
            ))
        else:
            # Update display_name and default_config in case they changed
            existing.display_name = rule_data["display_name"]
            existing.default_config = rule_data["default_config"]
            existing.applies_to = rule_data["applies_to"]
    await db.commit()
