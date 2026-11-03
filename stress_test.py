"""
Stress test: concurrent participants, SSE connections, answer submission burst.

Scenarios:
  1. Join 300 participants (rate limit: 300/min per IP — this is the realistic cap
     for a shared NAT; in production participants come from diverse IPs)
  2. Open 300 SSE connections and verify all establish (validates Redis pool fix)
  3. 300 simultaneous answer submissions (validates DB pool + sub-second latency)

Usage: python3 stress_test.py
"""
import asyncio
import json
import os
import time
import statistics
import httpx

BASE = "http://localhost:8004/api/v1"
QUIZ_ID = 1006          # Photosynthesis — 10 questions, id=1629..1638
N_PARTICIPANTS = 300    # 300/min join rate-limit per IP; scales to 1000+ with real IPs
JOIN_BATCH = 50         # concurrent join goroutines per batch

# ── helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

async def host_login(client: httpx.AsyncClient) -> str:
    r = await client.post(f"{BASE}/auth/login",
                          json={"email": os.environ.get("STRESS_EMAIL", "demo@swaya.me"),
                                "password": os.environ["STRESS_PASSWORD"]})
    r.raise_for_status()
    return r.json()["access_token"]

async def start_session(client: httpx.AsyncClient) -> dict:
    r = await client.post(f"{BASE}/quizzes/sessions/start",
                          params={"quiz_id": QUIZ_ID})
    r.raise_for_status()
    return r.json()

async def advance(client: httpx.AsyncClient, session_id: int):
    r = await client.post(f"{BASE}/quizzes/sessions/{session_id}/advance")
    r.raise_for_status()

async def end_session(client: httpx.AsyncClient, session_id: int):
    try:
        await client.post(f"{BASE}/quizzes/sessions/{session_id}/end")
    except Exception:
        pass

async def join_one(client: httpx.AsyncClient, join_code: str, idx: int):
    try:
        r = await client.post(f"{BASE}/quizzes/sessions/join",
                              json={"join_code": join_code,
                                    "display_name": f"LoadP{idx:04d}"})
        if r.status_code == 200:
            d = r.json()
            return d.get("session_token"), d.get("session_id")
        return None, r.status_code   # return status code for diagnostics
    except Exception as e:
        return None, str(e)

async def submit_one(client: httpx.AsyncClient, session_id: int,
                     session_token: str, question_id: int):
    t0 = time.monotonic()
    try:
        r = await client.post(
            f"{BASE}/quizzes/sessions/submit-answer",
            params={"session_token": session_token},
            json={"session_id": session_id,
                  "question_id": question_id,
                  "selected_option_index": 0},
        )
        elapsed = time.monotonic() - t0
        if r.status_code == 200:
            return elapsed, None
        return None, f"HTTP {r.status_code}: {r.text[:120]}"
    except Exception as e:
        return None, str(e)

# ── SSE connection ────────────────────────────────────────────────────────────

async def sse_connect(session_id: int, session_token: str,
                      connected: list, failed: list, target: int,
                      ready_event: asyncio.Event):
    url = f"{BASE}/quizzes/sessions/{session_id}/events?session_token={session_token}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=120.0)) as c:
            async with c.stream("GET", url) as r:
                if r.status_code != 200:
                    failed.append(r.status_code)
                else:
                    connected.append(1)
                if len(connected) + len(failed) >= target and not ready_event.is_set():
                    ready_event.set()
                async for _ in r.aiter_lines():
                    pass
    except asyncio.CancelledError:
        pass
    except Exception as e:
        failed.append(str(e)[:60])
        if len(connected) + len(failed) >= target and not ready_event.is_set():
            ready_event.set()

# ── main ─────────────────────────────────────────────────────────────────────

