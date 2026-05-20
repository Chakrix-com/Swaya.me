#!/usr/bin/env python3
"""
One-time AI Generate feature announcement email broadcast.
Targets all is_active=TRUE, is_email_verified=TRUE users in the production database.

Usage:
  # Dry run — no emails sent, just prints recipients and preview
  ENV_FILE=/www/wwwroot/swaya-live/backend/.env PYTHONPATH=. .venv/bin/python3 scripts/send_ai_feature_announcement.py --dry-run

  # Live send
  ENV_FILE=/www/wwwroot/swaya-live/backend/.env PYTHONPATH=. .venv/bin/python3 scripts/send_ai_feature_announcement.py
"""

import asyncio
import os
import sys

env_file = os.environ.get("ENV_FILE", ".env")
from dotenv import load_dotenv
load_dotenv(env_file, override=True)

from persistence.database import SessionLocal
from persistence.models.core import User
from core.auth.email_service import send_email

DRY_RUN = "--dry-run" in sys.argv

SUBJECT = "✨ Build your next quiz in seconds — AI is now in your hands"

HTML_BODY_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{subject}</title>
  <style>
    body {{ margin: 0; padding: 0; background: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1a1a1a; }}
    .wrapper {{ max-width: 580px; margin: 32px auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
    .header {{ background: #1677ff; padding: 28px 32px; }}
    .header h1 {{ margin: 0; color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }}
    .header p {{ margin: 4px 0 0; color: rgba(255,255,255,0.8); font-size: 13px; }}
    .body {{ padding: 32px; }}
    .greeting {{ font-size: 16px; margin: 0 0 16px; }}
    .intro {{ font-size: 15px; color: #444; margin: 0 0 20px; line-height: 1.6; }}
    .section-label {{ font-size: 12px; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: 0.8px; margin: 0 0 12px; }}
    .steps {{ margin: 0 0 28px; padding: 0; list-style: none; counter-reset: steps; }}
    .steps li {{ padding: 12px 0; border-bottom: 1px solid #f0f0f0; display: flex; gap: 12px; align-items: flex-start; }}
    .steps li:last-child {{ border-bottom: none; }}
    .step-num {{ background: #1677ff; color: #fff; font-size: 12px; font-weight: 700; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px; }}
    .step-text {{ font-size: 14px; color: #333; line-height: 1.5; }}
    .step-text code {{ background: #f0f5ff; color: #1677ff; padding: 1px 6px; border-radius: 4px; font-size: 13px; }}
    .benefits {{ margin: 0 0 28px; padding: 0; list-style: none; }}
    .benefits li {{ padding: 12px 0; border-bottom: 1px solid #f0f0f0; display: flex; gap: 12px; align-items: flex-start; }}
    .benefits li:last-child {{ border-bottom: none; }}
    .benefit-icon {{ font-size: 20px; flex-shrink: 0; width: 28px; text-align: center; margin-top: 1px; }}
    .benefit-text strong {{ display: block; font-size: 15px; color: #1a1a1a; margin-bottom: 2px; }}
    .benefit-text span {{ font-size: 13px; color: #666; line-height: 1.5; }}
    .cta-wrap {{ text-align: center; margin: 28px 0 8px; }}
    .cta {{ display: inline-block; background: #1677ff; color: #ffffff; text-decoration: none; padding: 13px 32px; border-radius: 6px; font-size: 15px; font-weight: 600; letter-spacing: 0.1px; }}
    .sign-off {{ font-size: 14px; color: #555; text-align: center; margin-top: 20px; line-height: 1.6; }}
    .footer {{ background: #fafafa; border-top: 1px solid #f0f0f0; padding: 20px 32px; text-align: center; }}
    .footer p {{ margin: 0; font-size: 12px; color: #999; line-height: 1.6; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>⚡ Generate with AI</h1>
      <p>Quiz building just got a whole lot faster.</p>
    </div>
    <div class="body">
      <p class="greeting">Hi {name},</p>
      <p class="intro">
        We've just rolled out <strong>Generate with AI</strong> for every Swaya.me user.
        Describe the quiz you want in plain language, and our AI builds the questions for you —
        complete with answer options and explanations.
      </p>

      <p class="section-label">Here's how it works</p>
      <ol class="steps">
        <li>
          <span class="step-num">1</span>
          <span class="step-text">Open any quiz or exam in the <strong>Quiz Builder</strong></span>
        </li>
        <li>
          <span class="step-num">2</span>
          <span class="step-text">Click the <code>⚡ Generate with AI</code> button</span>
        </li>
        <li>
          <span class="step-num">3</span>
          <span class="step-text">Type a prompt — e.g. <em>"10 MCQs on Indian history for high school students"</em></span>
        </li>
        <li>
          <span class="step-num">4</span>
          <span class="step-text">Review, edit if needed, and add them to your quiz in one click</span>
        </li>
      </ol>

      <p class="section-label">Why you'll love it</p>
      <ul class="benefits">
        <li>
          <span class="benefit-icon">⏱️</span>
          <span class="benefit-text">
            <strong>Save hours</strong>
            <span>Go from blank page to a full quiz in under a minute.</span>
          </span>
        </li>
        <li>
          <span class="benefit-icon">🌍</span>
          <span class="benefit-text">
            <strong>Any topic, any language</strong>
            <span>Science, law, HR compliance, trivia — just describe it in the language you teach in.</span>
          </span>
        </li>
        <li>
          <span class="benefit-icon">✏️</span>
          <span class="benefit-text">
            <strong>You stay in control</strong>
            <span>Every generated question is fully editable before it goes live.</span>
          </span>
        </li>
      </ul>

      <div class="cta-wrap">
        <a class="cta" href="https://www.swaya.me/dashboard">Open Quiz Builder &rarr;</a>
      </div>
      <p class="sign-off">
        As always, hit reply if you have feedback or questions — we read every message.<br><br>
        — The Swaya.me Team
      </p>
    </div>
    <div class="footer">
      <p>
        You're receiving this because you registered at Swaya.me.<br>
        &copy; 2026 Swaya.me &nbsp;&middot;&nbsp; <a href="https://www.swaya.me" style="color:#999;">www.swaya.me</a>
      </p>
    </div>
  </div>
</body>
</html>
"""


def get_greeting_name(full_name: str, email: str) -> str:
    if full_name and full_name.strip():
        return full_name.strip().split()[0]
    return email.split("@")[0]


async def main():
    with SessionLocal() as db:
        users = (
            db.query(User.email, User.full_name)
            .filter(User.is_active == True, User.is_email_verified == True)
            .order_by(User.id)
            .all()
        )

    print(f"\n{'DRY RUN — ' if DRY_RUN else ''}Sending to {len(users)} recipients\n")
    print(f"Subject : {SUBJECT}")
    print(f"From    : Swaya.me <info@chakrix.com>")
    print("-" * 60)

    if DRY_RUN:
        print("\nRECIPIENT LIST:")
        for i, u in enumerate(users, 1):
            name = get_greeting_name(u.full_name or "", u.email)
            print(f"  {i:>3}. {u.email:<45}  greeting: Hi {name},")
        print("\n--- EMAIL PREVIEW (first recipient) ---\n")
        sample = users[0]
        name = get_greeting_name(sample.full_name or "", sample.email)
        body = HTML_BODY_TEMPLATE.format(subject=SUBJECT, name=name)
        import re
        text = re.sub(r'<[^>]+>', '', body)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        print(text[:2000])
        print("\n[DRY RUN complete — no emails sent]")
        return

    sent = 0
    failed = 0
    for u in users:
        name = get_greeting_name(u.full_name or "", u.email)
        html = HTML_BODY_TEMPLATE.format(subject=SUBJECT, name=name)
        ok = await send_email(
            subject=SUBJECT,
            recipients=[u.email.lower()],
            html_body=html,
        )
        status = "✓ sent" if ok else "✗ failed"
        print(f"  {status}  {u.email}")
        if ok:
            sent += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"Done.  Sent: {sent}  |  Failed: {failed}  |  Total: {sent + failed}")
    if failed:
        print("Check logs above for failed addresses.")


if __name__ == "__main__":
    asyncio.run(main())
