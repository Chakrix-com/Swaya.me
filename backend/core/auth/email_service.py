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
) -> bool:
    """Send a branded results email to the participant after exam submission."""
    import html as _html_mod
    recipient = (name or email.split('@')[0]).strip().split()[0]
    score_colour = _score_colour(percentage)
    pct_int = int(round(percentage))

    # ── Score card ──────────────────────────────────────────────────────────
    score_card = f"""
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 24px;">
  <tr>
    <td align="center" style="background:#fafafa;border:1px solid #f0f0f0;border-radius:10px;padding:28px 16px;">
      <div style="font-size:56px;font-weight:800;color:{score_colour};line-height:1;">{pct_int}%</div>
      <div style="font-size:16px;color:#555;margin-top:6px;font-weight:500;">{total_score} / {max_score} pts</div>
    </td>
  </tr>
</table>
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 28px;">
  <tr>
    <td align="center" width="33%" style="padding:12px 8px;background:#f6ffed;border-radius:8px;border:1px solid #b7eb8f;">
      <div style="font-size:22px;font-weight:700;color:#389e0d;">{correct_count}</div>
      <div style="font-size:12px;color:#52c41a;margin-top:2px;text-transform:uppercase;letter-spacing:.5px;">Correct</div>
    </td>
    <td width="8"></td>
    <td align="center" width="33%" style="padding:12px 8px;background:#fff2f0;border-radius:8px;border:1px solid #ffccc7;">
      <div style="font-size:22px;font-weight:700;color:#cf1322;">{wrong_count}</div>
      <div style="font-size:12px;color:#ff4d4f;margin-top:2px;text-transform:uppercase;letter-spacing:.5px;">Wrong</div>
    </td>
    <td width="8"></td>
    <td align="center" width="33%" style="padding:12px 8px;background:#f5f5f5;border-radius:8px;border:1px solid #d9d9d9;">
      <div style="font-size:22px;font-weight:700;color:#595959;">{unanswered_count}</div>
      <div style="font-size:12px;color:#8c8c8c;margin-top:2px;text-transform:uppercase;letter-spacing:.5px;">Skipped</div>
    </td>
  </tr>
</table>"""

    # ── Exam meta row (date / time / duration) ──────────────────────────────
    import datetime as _dt
    meta_parts = []
    if started_at:
        try:
            dt = started_at if isinstance(started_at, _dt.datetime) else _dt.datetime.fromisoformat(str(started_at).replace('Z', '+00:00'))
            meta_parts.append(f"<strong>Date:</strong> {dt.strftime('%d %b %Y')}")
            meta_parts.append(f"<strong>Started:</strong> {dt.strftime('%H:%M')} UTC")
        except Exception:
            pass
    if completed_at:
        try:
            dt2 = completed_at if isinstance(completed_at, _dt.datetime) else _dt.datetime.fromisoformat(str(completed_at).replace('Z', '+00:00'))
            meta_parts.append(f"<strong>Submitted:</strong> {dt2.strftime('%H:%M')} UTC")
        except Exception:
            pass
    if time_taken_seconds is not None:
        m, s = divmod(int(time_taken_seconds), 60)
        meta_parts.append(f"<strong>Duration:</strong> {m}m {s}s")

    meta_row = ''
    if meta_parts:
        meta_row = f"""
<div style="background:#f0f5ff;border:1px solid #d6e4ff;border-radius:8px;padding:12px 16px;margin-bottom:24px;font-size:13px;color:#555;line-height:1.8;">
  {'&nbsp;&nbsp;·&nbsp;&nbsp;'.join(meta_parts)}
</div>"""

    # ── Per-question rows ────────────────────────────────────────────────────
    q_rows = ''
    for i, qr in enumerate(question_results, 1):
        q_text = _html_for_email(qr.question_text or '')

        options = qr.options or []
        correct_idx = qr.correct_answer_index
        participant_idx = qr.participant_answer
        is_correct = qr.is_correct
        explanation = _html_for_email(qr.answer_explanation or '')

        if participant_idx is None:
            status_badge = '<span style="background:#f5f5f5;color:#595959;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">SKIPPED</span>'
            pts_label = ''
        elif is_correct:
            status_badge = '<span style="background:#f6ffed;color:#389e0d;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;border:1px solid #b7eb8f;">&#10003; CORRECT</span>'
            pts_label = f'<span style="color:#389e0d;font-size:12px;font-weight:600;">+{qr.points_earned} pts</span>'
        else:
            status_badge = '<span style="background:#fff2f0;color:#cf1322;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;border:1px solid #ffccc7;">&#10007; WRONG</span>'
            neg = qr.negative_points_applied
            pts_label = f'<span style="color:#cf1322;font-size:12px;font-weight:600;">{("-"+str(neg)) if neg else "0"} pts</span>'

        your_ans = _html_for_email(options[participant_idx]) if participant_idx is not None and participant_idx < len(options) else '—'
        correct_ans = _html_for_email(options[correct_idx]) if correct_idx is not None and correct_idx < len(options) else '—'

        answer_row = ''
        if participant_idx is not None:
            your_colour = '#389e0d' if is_correct else '#cf1322'
            answer_row = f'<div style="margin-top:6px;font-size:12px;color:#555;">Your answer: <strong style="color:{your_colour};">{your_ans}</strong>'
            if not is_correct:
                answer_row += f' &nbsp;·&nbsp; Correct: <strong style="color:#389e0d;">{correct_ans}</strong>'
            answer_row += '</div>'

        explanation_row = ''
        if explanation:
            explanation_row = f'<div style="margin-top:8px;font-size:12px;color:#555;background:#fffbe6;border-left:3px solid #faad14;padding:8px 10px;border-radius:0 4px 4px 0;">💡 {explanation}</div>'

        row_bg = '#ffffff' if i % 2 == 1 else '#fafafa'
        q_rows += f"""
<tr>
  <td style="padding:14px 16px;background:{row_bg};border-bottom:1px solid #f0f0f0;vertical-align:top;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="font-size:12px;color:#8c8c8c;font-weight:700;width:28px;vertical-align:top;padding-top:2px;">Q{i}</td>
        <td style="font-size:13px;color:#1a1a1a;line-height:1.6;">{q_text}</td>
        <td style="white-space:nowrap;padding-left:12px;text-align:right;vertical-align:top;">{status_badge}</td>
      </tr>
      <tr>
        <td></td>
        <td colspan="2">{answer_row}{explanation_row}{'<div style="margin-top:4px;text-align:right;">'+pts_label+'</div>' if pts_label else ''}</td>
      </tr>
    </table>
  </td>
</tr>"""

    # ── AI summary section ───────────────────────────────────────────────────
    ai_section = ''
    if ai_summary:
        ai_section = f"""
    <!-- AI Summary -->
    <tr><td style="padding:0 32px 32px;">
      <div style="background:#f0f5ff;border:1px solid #d6e4ff;border-radius:10px;padding:24px;">
        {ai_summary}
      </div>
    </td></tr>"""

    # ── Full template ────────────────────────────────────────────────────────
    safe_title = _html_mod.escape(quiz_title)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Your results — {safe_title}</title>
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1a1a1a;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0f2f5;padding:32px 16px;">
  <tr><td align="center">
  <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

    <!-- Header -->
    <tr><td style="background:#1677ff;padding:28px 32px;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
        <td>
          <div style="font-size:20px;font-weight:800;color:#ffffff;letter-spacing:-0.3px;">swaya<span style="font-weight:400;opacity:.85;">.me</span></div>
          <div style="font-size:13px;color:rgba(255,255,255,0.75);margin-top:3px;">Exam Results</div>
        </td>
        <td align="right">
          <div style="font-size:13px;color:rgba(255,255,255,0.75);">{safe_title}</div>
        </td>
      </tr></table>
    </td></tr>

    <!-- Body -->
    <tr><td style="padding:32px 32px 24px;">
      <p style="font-size:16px;margin:0 0 24px;color:#1a1a1a;">Hi <strong>{_html_mod.escape(recipient)}</strong>, here are your results.</p>

      {score_card}

      {meta_row}

      <!-- Question breakdown -->
      <div style="font-size:13px;font-weight:600;color:#595959;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px;">Question Breakdown</div>
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid #f0f0f0;border-radius:8px;overflow:hidden;margin-bottom:32px;">
        {q_rows}
      </table>

      <div style="text-align:center;margin-bottom:0;">
        <a href="https://www.swaya.me" style="display:inline-block;background:#1677ff;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:6px;font-size:15px;font-weight:600;">Go to Swaya.me</a>
      </div>
    </td></tr>

    {ai_section}

    <!-- Footer -->
    <tr><td style="background:#fafafa;border-top:1px solid #f0f0f0;padding:18px 32px;text-align:center;">
      <p style="margin:0;font-size:12px;color:#aaa;line-height:1.6;">
        You received this because you participated in an exam on Swaya.me.<br/>
        &copy; 2026 Swaya.me &nbsp;·&nbsp; <a href="https://www.swaya.me" style="color:#aaa;">www.swaya.me</a>
      </p>
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
    )


async def send_email(subject: str, recipients: list[EmailStr], html_body: str) -> bool:
    """
    Send an email using FastMail. If SMTP is not configured, logs the email content.
    """
    if not smtp_enabled or not fast_mail:
        # Fallback to logging for development
        logger.info(f"--- MOCK EMAIL ---")
        logger.info(f"To: {recipients}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {html_body}")
        logger.info(f"------------------")
        return True
        
    try:
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=html_body,
            subtype=MessageType.html
        )
        await fast_mail.send_message(message)
        logger.info(f"Email sent successfully to {recipients}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipients}: {e}")
        # In development, don't fail registering just because email fails
        if settings.app.environment == "development":
            logger.info(f"Development fallback: Simulated email sending because real sending failed.")
            return True
        return False
