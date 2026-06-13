"""
Send Swarna Kamal Dey's C11 interview question paper to nishant.verma@natwest.com
Exam: C11 Data Engineer - Screening (Quiz 202)
Score: 14/15 (93.3%) | 1 wrong: Q1 (CAS — believed final value nondeterministic)
Completion time: ~14 minutes (flag for interviewer)
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
import re

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
SUBJECT = "Interview Question Paper — Swarna Kamal Dey | C11 Data Engineer Screening | Score: 14/15"

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
  .chip-time { background: #e8d5f7; color: #5a0f80; }
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
      <b>Candidate:</b> Swarna Kamal Dey &nbsp;|&nbsp; <b>Email:</b> swarna.kamaldey@natwest.com<br>
      <b>Role:</b> Data Engineer — C11 Cohort &nbsp;|&nbsp; <b>Exam:</b> C11 Data Engineer Screening (Quiz #202)<br>
      <b>Exam Date:</b> 22 May 2026 &nbsp;|&nbsp; <b>Duration: ~14 minutes</b> &nbsp;|&nbsp; <b>Prepared:</b> 08 Jun 2026
    </div>
  </div>

  <!-- SCORE BAR -->
  <div class="score-bar">
    <span class="score-chip chip-total">15 Questions</span>
    <span class="score-chip chip-correct">✓ 14 Correct</span>
    <span class="score-chip chip-wrong">✗ 1 Wrong</span>
    <span class="score-chip chip-pct">Score: 93.3%</span>
    <span class="score-chip chip-time">⏱ ~14 min completion</span>
  </div>

  <!-- INTERVIEWER NOTE -->
  <div style="margin: 20px 30px 0 30px; padding: 14px 18px; background: #fffbea; border-radius: 8px; border: 1px solid #ffe58f; font-size: 13px; line-height: 1.7; color: #5a4a00;">
    <b>Interviewer Note:</b> Exceptional screening result — 14/15 (93.3%). Two specific things to probe:
    <br>1. <b>Speed flag:</b> Completed 15 highly technical questions in approximately <b>14 minutes</b> (&lt;1 min/question). This is unusually fast. Probe depth early — either she has deep, instant recall of these topics (strong signal) or she made educated guesses (verify via open-ended explanations).
    <br>2. <b>CAS misconception:</b> Her one wrong answer (Q1) reveals a fundamental misunderstanding of CAS retry semantics — she believed concurrent CAS leaves the final value <em>nondeterministic</em>. Probe directly.
    <br>Questions marked <span style="background:#dc3545;color:white;padding:1px 7px;border-radius:8px;font-size:11px;">✗ WRONG</span> carry a <i>Candidate's Mistake</i> section.
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
      <div class="q-text">In a row-oriented store, you update a row changing only a non-indexed column. Explain the two update strategies the engine might use, and under what two conditions the more efficient "HOT-style" strategy applies. What is its key limitation in practice, and how does <code>FILLFACTOR</code> relate to it?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>HOT = Heap-Only Tuple — new row version written in-place on same page, chained to old; no index entry rewritten</li>
        <li>Two conditions: (1) updated column not indexed; (2) new row version fits on the same physical page</li>
        <li>Limitation: FILLFACTOR=100 fills pages completely — no space for HOT, so even qualifying updates fall back to Strategy A</li>
        <li><b>Bonus:</b> VACUUM's role in cleaning HOT chains; free-space map; fillfactor tuning (70–80%) for UPDATE-heavy tables</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        HOT avoids secondary index maintenance by writing the new row version into the same heap page as the old version and chaining them via an in-page pointer. Index entries still point to the old version's physical location — readers follow the chain to find the latest version. Two hard requirements: (1) none of the updated columns appear in any secondary index (otherwise stale physical pointers in indexes would silently return wrong rows); (2) the new version must fit on the same page as the old (otherwise the chain pointer would cross pages, breaking the mechanism). FILLFACTOR controls how full each page is filled at insert time — setting FILLFACTOR=70 reserves 30% of each page for future in-place updates. If FILLFACTOR=100, pages are packed and HOT becomes impossible even when both conditions hold. VACUUM reclaims HOT chains by scanning pages, finding chains where the old version is no longer visible to any transaction, and removing the dead tuple.
      </div>
    </div>
  </div>

  <!-- Q2: CAS — WRONG -->
  <div class="question-block">
    <div class="q-header wrong">
      <span class="q-badge badge-wrong">✗ Wrong</span>
      <span class="q-topic">Q2 &nbsp;·&nbsp; Compare-and-Swap (CAS) &amp; Retry Semantics</span>
    </div>
    <div class="q-body">
      <div class="q-label">Candidate's Mistake</div>
      <div class="mistake-box">
        <b>Candidate chose:</b> "Could be 1, 2, or 3 — concurrent CAS leaves the final value nondeterministic."<br>
        <b>Correct answer:</b> "Exactly 3 — each thread eventually wins one CAS; the retry loop ensures all three increments are applied."<br>
        <b>Root cause:</b> Swarna believes CAS under concurrency is equivalent to a non-atomic operation where updates can be silently lost — she treats CAS failure as a lost increment. This is a fundamental misunderstanding of CAS retry semantics. Note: a failed CAS triggers an immediate retry, not a dropped update. The guarantee is exactly equal to the number of callers, deterministically.
      </div>
      <div class="q-label">Interview Question</div>
      <div class="q-text wrong-context">Walk me through the exact lifecycle of a single CAS call that fails. Thread A and Thread B both read <code>{value: 0, version: 0}</code>. Thread A wins the CAS and sets <code>{value: 1, version: 1}</code>. Thread B's CAS fails. What happens to Thread B's increment — is it lost? If 1,000 threads all call <code>increment()</code> simultaneously with this retry loop, what is the <em>guaranteed</em> final value and why? What is the worst-case performance problem with this approach?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>A failed CAS triggers a retry — the increment is deferred, not lost</li>
        <li>Thread B re-reads current state <code>{value:1, version:1}</code> and retries; eventually it wins a CAS slot</li>
        <li>1,000 threads → final value = 1,000, deterministically — each thread wins exactly one CAS</li>
        <li>Performance risk: very high contention → many retries → spinning; throughput degrades but eventual progress is guaranteed</li>
        <li><b>Bonus:</b> ABA problem; compare CAS vs mutex vs partitioned counter; hardware <code>LOCK CMPXCHG</code> instruction</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box wrong-ans">
        Thread B's CAS fails because the version changed — it does not mean Thread B's increment is lost. The retry loop immediately re-reads the current counter state <code>{value:1, version:1}</code> and retries the CAS with the new expected version. Thread B will eventually reach a moment where no other thread simultaneously wins a CAS, so its own CAS succeeds and increments the counter. A failed CAS is a <em>deferred</em> increment, not a discarded one.
        <br><br>
        With 1,000 threads, the final value is deterministically 1,000 — each thread runs through the retry loop until it wins exactly one CAS. The result is exactly equal to the number of callers regardless of contention level or timing. CAS atomically enforces: "set this value only if the state I read hasn't been changed by anyone else." This prevents lost updates entirely — it does not leave the outcome nondeterministic.
        <br><br>
        Performance risk: under extreme contention (many threads on one counter), most CAS calls fail on the first attempt and retry — threads effectively spin. Throughput degrades proportionally to contention. For a shared counter with thousands of concurrent writers, a mutex (one thread proceeds, others sleep) or a sharded counter (N separate counters, periodically summed) is more efficient.
      </div>
    </div>
  </div>

  <!-- Q3: WAL CRASH RECOVERY CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q3 &nbsp;·&nbsp; WAL Crash Recovery &amp; Durability Guarantee</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">A WAL contains <code>[BEGIN] → [DATA: record R] → [COMMIT]</code>, all three fsynced to disk. The process crashes before the page buffer is flushed. After recovery, is R present? Walk through the exact recovery sequence. Now: what if the crash had happened after [DATA] was fsynced but before [COMMIT] was written? What does this asymmetry tell us about atomicity?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>COMMIT fsynced = durable = R is guaranteed present after recovery</li>
        <li>Recovery: scan WAL → entries with COMMIT → redo to storage; entries without COMMIT → discard</li>
        <li>Pre-COMMIT crash: no COMMIT marker → incomplete transaction → R is discarded (atomicity enforced)</li>
        <li>Explains that page_buffer is an optimization, not the source of durability</li>
        <li><b>Bonus:</b> LSN (Log Sequence Number), fuzzy checkpoints, WAL archiving/PITR</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        R is present after recovery — guaranteed. The WAL COMMIT marker was durably fsynced to disk before the crash. During recovery, the engine scans the WAL and applies the redo rule: any log entry with a durable COMMIT marker is replayed to storage. Since [COMMIT] for R is on disk, the recovery process replays [DATA: R] to the main data files. The page_buffer write is purely an optimization — it keeps recently-written data in RAM to avoid re-reading from WAL on the hot path. Durability is established by the WAL COMMIT, not by the page_buffer flush.
        <br><br>
        If the crash had occurred after [DATA] was fsynced but before [COMMIT] was written, recovery would find no COMMIT marker for that entry and would discard it — leaving no trace of R in the database. This asymmetry is atomicity: the COMMIT marker is the single, binary decision point — the transaction either committed (COMMIT on disk, redo) or it didn't (no COMMIT, discard). There is no in-between state after recovery. This is the foundational guarantee WAL provides: any transaction that reached a durable COMMIT survives any crash; any transaction that did not is completely rolled back.
      </div>
    </div>
  </div>

  <!-- Q4: WAL REPLICATION SLOT CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q4 &nbsp;·&nbsp; WAL Replication Slots &amp; Disk Growth</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">You're on-call. PagerDuty fires: "PostgreSQL WAL directory at 95% disk." The primary has 5 replication slots. What SQL command tells you which slot is causing this? What's the immediate fix and the config change that prevents recurrence? What monitoring query should have caught this earlier?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Check <code>pg_replication_slots</code> for <code>active=false</code> and large <code>(pg_current_wal_lsn() - restart_lsn)</code></li>
        <li>Immediate fix: <code>SELECT pg_drop_replication_slot('stale_slot_name')</code></li>
        <li>Prevention: <code>max_slot_wal_keep_size</code> in postgresql.conf</li>
        <li>Alert: inactive slot with lag > threshold (e.g., 20 GB)</li>
        <li><b>Bonus:</b> difference between <code>wal_keep_size</code> and slot-held WAL; logical vs physical replication slots</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        Diagnosis: <code>SELECT slot_name, active, restart_lsn, pg_current_wal_lsn() - restart_lsn AS lag_bytes FROM pg_replication_slots ORDER BY lag_bytes DESC;</code> — any slot with <code>active=false</code> and large lag_bytes is the culprit. Immediate fix: <code>SELECT pg_drop_replication_slot('slot_name');</code> — dropping the slot releases the WAL hold and WAL GC runs immediately. Prevention: <code>max_slot_wal_keep_size = '20GB'</code> in postgresql.conf — any slot accumulating more than 20 GB is automatically invalidated (the subscriber must resync, but the primary doesn't run out of disk). Note: this is distinct from <code>wal_keep_size</code>, which only controls WAL retained between checkpoints — slot-held WAL is governed separately. Monitoring alert: when <code>(pg_current_wal_lsn() - restart_lsn) > 10GB</code> on any inactive slot — fire before it becomes critical.
      </div>
    </div>
  </div>

  <!-- Q5: CHECK-THEN-ACT CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q5 &nbsp;·&nbsp; Check-Then-Act Race Condition</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">A colleague adds a unique constraint on <code>payment_id</code> to a payment deduplication service and says "we're safe from duplicates." The code still calls <code>notify_payment_processed()</code> unconditionally after <code>db.insert()</code>. What is still broken, what's the exact race sequence that causes it, and what is the minimal fix?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Constraint stops duplicate inserts — but both threads call <code>notify</code> before either insert completes</li>
        <li>Race: Thread A and B pass <code>exists()</code> check → both call <code>notify</code> → second insert fails but notification already sent twice</li>
        <li>Fix: gate <code>notify</code> on insert success (catch duplicate key exception)</li>
        <li><b>Bonus:</b> idempotency keys on downstream; <code>SELECT FOR UPDATE</code> to serialize; outbox pattern</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        Not sufficient. The unique constraint stops the second <code>db.insert()</code> from completing, but <code>notify_payment_processed()</code> is called before the insert result is checked. In the race: Thread A and B both pass the <code>exists()</code> check (neither insert has completed yet), both call <code>run_payment()</code>, both call <code>db.insert()</code> — and critically, both call <code>notify_payment_processed()</code> before either insert returns. By the time the DB rejects the duplicate insert, the external notification has already been sent twice. The minimal fix: wrap <code>db.insert()</code> in a try/except and only call <code>notify_payment_processed()</code> if the insert succeeds without a duplicate-key error. The general principle: check-then-act is not atomic — the DB constraint enforces uniqueness at the data layer, but non-idempotent side effects must be explicitly gated on the outcome of that constraint check.
      </div>
    </div>
  </div>

  <!-- Q6: Iceberg CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q6 &nbsp;·&nbsp; Iceberg Metadata Pruning (3-Level Hierarchy)</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">An Iceberg table has 3 years of daily partitions (~500M rows). A query runs <code>WHERE event_date BETWEEN '2024-01-01' AND '2024-03-31' AND user_id = 12345</code>. Walk through the exact pruning sequence: which metadata level handles which predicate, what statistics are stored at each level, and what is the fundamental limitation of column-stats pruning for <code>user_id</code>?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Manifest list: partition bounds for <code>event_date</code> → eliminate ~90% of manifests without opening them</li>
        <li>Manifest files: per-data-file min/max column stats → prune on <code>user_id</code></li>
        <li>Parquet row-group stats: further pruning within files</li>
        <li>Limitation: <code>user_id</code> not a partition key → can't prune at manifest list; column stats are approximate (min/max range may include non-matching files)</li>
        <li><b>Bonus:</b> Z-ordering / data clustering to improve <code>user_id</code> selectivity; Iceberg v2 equality deletes</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        3-stage pruning: (1) <b>Manifest list</b>: a small Avro file with one entry per manifest, each storing <code>lower_bound</code> and <code>upper_bound</code> for <code>event_date</code>. Entries where the date range doesn't overlap <code>[2024-01-01, 2024-03-31]</code> are eliminated without opening the manifest file — ~90% of entries skipped. (2) <b>Manifest files</b>: each entry stores per-column statistics (min, max, null count) per data file. For <code>user_id = 12345</code>, any data file where <code>max(user_id) &lt; 12345</code> or <code>min(user_id) &gt; 12345</code> is skipped. (3) <b>Parquet row groups</b>: row-group statistics provide finer pruning before actual page reads.
        <br><br>
        Limitation: <code>user_id</code> is not a partition column — it can't be pruned at the manifest list level. Column-stats pruning at the manifest file level is approximate: a file where <code>min ≤ 12345 ≤ max</code> is opened even if 12345 doesn't actually exist there. Without data clustering (Z-order or range sorting on <code>user_id</code>), most data files survive the filter and must be scanned. Iceberg's <code>ORDER BY</code> on write or Z-ordering on multiple columns directly improves selectivity for such non-partition predicates.
      </div>
    </div>
  </div>

  <!-- ======== SECTION B ======== -->
  <div class="section-title">Section B — Distributed Systems &amp; Concurrency (6 Questions)</div>

  <!-- Q7: DISTRIBUTED LEASE CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q7 &nbsp;·&nbsp; Distributed Lease &amp; Fencing Token</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">You need distributed mutual exclusion for a pipeline writing to S3 — only one node at a time. You use a Redis-based lease (TTL=30s). A GC pause of 45s can occur. Design the fencing token mechanism end-to-end. How does the external system (S3) enforce exclusion given that S3 itself has no fencing concept?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Fencing token = monotonically increasing integer issued with each lease acquisition</li>
        <li>Node includes token in every write request</li>
        <li>Serialization layer (not S3 directly) tracks max_seen_token and rejects writes with lower tokens</li>
        <li>Concrete implementation: DynamoDB conditional write or a custom proxy layer as the serialization point</li>
        <li><b>Bonus:</b> S3 conditional writes (<code>If-Match</code>/<code>If-None-Match</code> on ETags) for object-level coordination</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        Each successful Redis lock acquisition increments a counter (via <code>INCR</code>) to produce a monotonically increasing token — e.g., Node A acquires the lease and gets token=7. Every write to S3 carries token=7 in its request. A serialization layer (e.g., a DynamoDB item with a <code>max_seen_token</code> attribute) enforces: only process writes where <code>token ≥ max_seen_token</code>, updating <code>max_seen_token</code> atomically via conditional write. Node A pauses 45s → lease expires → Node B acquires it with token=8 → writes with token=8, setting <code>max_seen_token=8</code>. When Node A resumes with token=7, the DynamoDB condition rejects its write. S3 itself is a dumb store — fencing enforcement must live in a proxy or coordination layer. Alternatively, S3's <code>If-Match</code> conditional headers provide per-object mutual exclusion using ETags as fencing tokens for single-object writes.
      </div>
    </div>
  </div>

  <!-- Q8: NUMA CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q8 &nbsp;·&nbsp; NUMA Architecture &amp; numactl Binding</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">A 4-socket server runs a Spark executor with <code>-XX:+UseNUMA</code>. A profiler shows GC threads on node 0 are allocating from node 2's DRAM 40% of the time. Why does <code>-XX:+UseNUMA</code> alone fail to prevent this? Write the correct <code>numactl</code> command to fix it, and explain what each flag does.</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li><code>-XX:+UseNUMA</code> only makes JVM allocate from the NUMA node of the <em>current running CPU</em> — if the OS migrates threads, allocations follow</li>
        <li>Without OS-level pinning, the Linux scheduler freely migrates threads across NUMA nodes</li>
        <li>Fix: <code>numactl --cpunodebind=0 --membind=0 java -XX:+UseNUMA -jar executor.jar</code></li>
        <li><code>--cpunodebind</code>: restrict thread scheduling; <code>--membind</code>: restrict mmap/malloc</li>
        <li><b>Bonus:</b> <code>numastat -p &lt;pid&gt;</code> to verify numa_miss drops; <code>--interleave=all</code> for workloads exceeding one node</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        <code>-XX:+UseNUMA</code> makes the JVM allocate from the NUMA node of whichever CPU the current thread is running on. This works only if threads stay pinned to a single NUMA node. Without OS-level binding, the Linux scheduler is free to migrate threads across sockets — when a GC thread migrates from node 0 to node 2, the next allocation lands on node 2's DRAM. The JVM cannot override OS scheduling without help.
        <br><br>
        Correct fix: <code>numactl --cpunodebind=0 --membind=0 java -XX:+UseNUMA -jar executor.jar</code>. <code>--cpunodebind=0</code> restricts OS thread scheduling to CPUs physically on NUMA node 0 — the OS scheduler cannot migrate threads to other sockets. <code>--membind=0</code> restricts all <code>mmap()</code> and <code>malloc()</code> allocations to node 0's DRAM — even if somehow a thread runs elsewhere, memory still comes from the local socket. Together they eliminate cross-NUMA bus traffic. <code>-XX:+UseNUMA</code> then optimizes intra-JVM allocation for multi-region GC. Verify improvement with: <code>numastat -p &lt;java_pid&gt;</code> — compare <code>numa_miss</code> counts before and after.
      </div>
    </div>
  </div>

  <!-- Q9: CGROUPS OOM CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q9 &nbsp;·&nbsp; cgroups v2 OOM Killer &amp; Container Memory Limits</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">A Kubernetes pod running a Spark executor is OOM-killed. JVM is <code>-Xmx6g</code>, pod limit is <code>8Gi</code>. Why might the pod be OOM-killed despite the apparent 2 GB headroom? Trace the exact kernel sequence from when the container's memory hits the cgroup limit. What does Kubernetes' default <code>memory.memsw.max</code> setting mean for swap usage?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>JVM off-heap: metaspace, direct memory (Netty/Parquet), thread stacks, code cache, native libs → easily 1.5–3 GB</li>
        <li>Kernel sequence: (1) page-cache reclaim within cgroup; (2) OOM killer scoped to cgroup → highest <code>oom_score</code> process → SIGKILL</li>
        <li>Kubernetes default: <code>memory.memsw.max = memory.max</code> → no swap allowed</li>
        <li>Fix: set <code>-Xmx</code> to 70–75% of pod limit; use <code>-XX:NativeMemoryTracking=detail</code></li>
        <li><b>Bonus:</b> <code>oom_score_adj</code> tuning; difference between RSS and working set; Kubernetes swap alpha feature</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        The 2 GB headroom is consumed by JVM off-heap memory: (1) metaspace — class metadata for large Spark jobs: 500 MB–1 GB; (2) direct memory — <code>ByteBuffer.allocateDirect()</code> used by Netty (Spark RPC) and Parquet readers: 1–2 GB; (3) thread stacks — each thread ~512 KB, Spark runs 100+ threads; (4) JIT code cache: 200–500 MB; (5) native libraries (libsnappy, Arrow, etc.). Total off-heap routinely exceeds 2 GB, pushing RSS past 8 GB.
        <br><br>
        Kernel OOM sequence: (1) memory.max is hit → kernel tries to reclaim memory within the cgroup (drop clean page cache, flush dirty pages via kswapd, invoke per-cgroup shrinkers); (2) if reclaim fails → cgroup-scoped OOM killer fires, computing <code>oom_score</code> for all processes in the cgroup (proportional to memory, adjustable via <code>oom_score_adj</code>) → SIGKILL to the highest-scoring process (typically the JVM). Logged to dmesg.
        <br><br>
        Kubernetes default: <code>memory.memsw.max = memory.max = 8 GB</code> — RAM + swap is capped at the same value as RAM alone → zero swap available to the container. Any allocation pushing RSS past 8 GB is OOM-killed immediately. Fix: set <code>-Xmx4g</code> for an 8 GB pod (not 6g), leaving 4 GB for off-heap. Profile off-heap with <code>jcmd &lt;pid&gt; VM.native_memory</code>.
      </div>
    </div>
  </div>

  <!-- Q10: io_uring CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q10 &nbsp;·&nbsp; io_uring SQPOLL &amp; Zero-Syscall I/O</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">A file ingestion service using <code>io_uring</code> with <code>IORING_SETUP_SQPOLL</code> shows no latency improvement at low traffic (&lt;100 ops/sec) vs epoll, but is significantly faster at 10K+ ops/sec. Explain the exact mechanism behind this difference. If you had to serve both traffic levels efficiently, what design change would you make?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Low traffic: SQPOLL kthread sleeps after <code>sq_thread_idle</code> ms → app must call <code>io_uring_enter()</code> to wake it → same cost as epoll syscall</li>
        <li>High traffic: kthread continuously spinning → picks up SQEs immediately, zero syscalls</li>
        <li>Dual-mode: SQPOLL ring for high-throughput path; non-SQPOLL (interrupt-driven) ring for bursty/low-rate I/O</li>
        <li><b>Bonus:</b> <code>IORING_SQ_NEED_WAKEUP</code> flag; <code>sq_thread_idle</code> tuning; liburing auto-handling of wakeup</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        SQPOLL kthread sleep behavior explains the difference. In SQPOLL mode, the kthread continuously polls the submission ring — zero syscalls at high throughput. However, to avoid burning a CPU core when idle, the kthread sleeps after <code>sq_thread_idle</code> ms of inactivity (default ~1 second). At low traffic, the kthread is almost always asleep — the app must check <code>IORING_SQ_NEED_WAKEUP</code> and call <code>io_uring_enter(fd, 0, 0, IORING_ENTER_SQ_WAKEUP)</code> to wake it. This wakeup syscall eliminates the "zero-syscall" benefit. At high traffic, the kthread never sleeps, SQEs are consumed instantly, and no syscall is needed.
        <br><br>
        Dual-mode design: create two io_uring rings — one with <code>IORING_SETUP_SQPOLL</code> for sustained high-throughput I/O (bulk file reads/writes), one without (interrupt-driven, lower overhead when idle) for bursty or low-rate I/O. Route requests to the appropriate ring based on I/O class or rate. This avoids pinning a CPU core for the SQPOLL kthread when most I/O is bursty.
      </div>
    </div>
  </div>

  <!-- Q11: RAFT CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q11 &nbsp;·&nbsp; Raft Consensus — Partition &amp; Log Safety</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">5-node Raft cluster {A (leader, term 5), B, C, D, E}. Network splits into {A,B} and {C,D,E}. A client write arrives at A. Can A commit it? What happens in {C,D,E}? When the partition heals, what happens to A's uncommitted entry? If A had committed an entry just before the partition (got 3 acks), is that entry safe?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>{A,B} = 2 nodes, quorum = 3 → A cannot commit; write stays as pending log entry</li>
        <li>{C,D,E} elect new leader at term ≥ 6 (3-node quorum)</li>
        <li>On heal: A sees higher-term leader → steps down → uncommitted entry overwritten by leader's log</li>
        <li>Committed entry (3 acks): at least one of {C,D,E} has it; election safety ensures new leader has it too → preserved</li>
        <li><b>Bonus:</b> pre-vote; leader completeness property; AppendEntries conflict resolution; joint consensus for config changes</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        A cannot commit: quorum = 3 (majority of 5), {A,B} = 2. A sends AppendEntries to B, gets 2 acknowledgments total — not a majority. The write stays as an uncommitted entry in A's log; A keeps retrying but cannot advance its commit index. {C,D,E} has 3 nodes — a quorum. They detect missing heartbeats from A and start a RequestVote election at term 6+. The candidate with the most up-to-date log (highest last log term, or same term with longer log) wins and begins serving requests.
        <br><br>
        On partition heal: A receives an AppendEntries or RequestVote RPC with term 6+ — Raft rule: any node that sees a higher term immediately reverts to follower. A adopts the new leader, and the leader's AppendEntries overwrites A's uncommitted pending entry with the correct log. If A had gotten 3 acks before the partition (committed entry): at least one of {C,D,E} has that entry (majority intersection guarantees overlap). Raft's Leader Completeness property ensures the newly elected leader in {C,D,E} also has it — it cannot win an election against a node with a more up-to-date log. Committed entries are never lost.
      </div>
    </div>
  </div>

  <!-- Q12: LAMPORT/VECTOR CLOCKS CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q12 &nbsp;·&nbsp; Lamport &amp; Vector Clocks</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">Three processes P1, P2, P3 start with vector clock [0,0,0]. P1 sends a message to P2 (P1 at send: [1,0,0]). P2 receives then sends to P3. What is P2's clock at send? P3's clock after receive? Then: event E on P1 with V(E)=[3,0,0]; event F on P3 with V(F)=[1,2,1]. What is their causal relationship and how do you determine it? Why can't Lamport timestamps answer this?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>P2 receive: <code>max([1,0,0],[0,0,0]) + increment = [1,1,0]</code>; P2 send: <code>[1,2,0]</code></li>
        <li>P3 receive: <code>max([1,2,0],[0,0,1]) + increment = [1,2,1]</code> or <code>[1,2,2]</code></li>
        <li>V(E)=[3,0,0] vs V(F)=[1,2,1]: V(E)[0]=3 > V(F)[0]=1 → E ≮ F; V(F)[1]=2 > V(E)[1]=0 → F ≮ E → concurrent</li>
        <li>Lamport limitation: L(A) &lt; L(B) is necessary but not sufficient for A→B; equal/crossing Lamport timestamps cannot prove concurrency or causality</li>
        <li><b>Bonus:</b> interval tree clocks; CRDT conflict resolution using vector clocks; causal consistency databases</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        Vector clock receive rule: component-wise max with sender's clock, then increment own component. P1 sends at [1,0,0]. P2 receives: max([1,0,0],[0,0,0])=[1,0,0], increment P2 → [1,1,0]. P2 sends at [1,2,0] (increment own before send). P3 receives: max([1,2,0],[0,0,0])=[1,2,0], increment P3 → [1,2,1].
        <br><br>
        V(E)=[3,0,0] vs V(F)=[1,2,1]: V(E) &lt; V(F) requires ALL V(E)[i] ≤ V(F)[i] — but V(E)[0]=3 &gt; V(F)[0]=1, so E does not causally precede F. V(F) &lt; V(E) requires ALL V(F)[i] ≤ V(E)[i] — but V(F)[1]=2 &gt; V(E)[1]=0, so F does not causally precede E. Neither dominates → E and F are concurrent: no causal relationship.
        <br><br>
        Why Lamport clocks can't answer this: Lamport's theorem is one-directional — A→B implies L(A) &lt; L(B), but L(A) &lt; L(B) does NOT imply A→B. Two events with equal or close Lamport timestamps could be concurrent OR causally related — there is no way to tell. Vector clocks provide the exact, complete causal relationship in both directions.
      </div>
    </div>
  </div>

  <!-- ======== SECTION C ======== -->
  <div class="section-title">Section C — Data Platforms &amp; Systems (4 Questions)</div>

  <!-- Q13: SAGA CHOREOGRAPHY CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q13 &nbsp;·&nbsp; Saga — Choreography vs Orchestration</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">A refund workflow spans 4 services under choreography. A junior engineer says "we don't need a saga monitor — if a service crashes, the others will time out eventually." Is that sufficient? What is the "lost saga" problem specifically? How does an orchestration approach (e.g., Temporal) fundamentally solve it rather than just detect it?</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Timing out ≠ compensating — timed-out services don't know to emit compensating events; upstream funds/stock remain held</li>
        <li>Lost saga: transaction stuck in partially-committed state with no automated path out</li>
        <li>Orchestration (Temporal): durable workflow with explicit compensation steps; central state machine retries compensation until it succeeds</li>
        <li>Choreography detection requires a saga monitor (external process tracking event sequences with timeouts)</li>
        <li><b>Bonus:</b> idempotency requirements for compensating events; outbox pattern for reliable event emission</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        Timing out alone is not sufficient — a service that times out waiting for an event simply stops waiting. It doesn't know which upstream services have already committed, and it sends no compensating events to undo them. In choreography, each service only reacts to events it receives — if <code>FraudApproved</code> never arrives, services 4 and 5 either time out silently or wait forever. Services 1 and 2 (which already reserved payment and stock) have no mechanism to learn that service 3 crashed — there is no <code>FraudFailed</code> event to trigger <code>PaymentCancelled</code>. Funds and stock remain permanently held — the lost saga failure mode.
        <br><br>
        Orchestration (Temporal workflow) fundamentally solves this rather than just detecting it: the entire saga is a durable function with explicit steps and compensation blocks. After <code>reserve_payment()</code> succeeds, the workflow engine persists state. If <code>check_fraud()</code> times out, the orchestrator explicitly calls <code>cancel_payment()</code> and <code>release_stock()</code> — retrying each compensation activity until it succeeds. The durable state machine guarantees compensation always reaches completion, even across process restarts. In choreography, you'd need a separate saga monitor service that tracks saga state per transaction_id, sets per-step timeouts, and emits compensating events on timeout — essentially reinventing an orchestrator.
      </div>
    </div>
  </div>

  <!-- Q14: SPANNER TRUETIME CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q14 &nbsp;·&nbsp; Spanner TrueTime &amp; External Consistency</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">Spanner's commit-wait adds up to 2ε (~2–14ms) per write transaction. A colleague argues: "Read-only transactions don't commit so they need no commit-wait — they're safe." Is this correct? Walk through where exactly commit-wait sits in the write path, and what guarantee it provides to any transaction that starts after a write becomes visible.</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>Colleague is correct: read-only transactions have no commit, no commit-wait needed</li>
        <li>Commit-wait is on the writer side: writer waits until <code>TT.now().earliest > ts1</code> before making T1 visible</li>
        <li>Guarantee: any T2 starting after T1 is visible gets <code>ts2 = TT.now().latest > ts1</code> → T2 sees T1's writes</li>
        <li><b>Bonus:</b> HLC as an alternative; Spanner GPS+atomic clock infra to minimize ε; 2PL+MVCC hybrid</li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        The colleague is correct but for a precise reason. Commit-wait is a burden exclusively on read-write transactions that commit — it sits between "write committed to Paxos" and "write made visible to readers." Read-only transactions in Spanner choose a read timestamp from TrueTime (<code>TT.now().latest</code>) and read from a consistent snapshot at that time — no commit phase, no commit-wait.
        <br><br>
        Commit-wait guarantee: T1 (a write) commits at <code>ts1 = TT.now().latest</code>. Spanner holds it invisible until <code>TT.now().earliest > ts1</code> — meaning the true current time is provably past ts1 everywhere (because TT.earliest ≤ actual time ≤ TT.latest). Any transaction T2 that starts <em>after</em> T1 is externally visible receives <code>ts2 = TT.now().latest ≥ actual_time > ts1</code>. So <code>ts2 > ts1</code> — T2's snapshot includes T1's writes. This is external consistency (linearizability): if T1 commits before T2 starts in real time (as seen by any external observer), T2 is guaranteed to see T1. Without commit-wait, a T2 on a lagging node could get <code>ts2 &lt; ts1</code>, making T1 invisible to T2 — a direct linearizability violation.
      </div>
    </div>
  </div>

  <!-- Q15: HUDI CORRECT -->
  <div class="question-block">
    <div class="q-header correct">
      <span class="q-badge badge-correct">✓ Correct</span>
      <span class="q-topic">Q15 &nbsp;·&nbsp; Hudi MoR vs CoW for CDC Workloads</span>
    </div>
    <div class="q-body">
      <div class="q-label">Interview Question</div>
      <div class="q-text">You're designing a Hudi pipeline: 50 TB IoT table, currently 95% INSERTs, 5% UPDATEs at 10K/s. Next quarter the ratio flips to 95% UPDATEs at 200K/s. Compare CoW and MoR for both workloads. Describe the compaction configuration for MoR, and explain the read-latency trade-off between compaction runs in quantitative terms.</div>
      <div class="q-label" style="margin-top:12px;">What to Look For</div>
      <div class="loofor"><ul>
        <li>INSERT-heavy: CoW works (inserts = new files, no rewrites); MoR also viable but adds ops overhead</li>
        <li>UPDATE-heavy at 200K/s: CoW fails — rewrites entire base Parquet files, O(file size) per update batch</li>
        <li>MoR config: <code>hoodie.compact.inline=false</code> on ingestion + separate scheduled Spark compaction job</li>
        <li>Read trade-off: real-time view merges base + uncompacted log files at query time; log count grows with time since last compaction</li>
        <li><b>Bonus:</b> file-size tuning to avoid small-files problem; Z-ordering/clustering for read performance; <code>hoodie.cleaner.commits.retained</code></li>
      </ul></div>
      <div class="q-label">Model Answer</div>
      <div class="answer-box">
        INSERT-heavy (95% inserts, 10K/s): CoW is straightforward — inserts write new Parquet files, only 5% of batches rewrite existing files. Read performance is excellent (no merge at read time). MoR is also viable but adds compaction complexity without significant benefit at this write rate.
        <br><br>
        UPDATE-heavy flip (95% updates, 200K/s): CoW breaks — every micro-batch touches existing files across hundreds of partitions. Each CoW rewrite is O(base file size), not O(records updated). At 200K/s × 80% updates on a 50 TB table, you'd rewrite GBs of Parquet per second — ingestion falls permanently behind. MoR is the only viable choice: updates append cheaply to Avro delta log files (O(records written), milliseconds per micro-batch).
        <br><br>
        MoR compaction config: on the ingestion job, set <code>hoodie.compact.inline=false</code> to prevent compaction from blocking ingestion. Run a separate scheduled Spark job every 30–60 minutes with <code>hoodie.compact.inline=true</code>. Read latency trade-off: between compaction runs, the real-time view must merge base Parquet + all uncompacted delta logs at query time. At 200K/s × 60 min = ~720M delta records per hour spread across file groups — each additional log file per file group adds merge overhead proportionally. In practice: keep compaction frequent enough that no file group has more than 10 delta log files, to bound the read-time merge cost.
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
