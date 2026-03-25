# Release Plan — Swaya.me Beta Update (2026-03-25)

> **Last prod release tag:** `release/20260321_005159` (2026-03-21 00:51 IST)
> **Commits since prod:** 17 commits (2026-03-21 03:00 → 2026-03-25 02:12)

---

## User-Facing Features to Announce (7)

| # | Feature |
|---|---------|
| 1 | **Whiteboard** — hosts can draw and annotate on a canvas during a live quiz presentation |
| 2 | **Offline Poll** — run a poll without a live session; share a link and collect responses asynchronously |
| 3 | **Dark / Light mode** — theme toggle available on every page including participant and join screens |
| 4 | **Create a Test** — new quiz type with time limits, negative marking, and automatic scoring |
| 5 | **Rich text questions** — full formatting toolbar in the question editor: bold, italic, code blocks, tables, lists, headings, colours |
| 6 | **Rich text options** — same rich text formatting now available for MCQ answer options, with a Simple / Rich Text toggle |
| 7 | **Feedback button** — floating button on every page; anyone (logged in or not) can send feedback directly to the team |

---

## Release Steps

### Step 1 — Run Regression on Test

```bash
# Mandatory gate — Suites A (smoke) + B (core functional) + C (negative/security)
BASE_URL=https://test.swaya.me/api/v1 \
APP_BASE_URL=https://test.swaya.me \
HOST_EMAIL=demo@swaya.me \
HOST_PASSWORD=Demo1234 \
bash scripts/regression/run_preprod_gate.sh

# Extended suite D — Selenium E2E (advisory, not a hard gate)
RUN_EXTENDED=1 \
BASE_URL=https://test.swaya.me/api/v1 \
APP_BASE_URL=https://test.swaya.me \
HOST_EMAIL=demo@swaya.me \
HOST_PASSWORD=Demo1234 \
bash scripts/regression/run_preprod_gate.sh
```

Pass criteria: **A + B + C all green.** Suite D advisory only.

---

### Step 2 — Promote to Production

```bash
bash deploy.sh promote-live
bash deploy.sh health
```

`promote-live` automatically:
- Creates release tag `release/YYYYMMDD_HHMMSS`
- Backs up live frontend + backend to `/home/vinay/swaya-backups/`
- rsyncs backend (excludes `.env`, `.venv/`, `uploads/`)
- Runs `alembic upgrade head` — applies `app_feedback` table migration
- Copies `frontend/dist/` → `/www/wwwroot/www.swaya.me/`
- Restarts `swayame-backend.service` + reloads nginx
- Auto-rolls back if post-deploy health check fails

---

### Step 3 — Send Release Email to Production Users

**Script:** `backend/scripts/send_release_email.py`

**Run order (always dry-run first):**
```bash
cd /home/vinay/Swaya.me/backend

# 1. Preview — no emails sent
ENV_FILE=/www/wwwroot/swaya-live/backend/.env \
PYTHONPATH=. .venv/bin/python3 scripts/send_release_email.py --dry-run

# 2. Live send — only after reviewing dry-run output
ENV_FILE=/www/wwwroot/swaya-live/backend/.env \
PYTHONPATH=. .venv/bin/python3 scripts/send_release_email.py
```

**Script behaviour:**
- `--dry-run`: prints recipient list + full email preview, sends nothing
- Sends one email per user (not bulk BCC), personalised greeting
- Logs `✓ sent` / `✗ failed` per address; prints totals at end
- SMTP failure for one address logs and continues — does not abort

---

## Recipient List (19 active prod users)

> Edit this list to remove or skip any addresses before sending.
> The script sends to all `is_active = TRUE` users in the prod DB — matches this list exactly.

