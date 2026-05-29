"""
Email service for sending verification emails and other notifications
"""
import logging
from typing import Optional, Dict, Any
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from core.config.settings import settings

logger = logging.getLogger(__name__)

# Configure FastMail
try:
    conf = ConnectionConfig(
        MAIL_USERNAME=settings.smtp.user,
        MAIL_PASSWORD=settings.smtp.password,
        MAIL_FROM=settings.smtp.from_email,
        MAIL_PORT=settings.smtp.port,
        MAIL_SERVER=settings.smtp.host,
        MAIL_FROM_NAME=settings.smtp.from_name,
        MAIL_STARTTLS=False,
        MAIL_SSL_TLS=True,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True
    )
    
    # Check if SMTP is configured
    smtp_enabled = bool(settings.smtp.host and settings.smtp.user and settings.smtp.password)
    
    if not smtp_enabled:
        logger.warning("SMTP configuration is incomplete. Emails will only be logged, not sent.")
except Exception as e:
    logger.error(f"Failed to initialize email configuration: {e}")
    smtp_enabled = False
    conf = None

# Initialize FastMail
fast_mail = FastMail(conf) if conf and smtp_enabled else None


async def send_verification_email(email: EmailStr, token: str, name: Optional[str] = None) -> bool:
    """
    Send an email verification link to the user.
    """
    frontend_url = settings.app.frontend_url.rstrip('/')
    verification_link = f"{frontend_url}/verify-email?token={token}"
    
    recipient_name = name or email.split('@')[0]
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Welcome to Swaya, {recipient_name}!</h2>
        <p>Thank you for registering. Please confirm your email address to activate your account and start creating quizzes.</p>
        <div style="margin: 30px 0;">
            <a href="{verification_link}" style="background-color: #1890ff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                Verify Email Address
            </a>
        </div>
        <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
        <p><a href="{verification_link}">{verification_link}</a></p>
        <br/>
        <p>If you didn't create an account with us, you can safely ignore this email.</p>
        <p>Best regards,<br/>The Swaya Team</p>
    </div>
    """
    
    return await send_email(
        subject="Verify your Swaya account",
        recipients=[email],
        html_body=html_content
    )


async def send_password_reset_email(email: EmailStr, token: str, name: Optional[str] = None) -> bool:
    """
    Send a password reset link to the user.
    """
    frontend_url = settings.app.frontend_url.rstrip('/')
    reset_link = f"{frontend_url}/reset-password?token={token}"
    
    recipient_name = name or email.split('@')[0]
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Password Reset Request</h2>
        <p>Hi {recipient_name},</p>
        <p>We received a request to reset your password for your Swaya account. Click the button below to choose a new password:</p>
        <div style="margin: 30px 0;">
            <a href="{reset_link}" style="background-color: #1890ff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                Reset Password
            </a>
        </div>
        <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
        <p><a href="{reset_link}">{reset_link}</a></p>
        <br/>
        <p>This link will expire in 1 hour. If you didn't request a password reset, you can safely ignore this email and your password will remain unchanged.</p>
        <p>Best regards,<br/>The Swaya Team</p>
    </div>
    """
    
    return await send_email(
        subject="Reset your Swaya password",
        recipients=[email],
        html_body=html_content
    )


