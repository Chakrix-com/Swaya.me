"""
Send Zulkarnain A. Shaikh's C11 interview question paper to nishant.verma@natwest.com
Exam: C11 Data Engineer - Screening (Quiz 202)
Score: 13/15 (86.7%) | 2 wrong: Q1 (CAS), Q4 (WAL crash recovery)
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
import re

# --- Load SMTP settings from backend/.env ---
env_path = Path(__file__).parent.parent / "backend" / ".env"
env = {}
for line in env_path.read_text().splitlines():
    m = re.match(r'^(SMTP_[A-Z_]+)\s*=\s*(.+)', line.strip())
    if m:
        env[m.group(1)] = m.group(2).strip().strip('"')

SMTP_HOST = env["SMTP_HOST"]
SMTP_PORT = int(env["SMTP_PORT"])
SMTP_USER = env["SMTP_USER"]
SMTP_PASSWORD = env["SMTP_PASSWORD"]
SMTP_FROM_EMAIL = env["SMTP_FROM_EMAIL"]
SMTP_FROM_NAME = env.get("SMTP_FROM_NAME", "Swaya")

TO_EMAIL = "nishant.verma@natwest.com"
SUBJECT = "Interview Question Paper — Zulkarnain A. Shaikh | C11 Data Engineer Screening | Score: 13/15"

HTML_BODY = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #f5f7fa; margin: 0; padding: 20px; color: #1a1a2e; }
  .container { max-width: 900px; margin: 0 auto; background: #fff; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.10); overflow: hidden; }
  .header { background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%); color: white; padding: 32px 40px; }
  .header h1 { margin: 0 0 8px 0; font-size: 22px; letter-spacing: 0.5px; }
  .header .meta { font-size: 13px; opacity: 0.85; line-height: 1.8; }
  .score-bar { display: flex; gap: 20px; padding: 20px 40px; background: #f0f4f8; border-bottom: 1px solid #dde3ea; flex-wrap: wrap; }
  .score-chip { padding: 8px 20px; border-radius: 20px; font-size: 13px; font-weight: 600; }
  .chip-total { background: #1e3a5f; color: white; }
  .chip-correct { background: #d4edda; color: #155724; }
  .chip-wrong { background: #f8d7da; color: #721c24; }
  .chip-pct { background: #fff3cd; color: #856404; }
  .section-title { font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; padding: 28px 40px 8px 40px; color: #1e3a5f; border-top: 2px solid #e8edf2; margin-top: 10px; }
  .section-title:first-of-type { border-top: none; }
  .question-block { margin: 0 30px 24px 30px; border-radius: 10px; border: 1px solid #e0e6ed; overflow: hidden; }
  .q-header { padding: 14px 20px; display: flex; align-items: center; gap: 12px; }
  .q-header.correct { background: #f0faf3; border-bottom: 1px solid #c3e6cb; }
  .q-header.wrong { background: #fff5f5; border-bottom: 1px solid #f5c6cb; }
  .q-badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
  .badge-correct { background: #28a745; color: white; }
  .badge-wrong { background: #dc3545; color: white; }
  .q-topic { font-size: 13px; font-weight: 600; color: #444; }
  .q-body { padding: 16px 20px; }
  .q-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #888; margin-bottom: 6px; margin-top: 14px; }
  .q-label:first-child { margin-top: 0; }
  .q-text { font-size: 14px; line-height: 1.7; color: #2c3e50; background: #f8f9fa; border-radius: 6px; padding: 12px 16px; border-left: 3px solid #2d6a9f; }
  .q-text.wrong-context { border-left-color: #dc3545; background: #fff8f8; }
  .loofor { font-size: 13px; line-height: 1.7; color: #444; }
  .loofor ul { margin: 4px 0 0 0; padding-left: 20px; }
  .loofor li { margin-bottom: 4px; }
  .answer-box { background: #f0faf3; border-radius: 6px; padding: 12px 16px; font-size: 13px; line-height: 1.75; color: #1d4a2a; border: 1px solid #c3e6cb; }
  .answer-box.wrong-ans { background: #fff8f0; border-color: #f5c6a0; color: #5a3310; }
  .mistake-box { background: #fff0f0; border: 1px solid #f5b8b8; border-radius: 6px; padding: 10px 14px; font-size: 13px; color: #7a1414; margin-bottom: 10px; line-height: 1.6; }
  .mistake-box strong { color: #c0392b; }
  .footer { background: #f0f4f8; padding: 18px 40px; font-size: 12px; color: #666; text-align: center; border-top: 1px solid #dde3ea; }
  code { background: #e8edf2; padding: 1px 5px; border-radius: 3px; font-family: 'Courier New', monospace; font-size: 12px; }
</style>
</head>
<body>
<div class="container">

  <!-- HEADER -->
  <div class="header">
    <h1>Technical Interview Question Paper</h1>
    <div class="meta">
      <b>Candidate:</b> Zulkarnain A. Shaikh &nbsp;|&nbsp; <b>Email:</b> zulkarnain.a.shaikh@natwest.com<br>
      <b>Role:</b> Data Engineer — C11 Cohort &nbsp;|&nbsp; <b>Exam:</b> C11 Data Engineer Screening (Quiz #202)<br>
      <b>Exam Date:</b> 22 May 2026 &nbsp;|&nbsp; <b>Duration:</b> ~48 minutes &nbsp;|&nbsp; <b>Prepared:</b> 08 Jun 2026
    </div>
  </div>

  <!-- SCORE BAR -->
  <div class="score-bar">
    <span class="score-chip chip-total">15 Questions</span>
    <span class="score-chip chip-correct">✓ 13 Correct</span>
    <span class="score-chip chip-wrong">✗ 2 Wrong</span>
    <span class="score-chip chip-pct">Score: 86.7%</span>
  </div>

  <!-- INTERVIEWER NOTE -->
  <div style="margin: 20px 30px 0 30px; padding: 14px 18px; background: #fffbea; border-radius: 8px; border: 1px solid #ffe58f; font-size: 13px; line-height: 1.7; color: #5a4a00;">
    <b>Interviewer Note:</b> Strong overall performance. Two goals for this interview:
    <br>1. <b>Verify genuine understanding</b> on correct answers — probe depth, not just recall.
    <br>2. <b>Check learning on wrong answers</b> (Q1: CAS retries; Q4: WAL durability guarantees).
    <br>Questions marked <span style="background:#dc3545;color:white;padding:1px 7px;border-radius:8px;font-size:11px;">✗ WRONG</span> carry a <i>Candidate's Mistake</i> section — use it to open a targeted discussion.
  </div>

  <!-- ======== SECTION A ======== -->
  <div class="section-title">Section A — Storage Internals (5 Questions)</div>

  <!-- Q1: HOT CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q1 &nbsp;·&nbsp; Heap-Only Tuple (HOT) Updates</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">In a row-oriented store, you update a row changing only a non-indexed column. Can you explain the two update strategies the engine might use, and under what two conditions does the more efficient "HOT-style" strategy apply? What is its key limitation in practice, and how does <code>FILLFACTOR</code> relate to it?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>HOT = Heap-Only Tuple — new row version written in-place on same page, chained to old via pointer; no index entry rewritten</li>
        <li>Two conditions: (1) updated column not indexed; (2) new row fits on the same physical page</li>
        <li>Limitation: if FILLFACTOR=100%, pages are full and HOT is impossible</li>
        <li><b>Bonus:</b> vacuum's role in cleaning HOT chains; per-page free-space map</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        HOT avoids secondary index maintenance by writing the new row version into the same heap page as the old version and chaining them via an in-page pointer. Index entries still point to the old version's physical location — readers follow the chain to find the latest version. Two hard requirements: (1) none of the updated columns appear in any secondary index (otherwise stale physical pointers in indexes would silently return wrong rows); (2) the new version must fit on the same page as the old (otherwise the chain pointer would cross pages, breaking the mechanism). FILLFACTOR controls how full each page is filled on insert — setting FILLFACTOR=70 reserves 30% of each page for future in-place updates. If FILLFACTOR=100, pages are packed; HOT becomes impossible even when both conditions hold. VACUUM is responsible for reclaiming HOT chains — it scans pages, finds chains where the old version is no longer visible to any transaction, and removes the dead tuple.
      </div>
    </div>
  </div>

  <!-- Q2: WAL CRASH RECOVERY — WRONG -->
  <div class="question-block">
    <div class="q-header wrong">
      <span class="q-badge badge-wrong">✗ Wrong</span>
      <span class="q-topic">Q2 &nbsp;·&nbsp; WAL Crash Recovery &amp; Durability Guarantee</span>
    </div>
    <div class="q-body">
      <div class="q-label">Candidate's Mistake</div>
      <div class="mistake-box">
        <b>Candidate chose:</b> "R may or may not be present — crash timing determines whether the WAL fsync completed."<br>
        <b>Correct answer:</b> "R is present — the WAL COMMIT was durably written to disk before the crash; recovery redoes the write."<br>
        <b>Root cause:</b> The question explicitly states the crash occurs <em>after</em> COMMIT is fsynced. The candidate seems to doubt WAL's durability guarantee once COMMIT is on disk, or misread the timing condition. This is a critical concept gap for a data engineer — probe carefully.
      </div>
      <div class="q-label">Interview Question</div>
      <div class="q-text wrong-context">A WAL contains three entries in order: [BEGIN], [DATA: record R], [COMMIT] — all three were fsynced to disk before the process crashed. The page_buffer write had not yet occurred. After recovery, is record R in the database? Walk me through the exact recovery sequence. Now: what if the crash had happened after [DATA] was fsynced but before [COMMIT] was written — what would recovery do then?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Clearly states: COMMIT fsynced = durable = R is guaranteed present after recovery</li>
        <li>Recovery sequence: scan WAL; for entries with a matching COMMIT marker → redo (replay to storage); for entries without COMMIT → skip/discard</li>
        <li>Pre-COMMIT crash: no COMMIT in WAL → incomplete transaction → record discarded</li>
        <li>Explains that page_buffer is an optimization, not the source of durability — WAL is the source of truth</li>
        <li><b>Bonus:</b> fuzzy checkpoints, LSN (Log Sequence Number), WAL archiving</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box wrong-ans">
        R is present after recovery — guaranteed. The WAL COMMIT marker was durably fsynced to disk before the crash. During recovery, the engine scans the WAL file and applies the redo rule: any log entry that has a corresponding durable COMMIT marker is replayed to storage. Since [COMMIT] for record R is on disk, the recovery process replays [DATA: R] to the main storage files. The page_buffer write is purely an optimization — it keeps recently-written records in RAM to avoid re-reading from WAL on the hot path. Durability is established by the WAL COMMIT, not by the page_buffer flush. If the crash had occurred after [DATA] was fsynced but before [COMMIT] was written, recovery would find no COMMIT marker for that entry and would discard it — leaving no trace of R. This asymmetry is intentional: it enforces atomicity (all-or-nothing) at the WAL level.
      </div>
    </div>
  </div>

  <!-- Q3: WAL REPLICATION SLOT CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q3 &nbsp;·&nbsp; WAL Replication Slots &amp; Disk Growth</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">You're on-call. A PagerDuty alert fires: "PostgreSQL WAL directory at 95% disk capacity." The primary has 5 replication slots. How do you diagnose which slot is causing this? What's the immediate fix, and what configuration prevents it recurring? What monitoring query would have caught this earlier?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Check <code>pg_replication_slots</code> for <code>active=false</code> and large <code>(pg_current_wal_lsn() - restart_lsn)</code></li>
        <li>Immediate fix: <code>SELECT pg_drop_replication_slot('stale_slot_name')</code></li>
        <li>Prevention: <code>max_slot_wal_keep_size</code> in postgresql.conf</li>
        <li>Monitoring: alert when any inactive slot's lag exceeds threshold (e.g., 20 GB)</li>
        <li><b>Bonus:</b> difference between <code>wal_keep_size</code> and slot-held WAL</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        Diagnosis: <code>SELECT slot_name, active, restart_lsn, pg_current_wal_lsn() - restart_lsn AS lag_bytes FROM pg_replication_slots ORDER BY lag_bytes DESC;</code> — any slot with <code>active=false</code> and large lag_bytes is holding WAL accumulation. Immediate fix: drop the stale slot — <code>SELECT pg_drop_replication_slot('slot_name');</code> — WAL GC runs automatically and reclaims the held WAL. Prevention: set <code>max_slot_wal_keep_size = '20GB'</code> in postgresql.conf — any slot that accumulates more than 20 GB of WAL is automatically invalidated, preventing unbounded growth (the subscriber must resync from scratch, but the primary survives). Note: this is different from <code>wal_keep_size</code>, which only controls WAL retained between checkpoints — slot-held WAL overrides it. Monitoring: alert when <code>(pg_current_wal_lsn() - restart_lsn) > 10GB</code> on any slot — that's the early warning. A runbook link in the alert helps on-call engineers act without diving into docs.
      </div>
    </div>
  </div>

  <!-- Q4: CHECK-THEN-ACT CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q4 &nbsp;·&nbsp; Check-Then-Act Race Condition</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">You're reviewing a PR for a payment deduplication service. The developer has added a unique constraint on <code>payment_id</code> and says: "The DB will throw a constraint error on duplicate insert — we're safe." The code still calls <code>notify_payment_processed()</code> unconditionally after <code>db.insert()</code>. Is the unique constraint alone sufficient? What's still wrong, and what is the minimal one-line fix?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Unique constraint stops duplicate inserts — but <code>notify_payment_processed()</code> fires before the insert result is checked</li>
        <li>Both threads can call notify before either's insert completes → double notification</li>
        <li>Fix: only call notify <em>if</em> the insert succeeded (catch duplicate key exception)</li>
        <li><b>Bonus:</b> idempotency keys on downstream services as defense-in-depth; database-level SELECT FOR UPDATE</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        Not sufficient. The unique constraint stops the second <code>db.insert()</code> from completing, but <code>notify_payment_processed()</code> is called <em>before</em> the insert result is checked. In the race: Thread A and B both pass the <code>exists()</code> check, both call <code>run_payment()</code>, both call <code>db.insert()</code> — and both call <code>notify_payment_processed()</code> before the constraint fires on the second insert. By the time the DB rejects the duplicate, the notification has already been sent twice. The minimal fix: wrap <code>db.insert()</code> in a try/except, and only call <code>notify_payment_processed()</code> if the insert succeeded without a duplicate-key error. The pattern: check-then-act is not atomic — a DB-level constraint enforces uniqueness, but side effects (notifications, charges, emails) must be gated on the insert outcome, not assumed safe after a pre-check.
      </div>
    </div>
  </div>

  <!-- Q5: Iceberg CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q5 &nbsp;·&nbsp; Iceberg Metadata Pruning (3-Level Hierarchy)</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">An Iceberg table has 3 years of daily partitions, ~500M rows. A query runs <code>WHERE event_date BETWEEN '2024-01-01' AND '2024-03-31' AND user_id = 12345</code>. Walk me through the exact pruning sequence. At which metadata level is each predicate applied, and what statistics are stored at each level that make this possible? What is the limitation of column-stats pruning for the <code>user_id</code> predicate?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Level 1 (manifest list): partition-level bounds eliminate ~90% of manifest entries for <code>event_date</code></li>
        <li>Level 2 (manifest files): per-data-file column min/max statistics used to prune on <code>user_id</code></li>
        <li>Level 3 (Parquet files): row-group statistics for further pruning</li>
        <li>Limitation: <code>user_id</code> is not a partition key → cannot be pruned at manifest list level; column stats are approximate (files where min ≤ 12345 ≤ max are opened even if they don't contain it)</li>
        <li><b>Bonus:</b> Iceberg v2 row-level deletes (equality deletes vs position deletes)</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        Pruning happens in 3 stages: (1) <b>Manifest list</b> (tiny Avro file, one entry per manifest): each entry stores <code>lower_bound</code> and <code>upper_bound</code> for <code>event_date</code>. Entries outside the date range are skipped without opening the manifest file — ~90% of entries eliminated in one scan of a KB-sized file. (2) <b>Manifest files</b> (Avro, one per day's data files): each entry stores column-level statistics (min, max, null count) per data file. The planner scans these to prune files where <code>max(user_id) &lt; 12345</code> or <code>min(user_id) &gt; 12345</code>. (3) <b>Parquet data files</b>: row-group statistics provide finer pruning before actual page reads. Limitation for <code>user_id</code>: because it's not a partition key, it can't be pruned at the manifest list level. Column stats pruning at the manifest file level is approximate — a file where min ≤ 12345 ≤ max is opened even if 12345 doesn't exist in that file. Without Z-order or data clustering on <code>user_id</code>, most data files survive the stats filter. Iceberg's <code>ORDER BY</code> / Z-ordering on write significantly improves selectivity here.
      </div>
    </div>
  </div>

  <!-- ======== SECTION B ======== -->
  <div class="section-title">Section B — Distributed Systems &amp; Concurrency (6 Questions)</div>

  <!-- Q6: CAS — WRONG -->
  <div class="question-block">
    <div class="q-header wrong">
      <span class="q-badge badge-wrong">✗ Wrong</span>
      <span class="q-topic">Q6 &nbsp;·&nbsp; Compare-and-Swap (CAS) &amp; Lost Updates</span>
    </div>
    <div class="q-body">
      <div class="q-label">Candidate's Mistake</div>
      <div class="mistake-box">
        <b>Candidate chose:</b> "Exactly 3 only if all three threads start before any single CAS succeeds."<br>
        <b>Correct answer:</b> "Exactly 3 — each thread eventually wins one CAS; the retry loop ensures all three increments are applied."<br>
        <b>Root cause:</b> Candidate understands CAS gives a deterministic final value, but adds an incorrect timing condition. This suggests he may confuse a <em>failed CAS</em> (which retries) with a <em>lost update</em> (which doesn't retry). Probe the retry semantics carefully.
      </div>
      <div class="q-label">Interview Question</div>
      <div class="q-text wrong-context">Thread A and Thread B both read <code>{value: 0, version: 0}</code>. Thread A's CAS succeeds and sets <code>{value: 1, version: 1}</code>. Thread B's CAS fails because the version has changed. What does Thread B do next? Is Thread B's increment lost? If 1,000 threads all call <code>increment()</code> simultaneously, what is the <em>guaranteed</em> final value, and why? What is the performance risk of this approach under very high contention?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Thread B retries: re-reads current state <code>{value:1, version:1}</code>, retries CAS — not lost</li>
        <li>1,000 threads → final value = 1,000, deterministically (each thread wins exactly one CAS)</li>
        <li>Performance risk: high contention → many retries → livelock-like spinning, though eventual progress is guaranteed for increment</li>
        <li><b>Bonus:</b> compare with mutex (one proceeds, others sleep vs all spinning); hardware-level CAS atomicity; ABA problem</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box wrong-ans">
        Thread B's CAS fails because the version changed — it immediately re-reads the current counter state <code>{value:1, version:1}</code> and retries the CAS. A failed CAS is a <em>deferred</em> increment, not a lost one. The retry loop guarantees that every caller eventually wins a CAS — their increment is never discarded. With 1,000 threads, the final value is deterministically 1,000: each thread runs through the loop, retries on contention, and eventually gets a moment where no other thread simultaneously wins a CAS, so its own CAS succeeds. The result is exactly equal to the number of callers, regardless of contention level. Performance risk: under extreme contention (thousands of threads on a single counter), most threads retry many times — effectively spinning. This is bounded (threads do make progress), but throughput degrades compared to a mutex (where only one thread runs, others sleep). CAS is ideal for low-to-moderate contention; a centralized counter with mutex or a partitioned/sharded counter is better under very high write rates. Note: the timing of when threads start relative to each other has no bearing on the final value — this is the key insight the exam question was testing.
      </div>
    </div>
  </div>

  <!-- Q7: DISTRIBUTED LEASE CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q7 &nbsp;·&nbsp; Distributed Lease &amp; Fencing Token</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">You need distributed mutual exclusion for a pipeline that writes to S3 — only one node should write at a time. You're using a Redis-based lease (TTL = 30s). A GC pause of 45s can occur. Design the fencing token mechanism. How does S3 (which doesn't natively support fencing) enforce exclusion in this design?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Fencing token = monotonically increasing integer issued with each new lease acquisition</li>
        <li>Node includes the token in every write request</li>
        <li>A serialization layer (not S3 itself) tracks max_seen_token and rejects writes with stale tokens</li>
        <li>Acknowledges that S3 lacks native fencing — needs DynamoDB conditional writes or a custom proxy layer</li>
        <li><b>Bonus:</b> S3 conditional writes (If-Match on ETag) for object-level mutual exclusion</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        Redis lease + fencing token: each successful lock acquisition increments a Redis counter (via <code>INCR</code>) to get a monotonically increasing token — e.g., Node A gets token=7 when it acquires the lease. When Node A writes to S3, it includes token=7 in the request metadata. A serialization layer (e.g., a DynamoDB item with <code>max_seen_token</code> attribute, updated via conditional write) enforces: only process writes where <code>token ≥ max_seen_token</code>. If Node A's process pauses 45s, the lease expires, Node B acquires it with token=8, and writes with token=8 — updating max_seen_token to 8. When Node A resumes with token=7, any write attempt is rejected by the DynamoDB conditional check. S3 itself is a dumb object store — the enforcement must happen in a wrapper around S3 (or use S3's own <code>If-Match</code> / <code>If-None-Match</code> conditional headers for object-level coordination, which are atomic). The key property: fencing works even if the paused node doesn't know its lease has expired.
      </div>
    </div>
  </div>

  <!-- Q8: RAFT CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q8 &nbsp;·&nbsp; Raft Consensus — Partition &amp; Log Safety</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">A 5-node Raft cluster {A (leader, term 5), B, C, D, E} is network-partitioned into {A,B} and {C,D,E}. A client write arrives at A. Walk through: (1) can A commit this write? (2) what happens in {C,D,E}? (3) when the partition heals, A discovers the new leader — what happens to A's uncommitted entry? What if A had committed an entry (gotten 3 acks) just before the partition?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>{A,B} = 2 nodes, quorum = 3 → A cannot commit; the write stays pending in A's log</li>
        <li>{C,D,E} elect a new leader at term ≥ 6</li>
        <li>On partition heal: A sees a higher-term leader → steps down; A's uncommitted entry is overwritten</li>
        <li>If A had committed (3 acks): at least one of {C,D,E} has that entry; election safety ensures new leader has it; it's preserved</li>
        <li><b>Bonus:</b> pre-vote protocol; leader completeness property; AppendEntries conflict resolution</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        (1) A cannot commit: quorum = 3 (majority of 5), but {A,B} is only 2 nodes. A sends AppendEntries to B, gets 1 ack (itself + B = 2) — not a majority. The write sits as an uncommitted entry in A's log. A keeps retrying but cannot advance the commit index. (2) {C,D,E} has 3 nodes — a quorum. They detect no heartbeat from A, start an election at term 6 (higher than A's term 5). The candidate with the most up-to-date log (latest term and length) wins. A new leader is elected and begins serving requests. (3) When the partition heals: A receives an AppendEntries or RequestVote RPC with term 6+ — higher than its term 5. Raft rule: any node that sees a higher term immediately reverts to follower. A adopts the new leader, and the leader's AppendEntries overwrites A's uncommitted pending entry with the correct log. If A had committed an entry before the partition (3 acks = majority), at least one of {C,D,E} has it (since majority intersection guarantees overlap). Raft's Leader Completeness property ensures the newly elected leader also has it — so it's never lost.
      </div>
    </div>
  </div>

  <!-- Q9: LAMPORT/VECTOR CLOCKS CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q9 &nbsp;·&nbsp; Lamport &amp; Vector Clocks</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">Three processes P1, P2, P3 each start with vector clock [0,0,0]. P1 sends a message to P2 (P1's clock at send: [1,0,0]). P2 receives it, then sends a message to P3. What is P2's vector clock at the send event? What is P3's vector clock after receiving? If we now observe event E on P1 with V(E)=[3,0,0] and event F on P3 with V(F)=[1,2,1] — what is the causal relationship between E and F, and how do you determine it?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>P2 on receive: <code>max([1,0,0],[0,1,0]) + P2 increment = [1,1,0]</code> (then <code>[1,2,0]</code> on send)</li>
        <li>P3 on receive: <code>max([1,2,0],[0,0,1]) + P3 increment = [1,2,1]</code> (or <code>[1,2,2]</code> on receive + increment)</li>
        <li>V(E)=[3,0,0] vs V(F)=[1,2,1]: V(E)[0]=3 > V(F)[0]=1 → E does not precede F; V(F)[1]=2 > V(E)[1]=0 → F does not precede E → concurrent</li>
        <li>Rule: V(A) &lt; V(B) iff ∀i: V(A)[i] ≤ V(B)[i] and ∃j: V(A)[j] &lt; V(B)[j]</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        P1 sends with clock [1,0,0]. P2 receives: apply receive rule — component-wise max([1,0,0], P2's current [0,0,0]) = [1,0,0], then increment P2's own component → [1,1,0]. P2 sends at [1,2,0] (increment own before send). P3 receives: max([1,2,0],[0,0,0]) = [1,2,0], increment P3 → [1,2,1].
        <br><br>
        For V(E)=[3,0,0] vs V(F)=[1,2,1]: apply the dominance check: E &lt; F requires <em>all</em> V(E)[i] ≤ V(F)[i] — but V(E)[0]=3 > V(F)[0]=1, so E does not causally precede F. F &lt; E requires all V(F)[i] ≤ V(E)[i] — but V(F)[1]=2 > V(E)[1]=0, so F does not causally precede E. Neither dominates the other → E and F are <em>concurrent</em>: no causal relationship. This is the key advantage of vector clocks over Lamport timestamps: Lamport can tell you <em>if</em> causality might exist (L(A) &lt; L(B) is necessary but not sufficient), but vector clocks give you the <em>exact and complete</em> causal relationship.
      </div>
    </div>
  </div>

  <!-- Q10: SAGA CHOREOGRAPHY CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q10 &nbsp;·&nbsp; Saga — Choreography vs Orchestration</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">You're designing a refund workflow across 4 services: payment, inventory, notification, ledger. A junior engineer proposes choreography. You raise the "lost saga" problem. How would you detect and recover from a stuck saga in a choreography-based design without switching to orchestration? And what does an orchestration approach (e.g., Temporal) give you that choreography fundamentally cannot?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Choreography detection: a saga monitor service tracks expected event sequences with timeouts; alerts on missing events</li>
        <li>Recovery in choreography: dead-letter queue handler emits compensating events; requires idempotency since events may re-arrive</li>
        <li>Orchestration (Temporal/Step Functions): durable workflow state machine; compensation is explicit and guaranteed; debugging is trivial (single workflow trace)</li>
        <li>Fundamental limit of choreography: no single place has the full saga state — distributed state across services</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        In choreography, detecting a stuck saga requires a dedicated saga monitor: subscribe to all domain events, track saga state per <code>saga_id</code> in a DB table (state machine: <code>payment_reserved → stock_reserved → fraud_checked → ...</code>), and set timeouts. If <code>FraudApproved</code> or <code>FraudRejected</code> doesn't arrive within 60 seconds after <code>StockReserved</code>, the monitor emits compensating events: <code>StockReleased</code> and <code>PaymentCancelled</code>. These must be idempotent — the downstream services may have already compensated if they received a late event. This monitor is effectively a hand-rolled orchestrator.
        <br><br>
        Orchestration (Temporal): the entire saga is a durable function. <code>workflow.execute_activity("reserve_payment") → execute_activity("reserve_stock") → execute_activity("check_fraud")</code>. If step 3 times out, the orchestrator automatically calls <code>execute_activity("cancel_stock")</code> and <code>execute_activity("cancel_payment")</code> — retrying until they succeed. The workflow's complete execution history is persisted after each step — a crash mid-saga is fully recoverable. You get a single execution trace per saga for debugging. The fundamental difference: in choreography, saga state is implicit (inferred from the event stream); in orchestration, it's explicit and durable in one place.
      </div>
    </div>
  </div>

  <!-- Q11: SPANNER TRUETIME CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q11 &nbsp;·&nbsp; Spanner TrueTime &amp; External Consistency</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">Spanner's commit-wait adds up to 2ε (~2–14ms) per write transaction. A colleague argues: "Read-only transactions don't commit, so they don't need commit-wait — they're safe from linearizability violations." Is this correct? Where exactly does the commit-wait overhead sit in Spanner's transaction flow, and what guarantee does it provide to read-only transactions started <em>after</em> a write commits?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Colleague is correct: read-only transactions don't commit → no commit-wait for them</li>
        <li>Commit-wait sits on the writer side: writer waits until <code>TT.now().earliest > ts1</code> before making T1 visible</li>
        <li>Guarantee to subsequent readers: any transaction starting after T1 is visible gets <code>ts2 = TT.now().latest > ts1</code> — it will see T1's writes</li>
        <li><b>Bonus:</b> HLC (Hybrid Logical Clock) as an alternative; Spanner's GPS + atomic clock infrastructure to minimize ε</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        The colleague is correct but for a nuanced reason. Commit-wait is a burden on read-write transactions only — it sits between "write committed to Paxos" and "write made visible to readers." Read-only transactions choose a read timestamp from TrueTime (<code>TT.now().latest</code>) and read a consistent snapshot at that time — no commit, no commit-wait.
        <br><br>
        What commit-wait guarantees to subsequent readers: when T1 (a write) commits at timestamp <code>ts1 = TT.now().latest</code>, Spanner holds it invisible until <code>TT.now().earliest > ts1</code>. This means the true current time is provably past ts1 everywhere. Any transaction T2 that starts after T1 is externally visible (i.e., T2 starts after T1's commit-wait completes) will receive <code>ts2 = TT.now().latest</code>. Since TT.now().latest ≥ actual current time ≥ ts1 + ε, we have <code>ts2 > ts1</code> — T2's snapshot includes T1's writes. This is external consistency (linearizability): if T1 commits before T2 starts in real time, T2 sees T1's writes. Skipping commit-wait would allow a T2 on a slightly-lagged node to receive <code>ts2 < ts1</code>, making T1 invisible to T2 — a direct linearizability violation.
      </div>
    </div>
  </div>

  <!-- ======== SECTION C ======== -->
  <div class="section-title">Section C — Data Platforms &amp; Systems (4 Questions)</div>

  <!-- Q12: HUDI CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q12 &nbsp;·&nbsp; Hudi MoR vs CoW for CDC Workloads</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">You're building a Hudi pipeline for a 50 TB IoT table — 95% INSERTs, 5% UPDATEs, 10 K events/second. Your manager then says the ratio will flip next quarter to 95% UPDATEs at 200 K/s. Compare CoW and MoR for both workloads, and describe the compaction configuration you'd set for MoR. What does the read-latency trade-off look like between compaction runs?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>INSERT-heavy: CoW acceptable (inserts = new files, no rewrites); MoR also works but adds complexity</li>
        <li>UPDATE-heavy at 200K/s: CoW is unsuitable — each update batch rewrites entire base Parquet files across many partitions → write latency compounds</li>
        <li>MoR compaction config: <code>hoodie.compact.inline=false</code> on ingestion; separate scheduled Spark compaction job</li>
        <li>Read trade-off: real-time view merges base + delta logs at query time; more uncompacted logs = higher read latency</li>
        <li><b>Bonus:</b> Z-ordering / clustering for read performance; file-size tuning to avoid the small-files problem</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        INSERT-heavy (95% inserts, 10K/s): CoW is straightforward — inserts write new Parquet files, and the 5% updates rewrite a small fraction of existing files. Read performance is excellent (no merge at read time). MoR is also viable but adds compaction overhead without much benefit at this write rate.
        <br><br>
        UPDATE-heavy flip (95% updates, 200K/s): CoW breaks — every micro-batch touches existing files across hundreds of partitions. Each CoW rewrite is O(base file size), not O(records updated). At 200K/s with 80% updates, you'd be continuously rewriting 10s of GB of Parquet per second — ingestion falls behind permanently. MoR is the only viable choice: updates are appended as delta Avro log files (O(records written)), keeping ingestion fast.
        <br><br>
        Compaction config: on the ingestion job, set <code>hoodie.compact.inline=false</code> to prevent compaction from blocking ingestion. Run a separate scheduled Spark job every 30–60 minutes with <code>hoodie.compact.inline=true</code>. Read trade-off: between compaction runs, Hudi's real-time view must merge base Parquet + all uncompacted delta log files at query time. At 200K/s × 60 min = ~720M log records per hour, the number of log files per file group grows — each additional log file adds merge overhead on the read path. Keep compaction frequent enough that no file group has >10 log files.
      </div>
    </div>
  </div>

  <!-- Q13: NUMA CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q13 &nbsp;·&nbsp; NUMA Architecture &amp; Memory Binding</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">Your Spark job on a 4-socket server uses <code>-XX:+UseNUMA</code>. A profiler shows GC threads on node 0 are allocating from node 2's memory 40% of the time. Why might <code>-XX:+UseNUMA</code> alone be insufficient? What is the correct combined command to pin both thread scheduling and heap allocation to node 0 for this executor?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li><code>-XX:+UseNUMA</code> only makes JVM allocate from the NUMA node of the <em>current</em> running CPU — if the OS migrates threads across NUMA nodes, allocations follow the wrong node</li>
        <li>Without OS-level pinning (<code>numactl</code> or cgroups cpuset), the OS scheduler can freely move threads</li>
        <li>Correct fix: <code>numactl --cpunodebind=0 --membind=0 java -XX:+UseNUMA -jar executor.jar</code></li>
        <li><b>Bonus:</b> <code>numactl --interleave=all</code> for workloads larger than one NUMA node's memory; <code>numastat</code> to measure cross-NUMA traffic</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        <code>-XX:+UseNUMA</code> tells the JVM to allocate from the NUMA node of whichever CPU the current thread is running on. This works only if threads stay pinned to a single NUMA node. Without OS-level binding, the Linux scheduler is free to migrate threads to any available CPU — potentially on a different NUMA socket. When a GC thread migrates from node 0 to node 2, its next allocation goes to node 2's DRAM. The JVM cannot override OS-level scheduling without help.
        <br><br>
        Correct command: <code>numactl --cpunodebind=0 --membind=0 java -XX:+UseNUMA -jar executor.jar</code>. <code>--cpunodebind=0</code> restricts thread scheduling to CPUs on NUMA node 0; <code>--membind=0</code> restricts all <code>mmap()</code> and <code>malloc()</code> calls to node 0's DRAM. Together they ensure local memory access. <code>-XX:+UseNUMA</code> then optimizes intra-JVM allocation for multi-region GC. To measure whether cross-NUMA traffic drops: run <code>numastat -p &lt;java_pid&gt;</code> before and after — compare <code>numa_miss</code> counts.
      </div>
    </div>
  </div>

  <!-- Q14: io_uring CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q14 &nbsp;·&nbsp; io_uring SQPOLL &amp; Zero-Syscall I/O</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">A file ingestion service uses <code>io_uring</code> with <code>IORING_SETUP_SQPOLL</code>. At low traffic (&lt;100 ops/sec) there's no latency improvement over epoll. At high traffic (10K+ ops/sec) it's significantly faster. Explain the exact mechanism for this difference. If you had to serve <em>both</em> traffic levels efficiently, what design would you use?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Low traffic: SQPOLL kthread goes to sleep after <code>sq_thread_idle</code> ms of inactivity; app must call <code>io_uring_enter()</code> to wake it → same cost as epoll</li>
        <li>High traffic: kthread is continuously spinning → picks up SQEs with zero syscall → benefit materializes</li>
        <li>Dual-mode design: SQPOLL ring for high-throughput I/O class; non-SQPOLL (interrupt-driven) ring for bursty/low-priority I/O; route requests based on expected rate</li>
        <li><b>Bonus:</b> <code>sq_thread_idle</code> tuning; <code>IORING_SQ_NEED_WAKEUP</code> flag check; liburing's <code>io_uring_submit()</code> handling this automatically</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        The difference is the SQPOLL kthread's sleep behavior. In SQPOLL mode, the kernel spawns a kthread that continuously polls the submission ring — the app writes SQEs via mmap and the kthread picks them up with zero syscalls. However, a permanently spinning kthread wastes a CPU core. To mitigate this, the kthread sleeps after <code>sq_thread_idle</code> ms of no new submissions (default ~1 second). At low traffic, the kthread is almost always asleep — the app must check <code>IORING_SQ_NEED_WAKEUP</code> and call <code>io_uring_enter(fd, 0, 0, IORING_ENTER_SQ_WAKEUP)</code> to wake it. This syscall eliminates the zero-syscall benefit — same overhead as epoll. At high traffic, the kthread never sleeps, SQEs are consumed immediately, and no wakeup syscall is needed.
        <br><br>
        Dual-mode design: create two io_uring rings — one with SQPOLL (for high-throughput paths, e.g., bulk file reads) and one without (interrupt-driven, for low-rate or latency-sensitive I/O). Route requests to the appropriate ring based on expected rate or I/O class. Alternatively, set a very low <code>sq_thread_idle</code> (e.g., 10ms) to keep the kthread active during bursty intervals, accepting the CPU cost during idle gaps — this reduces wakeup latency at the cost of wasted cycles.
      </div>
    </div>
  </div>

  <!-- Q15: CGROUPS OOM CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q15 &nbsp;·&nbsp; cgroups v2 OOM Killer &amp; Container Memory</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">A Kubernetes pod running a Spark executor is OOM-killed. The JVM is set to <code>-Xmx6g</code> and the pod limit is <code>8Gi</code>. Why might the pod be OOM-killed despite the apparent 2GB headroom? Trace the exact kernel sequence from the moment the container's memory usage hits the cgroup limit. How does Kubernetes' default <code>memory.memsw.max</code> setting affect whether the container can use swap?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>JVM off-heap: metaspace, direct memory (Netty/Parquet), thread stacks, code cache, native libs → can consume 1.5–3 GB</li>
        <li>OOM sequence: (1) page-cache reclaim within cgroup; (2) if reclaim fails → OOM killer scores processes in cgroup; (3) SIGKILL to highest <code>oom_score</code> process</li>
        <li>Kubernetes default: <code>memory.memsw.max = memory.max</code> → no swap allowed (swap effectively disabled)</li>
        <li>Fix: set <code>-Xmx</code> to 70–75% of pod limit; use <code>-XX:NativeMemoryTracking=detail</code> to measure off-heap</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        The 2 GB headroom is consumed by JVM off-heap memory: (1) metaspace — class metadata for large Spark jobs: 500 MB–1 GB; (2) direct memory — <code>ByteBuffer.allocateDirect()</code> used by Netty (Spark's RPC layer) and Parquet readers: can reach 1–2 GB; (3) thread stacks — each thread ~512 KB, Spark executors run 100+ threads; (4) code cache — JIT-compiled methods: 200–500 MB; (5) native libraries: libsnappy, liblz4, Arrow. Total off-heap easily 1.5–3 GB, pushing total RSS past the 8 GB limit.
        <br><br>
        Kernel OOM sequence: (1) The kernel's memory reclaim path fires — it tries to drop clean page cache and shrink the cgroup's memory usage below <code>memory.max = 8 GB</code>. (2) If reclaim fails (no reclaimable pages), the cgroup-scoped OOM killer runs — it computes <code>oom_score</code> for all processes in the cgroup (proportional to memory usage, adjusted by <code>oom_score_adj</code>) and sends <code>SIGKILL</code> to the process with the highest score — typically the JVM. The kernel logs this to <code>dmesg</code> / <code>journalctl</code>.
        <br><br>
        Kubernetes default: <code>memory.memsw.max = memory.max = 8 GB</code> (pod limit). Since RAM + swap is capped at the same value as RAM alone, the container effectively cannot use any swap — any allocation that would spill to swap hits the combined limit immediately. Fix: set <code>-Xmx4g</code> (not 6g) for an 8 GB pod limit, leaving ~4 GB for JVM overhead. Use <code>-XX:NativeMemoryTracking=detail</code> and <code>jcmd &lt;pid&gt; VM.native_memory</code> to profile off-heap consumption.
      </div>
    </div>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    Generated from Swaya.me screening platform &nbsp;·&nbsp; Quiz #202: C11 Data Engineer Screening &nbsp;·&nbsp; Exam date: 22 May 2026
    <br>This document is confidential and intended for the interviewer only.
  </div>

</div>
</body>
</html>
"""

def send_email():
    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(HTML_BODY, "html"))

    context = ssl.create_default_context()
    print(f"Connecting to {SMTP_HOST}:{SMTP_PORT} ...")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, TO_EMAIL, msg.as_string())
    print(f"Email sent successfully to {TO_EMAIL}")

if __name__ == "__main__":
    send_email()