async def main():
    host = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=50),
        timeout=httpx.Timeout(30.0),
    )

    # 1. Login
    log("Logging in as demo host…")
    token = await host_login(host)
    host.headers["Authorization"] = f"Bearer {token}"

    # 2. Start session
    log("Starting quiz session…")
    sess = await start_session(host)
    session_id = sess["id"]
    join_code   = sess["join_code"]
    log(f"Session {session_id} | join_code={join_code}")

    # Fetch questions
    qr = await host.get(f"{BASE}/quizzes/{QUIZ_ID}")
    questions = qr.json().get("questions", [])
    question_id = questions[0]["id"] if questions else None
    log(f"Quiz has {len(questions)} questions; Q1 id={question_id}")

    # Advance to Q1 before participants join
    await advance(host, session_id)
    log("Advanced to Q1.")

    # ── PHASE 1: Join ─────────────────────────────────────────────────────────
    log(f"\n=== PHASE 1: Join {N_PARTICIPANTS} participants (batches of {JOIN_BATCH}) ===")
    p_client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=JOIN_BATCH + 10, max_keepalive_connections=JOIN_BATCH),
        timeout=httpx.Timeout(10.0),
    )

    tokens = []         # list of (session_token, session_id)
    fail_reasons = {}   # reason → count
    join_times = []

    t_join0 = time.monotonic()
    for batch_start in range(0, N_PARTICIPANTS, JOIN_BATCH):
        indices = range(batch_start, min(batch_start + JOIN_BATCH, N_PARTICIPANTS))
        t0 = time.monotonic()
        results = await asyncio.gather(*[
            join_one(p_client, join_code, i) for i in indices
        ])
        elapsed = time.monotonic() - t0
        join_times.append(elapsed / len(indices))

        for tok, sid_or_err in results:
            if tok:
                tokens.append((tok, sid_or_err or session_id))
            else:
                key = str(sid_or_err)
                fail_reasons[key] = fail_reasons.get(key, 0) + 1

    t_join1 = time.monotonic()
    log(f"Joined {len(tokens)}/{N_PARTICIPANTS} in {t_join1 - t_join0:.2f}s")
    log(f"Join latency per request: avg={statistics.mean(join_times)*1000:.1f}ms  "
        f"max={max(join_times)*1000:.1f}ms  (batch averages)")
    if fail_reasons:
        for reason, cnt in sorted(fail_reasons.items(), key=lambda x: -x[1])[:5]:
            log(f"  FAIL ×{cnt}: {reason}")

    if not tokens:
        log("ERROR: zero participants joined, aborting.")
        await end_session(host, session_id)
        return

    # ── PHASE 2: SSE connections ──────────────────────────────────────────────
    log(f"\n=== PHASE 2: Open {len(tokens)} SSE connections ===")
    connected, failed_sse = [], []
    ready_event = asyncio.Event()
    target = len(tokens)

    t_sse0 = time.monotonic()
    sse_tasks = [
        asyncio.create_task(
            sse_connect(session_id, tok, connected, failed_sse, target, ready_event)
        )
        for tok, _ in tokens
    ]

    # Wait up to 30s for all connections to report in
    try:
        await asyncio.wait_for(ready_event.wait(), timeout=30.0)
    except asyncio.TimeoutError:
        log("  (timed out waiting for all SSE connections)")

    t_sse1 = time.monotonic()
    log(f"SSE connected: {len(connected)}  failed: {len(failed_sse)}  "
        f"time: {t_sse1 - t_sse0:.2f}s")
    if failed_sse:
        sample = {}
        for r in failed_sse:
            sample[str(r)] = sample.get(str(r), 0) + 1
        for reason, cnt in list(sample.items())[:5]:
            log(f"  FAIL ×{cnt}: {reason}")

    # ── PHASE 3: Simultaneous answer submission burst ─────────────────────────
    if not question_id:
        log("Skipping submission test — could not determine question_id")
    else:
        log(f"\n=== PHASE 3: {len(tokens)} simultaneous answer submissions ===")
        sub_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=N_PARTICIPANTS + 50,
                                max_keepalive_connections=N_PARTICIPANTS),
            timeout=httpx.Timeout(30.0),
        )

        t_sub0 = time.monotonic()
        results = await asyncio.gather(*[
            submit_one(sub_client, session_id, tok, question_id)
            for tok, _ in tokens
        ])
        t_sub1 = time.monotonic()

        good = [lat for lat, err in results if lat is not None]
        bad_reasons = {}
        for lat, err in results:
            if err:
                key = err[:80]
                bad_reasons[key] = bad_reasons.get(key, 0) + 1

        log(f"Submitted: {len(good)} ok / {len(results) - len(good)} failed  "
            f"wall_time={t_sub1 - t_sub0:.3f}s")
        if good:
            ms = sorted(l * 1000 for l in good)
            n  = len(ms)
            log(f"Latency (ms):  "
                f"P50={ms[n//2]:.0f}  "
                f"P90={ms[int(n*0.90)]:.0f}  "
                f"P99={ms[int(n*0.99)]:.0f}  "
                f"max={ms[-1]:.0f}")
            log(f"Throughput: {len(good)/(t_sub1 - t_sub0):.0f} req/s")
        if bad_reasons:
            for reason, cnt in sorted(bad_reasons.items(), key=lambda x: -x[1])[:5]:
                log(f"  FAIL ×{cnt}: {reason}")

        await sub_client.aclose()

    # ── Cleanup ───────────────────────────────────────────────────────────────
    log("\nCleaning up…")
    for task in sse_tasks:
        task.cancel()
    await asyncio.gather(*sse_tasks, return_exceptions=True)
    await end_session(host, session_id)
    await host.aclose()
    await p_client.aclose()
    log("Done.")


if __name__ == "__main__":
    asyncio.run(main())