WELCOME_EMAIL_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Welcome to Swaya.me</title>
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
      <h1>You're in. Let's run something.</h1>
      <p>Your Swaya.me account is ready.</p>
    </div>
    <div class="body">
      <p class="greeting">Hi {name},</p>
      <p class="intro">
        Welcome to Swaya.me. Here's the full picture of what you can do from day one:
      </p>
      <ul class="feature-list">
        <li>
          <span class="feature-icon">🎯</span>
          <span class="feature-text">
            <strong>Live Quiz</strong>
            <span>Share a join code — your audience answers MCQs in real time and the leaderboard updates live.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">⚡</span>
          <span class="feature-text">
            <strong>Generate with AI</strong>
            <span>Describe what you want and AI builds your quiz questions — with options and explanations — in seconds.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">📊</span>
          <span class="feature-text">
            <strong>Live Poll</strong>
            <span>Run instant polls with word clouds, rating scales, open-ended, or one-word answers — results animate on screen.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">📋</span>
          <span class="feature-text">
            <strong>Offline Poll</strong>
            <span>No live session needed. Share a link and collect responses at any pace.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">📝</span>
          <span class="feature-text">
            <strong>Test / Exam</strong>
            <span>Schedule a timed exam with negative marking, fullscreen enforcement, and automatic scoring.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">🔒</span>
          <span class="feature-text">
            <strong>Proctoring</strong>
            <span>Webcam monitoring, tab-switch detection, and session locking — for exams that need to be fair.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">📂</span>
          <span class="feature-text">
            <strong>Import from Excel</strong>
            <span>Bulk-upload questions from a spreadsheet. Download the template, fill it in, and you're done.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">🗂️</span>
          <span class="feature-text">
            <strong>Templates &amp; Folders</strong>
            <span>Save any quiz as a reusable template. Organise everything into folders.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">✍️</span>
          <span class="feature-text">
            <strong>Rich Text Questions</strong>
            <span>Bold, italic, code blocks, tables, headings, colours — questions can be fully formatted.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">🖊️</span>
          <span class="feature-text">
            <strong>Whiteboard</strong>
            <span>Draw and annotate live on a canvas during your quiz presentations.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">📈</span>
          <span class="feature-text">
            <strong>Session History &amp; Export</strong>
            <span>Every past session is saved. Download results as a spreadsheet anytime.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">🌐</span>
          <span class="feature-text">
            <strong>11 Languages</strong>
            <span>English, Hindi, Tamil, Telugu, Kannada, Bengali, Gujarati, Spanish, French, German, and Russian.</span>
          </span>
        </li>
        <li>
          <span class="feature-icon">🌙</span>
          <span class="feature-text">
            <strong>Dark / Light Mode</strong>
            <span>Switch themes on every screen — host, participant, and join views.</span>
          </span>
        </li>
      </ul>
      <div class="cta-wrap">
        <a class="cta" href="https://www.swaya.me">Open Dashboard →</a>
      </div>
      <p style="font-size:14px; color:#555; text-align:center; margin-top:20px; line-height:1.6;">
        Thanks for joining Swaya.me.<br>
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


