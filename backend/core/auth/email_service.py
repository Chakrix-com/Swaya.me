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
        subject="Welcome to Swaya.me — here's what you can do",
        recipients=[email],
        html_body=html_content,
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
