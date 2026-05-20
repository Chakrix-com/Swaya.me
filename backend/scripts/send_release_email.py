#!/usr/bin/env python3
"""
One-time release announcement email broadcast.
Targets all is_active=TRUE users in the production database.

Usage:
  # Dry run — no emails sent, just prints recipients and preview
  ENV_FILE=/path/to/backend/.env PYTHONPATH=. .venv/bin/python3 scripts/send_release_email.py --dry-run

  # Live send
  ENV_FILE=/path/to/backend/.env PYTHONPATH=. .venv/bin/python3 scripts/send_release_email.py
"""

import asyncio
import os
import sys

# Load env file before importing anything else
env_file = os.environ.get("ENV_FILE", ".env")
from dotenv import load_dotenv
load_dotenv(env_file, override=True)

from persistence.database import SessionLocal
from persistence.models.core import User
from core.auth.email_service import send_email

DRY_RUN = "--dry-run" in sys.argv

SUBJECT = "What's new in Swaya.me Beta — 7 new features just landed"

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
    .intro {{ font-size: 15px; color: #444; margin: 0 0 24px; line-height: 1.6; }}
    .feature-list {{ margin: 0 0 28px; padding: 0; list-style: none; }}
    .feature-list li {{ padding: 12px 0; border-bottom: 1px solid #f0f0f0; display: flex; gap: 12px; align-items: flex-start; }}
    .feature-list li:last-child {{ border-bottom: none; }}
    .feature-icon {{ font-size: 20px; flex-shrink: 0; width: 28px; text-align: center; margin-top: 1px; }}
    .feature-text strong {{ display: block; font-size: 15px; color: #1a1a1a; margin-bottom: 2px; }}
    .feature-text span {{ font-size: 13px; color: #666; line-height: 1.5; }}
    .cta-wrap {{ text-align: center; margin: 28px 0 8px; }}
    .cta {{ display: inline-block; background: #1677ff; color: #ffffff; text-decoration: none; padding: 13px 32px; border-radius: 6px; font-size: 15px; font-weight: 600; letter-spacing: 0.1px; }}
    .footer {{ background: #fafafa; border-top: 1px solid #f0f0f0; padding: 20px 32px; text-align: center; }}
    .footer p {{ margin: 0; font-size: 12px; color: #999; line-height: 1.6; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>Swaya.me Beta</h1>
      <p>What's new — March 2026</p>
    </div>
    <div class="body">
      <p class="greeting">Hi {name},</p>
      <p class="intro">
        We've been busy building. Here's everything that just landed in
        <strong>Swaya.me Beta</strong>:
      </p>
      <ul class="feature-list">
        <li>
          <span class="feature-icon">🖊️</span>
          <span class="feature-text">
            <strong>Whiteboard</strong>
            <span>Draw and annotate live on a canvas during your quiz presentations.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">📋</span>
          <span class="feature-text">
            <strong>Offline Poll</strong>
            <span>No live session needed — share a link and collect responses at your own pace.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">🌙</span>
          <span class="feature-text">
            <strong>Dark / Light Mode</strong>
            <span>Switch themes on every page, including participant and join screens.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">📝</span>
          <span class="feature-text">
            <strong>Create a Test</strong>
            <span>A new quiz type built for exams — set time limits, enable negative marking, and get automatic scoring.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">✍️</span>
          <span class="feature-text">
            <strong>Rich Text Questions</strong>
            <span>Format your questions with bold, italic, code blocks, tables, headings, colours, and more.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">🔤</span>
          <span class="feature-text">
            <strong>Rich Text Options</strong>
            <span>The same rich text formatting is now available for MCQ answer options, with a Simple / Rich Text toggle.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">💬</span>
          <span class="feature-text">
            <strong>Feedback Button</strong>
            <span>A floating button on every page — click it to send feedback or report a bug directly to us, no login required.</span>
          </span>
        </li>
      </ul>
      <div class="cta-wrap">
        <a class="cta" href="https://www.swaya.me">Try it now →</a>
      </div>
      <p style="font-size:14px; color:#555; text-align:center; margin-top:20px; line-height:1.6;">
        Thanks for being an early user of Swaya.me Beta.<br>
        Your feedback helps us build something great.
      </p>
    </div>
    <div class="footer">
      <p>
        You're receiving this because you registered at Swaya.me.<br>
        © 2026 Swaya.me &nbsp;·&nbsp; <a href="https://www.swaya.me" style="color:#999;">www.swaya.me</a>
      </p>
    </div>
  </div>
</body>
</html>
"""


def get_greeting_name(full_name: str, email: str) -> str:
    if full_name and full_name.strip():
        return full_name.strip().split()[0]  # first name only
    return email.split("@")[0]


async def main():
    with SessionLocal() as db:
        users = (
            db.query(User.email, User.full_name)
            .filter(User.is_active == True)
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
            print(f"  {i:>2}. {u.email:<40}  greeting: Hi {name},")
        print("\n--- EMAIL PREVIEW (first recipient) ---\n")
        sample = users[0]
        name = get_greeting_name(sample.full_name or "", sample.email)
        body = HTML_BODY_TEMPLATE.format(subject=SUBJECT, name=name)
        # Print plain-text version of body for readability
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