async def send_welcome_email(email: str, name: Optional[str] = None) -> bool:
    """Send a welcome email after a new user account is created."""
    recipient_name = (name or email.split('@')[0]).strip().split()[0]
    html_content = WELCOME_EMAIL_HTML.format(name=recipient_name)
    return await send_email(
        subject="Welcome to Swaya.me — here's everything you can do",
        recipients=[email],
        html_body=html_content,
    )


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities from rich-text question strings."""
    import re, html
    clean = re.sub(r'<[^>]+>', ' ', text or '')
    clean = html.unescape(clean)
    return re.sub(r'\s+', ' ', clean).strip()


def _html_for_email(text: str) -> str:
    """
    Convert stored rich-text HTML to email-safe HTML.
    - Strips class/style/event attributes (email clients ignore them anyway)
    - Adds inline styles to <pre>/<code> so code blocks render in email
    - Allows: <strong>, <em>, <b>, <i>, <br>, <p>, <ul>, <ol>, <li>, <code>, <pre>
    - Strips everything else
    """
    import re, html as _html_mod
    if not text:
        return ''

    # Replace <pre><code ...>…</code></pre> with styled version before stripping attrs
    def style_pre(m: re.Match) -> str:
        code = m.group(1)
        return (
            '<pre style="background:#f6f8fa;border:1px solid #e8e8e8;border-radius:5px;'
            'padding:10px 14px;font-family:\'Courier New\',Courier,monospace;font-size:12px;'
            'line-height:1.5;overflow-x:auto;white-space:pre-wrap;word-break:break-all;">'
            f'<code style="font-family:\'Courier New\',Courier,monospace;">{code}</code></pre>'
        )
    text = re.sub(r'<pre[^>]*><code[^>]*>([\s\S]*?)</code></pre>', style_pre, text, flags=re.IGNORECASE)

    # Inline <code> outside <pre>
    text = re.sub(
        r'<code(?![^>]*style)[^>]*>',
        '<code style="background:#f6f8fa;padding:1px 5px;border-radius:3px;'
        'font-family:\'Courier New\',Courier,monospace;font-size:12px;">',
        text, flags=re.IGNORECASE
    )

    # Strip all attributes from remaining allowed tags (keeps the tag, drops attrs)
    ALLOWED = {'strong', 'em', 'b', 'i', 'br', 'p', 'ul', 'ol', 'li', 'code', 'pre'}
    def clean_tag(m: re.Match) -> str:
        slash = m.group(1) or ''
        tag = m.group(2).lower()
        rest = m.group(3)
        if tag in ALLOWED:
            # Keep pre/code as-is (already inlined styles above); strip attrs from others
            if tag in ('pre', 'code'):
                return m.group(0)
            return f'<{slash}{tag}>'
        return ''
    text = re.sub(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>', clean_tag, text)
    return text


def _score_colour(pct: float) -> str:
    if pct >= 70:
        return '#389e0d'
    if pct >= 40:
        return '#d46b08'
    return '#cf1322'


async def send_exam_result_email(
    email: str,
    name: str | None,
    quiz_title: str,
    total_score: int,
    max_score: int,
    percentage: float,
    correct_count: int,
    wrong_count: int,
    unanswered_count: int,
    question_results: list,
    started_at=None,
    completed_at=None,
    time_taken_seconds: float | None = None,
    ai_summary: str | None = None,
    attempt_count: int = 1,
    all_attempts: list | None = None,
    integrity_score: int | None = None,
    violation_count: int = 0,
    is_locked: bool = False,
    violation_types: list | None = None,
    sender_name: str | None = None,
) -> bool:
    """Send a branded results email to the participant after exam submission."""
    import html as _html_mod
    recipient = (name or email.split('@')[0]).strip().split()[0]
    score_colour = _score_colour(percentage)
    pct_int = int(round(percentage))

    # ── Helpers ──────────────────────────────────────────────────────────────
    import datetime as _dt

    def _fmt_time(s):
        if s is None: return '—'
        m, sec = divmod(int(s), 60)
        h, m = divmod(m, 60)
        return f'{h}h {m}m {sec}s' if h else f'{m}m {sec}s'

    def _fmt_date(dt):
        if dt is None: return '—'
        try:
            d = dt if isinstance(dt, _dt.datetime) else _dt.datetime.fromisoformat(str(dt).replace('Z', '+00:00'))
            return d.strftime('%d %b %Y')
        except Exception:
            return '—'

    def _fmt_clock(dt):
        if dt is None: return '—'
        try:
            d = dt if isinstance(dt, _dt.datetime) else _dt.datetime.fromisoformat(str(dt).replace('Z', '+00:00'))
            return d.strftime('%H:%M UTC')
        except Exception:
            return '—'

    # Score band colours
    if pct_int >= 70:
        band_dark, band_mid, band_light = '#1a7f37', '#2ea043', '#dcfce7'
    elif pct_int >= 40:
        band_dark, band_mid, band_light = '#9a3412', '#c2410c', '#fff7ed'
    else:
        band_dark, band_mid, band_light = '#991b1b', '#dc2626', '#fef2f2'

    # ── Score hero ───────────────────────────────────────────────────────────
    score_hero = f"""
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 8px;">
  <tr>
    <td align="center" style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);border-radius:16px;padding:36px 24px 28px;">
      <!-- Big percentage -->
      <div style="font-size:72px;font-weight:900;color:{band_mid};letter-spacing:-2px;line-height:1;">{pct_int}<span style="font-size:40px;font-weight:700;opacity:.85;">%</span></div>
      <div style="font-size:15px;color:rgba(255,255,255,0.6);margin-top:4px;letter-spacing:.3px;">{total_score} &nbsp;/&nbsp; {max_score} &nbsp;points</div>
      <!-- Stats pills -->
      <table cellpadding="0" cellspacing="0" border="0" style="margin:20px auto 0;">
        <tr>
          <td style="padding:0 6px;">
            <div style="background:rgba(46,160,67,0.18);border:1px solid rgba(46,160,67,0.4);border-radius:999px;padding:6px 18px;text-align:center;">
              <div style="font-size:20px;font-weight:800;color:#4ade80;line-height:1.1;">{correct_count}</div>
              <div style="font-size:10px;color:rgba(255,255,255,0.55);text-transform:uppercase;letter-spacing:.8px;margin-top:2px;">Correct</div>
            </div>
          </td>
          <td style="padding:0 6px;">
            <div style="background:rgba(220,38,38,0.18);border:1px solid rgba(220,38,38,0.4);border-radius:999px;padding:6px 18px;text-align:center;">
              <div style="font-size:20px;font-weight:800;color:#f87171;line-height:1.1;">{wrong_count}</div>
              <div style="font-size:10px;color:rgba(255,255,255,0.55);text-transform:uppercase;letter-spacing:.8px;margin-top:2px;">Wrong</div>
            </div>
          </td>
          <td style="padding:0 6px;">
            <div style="background:rgba(148,163,184,0.18);border:1px solid rgba(148,163,184,0.3);border-radius:999px;padding:6px 18px;text-align:center;">
              <div style="font-size:20px;font-weight:800;color:#94a3b8;line-height:1.1;">{unanswered_count}</div>
              <div style="font-size:10px;color:rgba(255,255,255,0.55);text-transform:uppercase;letter-spacing:.8px;margin-top:2px;">Skipped</div>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""

    # ── Meta strip ───────────────────────────────────────────────────────────
    meta_chips = []
    if started_at:
        meta_chips.append(f'<span style="color:#64748b;">&#128197;</span>&nbsp;{_fmt_date(started_at)}')
        meta_chips.append(f'<span style="color:#64748b;">&#9200;</span>&nbsp;Started {_fmt_clock(started_at)}')
    if completed_at:
        meta_chips.append(f'Submitted {_fmt_clock(completed_at)}')
    if time_taken_seconds is not None:
        meta_chips.append(f'<span style="color:#64748b;">&#9203;</span>&nbsp;{_fmt_time(time_taken_seconds)}')

    meta_row = ''
    if meta_chips:
        chips_html = ''.join(
            f'<td style="padding:0 4px;"><span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:999px;padding:5px 14px;font-size:12px;color:#475569;white-space:nowrap;">{c}</span></td>'
            for c in meta_chips
        )
        meta_row = f"""
<table cellpadding="0" cellspacing="0" border="0" style="margin:16px auto 28px;"><tr>{chips_html}</tr></table>"""

    # ── Attempt history ───────────────────────────────────────────────────────
    attempts_section = ''
    if attempt_count > 1 and all_attempts:
        att_rows = ''
        for i, att in enumerate(all_attempts, 1):
            sc = att.get('score', 0)
            mx = att.get('max_score', max_score)
            pct_a = round(sc / mx * 100) if mx else 0
            bg = '#f0fdf4' if i == 1 else ('#ffffff' if i % 2 == 1 else '#f8fafc')
            best_tag = '&nbsp;<span style="background:#1677ff;color:#fff;font-size:10px;padding:2px 7px;border-radius:999px;font-weight:700;vertical-align:middle;">BEST</span>' if i == 1 else ''
            att_rows += f"""
<tr style="background:{bg};">
  <td style="padding:10px 16px;font-size:13px;color:#64748b;text-align:center;width:40px;border-bottom:1px solid #f1f5f9;">{i}</td>
  <td style="padding:10px 16px;font-size:13px;color:#1e293b;border-bottom:1px solid #f1f5f9;">{_fmt_date(att.get('completed_at'))}{best_tag}</td>
  <td style="padding:10px 16px;font-size:13px;color:#1e293b;font-weight:{'700' if i==1 else '400'};text-align:center;border-bottom:1px solid #f1f5f9;">{sc}&nbsp;/&nbsp;{mx}&nbsp;<span style="color:#94a3b8;font-size:11px;">({pct_a}%)</span></td>
  <td style="padding:10px 16px;font-size:13px;color:#64748b;text-align:center;border-bottom:1px solid #f1f5f9;">{_fmt_time(att.get('time_taken_seconds'))}</td>
</tr>"""
        attempts_section = f"""
<div style="margin-bottom:28px;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
  <div style="background:#f8fafc;padding:12px 16px;border-bottom:1px solid #e2e8f0;">
    <span style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.8px;">Attempt History</span>
    <span style="font-size:11px;color:#94a3b8;margin-left:6px;">({attempt_count} attempts &mdash; breakdown below is for your best)</span>
  </div>
  <table width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr style="background:#f1f5f9;">
      <th style="padding:8px 16px;font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;font-weight:600;text-align:center;">#</th>
      <th style="padding:8px 16px;font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;font-weight:600;text-align:left;">Date</th>
      <th style="padding:8px 16px;font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;font-weight:600;text-align:center;">Score</th>
      <th style="padding:8px 16px;font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;font-weight:600;text-align:center;">Time</th>
    </tr>
    {att_rows}
  </table>
</div>"""

    # ── Integrity section ─────────────────────────────────────────────────────
    integrity_section = ''
    if integrity_score is not None:
        VIOLATION_LABELS = {
            'TAB_SWITCH_DETECT': 'Tab switch',
            'FULLSCREEN_EXIT': 'Fullscreen exit',
            'DEVTOOLS_OPEN': 'DevTools opened',
            'COPY_ATTEMPT': 'Copy / paste attempt',
            'WEBCAM_PERMISSION_DENIED': 'Webcam denied',
            'SESSION_LOCKED': 'Session locked',
            'LOW_INTEGRITY_SCORE': 'Integrity threshold breached',
        }
        if integrity_score >= 80:
            i_bg, i_fg, i_bar = '#f0fdf4', '#15803d', '#bbf7d0'
        elif integrity_score >= 50:
            i_bg, i_fg, i_bar = '#fffbeb', '#b45309', '#fde68a'
        else:
            i_bg, i_fg, i_bar = '#fef2f2', '#b91c1c', '#fecaca'

        vtypes = list(dict.fromkeys(violation_types or []))
        vtypes_clean = [VIOLATION_LABELS.get(v, v.replace('_', ' ').title()) for v in vtypes
                        if v not in ('SESSION_LOCKED', 'LOW_INTEGRITY_SCORE')]
        v_tags = ''.join(
            f'<span style="display:inline-block;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;padding:3px 10px;font-size:11px;color:#475569;margin:3px 4px 3px 0;">{v}</span>'
            for v in vtypes_clean
        )
        locked_row = ''
        if is_locked:
            locked_row = '<div style="margin-top:10px;font-size:12px;color:#b91c1c;font-weight:600;">&#128274; This session was locked by the proctoring system.</div>'

        integrity_section = f"""
<div style="margin-bottom:28px;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
  <div style="background:#f8fafc;padding:12px 16px;border-bottom:1px solid #e2e8f0;">
    <span style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.8px;">Exam Integrity</span>
  </div>
  <div style="padding:16px;">
    <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
      <td style="width:160px;vertical-align:top;">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;margin-bottom:8px;">Integrity Score</div>
        <div style="background:{i_bg};border:1px solid {i_bar};border-radius:10px;padding:10px 16px;display:inline-block;">
          <span style="font-size:28px;font-weight:900;color:{i_fg};line-height:1;">{integrity_score}</span>
          <span style="font-size:12px;color:{i_fg};opacity:.7;">&nbsp;/ 100</span>
        </div>
      </td>
      <td style="vertical-align:top;padding-left:20px;">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;margin-bottom:8px;">Violations ({violation_count})</div>
        <div>{v_tags if v_tags else '<span style="font-size:12px;color:#94a3b8;">None recorded</span>'}</div>
        {locked_row}
      </td>
    </tr></table>
  </div>
</div>"""

    # ── Question breakdown ────────────────────────────────────────────────────
    q_cards = ''
    for i, qr in enumerate(question_results, 1):
        q_text      = _html_for_email(qr.question_text or '')
        options     = qr.options or []
        correct_idx = qr.correct_answer_index
        p_idx       = qr.participant_answer
        is_corr     = qr.is_correct
        explanation = _html_for_email(qr.answer_explanation or '')

        if p_idx is None:
            left_border = '#94a3b8'
            badge = '<span style="background:#f1f5f9;color:#64748b;border:1px solid #e2e8f0;padding:3px 10px;border-radius:6px;font-size:10px;font-weight:700;letter-spacing:.4px;">SKIPPED</span>'
            pts_html = ''
        elif is_corr:
            left_border = '#16a34a'
            badge = '<span style="background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;padding:3px 10px;border-radius:6px;font-size:10px;font-weight:700;letter-spacing:.4px;">&#10003; CORRECT</span>'
            pts_html = f'<span style="color:#15803d;font-size:12px;font-weight:700;">+{qr.points_earned} pts</span>'
        else:
            left_border = '#dc2626'
            badge = '<span style="background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;padding:3px 10px;border-radius:6px;font-size:10px;font-weight:700;letter-spacing:.4px;">&#10007; WRONG</span>'
            neg = qr.negative_points_applied
            pts_html = f'<span style="color:#b91c1c;font-size:12px;font-weight:700;">{("-"+str(neg)) if neg else "0 pts"}</span>'

        your_ans    = _html_for_email(options[p_idx]) if p_idx is not None and p_idx < len(options) else '—'
        correct_ans = _html_for_email(options[correct_idx]) if correct_idx is not None and correct_idx < len(options) else '—'

        answer_line = ''
        if p_idx is not None:
            c = '#15803d' if is_corr else '#b91c1c'
            answer_line = f'<div style="margin-top:8px;font-size:12px;color:#64748b;">Your answer: <strong style="color:{c};">{your_ans}</strong>'
            if not is_corr:
                answer_line += f'&nbsp;&nbsp;&#8594;&nbsp;&nbsp;Correct: <strong style="color:#15803d;">{correct_ans}</strong>'
            answer_line += '</div>'

        exp_line = ''
        if explanation:
            exp_line = f'<div style="margin-top:10px;font-size:12px;color:#475569;background:#fefce8;border-left:3px solid #eab308;padding:8px 12px;border-radius:0 6px 6px 0;line-height:1.6;">&#128161;&nbsp;{explanation}</div>'

        pts_block = f'<div style="margin-top:6px;text-align:right;">{pts_html}</div>' if pts_html else ''

        q_cards += f"""
<tr>
  <td style="border-bottom:1px solid #f1f5f9;padding:0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="width:4px;background:{left_border};border-radius:0;" width="4">&nbsp;</td>
        <td style="padding:14px 16px 14px 14px;vertical-align:top;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="vertical-align:top;">
                <span style="font-size:10px;font-weight:800;color:#94a3b8;text-transform:uppercase;letter-spacing:.6px;margin-right:8px;">Q{i}</span>
                <span style="font-size:13px;color:#1e293b;line-height:1.65;">{q_text}</span>
                {answer_line}{exp_line}
              </td>
              <td style="vertical-align:top;padding-left:12px;white-space:nowrap;text-align:right;">
                {badge}
                {pts_block}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </td>
</tr>"""

    # ── AI summary ────────────────────────────────────────────────────────────
    ai_section = ''
    if ai_summary:
        ai_section = f"""
<div style="margin-bottom:28px;border:1px solid #bfdbfe;border-radius:12px;overflow:hidden;">
  <div style="background:#eff6ff;padding:12px 16px;border-bottom:1px solid #bfdbfe;">
    <span style="font-size:11px;font-weight:700;color:#1d4ed8;text-transform:uppercase;letter-spacing:.8px;">&#129302; AI Performance Summary</span>
  </div>
  <div style="padding:16px 20px;font-size:13px;color:#1e293b;line-height:1.7;">{ai_summary}</div>
</div>"""

    # ── Full template ─────────────────────────────────────────────────────────
    safe_title = _html_mod.escape(quiz_title)
    safe_recip = _html_mod.escape(recipient)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Your results — {safe_title}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#1e293b;">

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f1f5f9;padding:40px 16px 48px;">
<tr><td align="center">

