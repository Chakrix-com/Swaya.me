# Plan — Welcome Email on New User Registration

> **Status:** Draft — not yet implemented
> **Date:** 2026-03-25

---

## Objective

Send a branded welcome email to every new user the moment their email address is verified. The email introduces the key features of Swaya.me Beta and gives them a clear call-to-action to start using the app.

---

## When to Send

**Trigger: email verification confirmed** — i.e. immediately after `POST /api/v1/auth/verify-email` succeeds and `user.is_email_verified` is set to `True`.

This is preferred over sending at registration time because:
- The verification email is already sent at registration; two emails arriving at once risks both landing in spam.
- The user has confirmed they own the address, so the welcome email reaches a real, engaged inbox.
- It acts as a natural "you're in — here's what to do next" moment right before their first login.

**Hook location:** `backend/broker/api/auth.py` → `verify_email()` endpoint, after `await db.commit()` and before the return statement.

---

## Email Specification

| Field | Value |
|-------|-------|
| **From** | `Swaya <info@chakrix.com>` |
| **Subject** | `Welcome to Swaya.me Beta — here's what you can do` |
| **Greeting** | `Hi [first name],` (falls back to email prefix if no name) |
| **CTA button** | `Go to Dashboard →` → `https://www.swaya.me` |
| **Footer** | `You're receiving this because you registered at Swaya.me. © 2026 Swaya.me` |

### Feature list to highlight

| # | Feature | One-line description |
|---|---------|---------------------|
| 1 | **Live Quiz** | Create and run a live quiz with a join code — audience answers in real time. |
| 2 | **Live Poll** | Run an instant live poll and see results update live on screen. |
| 3 | **Offline Poll** | Share a link, collect responses at your own pace — no live session needed. |
| 4 | **Test / Exam** | Set time limits, enable negative marking, and get automatic scoring. |
| 5 | **Rich Text Questions** | Format questions with bold, italic, code blocks, tables, headings, and colours. |
| 6 | **Whiteboard** | Draw and annotate live on a canvas during your quiz presentations. |
| 7 | **Dark / Light Mode** | Switch themes on every page, including participant and join screens. |
| 8 | **Feedback Button** | A floating button on every page — send us feedback or report a bug instantly. |
| 9 | **11 Languages** | The full app — host, participant, and join screens — is available in English, Hindi, Tamil, Telugu, Kannada, Bengali, Gujarati, Spanish, French, German, and Russian. |

---

## Email Draft

> Edit subject line, greeting, feature copy, or CTA text here before approving implementation.

---

**From:** Swaya \<info@chakrix.com\>
**Subject:** Welcome to Swaya.me Beta — here's what you can do

---

**HTML Body (rendered in mail client):**

```
Hi [name],

Welcome to Swaya.me Beta! Your account is now verified and ready to go.

Here's what you can do straight away:

  🎯  Live Quiz
      Create a quiz, share a join code, and run it live with your
      audience — they answer in real time from any device.

  📊  Live Poll
      Run an instant live poll and watch results update on screen
      as your audience responds.

  📋  Offline Poll
      No live session needed — share a link and collect responses
      at your own pace, on your schedule.

  📝  Test / Exam
      Set a time limit, enable negative marking, and let Swaya
      score submissions automatically.

  ✍️  Rich Text Questions
      Format your questions with bold, italic, code blocks, tables,
      headings, colours, and more.

  🖊️  Whiteboard
      Draw and annotate live on a canvas during your quiz
      presentations.

  🌙  Dark / Light Mode
      Switch themes on every page, including participant and join
      screens.

  💬  Feedback Button
      A floating button on every page — click it to send us
      feedback or report a bug, no extra steps needed.

  🌐  11 Languages
      The full app — host, participant, and join screens — is
      available in English, Hindi, Tamil, Telugu, Kannada, Bengali,
      Gujarati, Spanish, French, German, and Russian.


[ Go to Dashboard → ]   https://www.swaya.me


Thanks for joining Swaya.me Beta. We're building this together —
your feedback shapes what comes next.

— The Swaya.me Team


────────────────────────────────────────────────────
You're receiving this because you registered at Swaya.me.
© 2026 Swaya.me  ·  www.swaya.me
```