| # | Email | Name | Role |
|---|-------|------|------|
| 1 | demo@swaya.me | Demo User | super_admin |
| 2 | meetnishant@gmail.com | Nishant Verma | admin |
| 3 | salonimishratiwary@gmail.com | Ruchi Mishra | user |
| 4 | Itssaurabhrawat@gmail.com | Saurabh Rawat | user |
| 5 | Yakgna.kumar@gmail.com | Yakgna | user |
| 6 | sameerrao20118@gmail.com | Sameer | user |
| 7 | sushant0511@gmail.com | Sushant Varma | user |
| 8 | sushant051183@gmail.com | Sushant Varma | user |
| 9 | ruchimishratiwary@gmail.com | Ruchi Mishra | user |
| 10 | sudalwayshere@gmail.com | _(no name — will greet as "sudalwayshere")_ | user |
| 11 | rbhagi@gmail.com | Rohit Bhagj | user |
| 12 | avant.vyas@yahoo.com | Avant | user |
| 13 | Amardeep@mann.ai | amardeep@mann.ai | user |
| 14 | ashgup11@hotmail.com | Ashish | user |
| 15 | Manojmit@hotmail.com | Manoj | user |
| 16 | Ashishchadha86@gmail.com | Ashish Chadha | user |
| 17 | vgxninjaedgy34@gmail.com | Akshay Khanna | user |
| 18 | shreevidhya89@gmail.com | Sri Vidhya | user |
| 19 | pravat.mallick@gmail.com | Pravat Mallick | user |

---

## Email Draft

> Edit the subject, greeting, feature lines, and footer below before approving the send.

---

**From:** Swaya \<info@chakrix.com\>
**Subject:** What's new in Swaya.me Beta — 7 new features just landed

---

**HTML Body (what each user receives):**

```
Hi [name],

We've been working hard on Swaya.me Beta, and we're excited to share
what's new. Here's everything that just landed:

  1. 🖊  Whiteboard
     Draw and annotate live on a canvas during your quiz presentations.

  2. 📋  Offline Poll
     No live session needed — share a link and collect responses at
     your own pace.

  3. 🌙  Dark / Light Mode
     Switch themes on every page, including participant and join screens.

  4. 📝  Create a Test
     A new quiz type built for exams — set time limits, enable negative
     marking, and get automatic scoring.

  5. ✍️  Rich Text Questions
     Format your questions with bold, italic, code blocks, tables,
     headings, colours, and more.

  6. 🔤  Rich Text Options
     The same rich text formatting is now available for MCQ answer
     options, with a Simple / Rich Text toggle.

  7. 💬  Feedback Button
     A floating button on every page — click it to send feedback or
     report a bug directly to us, no login required.

Try it now → https://www.swaya.me

Thanks for being an early user of Swaya.me Beta. Your feedback helps
us build something great.

— The Swaya.me Team


────────────────────────────────────────
You're receiving this because you registered at Swaya.me.
© 2026 Swaya.me
```

---

## Files

| File | Action |
|------|--------|
| `Docs/release-plan-2026-03-25.md` | This file |
| `backend/scripts/send_release_email.py` | **Create** — one-time broadcast script |
| `backend/core/auth/email_service.py` | Reuse `send_email()` — no changes |
| `deploy.sh` | Run only — no changes |
| `scripts/regression/run_preprod_gate.sh` | Run only — no changes |

---

## Verification Checklist

- [ ] Regression suites A + B + C exit 0
- [ ] `bash deploy.sh health` shows live backend green after promote
- [ ] `alembic current` on live DB shows latest head (`app_feedback` table present)
- [ ] Recipient list reviewed — remove any addresses not to receive the email
- [ ] Dry-run output reviewed — correct recipients, correct email body
- [ ] Manual spot-check `https://www.swaya.me` — whiteboard, offline poll, dark mode, test type all functional
- [ ] Email send completes with 0 failures (or failures are only invalid/bounced addresses)

---

## Risks

- `app_feedback` migration runs automatically via `promote-live` — no manual DB action needed.
- **Do not re-run** the email script after a successful send — no dedup guard, would double-send.
- Script targets prod DB via `ENV_FILE` — do not run without `ENV_FILE` set (would hit test DB).
- #10 (`sudalwayshere@gmail.com`) has no full name — will be greeted by email prefix.
- #13 (`Amardeep@mann.ai`) has mixed-case email address — normalised to lowercase before sending.