<table width="600" cellpadding="0" cellspacing="0" border="0"
       style="max-width:600px;width:100%;border-radius:20px;overflow:hidden;
              box-shadow:0 4px 24px rgba(15,23,42,0.12);">

  <!-- ═══ HEADER ═══ -->
  <tr><td style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 60%,#1d4ed8 100%);padding:28px 32px 24px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td>
        <div style="font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;line-height:1;">
          swaya<span style="font-weight:300;color:rgba(255,255,255,0.7);">.me</span>
        </div>
        <div style="font-size:11px;color:rgba(255,255,255,0.45);text-transform:uppercase;letter-spacing:1.2px;margin-top:4px;">Exam Results</div>
      </td>
      <td align="right">
        <div style="background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:8px;padding:6px 14px;display:inline-block;">
          <div style="font-size:12px;color:rgba(255,255,255,0.9);font-weight:600;">{safe_title}</div>
        </div>
      </td>
    </tr></table>
  </td></tr>

  <!-- ═══ WHITE CARD BODY ═══ -->
  <tr><td style="background:#ffffff;padding:32px 32px 8px;">

    <!-- Greeting -->
    <p style="font-size:17px;margin:0 0 28px;color:#0f172a;font-weight:400;line-height:1.5;">
      Hi <strong style="color:#1d4ed8;">{safe_recip}</strong>,<br/>
      <span style="color:#475569;font-size:14px;">Here are your results for <strong style="color:#0f172a;">{safe_title}</strong>.</span>
    </p>

    <!-- Score hero -->
    {score_hero}

    <!-- Meta chips -->
    {meta_row}

    <!-- Attempt history -->
    {attempts_section}

    <!-- Integrity -->
    {integrity_section}

    <!-- Question breakdown header -->
    <div style="display:flex;align-items:center;margin-bottom:12px;">
      <span style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.8px;">Question Breakdown</span>
      <span style="flex:1;height:1px;background:#e2e8f0;margin-left:12px;display:inline-block;vertical-align:middle;"></span>
    </div>

    <!-- Question table -->
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;margin-bottom:32px;">
      {q_cards}
    </table>

    <!-- AI summary -->
    {ai_section}

    <!-- CTA -->
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:32px;">
      <tr><td align="center">
        <a href="https://www.swaya.me"
           style="display:inline-block;background:linear-gradient(135deg,#1d4ed8,#2563eb);color:#ffffff;
                  text-decoration:none;padding:14px 40px;border-radius:999px;font-size:14px;
                  font-weight:700;letter-spacing:.3px;box-shadow:0 4px 14px rgba(29,78,216,0.35);">
          Visit Swaya.me &#8594;
        </a>
      </td></tr>
    </table>

  </td></tr>

  <!-- ═══ FOOTER ═══ -->
  <tr><td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td>
        <div style="font-size:18px;font-weight:900;color:#94a3b8;letter-spacing:-0.3px;">
          swaya<span style="font-weight:300;">.me</span>
        </div>
      </td>
      <td align="right">
        <p style="margin:0;font-size:11px;color:#94a3b8;line-height:1.7;text-align:right;">
          You received this because you participated in an exam.<br/>
          &copy; 2026 &nbsp;<a href="https://www.swaya.me" style="color:#64748b;text-decoration:none;">Swaya.me</a>
        </p>
      </td>
    </tr></table>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    return await send_email(
        subject=f"Your results: {quiz_title} — {pct_int}%",
        recipients=[email],
        html_body=html,
        sender_name=sender_name,
    )


