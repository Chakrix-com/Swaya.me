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
<title>Welcome to Swaya.me — {first_name}</title>
  <style>
    /* ─── browser preview only — production version must use inline CSS ─── */
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #ede9fe; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #1e1b4b; }}

    @media (max-width: 640px) {{
      .email-wrapper {{ width: 100% !important; border-radius: 0 !important; }}
      .hdr-pad {{ padding: 28px 20px 24px !important; }}
      .body-pad {{ padding: 28px 20px !important; }}
      .act-cell {{ display: block !important; width: 100% !important; padding: 0 0 12px 0 !important; }}
      .perk-cell {{ display: block !important; width: 100% !important; padding: 0 0 12px 0 !important; }}
      .ai-col {{ display: block !important; width: 100% !important; padding: 0 0 16px 0 !important; }}
      .qs-cell {{ display: block !important; width: 100% !important; padding: 0 0 12px 0 !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#ede9fe;">

<!-- ═══════════════════════════════════════════════════════════
     OUTER WRAPPER
═══════════════════════════════════════════════════════════ -->
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#ede9fe;padding:36px 16px 48px;">
<tr><td align="center">

<table class="email-wrapper" width="600" cellpadding="0" cellspacing="0" border="0"
       style="max-width:600px;width:100%;border-radius:20px;overflow:hidden;
              box-shadow:0 8px 40px rgba(88,28,235,0.18);">


<!-- ═══ HEADER ════════════════════════════════════════════════ -->
<tr><td style="background:linear-gradient(145deg,#0f0c2e 0%,#1e1165 40%,#3b0d8c 75%,#5b21b6 100%);position:relative;overflow:hidden;">
  <!-- decorative blobs -->
  <div style="position:absolute;top:-40px;right:-40px;width:200px;height:200px;border-radius:50%;background:radial-gradient(circle,rgba(139,92,246,0.35) 0%,transparent 70%);"></div>
  <div style="position:absolute;bottom:-30px;left:30px;width:140px;height:140px;border-radius:50%;background:radial-gradient(circle,rgba(245,158,11,0.18) 0%,transparent 70%);"></div>

  <div class="hdr-pad" style="padding:36px 36px 32px;position:relative;z-index:1;">

    <!-- Logo -->
    <div style="margin-bottom:28px;">
      <table cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="vertical-align:middle;padding-right:12px;">
            <img src="https://www.swaya.me/logo-email.png"
                 alt="Swaya.me"
                 width="48" height="48"
                 style="display:block;width:48px;height:48px;border-radius:10px;" />
          </td>
          <td style="vertical-align:middle;">
            <span style="font-size:26px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;line-height:1;">
              swaya<span style="font-weight:300;color:rgba(255,255,255,0.55);">.me</span>
            </span>
          </td>
        </tr>
      </table>
    </div>

    <!-- Hero headline -->
    <h1 style="margin:0 0 10px;font-size:30px;font-weight:900;color:#ffffff;line-height:1.15;letter-spacing:-0.5px;">
      Your audience engagement<br/>platform is ready.
    </h1>
    <p style="margin:0;font-size:15px;color:rgba(255,255,255,0.65);line-height:1.6;">
      Live quizzes. Self-paced exams. Real-time polls. All in one place — no app needed for your audience.
    </p>

    <!-- Stats strip -->
    <table cellpadding="0" cellspacing="0" border="0" style="margin-top:28px;">
      <tr>
        <td style="padding-right:28px;">
          <div style="font-size:22px;font-weight:900;color:#a78bfa;line-height:1;">4</div>
          <div style="font-size:11px;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:.8px;margin-top:2px;">Activity types</div>
        </td>
        <td style="padding-right:28px;border-left:1px solid rgba(255,255,255,0.1);padding-left:28px;">
          <div style="font-size:22px;font-weight:900;color:#a78bfa;line-height:1;">11</div>
          <div style="font-size:11px;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:.8px;margin-top:2px;">Languages</div>
        </td>
        <td style="padding-right:28px;border-left:1px solid rgba(255,255,255,0.1);padding-left:28px;">
          <div style="font-size:22px;font-weight:900;color:#a78bfa;line-height:1;">500+</div>
          <div style="font-size:11px;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:.8px;margin-top:2px;">Participants / session</div>
        </td>
        <td style="border-left:1px solid rgba(255,255,255,0.1);padding-left:28px;">
          <div style="font-size:22px;font-weight:900;color:#f59e0b;line-height:1;">AI</div>
          <div style="font-size:11px;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:.8px;margin-top:2px;">Built in</div>
        </td>
      </tr>
    </table>
  </div>
</td></tr>


<!-- ═══ GREETING ══════════════════════════════════════════════ -->
<tr><td class="body-pad" style="background:#ffffff;padding:36px 36px 0;">

  <p style="font-size:17px;color:#1e1b4b;margin:0 0 6px;font-weight:400;">
    Hi <strong style="color:#5b21b6;">{first_name}</strong>,
  </p>
  <p style="font-size:15px;color:#4b5563;line-height:1.7;margin:0 0 28px;">
    You've joined a platform built for teachers, trainers, event hosts, and anyone who needs
    to engage a room — live or async. Here's everything you can do from the moment you log in.
  </p>

  <!-- Quick-start 3-step -->
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:linear-gradient(135deg,#f5f3ff 0%,#ede9fe 100%);border-radius:14px;
                border:1px solid #ddd6fe;margin-bottom:36px;">
    <tr>
      <td class="qs-cell" style="padding:20px 24px;text-align:center;border-right:1px solid #ddd6fe;" width="33%">
        <div style="width:32px;height:32px;border-radius:50%;background:#5b21b6;color:#fff;font-size:14px;font-weight:800;display:inline-flex;align-items:center;justify-content:center;margin-bottom:8px;line-height:32px;">1</div>
        <div style="font-size:13px;font-weight:700;color:#3730a3;margin-bottom:3px;">Create</div>
        <div style="font-size:12px;color:#6b7280;line-height:1.5;">Type a prompt or paste questions from Excel</div>
      </td>
      <td class="qs-cell" style="padding:20px 24px;text-align:center;border-right:1px solid #ddd6fe;" width="33%">
        <div style="width:32px;height:32px;border-radius:50%;background:#5b21b6;color:#fff;font-size:14px;font-weight:800;display:inline-flex;align-items:center;justify-content:center;margin-bottom:8px;line-height:32px;">2</div>
        <div style="font-size:13px;font-weight:700;color:#3730a3;margin-bottom:3px;">Share</div>
        <div style="font-size:12px;color:#6b7280;line-height:1.5;">Share a 6-digit code or QR — no app needed</div>
      </td>
      <td class="qs-cell" style="padding:20px 24px;text-align:center;" width="33%">
        <div style="width:32px;height:32px;border-radius:50%;background:#5b21b6;color:#fff;font-size:14px;font-weight:800;display:inline-flex;align-items:center;justify-content:center;margin-bottom:8px;line-height:32px;">3</div>
        <div style="font-size:13px;font-weight:700;color:#3730a3;margin-bottom:3px;">Run</div>
        <div style="font-size:12px;color:#6b7280;line-height:1.5;">Watch the leaderboard update live in real time</div>
      </td>
    </tr>
  </table>

</td></tr>


<!-- ═══ SECTION 1: FOUR WAYS TO RUN A SESSION ════════════════ -->
<tr><td class="body-pad" style="background:#ffffff;padding:0 36px 32px;">

  <!-- Section label -->
  <div style="display:flex;align-items:center;margin-bottom:18px;">
    <span style="display:inline-block;width:26px;height:26px;border-radius:50%;background:linear-gradient(135deg,#5b21b6,#7c3aed);color:#fff;font-size:12px;font-weight:800;text-align:center;line-height:26px;margin-right:10px;flex-shrink:0;">1</span>
    <span style="font-size:16px;font-weight:800;color:#1e1b4b;letter-spacing:-0.2px;">Four ways to run a session</span>
  </div>

  <table width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <!-- Live Quiz -->
      <td class="act-cell" style="padding:0 6px 0 0;vertical-align:top;" width="50%">
        <div style="border:1px solid #e5e7eb;border-radius:12px;padding:18px;height:100%;background:#fafafa;">
          <div style="font-size:24px;margin-bottom:10px;">🎯</div>
          <div style="font-size:14px;font-weight:700;color:#1e1b4b;margin-bottom:6px;">Live Quiz</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.6;">
            Host-controlled, real-time competitive quiz. Live leaderboard after every question.
            Export results as PDF, Excel, or PowerPoint when you're done.
          </div>
        </div>
      </td>
      <!-- Live Poll -->
      <td class="act-cell" style="padding:0 0 0 6px;vertical-align:top;" width="50%">
        <div style="border:1px solid #e5e7eb;border-radius:12px;padding:18px;height:100%;background:#fafafa;">
          <div style="font-size:24px;margin-bottom:10px;">📊</div>
          <div style="font-size:14px;font-weight:700;color:#1e1b4b;margin-bottom:6px;">Live Poll</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.6;">
            Six question types: MCQ, animated word clouds, 1–10 scale, single-line, paragraph, and one-word.
            Results update instantly on screen.
          </div>
        </div>
      </td>
    </tr>
    <tr><td colspan="2" style="padding-bottom:12px;"></td></tr>
    <tr>
      <!-- Offline Survey -->
      <td class="act-cell" style="padding:0 6px 0 0;vertical-align:top;" width="50%">
        <div style="border:1px solid #e5e7eb;border-radius:12px;padding:18px;height:100%;background:#fafafa;">
          <div style="font-size:24px;margin-bottom:10px;">📋</div>
          <div style="font-size:14px;font-weight:700;color:#1e1b4b;margin-bottom:6px;">Offline Survey</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.6;">
            No live session required. Generate a QR code and let your audience respond at their own pace —
            ideal for conference posters, trade shows, and restaurant tables.
          </div>
        </div>
      </td>
      <!-- Exam Mode -->
      <td class="act-cell" style="padding:0 0 0 6px;vertical-align:top;" width="50%">
        <div style="border:1px solid #e5e7eb;border-radius:12px;padding:18px;height:100%;background:#fafafa;">
          <div style="font-size:24px;margin-bottom:10px;">📝</div>
          <div style="font-size:14px;font-weight:700;color:#1e1b4b;margin-bottom:6px;">Exam Mode</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.6;">
            Timed, self-paced exam with OTP email verification. Configurable open/close dates,
            negative marking, and automatic scoring. Full proctoring available.
          </div>
        </div>
      </td>
    </tr>
  </table>

</td></tr>


<!-- ═══ SECTION 2: AI ═════════════════════════════════════════ -->
<tr><td style="background:#0f0c2e;padding:0;">

  <div style="position:relative;overflow:hidden;">
    <div style="position:absolute;top:-60px;right:-60px;width:250px;height:250px;border-radius:50%;background:radial-gradient(circle,rgba(245,158,11,0.15) 0%,transparent 65%);"></div>
    <div style="position:absolute;bottom:-40px;left:20px;width:180px;height:180px;border-radius:50%;background:radial-gradient(circle,rgba(139,92,246,0.2) 0%,transparent 65%);"></div>

    <div style="padding:32px 36px;position:relative;z-index:1;">

      <!-- Section label -->
      <div style="margin-bottom:20px;">
        <span style="display:inline-block;width:26px;height:26px;border-radius:50%;background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;font-size:12px;font-weight:800;text-align:center;line-height:26px;margin-right:10px;">2</span>
        <span style="font-size:16px;font-weight:800;color:#ffffff;letter-spacing:-0.2px;">AI does the heavy lifting</span>
      </div>

      <p style="font-size:14px;color:rgba(255,255,255,0.6);line-height:1.7;margin:0 0 24px;">
        Describe what you need. Gemini 2.0 Flash generates a complete, fully populated activity —
        title, questions, options, and all — streamed live as you watch. Works across all four activity types.
      </p>

      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td class="ai-col" style="padding-right:12px;vertical-align:top;" width="33%">
            <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:16px;">
              <div style="font-size:20px;margin-bottom:8px;">🎙️</div>
              <div style="font-size:13px;font-weight:700;color:#fde68a;margin-bottom:5px;">Voice Input</div>
              <div style="font-size:12px;color:rgba(255,255,255,0.55);line-height:1.6;">Speak your prompt — no typing required. AI transcribes and generates.</div>
            </div>
          </td>
          <td class="ai-col" style="padding:0 6px;vertical-align:top;" width="33%">
            <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:16px;">
              <div style="font-size:20px;margin-bottom:8px;">🖼️</div>
              <div style="font-size:13px;font-weight:700;color:#fde68a;margin-bottom:5px;">Image Suggestions</div>
              <div style="font-size:12px;color:rgba(255,255,255,0.55);line-height:1.6;">For visual topics, AI suggests image search queries per answer option.</div>
            </div>
          </td>
          <td class="ai-col" style="padding-left:12px;vertical-align:top;" width="33%">
            <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:16px;">
              <div style="font-size:20px;margin-bottom:8px;">📈</div>
              <div style="font-size:13px;font-weight:700;color:#fde68a;margin-bottom:5px;">Exam Analysis</div>
              <div style="font-size:12px;color:rgba(255,255,255,0.55);line-height:1.6;">After submissions come in, request an AI performance summary for the class.</div>
            </div>
          </td>
        </tr>
      </table>

    </div>
  </div>

</td></tr>


<!-- ═══ SECTION 3: PROCTORED EXAMS ════════════════════════════ -->
<tr><td class="body-pad" style="background:#ffffff;padding:32px 36px;">

  <!-- Section label -->
  <div style="display:flex;align-items:center;margin-bottom:18px;">
    <span style="display:inline-block;width:26px;height:26px;border-radius:50%;background:linear-gradient(135deg,#5b21b6,#7c3aed);color:#fff;font-size:12px;font-weight:800;text-align:center;line-height:26px;margin-right:10px;flex-shrink:0;">3</span>
    <span style="font-size:16px;font-weight:800;color:#1e1b4b;letter-spacing:-0.2px;">Exams that can't be faked</span>
  </div>

  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:linear-gradient(135deg,#fef2f2 0%,#fff7ed 100%);border:1px solid #fecaca;border-radius:14px;">
    <tr>
      <td style="padding:20px 24px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="vertical-align:top;padding-right:20px;" width="50%">
              <div style="font-size:13px;color:#7f1d1d;line-height:1.85;">
                <div style="margin-bottom:7px;">🔒 &nbsp;<strong>OTP email verification</strong> — candidates prove identity before the exam starts</div>
                <div style="margin-bottom:7px;">📸 &nbsp;<strong>Webcam snapshots</strong> — captured via MediaPipe (client-side, no external service)</div>
                <div style="margin-bottom:7px;">🚨 &nbsp;<strong>Violation detection</strong> — tab switch, fullscreen exit, copy-paste, focus loss</div>
              </div>
            </td>
            <td style="vertical-align:top;" width="50%">
              <div style="font-size:13px;color:#7f1d1d;line-height:1.85;">
                <div style="margin-bottom:7px;">🎯 &nbsp;<strong>Integrity score 0–100</strong> — automatically adjusts the final score</div>
                <div style="margin-bottom:7px;">🔐 &nbsp;<strong>Lock mid-exam</strong> — host can remove a candidate instantly</div>
                <div style="margin-bottom:7px;">📥 &nbsp;<strong>Downloadable evidence</strong> — violation timeline + snapshot grid</div>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

</td></tr>


<!-- ✦ DIVIDER ✦ -->
<tr><td style="background:#ffffff;padding:0 36px;">
  <div style="text-align:center;color:#c4b5fd;font-size:12px;letter-spacing:6px;padding:4px 0 16px;">✦ &nbsp; ✦ &nbsp; ✦</div>
</td></tr>


<!-- ═══ SECTION 4: THE DETAILS THAT DELIGHT ═════════════════ -->
<tr><td class="body-pad" style="background:#ffffff;padding:0 36px 32px;">

  <!-- Section label -->
  <div style="display:flex;align-items:center;margin-bottom:18px;">
    <span style="display:inline-block;width:26px;height:26px;border-radius:50%;background:linear-gradient(135deg,#5b21b6,#7c3aed);color:#fff;font-size:12px;font-weight:800;text-align:center;line-height:26px;margin-right:10px;flex-shrink:0;">4</span>
    <span style="font-size:16px;font-weight:800;color:#1e1b4b;letter-spacing:-0.2px;">The details that delight</span>
  </div>

  <table width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td class="perk-cell" style="padding:0 5px 10px 0;vertical-align:top;" width="50%">
        <div style="border-left:3px solid #7c3aed;padding-left:12px;">
          <div style="font-size:13px;font-weight:700;color:#1e1b4b;margin-bottom:3px;">🎨 &nbsp;Participant Skins</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.55;">Set the look and feel per quiz — Classroom, Boardroom, Party, or Default. Applies to all audience devices instantly.</div>
        </div>
      </td>
      <td class="perk-cell" style="padding:0 0 10px 5px;vertical-align:top;" width="50%">
        <div style="border-left:3px solid #7c3aed;padding-left:12px;">
          <div style="font-size:13px;font-weight:700;color:#1e1b4b;margin-bottom:3px;">🎭 &nbsp;UI Themes</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.55;">Classic Indigo, Funky-Studio, or Perky-Game — switchable from the header without a reload.</div>
        </div>
      </td>
    </tr>
    <tr>
      <td class="perk-cell" style="padding:0 5px 10px 0;vertical-align:top;" width="50%">
        <div style="border-left:3px solid #7c3aed;padding-left:12px;">
          <div style="font-size:13px;font-weight:700;color:#1e1b4b;margin-bottom:3px;">🎬 &nbsp;Video in Questions</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.55;">Embed YouTube or Vimeo videos directly in any question. Great for listening comprehension and case studies.</div>
        </div>
      </td>
      <td class="perk-cell" style="padding:0 0 10px 5px;vertical-align:top;" width="50%">
        <div style="border-left:3px solid #7c3aed;padding-left:12px;">
          <div style="font-size:13px;font-weight:700;color:#1e1b4b;margin-bottom:3px;">📱 &nbsp;Install as an App (PWA)</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.55;">Add Swaya.me to your home screen on any device. Dashboard loads from cache — no app store required.</div>
        </div>
      </td>
    </tr>
    <tr>
      <td class="perk-cell" style="padding:0 5px 10px 0;vertical-align:top;" width="50%">
        <div style="border-left:3px solid #7c3aed;padding-left:12px;">
          <div style="font-size:13px;font-weight:700;color:#1e1b4b;margin-bottom:3px;">🖊️ &nbsp;Live Host Cockpit</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.55;">Two-pane: left mirrors the audience view, right stays your controls. QR pinned throughout so latecomers can always join.</div>
        </div>
      </td>
      <td class="perk-cell" style="padding:0 0 10px 5px;vertical-align:top;" width="50%">
        <div style="border-left:3px solid #7c3aed;padding-left:12px;">
          <div style="font-size:13px;font-weight:700;color:#1e1b4b;margin-bottom:3px;">📂 &nbsp;Folders + Templates</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.55;">Organise everything into nested folders. Browse the template gallery and start with a fully populated activity in one click.</div>
        </div>
      </td>
    </tr>
    <tr>
      <td class="perk-cell" style="padding:0 5px 0 0;vertical-align:top;" width="50%">
        <div style="border-left:3px solid #7c3aed;padding-left:12px;">
          <div style="font-size:13px;font-weight:700;color:#1e1b4b;margin-bottom:3px;">📥 &nbsp;Import from Excel</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.55;">Bulk-upload questions from a spreadsheet. Download the template, fill it in, upload — done in under a minute.</div>
        </div>
      </td>
      <td class="perk-cell" style="padding:0 0 0 5px;vertical-align:top;" width="50%">
        <div style="border-left:3px solid #7c3aed;padding-left:12px;">
          <div style="font-size:13px;font-weight:700;color:#1e1b4b;margin-bottom:3px;">📤 &nbsp;Export Three Ways</div>
          <div style="font-size:12px;color:#6b7280;line-height:1.55;">Download session results as PDF, Excel, or a ready-to-present PowerPoint deck — immediately after each session.</div>
        </div>
      </td>
    </tr>
  </table>

</td></tr>


<!-- ═══ LANGUAGE STRIP ════════════════════════════════════════ -->
<tr><td style="background:#f5f3ff;border-top:1px solid #ede9fe;border-bottom:1px solid #ede9fe;padding:16px 36px;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="vertical-align:middle;">
        <span style="font-size:12px;font-weight:700;color:#5b21b6;text-transform:uppercase;letter-spacing:.8px;">🌐 &nbsp;11 Languages</span>
      </td>
      <td style="vertical-align:middle;text-align:right;">
        <span style="font-size:12px;color:#6b7280;">English · Hindi · Tamil · Telugu · Kannada · Bengali · Gujarati · Spanish · French · German · Russian</span>
      </td>
    </tr>
  </table>
</td></tr>


<!-- ═══ CTA PANEL ════════════════════════════════════════════ -->
<tr><td style="background:linear-gradient(145deg,#3730a3 0%,#5b21b6 50%,#7c3aed 100%);padding:40px 36px;text-align:center;">
  <h2 style="margin:0 0 8px;font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.3px;">
    Ready to run your first session?
  </h2>
  <p style="margin:0 0 24px;font-size:14px;color:rgba(255,255,255,0.65);line-height:1.6;">
    Create a quiz in under 2 minutes — or let AI build it for you in 10 seconds.
  </p>
  <a href="https://www.swaya.me"
     style="display:inline-block;background:#ffffff;color:#5b21b6;text-decoration:none;
            padding:14px 40px;border-radius:999px;font-size:15px;font-weight:800;
            letter-spacing:0.1px;box-shadow:0 4px 20px rgba(0,0,0,0.25);">
    Open My Dashboard →
  </a>
  <p style="margin:20px 0 0;font-size:12px;color:rgba(255,255,255,0.4);">
    No app install needed for your audience &nbsp;·&nbsp; Works on any device
  </p>
</td></tr>


<!-- ═══ OPEN SOURCE CALLOUT ══════════════════════════════════ -->
<tr><td style="background:#1e1b4b;padding:20px 36px;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="vertical-align:middle;padding-right:16px;">
        <div style="font-size:13px;color:rgba(255,255,255,0.85);font-weight:600;margin-bottom:3px;">⭐ &nbsp;Swaya.me is open source</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.45);line-height:1.6;">
          Star the repo, file issues, or self-host for your organisation at
          <a href="https://github.com/Chakrix-com/Swaya.me" style="color:#a78bfa;text-decoration:none;">github.com/Chakrix-com/Swaya.me</a>
        </div>
      </td>
      <td style="vertical-align:middle;text-align:right;white-space:nowrap;">
        <a href="https://github.com/Chakrix-com/Swaya.me"
           style="display:inline-block;border:1px solid rgba(255,255,255,0.2);border-radius:8px;
                  padding:8px 16px;font-size:12px;color:rgba(255,255,255,0.7);text-decoration:none;
                  background:rgba(255,255,255,0.06);">
          View on GitHub →
        </a>
      </td>
    </tr>
  </table>
</td></tr>


<!-- ═══ FOOTER ═══════════════════════════════════════════════ -->
<tr><td style="background:#13103b;padding:20px 36px;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td>
        <table cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="vertical-align:middle;padding-right:8px;">
              <img src="https://www.swaya.me/logo-email.png"
                   alt="" width="24" height="24"
                   style="display:block;width:24px;height:24px;border-radius:5px;opacity:0.35;" />
            </td>
            <td style="vertical-align:middle;">
              <span style="font-size:18px;font-weight:900;color:rgba(255,255,255,0.25);letter-spacing:-0.3px;">
                swaya<span style="font-weight:300;">.me</span>
              </span>
            </td>
          </tr>
        </table>
      </td>
      <td align="right">
        <p style="margin:0;font-size:11px;color:rgba(255,255,255,0.3);line-height:1.7;text-align:right;">
          You're receiving this because you registered at Swaya.me.<br/>
          &copy; 2026 &nbsp;<a href="https://www.swaya.me" style="color:rgba(255,255,255,0.4);text-decoration:none;">Swaya.me</a>
        </p>
      </td>
    </tr>
  </table>
</td></tr>


</table>
<!-- /email wrapper -->

</td></tr>
</table>
<!-- /outer -->

</body>
</html>
"""


async def send_welcome_email(email: str, name: Optional[str] = None) -> bool:
    """Send a welcome email after a new user account is created."""
    recipient_name = (name or email.split('@')[0]).strip().split()[0]
    html_content = WELCOME_EMAIL_HTML.format(first_name=recipient_name)
    return await send_email(
        subject="Welcome to Swaya.me — you just got a very powerful toolkit",
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
