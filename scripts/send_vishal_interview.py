"""
Send Vishal Goel's B8 interview question paper to nishant.verma@natwest.com
Exam: B8 Data Engineer - Screening (Quiz 186)
Score: 18/20 (90%) | Wrong: Q0 (generator state), Q1 (memoization cache poisoning)
Duration: ~49 minutes | Participant ID: 15616
"""
import smtplib, ssl, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

env_path = Path(__file__).parent.parent / "backend" / ".env"
env = {}
for line in env_path.read_text().splitlines():
    m = re.match(r'^(SMTP_[A-Z_]+)\s*=\s*(.+)', line.strip())
    if m:
        env[m.group(1)] = m.group(2).strip().strip('"')

SMTP_HOST     = env["SMTP_HOST"]
SMTP_PORT     = int(env["SMTP_PORT"])
SMTP_USER     = env["SMTP_USER"]
SMTP_PASSWORD = env["SMTP_PASSWORD"]
FROM_EMAIL    = env["SMTP_FROM_EMAIL"]
FROM_NAME     = env.get("SMTP_FROM_NAME", "Swaya")
TO_EMAIL      = "nishant.verma@natwest.com"
SUBJECT       = "Interview Question Paper — Vishal Goel | B8 Data Engineer Screening | Score: 18/20 | 40-Min Guide"