async def send_email(
    subject: str,
    recipients: list[EmailStr],
    html_body: str,
    sender_name: str | None = None,
) -> bool:
    """
    Send an email using FastMail. If SMTP is not configured, logs the email content.
    When sender_name is provided a temporary FastMail instance overrides the from-name.
    """
    if not smtp_enabled or not fast_mail:
        logger.info(f"--- MOCK EMAIL ---")
        logger.info(f"To: {recipients}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {html_body}")
        logger.info(f"------------------")
        return True

    mailer = fast_mail
    if sender_name and conf:
        try:
            override_conf = ConnectionConfig(
                MAIL_USERNAME=settings.smtp.user,
                MAIL_PASSWORD=settings.smtp.password,
                MAIL_FROM=settings.smtp.from_email,
                MAIL_PORT=settings.smtp.port,
                MAIL_SERVER=settings.smtp.host,
                MAIL_FROM_NAME=sender_name,
                MAIL_STARTTLS=False,
                MAIL_SSL_TLS=True,
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=True,
            )
            mailer = FastMail(override_conf)
        except Exception as cfg_err:
            logger.warning(f"Could not create override mailer for sender_name={sender_name!r}: {cfg_err}")

    try:
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=html_body,
            subtype=MessageType.html
        )
        await mailer.send_message(message)
        logger.info(f"Email sent successfully to {recipients}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipients}: {e}")
        if settings.app.environment == "development":
            logger.info(f"Development fallback: Simulated email sending because real sending failed.")
            return True
        return False
