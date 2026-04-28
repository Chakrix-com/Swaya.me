#!/usr/bin/env python3
"""
One-time proctoring announcement email broadcast.
Targets all is_active=TRUE, is_email_verified=TRUE users in the production database.

Usage:
  # Dry run — no emails sent, just prints recipients and preview
  ENV_FILE=/www/wwwroot/swaya-live/backend/.env PYTHONPATH=. .venv/bin/python3 scripts/send_proctoring_announcement.py --dry-run

  # Live send
  ENV_FILE=/www/wwwroot/swaya-live/backend/.env PYTHONPATH=. .venv/bin/python3 scripts/send_proctoring_announcement.py
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

SUBJECT = "Life isn't fair. Your exams are. — Introducing Proctoring"

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
    .intro {{ font-size: 15px; color: #444; margin: 0 0 8px; line-height: 1.6; }}
    .pivot {{ font-size: 16px; font-weight: 700; color: #1a1a1a; margin: 0 0 24px; }}
    .setup-note {{ font-size: 15px; color: #444; margin: 0 0 24px; line-height: 1.6; }}
    .section-label {{ font-size: 12px; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: 0.8px; margin: 0 0 12px; }}
    .feature-list {{ margin: 0 0 28px; padding: 0; list-style: none; }}
    .feature-list li {{ padding: 12px 0; border-bottom: 1px solid #f0f0f0; display: flex; gap: 12px; align-items: flex-start; }}
    .feature-list li:last-child {{ border-bottom: none; }}
    .feature-icon {{ font-size: 20px; flex-shrink: 0; width: 28px; text-align: center; margin-top: 1px; }}
    .feature-text strong {{ display: block; font-size: 15px; color: #1a1a1a; margin-bottom: 2px; }}
    .feature-text span {{ font-size: 13px; color: #666; line-height: 1.5; }}
    .no-install {{ font-size: 13px; color: #888; margin: 0 0 28px; line-height: 1.6; padding: 12px 16px; background: #f8f8f8; border-radius: 6px; border-left: 3px solid #1677ff; }}
    .cta-wrap {{ text-align: center; margin: 28px 0 8px; }}
    .cta {{ display: inline-block; background: #1677ff; color: #ffffff; text-decoration: none; padding: 13px 32px; border-radius: 6px; font-size: 15px; font-weight: 600; letter-spacing: 0.1px; }}
    .footer {{ background: #fafafa; border-top: 1px solid #f0f0f0; padding: 20px 32px; text-align: center; }}
    .footer p {{ margin: 0; font-size: 12px; color: #999; line-height: 1.6; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>Introducing Proctoring</h1>
      <p>Life isn't fair. Your exams are.</p>
    </div>
    <div class="body">
      <p class="greeting">Hi {name},</p>
      <p class="intro">
        Running an exam online has always come with an uncomfortable question:
        <em>did everyone play by the rules?</em>
      </p>
      <p class="pivot">Not anymore.</p>
      <p class="setup-note">
        Proctoring is now available on every Test in Swaya.me. Enable it once
        in your quiz settings &mdash; your participants do the rest.
      </p>
      <p class="section-label">Here's what happens when proctoring is on</p>
      <ul class="feature-list">
        <li>
          <span class="feature-icon">📷</span>
          <span class="feature-text">
            <strong>Webcam monitoring</strong>
            <span>Periodic snapshots are taken throughout the exam. No recording, no stream &mdash; just accountability.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">🚫</span>
          <span class="feature-text">
            <strong>Tab-switch detection</strong>
            <span>Every time a participant leaves the exam tab, it's logged as a violation.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">⛶</span>
          <span class="feature-text">
            <strong>Fullscreen enforcement</strong>
            <span>Participants must stay in fullscreen. Exiting triggers an alert and a violation entry.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">🔒</span>
          <span class="feature-text">
            <strong>Session locking</strong>
            <span>Spot something suspicious? Lock a participant's session instantly from the host view. Unlock when you're ready.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">📋</span>
          <span class="feature-text">
            <strong>Violation report</strong>
            <span>When the exam ends, download a full report &mdash; per participant, per violation, with timestamps.</span>
          </span>
        </li>
      </ul>
      <p class="no-install">
        No browser plugins. No software to install. Works on any device with a webcam.
      </p>
      <div class="cta-wrap">
        <a class="cta" href="https://www.swaya.me">Set up proctoring &rarr;</a>
      </div>
      <p style="font-size:14px; color:#555; text-align:center; margin-top:20px; line-height:1.6;">
        High-stakes exams deserve a fair playing field. This is ours.
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
    print(f"From    : Swaya <info@chakrix.com>")
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