HTML = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
body{font-family:'Segoe UI',Arial,sans-serif;background:#f5f7fa;margin:0;padding:20px;color:#1a1a2e}
.wrap{max-width:940px;margin:0 auto;background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,.10);overflow:hidden}
.hdr{background:linear-gradient(135deg,#1e3a5f,#2d6a9f);color:#fff;padding:32px 40px}
.hdr h1{margin:0 0 8px;font-size:22px;letter-spacing:.5px}
.hdr .meta{font-size:13px;opacity:.85;line-height:1.9}
.chips{display:flex;gap:16px;padding:18px 40px;background:#f0f4f8;border-bottom:1px solid #dde3ea;flex-wrap:wrap}
.chip{padding:7px 18px;border-radius:20px;font-size:13px;font-weight:600}
.c-tot{background:#1e3a5f;color:#fff}.c-ok{background:#d4edda;color:#155724}
.c-no{background:#f8d7da;color:#721c24}.c-pct{background:#fff3cd;color:#856404}
.c-time{background:#e8d5f7;color:#5a0f80}
.note{margin:20px 30px 4px;padding:14px 18px;background:#fffbea;border-radius:8px;border:1px solid #ffe58f;font-size:13px;line-height:1.7;color:#5a4a00}
.sec{font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:1px;padding:28px 40px 8px;color:#1e3a5f;border-top:2px solid #e8edf2;margin-top:8px}
.sec.first{border-top:none}
.q{margin:0 30px 22px;border-radius:10px;border:1px solid #e0e6ed;overflow:hidden}
.qh{padding:13px 20px;display:flex;align-items:center;gap:12px}
.qh.ok{background:#f0faf3;border-bottom:1px solid #c3e6cb}
.qh.no{background:#fff5f5;border-bottom:1px solid #f5c6cb}
.badge{font-size:11px;font-weight:700;padding:3px 10px;border-radius:10px;text-transform:uppercase;letter-spacing:.5px}
.b-ok{background:#28a745;color:#fff}.b-no{background:#dc3545;color:#fff}
.topic{font-size:13px;font-weight:600;color:#444}
.timing{margin-left:auto;font-size:11px;background:#e8edf2;color:#555;padding:3px 10px;border-radius:8px;font-weight:600}
.qb{padding:16px 20px}
.lbl{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:#888;margin:14px 0 6px}
.lbl:first-child{margin-top:0}
.qt{font-size:14px;line-height:1.75;color:#2c3e50;background:#f8f9fa;border-radius:6px;padding:13px 16px;border-left:3px solid #2d6a9f}
.qt.w{border-left-color:#dc3545;background:#fff8f8}
.mis{background:#fff0f0;border:1px solid #f5b8b8;border-radius:6px;padding:11px 15px;font-size:13px;color:#7a1414;margin-bottom:10px;line-height:1.65}
.mis strong{color:#c0392b}
.lf{font-size:13px;line-height:1.7;color:#444}
.lf ul{margin:4px 0 0;padding-left:20px}
.lf li{margin-bottom:4px}
.ans{background:#f0faf3;border-radius:6px;padding:13px 16px;font-size:13px;line-height:1.8;color:#1d4a2a;border:1px solid #c3e6cb}
.ans.w{background:#fff8f0;border-color:#f5c6a0;color:#5a3310}
.code{background:#1e2d3d;color:#e2e8f0;border-radius:6px;padding:12px 16px;font-family:'Courier New',monospace;font-size:12.5px;line-height:1.65;overflow-x:auto;margin:8px 0}
.code .kw{color:#93c5fd}.code .fn{color:#fde68a}.code .cm{color:#6b7280;font-style:italic}
.code .str{color:#86efac}.code .num{color:#f9a8d4}
code{background:#e8edf2;padding:1px 5px;border-radius:3px;font-family:'Courier New',monospace;font-size:12px}
.ft{background:#f0f4f8;padding:18px 40px;font-size:12px;color:#666;text-align:center;border-top:1px solid #dde3ea}
table.trace{border-collapse:collapse;font-size:13px;margin:8px 0;width:auto}
table.trace th{background:#e8edf2;padding:6px 14px;text-align:center;border:1px solid #cdd5df;font-weight:700}
table.trace td{padding:5px 14px;border:1px solid #e0e6ed;text-align:center}
table.trace tr.hi td{background:#fef9c3}
</style>
</head>
<body>
<div class="wrap">

<!-- HEADER -->
<div class="hdr">
  <h1>Technical Interview Question Paper — 40 Minutes</h1>
  <div class="meta">
    <b>Candidate:</b> Vishal Goel &nbsp;|&nbsp; <b>Email:</b> vishal.goel@natwest.com<br>
    <b>Role:</b> Data Engineer — B8 Cohort &nbsp;|&nbsp; <b>Exam:</b> B8 Data Engineer Screening (Quiz #186)<br>
    <b>Exam Date:</b> 21 May 2026 &nbsp;|&nbsp; <b>Duration:</b> ~49 min &nbsp;|&nbsp; <b>Prepared:</b> 12 Jun 2026
  </div>
</div>

<!-- CHIPS -->
<div class="chips">
  <span class="chip c-tot">20 Questions</span>
  <span class="chip c-ok">✓ 18 Correct</span>
  <span class="chip c-no">✗ 2 Wrong</span>
  <span class="chip c-pct">Score: 90%</span>
  <span class="chip c-time">⏱ ~49 min exam</span>
  <span class="chip c-time">🎯 40 min interview</span>
</div>

<!-- INTERVIEWER NOTE -->
<div class="note">
  <b>Interviewer Note:</b> Strong overall performer — 18/20 (90%) across a hard B8 paper spanning Python fundamentals, databases, streaming, and architecture. Two goals:<br>
  1. <b>Verify genuine understanding</b> on correct answers — 10 questions probe depth on the topics he got right.<br>
  2. <b>Expose and check learning</b> on 2 wrong answers: generator execution state (miscounted position) and memoization cache poisoning (traced fib(3) correctly but got fib(4) wrong).<br>
  <b>Time budget shown on each question.</b> Stay disciplined — this is calibrated for exactly 40 minutes.
</div>

<!-- ===== SECTION A ===== -->
<div class="sec first">Section A &nbsp;·&nbsp; Python Fundamentals &nbsp;·&nbsp; ~10 min &nbsp;·&nbsp; 2 Questions</div>

<!-- Q1 GENERATOR — WRONG -->
<div class="q">
  <div class="qh no">
    <span class="badge b-no">✗ Wrong</span>
    <span class="topic">Q1 &nbsp;·&nbsp; Generator Execution State &amp; Independent Instances</span>
    <span class="timing">~5 min</span>
  </div>
  <div class="qb">
    <div class="lbl">Candidate's Mistake</div>
    <div class="mis">
      <b>He chose:</b> <code>0 1 0 9</code> &nbsp;|&nbsp; <b>Correct:</b> <code>0 1 0 4</code><br>
      He correctly traced <code>a=0, b=1, c=0</code> but answered <code>d=9</code> (i.e. 3²) instead of <code>d=4</code> (i.e. 2²).
      After <code>a=NEXT(g)</code> and <code>b=NEXT(g)</code>, generator <code>g</code> is paused at <code>i=2</code>.
      Creating <code>g2</code> has zero effect on <code>g</code>. So <code>d=NEXT(g)</code> resumes at <code>i=2</code> → yields <code>4</code>.
      His error: likely treated <code>d</code> as the 4th call to <code>g</code> (yielding i=3 → 9) rather than the 3rd.
    </div>
    <div class="lbl">Interview Question</div>
    <div class="qt w">
      Consider this generator:
      <div class="code"><span class="kw">def</span> <span class="fn">counter</span>(start, step):
    n = start
    <span class="kw">while</span> <span class="kw">True</span>:
        <span class="kw">yield</span> n
        n += step

g1 = counter(<span class="num">0</span>, <span class="num">2</span>)   <span class="cm"># even numbers: 0, 2, 4, 6 …</span>
g2 = counter(<span class="num">1</span>, <span class="num">2</span>)   <span class="cm"># odd numbers: 1, 3, 5, 7 …</span>

a = next(g1)  <span class="cm"># ?</span>
b = next(g1)  <span class="cm"># ?</span>
c = next(g2)  <span class="cm"># ?</span>
d = next(g1)  <span class="cm"># ?</span>
e = next(g2)  <span class="cm"># ?</span>
<span class="kw">print</span>(a, b, c, d, e)</div>
      <b>Part 1 (trace):</b> What does this print? Walk me through each step out loud.<br><br>
      <b>Part 2 (concept):</b> I now call <code>g2 = counter(10, 1)</code> — reassigning <code>g2</code>. Does this affect <code>g1</code>'s state in any way?<br><br>
      <b>Part 3 (edge case):</b> I have a finite generator <code>g = (x for x in range(3))</code>. I call <code>next(g)</code> four times. What happens on the fourth call, and how do you handle this in production code?
    </div>
    <div class="lbl">What to Look For</div>
    <div class="lf"><ul>
      <li>Part 1: prints <code>0 2 1 4 3</code> — g1 resumes from where it paused, completely independent of g2</li>
      <li>Explains: each generator call creates a new execution frame with its own local variables; they share no state</li>
      <li>Part 2: reassigning g2 only rebinds the variable name; g1's frame is unchanged and still alive</li>
      <li>Part 3: fourth call raises <code>StopIteration</code>; production handling via <code>for</code> loop, <code>next(g, default)</code>, or try/except StopIteration</li>
      <li><b>Bonus:</b> Generator send() protocol; generator-based coroutines vs async/await; memory advantage of generators for large sequences</li>
    </ul></div>
    <div class="lbl">Model Answer</div>
    <div class="ans w">
      <b>Part 1 trace:</b>
      <table class="trace">
        <tr><th>Call</th><th>Generator</th><th>Resumes at n=</th><th>Yields</th><th>n becomes</th></tr>
        <tr class="hi"><td>next(g1)</td><td>g1</td><td>0</td><td><b>0</b></td><td>2</td></tr>
        <tr class="hi"><td>next(g1)</td><td>g1</td><td>2</td><td><b>2</b></td><td>4</td></tr>
        <tr><td>next(g2)</td><td>g2</td><td>1</td><td><b>1</b></td><td>3</td></tr>
        <tr class="hi"><td>next(g1)</td><td>g1</td><td>4</td><td><b>4</b></td><td>6</td></tr>
        <tr><td>next(g2)</td><td>g2</td><td>3</td><td><b>3</b></td><td>5</td></tr>
      </table>
      Output: <code>0 2 1 4 3</code>. Each generator is an independent object with its own suspended execution frame. Calling next(g2) or reassigning g2 has <em>zero</em> effect on g1's internal state — they are completely isolated objects.
      <br><br>
      <b>Part 2:</b> Reassigning the variable <code>g2</code> only rebinds the name to a new generator object. The old generator object (counter starting at 1) is orphaned and eventually garbage-collected. g1's frame is untouched. Python variable names are just references; reassigning one doesn't affect objects referenced by other names.
      <br><br>
      <b>Part 3:</b> <code>StopIteration</code> is raised. The safe patterns: (1) <code>for x in g</code> — the for loop catches StopIteration automatically; (2) <code>next(g, default_value)</code> — returns the default instead of raising; (3) explicit try/except StopIteration for fine-grained control.
    </div>
  </div>
</div>

<!-- Q2 MEMOIZATION — WRONG -->
<div class="q">
  <div class="qh no">
    <span class="badge b-no">✗ Wrong</span>
    <span class="topic">Q2 &nbsp;·&nbsp; Memoization, Cache Poisoning &amp; Shared Mutable State</span>
    <span class="timing">~5 min</span>
  </div>
  <div class="qb">
    <div class="lbl">Candidate's Mistake</div>
    <div class="mis">
      <b>He chose:</b> <code>3 21</code> &nbsp;|&nbsp; <b>Correct:</b> <code>3 30</code><br>
      He correctly computed <code>x = fib(4) = 3</code>. After <code>cache.clear()</code> and <code>cache[1] = 10</code>,
      the full recomputation is: <code>fib(2)=fib(1)+fib(0)=10+0=10</code>, <code>fib(3)=fib(2)+fib(1)=10+10=20</code>,
      <code>fib(4)=fib(3)+fib(2)=20+10=30</code>. He answered 21 — likely he used <code>fib(2)=1</code>
      (the standard value) for the final step instead of the recomputed <code>fib(2)=10</code>,
      suggesting he didn't fully trace the cache state after each recursive call.
    </div>
    <div class="lbl">Interview Question</div>
    <div class="qt w">
      <b>Part 1 (trace):</b> Here's a memoized function:
      <div class="code">cache = {}
<span class="kw">def</span> <span class="fn">fib</span>(n):
    <span class="kw">if</span> n <span class="kw">in</span> cache: <span class="kw">return</span> cache[n]
    <span class="kw">if</span> n &lt;= <span class="num">1</span>:    <span class="kw">return</span> n
    result   = fib(n - <span class="num">1</span>) + fib(n - <span class="num">2</span>)
    cache[n] = result
    <span class="kw">return</span> result</div>
      <code>cache[2] = 99</code> is set directly before calling <code>fib(5)</code>. What is returned? Trace the full call tree and show the cache state at each step — especially which calls hit the cache vs recurse.<br><br>
      <b>Part 2 (design):</b> This cache is a module-level global dict shared across all callers. Name two production risks this creates and how you'd fix them.<br><br>
      <b>Part 3 (application):</b> When is memoization inappropriate even for a pure function?
    </div>
    <div class="lbl">What to Look For</div>
    <div class="lf"><ul>
      <li>Part 1: fib(5) → fib(4) → fib(3) → fib(2) hits cache[2]=99 → returns 99; fib(3)=99+fib(1)=99+1=100; fib(4)=100+99=199; fib(5)=199+100=299</li>
      <li>Correctly identifies which calls hit cache and which recurse — must trace the actual call tree, not assume standard fib values</li>
      <li>Part 2 risks: (1) cache poisoning/corruption (as in the exam question); (2) unbounded memory growth — cache never evicted; thread safety if accessed concurrently</li>
      <li>Fixes: use <code>functools.lru_cache</code> (bounded, thread-safe); avoid module-level mutable shared state; use instance-level cache or pass cache explicitly</li>
      <li>Part 3: inappropriate when argument space is huge (cache grows unbounded), when side effects matter, or when results should be fresh (time-dependent, DB queries)</li>
    </ul></div>
    <div class="lbl">Model Answer</div>
    <div class="ans w">
      <b>Part 1 trace:</b> Starting with <code>cache = {2: 99}</code>, call <code>fib(5)</code>:
      <br>→ fib(5): not in cache → recurse → fib(4) + fib(3)
      <br>→ fib(4): not in cache → fib(3) + fib(2)
      <br>→ fib(3): not in cache → fib(2) + fib(1)
      <br>→ fib(2): <b>HIT cache[2] = 99</b> → returns 99
      <br>→ fib(1): base case → returns 1
      <br>→ fib(3) = 99 + 1 = 100; cache[3] = 100
      <br>→ fib(2): HIT → 99
      <br>→ fib(4) = 100 + 99 = 199; cache[4] = 199
      <br>→ fib(3): HIT → 100
      <br>→ fib(5) = 199 + 100 = 299; cache[5] = 299
      <br>Answer: <code>299</code>. Every call that builds on fib(2) is corrupted — the poison propagates through the entire call tree.
      <br><br>
      <b>Part 2 risks:</b> (1) <b>Cache poisoning</b> — any code path that writes to the global cache can corrupt results for all callers, silently, with no error raised. (2) <b>Unbounded memory</b> — the dict grows forever; for large n, this leaks memory. Additional: not thread-safe under concurrent writes. Fix: replace the hand-rolled cache with <code>@functools.lru_cache(maxsize=128)</code> — it's bounded, thread-safe, and isolated per function.
      <br><br>
      <b>Part 3 — when memoization is inappropriate:</b> (1) Input domain is too large or unbounded — cache grows without bound for inputs like arbitrary strings or large integers; (2) Results are time-sensitive or DB-backed — caching means stale data; (3) Functions with expensive serialization overhead that exceeds recomputation cost; (4) Functions that are called once per unique input — no reuse benefit.
    </div>
  </div>
</div>

<!-- ===== SECTION B ===== -->
<div class="sec">Section B &nbsp;·&nbsp; Databases &amp; Query Optimisation &nbsp;·&nbsp; ~13 min &nbsp;·&nbsp; 3 Questions</div>

<!-- Q3 SARGABILITY CORRECT -->
<div class="q">
  <div class="qh ok">
    <span class="badge b-ok">✓ Correct</span>
    <span class="topic">Q3 &nbsp;·&nbsp; Sargability, Partition Pruning &amp; Function-Wrapped Predicates</span>
    <span class="timing">~4 min</span>
  </div>
  <div class="qb">
    <div class="lbl">Interview Question</div>
    <div class="qt">
      You have a table <code>events</code> partitioned by <code>created_at TIMESTAMP</code>, one partition per day. These two queries return identical rows, but one takes 45 minutes and one takes 2 seconds:
      <div class="code"><span class="cm">-- 45 minutes</span>
WHERE <span class="fn">DATE</span>(created_at) = <span class="str">'2024-01-15'</span>

<span class="cm">-- 2 seconds</span>
WHERE created_at &gt;= <span class="str">'2024-01-15 00:00:00'</span>
  AND created_at  &lt;  <span class="str">'2024-01-16 00:00:00'</span></div>
      <b>Part 1:</b> Explain exactly why the first query fails to prune partitions.<br>
      <b>Part 2:</b> Give two other common patterns in SQL that cause the same "sargability" problem — one involving an index column, one involving a join.<br>
      <b>Part 3:</b> A junior engineer suggests adding a <em>computed column</em> <code>event_date DATE GENERATED AS (DATE(created_at))</code> and partitioning on that instead. Does this solve the problem? What's the trade-off?
    </div>
    <div class="lbl">What to Look For</div>
    <div class="lf"><ul>
      <li>Part 1: <code>DATE()</code> wraps the partition key — optimizer cannot invert the function to derive a partition range; scans all partitions defensively</li>
      <li>Part 2: index-column example: <code>WHERE YEAR(order_date) = 2024</code> or <code>WHERE UPPER(email) = 'FOO@BAR.COM'</code>; join example: <code>WHERE CAST(id AS VARCHAR) = other_table.str_id</code> forces implicit cast, disabling index use</li>
      <li>Part 3: computed column + partition on DATE column solves the problem AND preserves simplicity at query time; trade-off: extra storage, maintenance on INSERT, potential rewrite of existing data</li>
      <li><b>Bonus:</b> function-based indexes (Oracle/PostgreSQL) as an alternative; expression indexes in PostgreSQL</li>
    </ul></div>
    <div class="lbl">Model Answer</div>
    <div class="ans">
      <b>Part 1:</b> Partition pruning works by evaluating the partition predicate directly on the partition key to determine which partitions to skip. <code>DATE(created_at) = '2024-01-15'</code> applies a scalar function to <code>created_at</code>. The optimizer cannot "invert" <code>DATE()</code> to derive the equivalent range on the raw TIMESTAMP — it doesn't know which TIMESTAMP values map to which DATE. So it falls back to scanning every partition. The rewrite uses a half-open range directly on the raw column — the partition pruner trivially identifies the single matching day's partition.
      <br><br>
      <b>Part 2:</b> Index example: <code>WHERE UPPER(email) = 'FOO@BAR.COM'</code> — wrapping an indexed column in a function makes the B-tree index on <code>email</code> useless; the full table is scanned. Fix: use a functional index or normalize to lowercase on write. Join example: <code>WHERE CAST(user_id AS VARCHAR) = external_table.str_id</code> — implicit type coercion on the join key prevents index use on either side; fix by aligning column types.
      <br><br>
      <b>Part 3:</b> Yes, this solves the problem cleanly — partitioning on a <code>DATE</code> generated column allows <code>WHERE event_date = '2024-01-15'</code> to prune correctly. Trade-offs: the generated column adds storage overhead (~4 bytes per row); INSERTs have a small computational cost; existing data must be backfilled; it adds schema complexity. It's a good long-term fix if the team will never use the range-predicate form consistently.
    </div>
  </div>
</div>

<!-- Q4 WRITE SKEW CORRECT -->
<div class="q">
  <div class="qh ok">
    <span class="badge b-ok">✓ Correct</span>
    <span class="topic">Q4 &nbsp;·&nbsp; Write Skew, Isolation Levels &amp; Serializable Snapshot Isolation</span>
    <span class="timing">~5 min</span>
  </div>
  <div class="qb">
    <div class="lbl">Interview Question</div>
    <div class="qt">
      You correctly identified that write skew requires Serializable isolation to prevent. Let's go deeper.<br><br>
      <b>Part 1:</b> Explain the difference between a lost update, a dirty read, and write skew. Which isolation levels prevent each?<br><br>
      <b>Part 2:</b> PostgreSQL's Serializable uses SSI (Serializable Snapshot Isolation) rather than 2PL. How does SSI detect the write-skew anti-dependency cycle — what does it actually track at runtime, and what happens when it detects a conflict?<br><br>
      <b>Part 3:</b> You're designing a booking system: "a flight seat can only be booked once." Two concurrent transactions check <code>SELECT booked FROM seats WHERE id=42</code>, both see <code>booked=false</code>, both proceed to <code>UPDATE seats SET booked=true WHERE id=42</code>. Is this write skew? Which mechanism — SSI, 2PL, or a unique constraint — is the right tool here, and why?
    </div>
    <div class="lbl">What to Look For</div>
    <div class="lf"><ul>
      <li>Part 1: lost update = two txns read-modify-write the same row, second overwrites first; dirty read = reading uncommitted data; write skew = two txns read overlapping data and write to <em>different</em> rows, collectively violating an invariant — distinct from lost update</li>
      <li>Isolation: dirty read prevented by Read Committed+; lost update by Repeatable Read+ (or SELECT FOR UPDATE); write skew only by Serializable</li>
      <li>Part 2: SSI tracks "siread" locks on rows read; detects anti-dependency cycles (T1 reads data T2 writes, T2 reads data T1 writes); aborts one transaction with serialization failure, no blocking</li>
      <li>Part 3: NOT write skew — this is a lost update on the same row; unique constraint or SELECT FOR UPDATE is the right tool (simpler, no need for Serializable)</li>
      <li><b>Bonus:</b> SKIP LOCKED for queue-style work stealing; SELECT FOR UPDATE NOWAIT; optimistic vs pessimistic locking</li>
    </ul></div>
    <div class="lbl">Model Answer</div>
    <div class="ans">
      <b>Part 1:</b> <b>Dirty read</b>: reading data written by an uncommitted transaction — prevented by Read Committed+. <b>Lost update</b>: T1 and T2 both read value X, both modify it, T2's write overwrites T1's — prevented by Repeatable Read (via row-level locking) or SELECT FOR UPDATE. <b>Write skew</b>: T1 and T2 both read a shared condition, each writes to a <em>different</em> row, but together their writes violate an invariant that either transaction individually would not — only prevented by Serializable isolation. Write skew is subtle: each transaction looks correct in isolation.
      <br><br>
      <b>Part 2:</b> SSI in PostgreSQL uses "predicate locks" (siread locks) — lightweight read-intent markers on rows/ranges accessed. It tracks two types of anti-dependencies: (a) T1 reads a row that T2 later writes; (b) T2 reads a row that T1 writes. When SSI detects a cycle (T1 depends on T2 depends on T1), it identifies the "youngest" transaction in the cycle and aborts it with a serialization failure error (<code>ERROR 40001: could not serialize access</code>). The aborted transaction must retry. Key advantage over 2PL: SSI never blocks — it allows optimistic execution and only aborts on detected conflicts, yielding much higher concurrency.
      <br><br>
      <b>Part 3:</b> This is a <b>lost update</b> on the same row, not write skew — both transactions write to the same row. The right tool is a <b>unique constraint</b> on <code>(seat_id, booked=true)</code> or equivalently <code>SELECT ... FOR UPDATE</code> to serialize the read-modify-write. Enabling full Serializable isolation would work but is heavier than needed — it serializes all concurrent transactions, not just the conflicting ones. A unique constraint enforces the invariant at the data layer with zero runtime overhead and handles it at the exact right granularity.
    </div>
  </div>
</div>

<!-- Q5 MVCC CORRECT -->
<div class="q">
  <div class="qh ok">
    <span class="badge b-ok">✓ Correct</span>
    <span class="topic">Q5 &nbsp;·&nbsp; MVCC, Snapshot Isolation &amp; Visibility Rules</span>
    <span class="timing">~4 min</span>
  </div>
  <div class="qb">
    <div class="lbl">Interview Question</div>
    <div class="qt">
      <b>Part 1:</b> Under MVCC Repeatable Read, transaction T1 (started at T=100) reads a row at T=150. Another transaction T2 committed an INSERT of a new row at T=120. Does T1 see T2's new row? What if T2 had committed a DELETE of an existing row instead?<br><br>
      <b>Part 2:</b> MVCC stores multiple row versions. What mechanism cleans up old versions, and what happens if that mechanism falls behind? Give a concrete production symptom.<br><br>
      <b>Part 3:</b> Snapshot Isolation (SI) prevents most read anomalies but still allows write skew (as you identified). What is the one additional mechanism that Serializable SI (SSI) adds to close that gap?
    </div>
    <div class="lbl">What to Look For</div>
    <div class="lf"><ul>
      <li>Part 1: T1 does NOT see T2's INSERT (T2 committed after T1 started → not in T1's snapshot); T1 also does NOT see T2's DELETE — the row is still visible to T1 as it was at T=100</li>
      <li>This is also the phantom read guarantee at Repeatable Read in MVCC systems (PostgreSQL) — though strictly phantom reads require Serializable for full protection under SQL standard</li>
      <li>Part 2: VACUUM (PostgreSQL) / purge thread (MySQL) reclaims dead row versions; if it falls behind → table bloat, "table bloat" or "dead tuple accumulation"; query performance degrades; eventual disk exhaustion</li>
      <li>Production symptom: <code>pg_stat_user_tables.n_dead_tup</code> growing; table file size grows despite no net row increase; autovacuum blocked by long-running transactions holding old snapshots</li>
      <li>Part 3: SSI adds predicate/siread locks + anti-dependency cycle detection — the extra layer on top of SI that detects write skew without blocking</li>
    </ul></div>
    <div class="lbl">Model Answer</div>
    <div class="ans">
      <b>Part 1:</b> T1's snapshot is fixed at T=100. T2 committed its INSERT at T=120 — after T1's snapshot. T1 does not see the new row. Similarly, T2's DELETE at T=120 is invisible to T1 — T1 still sees the deleted row as it existed at T=100. MVCC ensures T1 has a completely consistent view of the database as it was when T1 started, regardless of any commits that happened after.
      <br><br>
      <b>Part 2:</b> VACUUM (PostgreSQL) reclaims row versions that are no longer visible to any active transaction. If VACUUM falls behind — due to a long-running transaction holding an old snapshot — dead row versions accumulate. Symptoms: table file on disk grows continuously despite no net row increase (table bloat); queries slow down because they must scan more pages to find live rows; eventually, the table file can exhaust disk. Monitor via <code>pg_stat_user_tables.n_dead_tup</code> and <code>pg_stat_activity</code> for long-running transactions. A transaction open for hours or days effectively prevents VACUUM from reclaiming any version newer than its snapshot.
      <br><br>
      <b>Part 3:</b> SSI adds predicate locks (siread locks) and anti-dependency tracking on top of SI. SI provides a consistent snapshot but allows two transactions to each read a shared predicate and write to non-overlapping rows, violating a cross-row invariant. SSI tracks which rows each transaction read and writes, builds a dependency graph, and aborts one transaction in any detected cycle. This closes the write-skew gap while remaining non-blocking.
    </div>
  </div>
</div>

<!-- ===== SECTION C ===== -->
<div class="sec">Section C &nbsp;·&nbsp; Streaming, CDC &amp; Data Platforms &nbsp;·&nbsp; ~14 min &nbsp;·&nbsp; 3 Questions</div>

<!-- Q6 FLINK EXACTLY-ONCE CORRECT -->
<div class="q">
  <div class="qh ok">
    <span class="badge b-ok">✓ Correct</span>
    <span class="topic">Q6 &nbsp;·&nbsp; Flink Exactly-Once: Two-Phase Commit Deep Dive</span>
    <span class="timing">~5 min</span>
  </div>
  <div class="qb">
    <div class="lbl">Interview Question</div>
    <div class="qt">
      You correctly identified that Flink exactly-once requires checkpointing + a Kafka transactional sink. Explain the mechanism.<br><br>
      <b>Part 1:</b> Walk through what happens step by step during a checkpoint: what does the source do, what does the sink do, and what is "pre-commit"?<br><br>
      <b>Part 2:</b> The Flink job crashes mid-checkpoint — specifically after the sink has pre-committed its Kafka transaction but before the checkpoint completes. On restart, what happens to: (a) the Kafka sink transaction; (b) the source Kafka offset; (c) messages already written to the pre-committed transaction?<br><br>
      <b>Part 3:</b> Exactly-once in Flink requires <code>isolation.level=read_committed</code> on downstream Kafka consumers. Why — what would happen without it?
    </div>
    <div class="lbl">What to Look For</div>
    <div class="lf"><ul>
      <li>Part 1: checkpoint barrier flows through the pipeline; source snapshots its offset; sink calls <code>beginTransaction()</code>, writes to Kafka transaction (data not yet visible to consumers); on barrier received → pre-commit (data flushed to Kafka, transaction not yet committed); JobManager confirms all operators checkpointed → notify sink → sink calls <code>commitTransaction()</code></li>
      <li>Part 2: (a) pre-committed Kafka transaction is aborted on recovery (transaction timeout or explicit abort); (b) source offset rolls back to last completed checkpoint; (c) messages in the aborted transaction become invisible — exactly-once maintained, no duplicates</li>
      <li>Part 3: without <code>read_committed</code>, consumers read at <code>read_uncommitted</code> level — they see messages from in-progress (not yet committed) Kafka transactions, including transactions that will later be aborted → duplicates visible to consumers before abort</li>
      <li><b>Bonus:</b> Kafka transaction timeout and its interaction with checkpoint interval; idempotent producer as a prerequisite; limitations with sinks that don't support 2PC</li>
    </ul></div>
    <div class="lbl">Model Answer</div>
    <div class="ans">
      <b>Part 1 — Checkpoint protocol:</b> The JobManager injects a checkpoint barrier into the source's input stream. Source: snapshots its current Kafka offset into the checkpoint state. The barrier flows downstream. Sink (Kafka transactional): when it receives the barrier, it calls <code>prepareCommit()</code> — flushes all buffered records into an open Kafka transaction and calls Kafka's <code>sendOffsetsToTransaction()</code>, but does NOT commit yet (data is in a pending Kafka transaction, invisible to <code>read_committed</code> consumers). When the JobManager receives acknowledgment from all operators that they've checkpointed successfully, it sends a "checkpoint complete" notification to the sink, which then calls <code>commitTransaction()</code> — making the Kafka messages visible to consumers. The source offset is also durably committed at this point.
      <br><br>
      <b>Part 2 — Crash after pre-commit:</b> On recovery: (a) The Kafka transactional sink aborts the pending transaction — either explicitly during recovery or via Kafka's transaction timeout. The pre-committed but uncommitted records become invisible. (b) The source rolls back to the last successfully completed checkpoint's offset — re-reading any messages processed since that checkpoint. (c) The pre-committed messages are gone (transaction aborted). Flink replays from the last checkpoint, produces the same records again, and commits them in a new transaction. Net result: exactly-once — no duplicates, no data loss.
      <br><br>
      <b>Part 3:</b> Kafka transactions make writes atomically visible upon <code>commitTransaction()</code>. But at the default <code>read_uncommitted</code> level, consumers can read records from open (uncommitted) transactions immediately. In Flink's 2PC protocol, records are in open transactions during checkpoint processing — they may be in transactions that get aborted on recovery. A consumer reading at <code>read_uncommitted</code> would see those records before the abort, and then see them again after replay → duplicate processing. <code>read_committed</code> ensures consumers only see fully committed, non-aborted data.
    </div>
  </div>
</div>

<!-- Q7 FLINK BACKPRESSURE CORRECT -->
<div class="q">
  <div class="qh ok">
    <span class="badge b-ok">✓ Correct</span>
    <span class="topic">Q7 &nbsp;·&nbsp; Flink Backpressure, State TTL &amp; Operational Diagnosis</span>
    <span class="timing">~4 min</span>
  </div>
  <div class="qb">
    <div class="lbl">Interview Question</div>
    <div class="qt">
      You correctly identified unbounded state growth + GC pressure as the root cause of the backpressure. Now design the fix and monitoring.<br><br>
      <b>Part 1:</b> Write the <code>StateTtlConfig</code> configuration (pseudocode or Java-style) you would add to the stateful aggregation operator. What TTL value would you choose for a session-based aggregation, and what does "on-create" vs "on-read-and-write" update strategy mean?<br><br>
      <b>Part 2:</b> Beyond state TTL, name two other Flink operator tuning knobs that directly address GC pressure on task managers.<br><br>
      <b>Part 3:</b> What four metrics would you add to your Flink monitoring dashboard to catch this class of problem early, before consumer lag becomes critical?
    </div>
    <div class="lbl">What to Look For</div>
    <div class="lf"><ul>
      <li>Part 1: <code>StateTtlConfig.newBuilder(Time.hours(2)).setUpdateType(UpdateType.OnReadAndWrite).setStateVisibility(NeverReturnExpired).build()</code>; on-create = TTL counts from first write only; on-read-and-write = TTL resets on every access (sliding window behavior); choose based on whether active sessions should stay alive</li>
      <li>Part 2: increase JVM heap / switch to RocksDB state backend (spills to disk, avoiding heap pressure); tune GC algorithm (G1GC parallelism, heap regions); operator chaining configuration</li>
      <li>Part 3: <code>State size per operator</code> (growing = leak), <code>GC pause duration</code> (spike = heap pressure), <code>Kafka consumer lag</code> (growing = processing falling behind), <code>Checkpoint duration</code> (increasing = state snapshot overhead growing)</li>
      <li><b>Bonus:</b> RocksDB block cache tuning; incremental checkpointing; Flink's managed memory vs JVM heap distinction</li>
    </ul></div>
    <div class="lbl">Model Answer</div>
    <div class="ans">
      <b>Part 1 — StateTtlConfig:</b>
      <div class="code">StateTtlConfig ttlConfig = StateTtlConfig
    .newBuilder(Time.hours(<span class="num">2</span>))
    .setUpdateType(UpdateType.OnReadAndWrite)  <span class="cm">// sliding TTL</span>
    .setStateVisibility(NeverReturnExpired)
    .build();
valueState.enableTimeToLive(ttlConfig);</div>
      For session aggregation, <code>OnReadAndWrite</code> is usually correct: the TTL resets every time the session's state is touched, keeping active sessions alive while purging inactive ones. <code>OnCreateAndWrite</code> would only reset on writes, not reads — appropriate when you want a hard expiry from last update regardless of read activity.
      <br><br>
      <b>Part 2 — Other GC tuning knobs:</b> (1) <b>RocksDB state backend</b>: switch from heap-based (HashMapStateBackend) to RocksDB — state spills to disk, dramatically reducing JVM heap pressure for large state volumes; trade-off is higher per-access latency. (2) <b>Increase managed memory and tune GC</b>: increase <code>taskmanager.memory.managed.size</code>; use G1GC with tuned region sizes (<code>-XX:G1HeapRegionSize</code>) and parallelism; enable GC logging to identify object allocation hot spots.
      <br><br>
      <b>Part 3 — Dashboard metrics:</b>
      (1) <b>State store size per operator</b> — growing monotonically indicates a TTL misconfiguration or missing cleanup;
      (2) <b>GC pause duration</b> (JVM metric) — spikes &gt;200ms on task managers indicate heap pressure;
      (3) <b>Kafka consumer lag</b> — leading indicator that throughput has fallen below ingestion rate;
      (4) <b>Checkpoint duration + checkpoint size</b> — growing checkpoint size means state is accumulating; duration spikes indicate serialization is now a bottleneck.
    </div>
  </div>
</div>

<!-- Q8 DELTA LAKE CORRECT -->
<div class="q">
  <div class="qh ok">
    <span class="badge b-ok">✓ Correct</span>
    <span class="topic">Q8 &nbsp;·&nbsp; Delta Lake Optimistic Concurrency &amp; Concurrent Write Conflicts</span>
    <span class="timing">~5 min</span>
  </div>
  <div class="qb">
    <div class="lbl">Interview Question</div>
    <div class="qt">
      You correctly identified Delta Lake's transaction log and optimistic concurrency. Let's stress-test it.<br><br>
      <b>Part 1:</b> Two Spark jobs run concurrently on the same Delta table. Job A reads log version 42, writes data files, and attempts to write commit file <code>00043.json</code>. Job B does the same and gets there first. Walk through exactly what Job A does from conflict detection to successful commit.<br><br>
      <b>Part 2:</b> When does Delta Lake abort a conflicting writer vs allow it to retry? Give a concrete example of a conflict that can be safely retried vs one that must be aborted.<br><br>
      <b>Part 3:</b> Delta Lake's Z-ordering is mentioned as a read optimization. Explain what it does at the data file level and why it must be combined with <code>OPTIMIZE</code>.
    </div>
    <div class="lbl">What to Look For</div>
    <div class="lf"><ul>
      <li>Part 1: Job A detects that 00043.json already exists (S3 atomic PUT fails or conflict detected); re-reads log from version 43 onwards; replays conflict detection logic — did Job B's commit touch the same files/partitions Job A read?; if no logical conflict → retry write as version 44; if conflict → abort and throw error to application</li>
      <li>Part 2: safe retry — Job A appended to partition A, Job B appended to partition B (no overlapping reads/writes); must abort — Job A and B both read and updated the same partition (overlapping file-level conflict)</li>
      <li>Part 3: Z-ordering applies a space-filling curve (Z-curve / Morton code) sort across multiple columns — co-locates rows with similar values in the same data files; Iceberg/Delta records per-file column stats (min/max); after Z-order, queries with multi-column predicates can skip most files; OPTIMIZE is needed because Z-ordering rewrites files — it requires compacting small files and re-sorting, which is a write-heavy operation run separately from ingestion</li>
      <li><b>Bonus:</b> Delta's conflict detection granularity (file-level vs partition-level); ConcurrentAppendException vs ConcurrentDeleteReadException</li>
    </ul></div>
    <div class="lbl">Model Answer</div>
    <div class="ans">
      <b>Part 1 — Conflict resolution flow:</b> Job A attempts to write <code>00043.json</code> to S3. S3's atomic PUT (with <code>If-None-Match</code>) fails because Job B already created it. Job A reads the transaction log from version 43 forward to understand what Job B committed. Delta's conflict checker then asks: "Did Job B's commit touch any files that Job A's commit depends on?" — specifically, did Job B write to the same partitions or files that Job A read during its planning phase? If Job B wrote to completely different partitions, there is no logical conflict — Job A increments its target version to 44 and writes <code>00044.json</code>. If there is a logical conflict (overlapping reads/writes), Job A throws a <code>ConcurrentModificationException</code> and the application must handle it.
      <br><br>
      <b>Part 2 — Retry vs abort:</b> Safe to retry: Job A appends new data to <code>partition=2024-06-01</code>; Job B appends to <code>partition=2024-06-02</code>. No overlapping data files were read or modified by both — Delta's file-level conflict detection sees no overlap, Job A can safely commit as the next version. Must abort: Job A and Job B both ran <code>UPDATE orders SET status='shipped' WHERE region='APAC'</code> — both read the same APAC partition files and attempted to rewrite them. The conflict is irresolvable; one must abort and re-execute from scratch.
      <br><br>
      <b>Part 3 — Z-ordering:</b> Z-ordering applies a space-filling curve sort to data within a table — rows that share similar values across multiple columns (e.g., <code>region='APAC'</code> AND <code>event_type='purchase'</code>) are physically co-located in the same data files. Delta records per-file column statistics (min/max). After Z-ordering, a query filtering on <code>region='APAC' AND event_type='purchase'</code> can skip most data files based on their column stats — files whose min/max ranges don't overlap with the query values. <code>OPTIMIZE</code> is required because Z-ordering is a full rewrite operation: it reads existing files, re-sorts and packs rows by the Z-curve, and writes new compacted files. Running Z-order during ingestion would make every micro-batch a full table rewrite. The operational pattern: ingest normally (fast appends), then periodically run <code>OPTIMIZE ZORDER BY (region, event_type)</code> off-peak.
    </div>
  </div>
</div>

<!-- ===== SECTION D ===== -->
<div class="sec">Section D &nbsp;·&nbsp; Architecture &amp; System Design &nbsp;·&nbsp; ~13 min &nbsp;·&nbsp; 2 Questions</div>

<!-- Q9 SCHEMA REGISTRY + CDC CORRECT -->
<div class="q">
  <div class="qh ok">
    <span class="badge b-ok">✓ Correct</span>
    <span class="topic">Q9 &nbsp;·&nbsp; Schema Evolution, CDC Pipeline Design &amp; MySQL Binlog</span>
    <span class="timing">~6 min</span>
  </div>
  <div class="qb">
    <div class="lbl">Interview Question</div>
    <div class="qt">
      You correctly answered both the Schema Registry backward-compatibility question and the MySQL CDC row-event question. Let's combine them into a design problem.<br><br>
      <b>Scenario:</b> You're building a CDC pipeline: MySQL (binlog_format=ROW) → Debezium → Kafka → Flink → Data Warehouse. The MySQL <code>orders</code> table has 50M rows and a Schema Registry enforcing BACKWARD compatibility.<br><br>
      <b>Part 1:</b> The MySQL DBA runs <code>ALTER TABLE orders ADD COLUMN discount DECIMAL(5,2) NOT NULL DEFAULT 0.00</code>. Walk through what happens in the CDC pipeline — specifically at the binlog, the Debezium connector, and the Schema Registry.<br><br>
      <b>Part 2:</b> The DBA then runs <code>ALTER TABLE orders DROP COLUMN notes VARCHAR(500)</code>. Is this BACKWARD-compatible? What must happen in the Schema Registry before this DDL can safely propagate downstream?<br><br>
      <b>Part 3:</b> A batch UPDATE changes <code>status = 'shipped'</code> for 200,000 rows at once. The CDC consumer falls 800,000 events behind. Name two independent strategies to manage this without losing data.
    </div>
    <div class="lbl">What to Look For</div>
    <div class="lf"><ul>
      <li>Part 1: binlog records the DDL; Debezium detects the schema change, updates its internal schema snapshot; produces new Avro schema to Schema Registry — adding a field WITH a default (0.00) is BACKWARD-compatible, so it's accepted; downstream Flink consumers using old schema can still read new messages (default fills missing field)</li>
      <li>Part 2: DROPPING a column is NOT BACKWARD-compatible — old consumers reading old schema expect the field; new messages won't have it. Must register new schema first; wait for all consumers to upgrade to new schema (or at least drain all old messages); then the DROP can propagate</li>
      <li>Part 3: (1) increase consumer parallelism (more Flink tasks / Kafka partitions) to speed through the burst; (2) pause Debezium connector temporarily + use binlog position to replay in batches after the burst settles; or increase Kafka retention so no data is lost even if consumers fall behind</li>
      <li><b>Bonus:</b> Debezium snapshot mode for initial load vs ongoing CDC; schema change handling in STATEMENT vs ROW binlog format; consumer group lag alerting</li>
    </ul></div>
    <div class="lbl">Model Answer</div>
    <div class="ans">
      <b>Part 1 — ADD COLUMN with DEFAULT:</b> MySQL writes the DDL to the binlog. Debezium (in ROW mode) detects the schema change via its internal table introspection and updates its schema representation. It pushes a new Avro schema to the Schema Registry: the new schema adds <code>discount</code> with <code>"default": 0.00</code>. The Registry compares it against v1 under BACKWARD compatibility — adding a field with a default is BACKWARD-compatible (old consumers can read new messages by using the default for the missing field). Schema is accepted. Debezium begins producing messages in the new schema. Flink consumers on the old schema can still deserialize new messages correctly via Avro's schema evolution (the <code>discount</code> field is populated with 0.00 when reading old-schema messages against the new reader schema).
      <br><br>
      <b>Part 2 — DROP COLUMN:</b> Dropping a field is NOT BACKWARD-compatible — the new schema is missing a field that old consumers expect. Registering it would be rejected by the Registry (409 Conflict). The safe procedure: (1) Register a new schema marking <code>notes</code> as optional with a null default; (2) Deploy all Flink consumers to upgrade to the new schema and handle null notes gracefully; (3) Wait until no consumer is still on the old schema; (4) Then the MySQL DBA can safely drop the column — all consumers are now tolerant of missing notes. Attempting the DROP before schema migration causes Debezium to produce messages that old-schema consumers cannot deserialize.
      <br><br>
      <b>Part 3 — Managing 200K-row batch update burst:</b> (1) <b>Scale consumer parallelism</b>: increase Flink task parallelism and ensure Kafka has enough partitions — more tasks consume from more partitions simultaneously, processing the 800K backlog faster without data loss; (2) <b>Increase Kafka retention</b> on the topic: ensure retention bytes/time is large enough to hold the burst while consumers catch up — as long as messages are in Kafka, no data is lost regardless of consumer lag. Additionally, alert on consumer lag and provision autoscaling of Flink task managers triggered by lag thresholds.
    </div>
  </div>
</div>

<!-- Q10 LAMBDA/KAPPA + SLA CORRECT -->
<div class="q">
  <div class="qh ok">
    <span class="badge b-ok">✓ Correct</span>
    <span class="topic">Q10 &nbsp;·&nbsp; Platform Architecture: Kappa Migration, SLA &amp; Reliability Design</span>
    <span class="timing">~7 min</span>
  </div>
  <div class="qb">
    <div class="lbl">Interview Question</div>
    <div class="qt">
      You correctly answered both the Kappa vs Lambda trade-off and the compound SLA availability question. Let's combine them into a design scenario.<br><br>
      <b>Scenario:</b> Your team runs a Lambda architecture (daily Spark batch + Flink speed layer) with this pipeline: Kafka (99.95%) → Flink (99.8%) → Data Warehouse (99.7%) → BI Layer (99.9%). Current compound availability ≈ 99.35%, SLA target is 99.5%.<br><br>
      <b>Part 1:</b> You've been asked to migrate to Kappa. The business has 3 years of historical data and needs to reprocess it fully whenever the aggregation logic changes (happens ~4 times/year). What is the minimum Kafka retention you must configure, and what's the operational risk if you cannot afford 3 years of Kafka retention?<br><br>
      <b>Part 2:</b> You've improved the Data Warehouse availability to 99.9% (closing the SLA gap). Six months later, Flink degrades to 99.7% due to a persistent memory leak between releases. Recalculate compound availability and identify which component to fix first now.<br><br>
      <b>Part 3:</b> Design one architectural change that improves compound SLA without improving any individual component's availability — explain the mechanism.
    </div>
    <div class="lbl">What to Look For</div>
    <div class="lf"><ul>
      <li>Part 1: need 3 years of Kafka retention (~tens of TB); if unaffordable → maintain a "cold replay store" (S3/GCS) of the raw events alongside Kafka; Kappa reprocessing reads from S3 when Kafka window insufficient; operational risk: Kappa's core promise (single code path) breaks if you need a separate replay system</li>
      <li>Part 2: new compound = 0.9995 × 0.997 × 0.999 × 0.999 ≈ 99.44% — still below 99.5%; Flink is now the weakest link (99.7% same as DW was); fix Flink first</li>
      <li>Part 3: make components parallel / redundant rather than sequential — e.g., multi-region active-active DW; parallel BI read replicas; async decoupling (buffer between Flink and DW so DW downtime doesn't block Flink); each reduces exposure to a single component failure</li>
      <li><b>Bonus:</b> distinguishing "availability" from "data freshness SLA"; graceful degradation (serve stale data from cache when DW is down); circuit breakers</li>
    </ul></div>
    <div class="lbl">Model Answer</div>
    <div class="ans">
      <b>Part 1 — Kappa reprocessing retention:</b> Minimum Kafka retention = 3 years of raw events. At typical IoT/e-commerce scale (say 100M events/day × 500 bytes = ~50 GB/day), 3 years = ~54 TB — feasible on cloud Kafka (Confluent/MSK) but expensive. If unaffordable: maintain a <b>cold replay store</b> on object storage (S3/GCS) — Kafka provides recent events (e.g., 30 days); for full historical reprocessing, the Flink job reads from S3 instead of Kafka. Operationally, this means maintaining two reading paths (Kafka for real-time, S3 for replay) — which partially defeats Kappa's "single code path" principle. In practice, this hybrid is common: the <em>processing logic</em> is unified (same Flink job), only the <em>data source</em> switches for reprocessing.
      <br><br>
      <b>Part 2 — Revised availability after DW improvement then Flink degradation:</b>
      <br>New compound = 0.9995 (Kafka) × 0.997 (Flink at 99.7%) × 0.999 (DW at 99.9%) × 0.999 (BI)
      <br>= 0.9995 × 0.997 × 0.999 × 0.999 ≈ <b>99.44%</b> — still below the 99.5% SLA.
      <br>Weakest link is now Flink (99.7%, tied with the old DW). Fix Flink first — the memory leak is a known issue with the highest improvement leverage. Bringing Flink back to 99.9% would yield: 0.9995 × 0.999 × 0.999 × 0.999 ≈ 99.65% — above SLA with margin.
      <br><br>
      <b>Part 3 — Improving compound SLA architecturally:</b> Convert sequential dependencies into <b>parallel paths with graceful degradation</b>. Example: replicate the BI query layer to two independent regions/clusters. If one fails, the other serves queries — the effective availability of the BI layer becomes 1 - (0.001)² = 99.9999%, not 99.9%. More impactfully: add an <b>async buffer</b> (e.g., a staging table or message queue) between Flink and the Data Warehouse. Flink writes to the buffer even when the DW is down; the DW loads from the buffer on recovery. This decouples Flink's availability from the DW's — a DW outage no longer causes Flink to backpressure or fail. In the compound availability formula, previously-sequential components become independent paths, and the product of two high-availability numbers is higher than either alone driving failure.
    </div>
  </div>
</div>

<!-- FOOTER -->
<div class="ft">
  Generated from Swaya.me screening platform &nbsp;·&nbsp; Quiz #186: B8 Data Engineer Screening &nbsp;·&nbsp; Exam date: 21 May 2026<br>
  10 questions &nbsp;·&nbsp; 40-minute calibrated interview &nbsp;·&nbsp; Confidential — for interviewer use only
</div>
</div>
</body>
</html>"""

def send():
    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT
    msg["From"]    = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"]      = TO_EMAIL
    msg.attach(MIMEText(HTML, "html"))
    ctx = ssl.create_default_context()
    print(f"Connecting to {SMTP_HOST}:{SMTP_PORT} …")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as s:
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
    print(f"Sent to {TO_EMAIL}")

if __name__ == "__main__":
    send()