---

## Email HTML Design

- Matches the style of the existing release email (`backend/scripts/send_release_email.py`): branded blue header (`#1677ff`), feature list with emoji icons, CTA button, and footer.
- Mobile-friendly max-width 580 px wrapper.
- Personalised greeting using first name from `user.full_name`, falling back to email prefix.
- **No new CSS framework or dependency** — inline styles only, consistent with other transactional emails.

---

## Implementation Plan

### Step 1 — Add `send_welcome_email()` to `email_service.py`

**File:** `backend/core/auth/email_service.py`

Add a new async function below `send_verification_email()`:

```python
async def send_welcome_email(email: str, name: Optional[str] = None) -> bool:
    """Send a welcome email after a user verifies their email address."""
    recipient_name = (name or email.split('@')[0]).strip().split()[0]
    html_content = WELCOME_EMAIL_HTML.format(name=recipient_name)
    return await send_email(
        subject="Welcome to Swaya.me Beta — here's what you can do",
        recipients=[email],
        html_body=html_content,
    )
```

Also define `WELCOME_EMAIL_HTML` as a module-level string constant in the same file — the full branded HTML template with all 8 feature rows, CTA button, and footer. Use `{name}` as the only format placeholder.

---

### Step 2 — Call `send_welcome_email()` from the verify-email endpoint

**File:** `backend/broker/api/auth.py`

After `await db.commit()` in the `verify_email()` endpoint, add:

```python
from core.auth.email_service import send_welcome_email   # add to imports at top

# Inside verify_email(), after await db.commit():
try:
    await send_welcome_email(user.email, user.full_name)
except Exception as e:
    logger.error(f"Failed to send welcome email to {user.email}: {e}")
# Continue — welcome email failure must never block verification
```

Pattern is identical to how `send_verification_email` is called in `service_async.py` — try/except, log on failure, never raise.

---

### Step 3 — Manual smoke test

1. Register a new account on `test.swaya.me` with a real email address.
2. Click the verification link in the verification email.
3. Confirm the welcome email arrives within ~30 seconds.
4. Verify: correct name greeting, all 8 features visible, CTA links to `https://www.swaya.me`, footer present.
5. Check `test.swaya.me` backend logs for `Email sent successfully` confirmation.

---

### Step 4 — Deploy

```bash
# 1. Run regression gate
BASE_URL=https://test.swaya.me/api/v1 \
APP_BASE_URL=https://test.swaya.me \
HOST_EMAIL=demo@swaya.me \
HOST_PASSWORD=Demo1234 \
bash scripts/regression/run_preprod_gate.sh

# 2. Promote to production
bash deploy.sh promote-live
bash deploy.sh health
```

---

## Files Changed

| File | Change |
|------|--------|
| `backend/core/auth/email_service.py` | Add `WELCOME_EMAIL_HTML` constant + `send_welcome_email()` function |
| `backend/broker/api/auth.py` | Import `send_welcome_email`, call it after `await db.commit()` in `verify_email()` |

**No schema changes. No migrations. No frontend changes.**

---

## Risks & Notes

- **No dedup guard needed** — `verify_email()` already guards against double-verification (`if user.is_email_verified: return {"message": "Email already verified"}`). The welcome email can only fire once per user.
- **SMTP failure is non-blocking** — wrapped in try/except, same as all other transactional emails. Failure is logged but does not affect verification flow.
- **Admin-created users** — users created by an admin (not self-registered) also go through email verification if `is_email_verified=False`. They will also receive the welcome email, which is appropriate.
- **Demo account** — `demo@swaya.me` bypasses email verification on login; it may never hit the `verify-email` endpoint, so it will not receive a welcome email. This is intentional.
