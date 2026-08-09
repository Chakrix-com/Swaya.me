/**
 * swaya-submit-timer — countdown + Submit Solution, in VS Code's status bar.
 *
 * Activates on `onStartupFinished` (no candidate gesture needed — see the
 * "available by default" decision in coder_submit_extension_plan.md), reads
 * /home/coder/.swaya/session.json (written by provision_workspace_job's
 * _write_session_file, backend/features/coding_challenge/coding_challenge_service_async.py),
 * and shows two status bar items:
 *   - a live countdown, deadline = createdAt + GRACE_SECONDS + timeBudgetSeconds
 *     (matches the candidate tab's own useCountdown in CodingChallengeSession.jsx)
 *   - a Submit Solution button that calls the real /submit endpoint
 *
 * Decisions this implements (2026-08-09, see the plan doc's "Decisions" block):
 *   - Adaptive refresh: 60s normally, 1s once under 5 minutes remain.
 *   - Auto-submit at zero, with retry/backoff, falling back to a live manual
 *     button if all retries fail.
 *   - Manual submit always requires a modal confirmation.
 *   - (2026-08-09, follow-up) Submit gets a permanent "prominent" status bar
 *     color instead of blending in as plain text, both items' tooltips carry
 *     "Swaya.me" branding, and a one-time toast on first activation points
 *     candidates at both items by name — real usage showed the plain
 *     StatusBarItem was easy to miss, exactly the risk flagged when this
 *     approach was chosen over a docked panel in the first place.
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as https from 'https';
import { URL } from 'url';

const SESSION_PATH = '/home/coder/.swaya/session.json';

// Matches CodingChallengeSession.jsx's GRACE_SECONDS exactly — a fixed
// frontend constant, not server-configured, so it's safe to mirror as a
// literal here rather than plumb it through session.json.
const GRACE_SECONDS = 60;

// Under this many seconds remaining: switch to 1s ticking + warning color.
// Matches T01/T02's decided threshold — the same number drives both the
// adaptive-interval switch and the visual warning, deliberately.
const WARNING_THRESHOLD_SECONDS = 5 * 60;

const NORMAL_INTERVAL_MS = 60_000;
const FAST_INTERVAL_MS = 1_000;

const AUTO_SUBMIT_RETRY_DELAYS_MS = [2_000, 5_000, 10_000];

// Shown once per workspace (persisted in context.workspaceState, which lives
// on the candidate's own persistent home volume — see docker_volume.home_volume
// in main.tf — so it survives a page reload but a genuinely new candidate
// workspace gets it fresh).
const ONBOARDING_SHOWN_KEY = 'swayaOnboardingShown';

interface SessionData {
  apiBase: string;
  inviteToken: string;
  timeBudgetSeconds: number | null;
  createdAt: string;
}

let timerItem: vscode.StatusBarItem;
let submitItem: vscode.StatusBarItem;
let outputChannel: vscode.OutputChannel;
let tickHandle: ReturnType<typeof setTimeout> | undefined;
let submitState: 'idle' | 'submitting' | 'submitted' = 'idle';
let autoSubmitAttempted = false;

function redact(text: string, token: string): string {
  return token ? text.split(token).join('[REDACTED]') : text;
}

function log(message: string, session?: SessionData): void {
  const safe = session ? redact(message, session.inviteToken) : message;
  outputChannel.appendLine(`[${new Date().toISOString()}] ${safe}`);
}

function readSession(): SessionData | null {
  try {
    const raw = fs.readFileSync(SESSION_PATH, 'utf8');
    const data = JSON.parse(raw);
    if (!data.apiBase || !data.inviteToken) {
      log('session.json missing apiBase/inviteToken — not activating status bar items');
      return null;
    }
    return data as SessionData;
  } catch (e) {
    // Best-effort by design (mirrors the backend write being best-effort too,
    // see _write_session_file's own docstring) — no session.json just means
    // no timer/submit UI, not a crash. Nothing here could contain the token
    // (the read itself failed), so no redaction needed on this branch.
    log(`session.json not readable: ${e}`);
    return null;
  }
}

// ── Countdown formatting — mirrors CodingChallengeSession.jsx's formatCountdown /
// formatDurationShort, same unit vocabulary as SetupPanel.jsx's DurationDHM
// picker (d/h/min), so a host configuring "3d 4h" and a candidate seeing
// "3d 4h 12m remaining" are reading the same units. ──

function formatRemaining(totalSeconds: number): string {
  const clamped = Math.max(0, Math.floor(totalSeconds));
  const days = Math.floor(clamped / 86400);
  if (days > 0) {
    const hours = Math.floor((clamped % 86400) / 3600);
    const minutes = Math.floor((clamped % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  }
  const h = Math.floor(clamped / 3600);
  const m = Math.floor((clamped % 3600) / 60);
  const s = clamped % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(s).padStart(2, '0');
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

function deadlines(session: SessionData): { startMs: number; endMs: number } | null {
  if (!session.timeBudgetSeconds) return null;
  const createdMs = new Date(session.createdAt).getTime();
  const startMs = createdMs + GRACE_SECONDS * 1000;
  const endMs = startMs + session.timeBudgetSeconds * 1000;
  return { startMs, endMs };
}

// ── Submit call — POST {apiBase}/coding-challenge/{inviteToken}/submit,
// Node's built-in https, no new dependency. ──

function postSubmit(session: SessionData): Promise<{ ok: boolean; status?: number; body?: string }> {
  return new Promise((resolve) => {
    let url: URL;
    try {
      url = new URL(`${session.apiBase}/coding-challenge/${session.inviteToken}/submit`);
    } catch (e) {
      resolve({ ok: false });
      return;
    }
    const req = https.request(
      {
        hostname: url.hostname,
        port: url.port || 443,
        path: url.pathname + url.search,
        method: 'POST',
        headers: { 'Content-Length': 0 },
        timeout: 15_000,
      },
      (res) => {
        let body = '';
        res.on('data', (chunk) => (body += chunk));
        res.on('end', () => {
          const ok = (res.statusCode || 0) >= 200 && (res.statusCode || 0) < 300;
          resolve({ ok, status: res.statusCode, body });
        });
      },
    );
    req.on('timeout', () => req.destroy());
    req.on('error', () => resolve({ ok: false }));
    req.end();
  });
}

// Corrected 2026-08-09: `statusBarItem.prominentBackground` (tried first)
// is NOT actually one of the colors StatusBarItem.backgroundColor supports —
// confirmed straight from vscode.d.ts's own doc comment: only
// `statusBarItem.errorBackground` and `statusBarItem.warningBackground` are
// guaranteed-supported ("More background colors may be supported in the
// future" — prominent isn't there yet). Using the unsupported value didn't
// error, it just silently rendered as a washed-out, low-contrast mismatch —
// confirmed live via screenshot, the opposite of the goal. warningBackground
// is the only semantically-reasonable, actually-supported option left, and
// it's already proven to render with good contrast in this exact
// environment (used for the countdown's own low-time state). Not setting
// `color` alongside it — the docs note VS Code overrides that anyway when a
// background is set, to guarantee readability.
function setSubmitIdleStyle(): void {
  submitItem.text = '$(cloud-upload) Submit Solution';
  submitItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
}

function setSubmittedUi(): void {
  submitState = 'submitted';
  submitItem.text = '$(check) Submitted';
  submitItem.command = undefined;
  submitItem.tooltip = 'Swaya.me — your solution has been submitted';
  // Settles back to the default look once the action is done — the
  // prominent color's job was to draw the eye to an action still waiting to
  // be taken, not to keep shouting after it's complete.
  submitItem.backgroundColor = undefined;
  submitItem.color = undefined;
  timerItem.text = `$(check) Submitted · ${new Date().toLocaleTimeString()}`;
  timerItem.backgroundColor = undefined;
}

async function doManualSubmit(session: SessionData): Promise<void> {
  if (submitState !== 'idle') return; // already submitting/submitted — ignore repeat clicks
  const choice = await vscode.window.showWarningMessage(
    'This ends your access to the workspace. Submit now?',
    { modal: true },
    'Submit',
  );
  if (choice !== 'Submit') return; // Cancel / dismiss (Escape, X) — full no-op, no request sent

  submitState = 'submitting';
  submitItem.text = '$(sync~spin) Submitting...';
  const result = await postSubmit(session);
  if (result.ok) {
    setSubmittedUi();
    log(`manual submit succeeded (status ${result.status})`, session);
  } else {
    submitState = 'idle';
    setSubmitIdleStyle();
    log(`manual submit FAILED (status ${result.status}, body ${result.body})`, session);
    vscode.window.showErrorMessage(
      'Swaya.me: submit failed — check your connection and try the button again, or use the original browser tab.',
    );
  }
}

async function attemptAutoSubmit(session: SessionData): Promise<void> {
  if (autoSubmitAttempted || submitState !== 'idle') return;
  autoSubmitAttempted = true;
  submitState = 'submitting';
  submitItem.text = '$(sync~spin) Auto-submitting...';
  timerItem.text = '$(clock) Time’s up — submitting...';

  for (let attempt = 0; attempt <= AUTO_SUBMIT_RETRY_DELAYS_MS.length; attempt++) {
    const result = await postSubmit(session);
    if (result.ok) {
      setSubmittedUi();
      log(`auto-submit succeeded on attempt ${attempt + 1} (status ${result.status})`, session);
      vscode.window.showInformationMessage(
        'Swaya.me: time’s up — your solution was submitted automatically.',
      );
      return;
    }
    log(`auto-submit attempt ${attempt + 1} failed (status ${result.status})`, session);
    if (attempt < AUTO_SUBMIT_RETRY_DELAYS_MS.length) {
      await new Promise((r) => setTimeout(r, AUTO_SUBMIT_RETRY_DELAYS_MS[attempt]));
    }
  }

  // All retries exhausted — fall back to a live manual button rather than
  // silently doing nothing. This is the explicit tradeoff accepted when
  // auto-submit-at-zero was decided over the plan's original "don't
  // auto-submit" recommendation (see plan's "Shared logic" section).
  submitState = 'idle';
  setSubmitIdleStyle();
  timerItem.text = '$(alert) Time’s up — click Submit';
  log('auto-submit exhausted all retries — falling back to manual button', session);
  vscode.window.showWarningMessage(
    'Swaya.me: time’s up, but automatic submission failed. Click "Submit Solution" in the status bar, or use the original browser tab.',
  );
}

function scheduleTick(session: SessionData): void {
  if (tickHandle) clearTimeout(tickHandle);

  const dl = deadlines(session);
  if (!dl) {
    timerItem.text = '$(clock) No time limit';
    timerItem.backgroundColor = undefined;
    timerItem.show();
    return; // no budget configured — nothing to count down, no auto-submit
  }

  const now = Date.now();

  if (now < dl.startMs) {
    const graceRemaining = Math.ceil((dl.startMs - now) / 1000);
    timerItem.text = `$(clock) Starting in ${graceRemaining}s`;
    timerItem.backgroundColor = undefined;
    tickHandle = setTimeout(() => scheduleTick(session), 1000);
    timerItem.show();
    return;
  }

  const remainingMs = dl.endMs - now;

  if (remainingMs <= 0) {
    timerItem.text = submitState === 'submitted' ? timerItem.text : '$(clock) 00:00';
    timerItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
    timerItem.show();
    void attemptAutoSubmit(session);
    return; // no further ticks needed — countdown is done
  }

  const remainingSeconds = remainingMs / 1000;
  const warning = remainingSeconds <= WARNING_THRESHOLD_SECONDS;
  timerItem.text = `$(clock) ${formatRemaining(remainingSeconds)} remaining`;
  timerItem.backgroundColor = warning
    ? new vscode.ThemeColor('statusBarItem.warningBackground')
    : undefined;
  timerItem.show();

  const nextInterval = warning ? FAST_INTERVAL_MS : NORMAL_INTERVAL_MS;
  tickHandle = setTimeout(() => scheduleTick(session), nextInterval);
}

export function activate(context: vscode.ExtensionContext): void {
  outputChannel = vscode.window.createOutputChannel('Swaya Submit Timer');
  context.subscriptions.push(outputChannel);

  const session = readSession();

  timerItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  submitItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 99);
  context.subscriptions.push(timerItem, submitItem);

  if (!session) {
    // No session data — nothing to show. Matches "best-effort" backend write:
    // the candidate's original browser tab still works regardless.
    return;
  }

  timerItem.tooltip = 'Swaya.me — time remaining for this coding challenge';
  submitItem.tooltip = 'Swaya.me — submit your solution now';
  setSubmitIdleStyle();
  submitItem.command = 'swayaSubmitTimer.submit';
  submitItem.show();

  context.subscriptions.push(
    vscode.commands.registerCommand('swayaSubmitTimer.submit', () => doManualSubmit(session)),
  );
  context.subscriptions.push({ dispose: () => tickHandle && clearTimeout(tickHandle) });

  // One-time onboarding nudge — the status bar alone turned out to be easy
  // to miss on first real use. Fire-and-forget: doesn't block activation or
  // the countdown starting on whether/how the candidate dismisses it.
  if (!context.workspaceState.get(ONBOARDING_SHOWN_KEY)) {
    void context.workspaceState.update(ONBOARDING_SHOWN_KEY, true);
    void vscode.window.showInformationMessage(
      '⏱️ Swaya.me — your countdown and Submit Solution button are in the status bar (bottom right).',
      'Got it',
    );
  }

  log('activated', session);
  scheduleTick(session);
}

export function deactivate(): void {
  if (tickHandle) clearTimeout(tickHandle);
}
