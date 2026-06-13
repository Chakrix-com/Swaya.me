# 45-Minute Technical Interview: Sanchayan Sen — C11

## Candidate Profile
- **Exam**: C11 (Quiz 202), **Score**: 60/75 — **80% in 31 minutes**
- **Correct (12)**: HOT update conditions ✅, CAS guaranteed value ✅, WAL replication slot ✅, WAL crash recovery ✅, Distributed lease/fencing token ✅, NUMA memory locality ✅, cgroups OOM killer ✅, io_uring SQPOLL wakeup ✅, Raft partition ✅, Spanner TrueTime ✅, Iceberg manifest pruning ✅, Hudi MOR/CoW ✅
- **Wrong / Missing (3)**:
  - **Q3** — TOCTOU idempotency: chose "unique PK constraint prevents double notify"; correct: race happens *before* either insert — both threads call `notify_downstream` before the insert catches them
  - **Q10** — Lamport/vector clocks: **not answered** (left blank)
  - **Q11** — Choreography saga: chose "built-in circuit breaker triggers rollback"; correct: no such mechanism — "lost saga" leaves funds/stock permanently reserved

**Interview posture:** Strong systems depth across storage engines, OS internals, and distributed systems. The three misses are concentrated in: concurrency correctness under race conditions (Q3), distributed causality theory (Q10 — skipped entirely), and saga failure semantics (Q11). All three are directly relevant for a lead role coordinating multi-service distributed workflows. This session should confirm he can *reason through* failure modes in real systems, not just recognise correct answers.

---

## BLOCK A — Concurrency & Idempotency (10 min)

### A1 — Probe Wrong Answer: TOCTOU Race in Idempotent Submit (Q3)

**Show him the code:**
```
function submit(job_id, payload):
  if db.exists("jobs", job_id):         // check
    return "duplicate"

  result = run_job(payload)             // expensive, idempotent itself
  db.insert("jobs", {id: job_id, result})
  notify_downstream(job_id, result)     // NOT idempotent (charges a card, sends an email)
  return "done"
```

**Ask:** "Two concurrent calls arrive with the same `job_id`. Both read `db.exists() = false`. Walk me through what happens, and what the worst-case outcome is."

**Expected:** Both threads pass the check before either inserts. Both call `run_job()` (fine — idempotent). Both then call `notify_downstream()` — **before either insert completes**. So `notify_downstream` fires twice. Even if the second `db.insert` later fails on a unique key constraint, the external event (charge, email) has already gone out twice.

**His exam answer:** "No risk — `db.insert` fails on a duplicate PK, preventing both `run_job` and `notify_downstream` from completing twice." This is wrong — the PK constraint catches the insert, but by then `notify_downstream` has already fired on both threads.

**Follow-up:** "What is the minimal fix?"
- Expected: Two changes together:
  1. Add a **unique constraint** on `jobs.job_id` to catch the race at the DB level
  2. Move `notify_downstream` to **after** the insert — only call it if the insert succeeds (rows affected = 1). If insert fails with a duplicate key, skip notify.
  ```
  inserted = db.insert_if_not_exists("jobs", {id: job_id, result})
  if inserted:
      notify_downstream(job_id, result)
  ```

**Probe:** "Even with this fix — is the system truly idempotent?"
- Expected: Not fully. `run_job` may still execute twice before the insert constraint fires. If `run_job` has side effects (writes to S3, mutates external state), those run twice. The deeper fix is: check-then-insert in a single atomic operation (e.g. `INSERT IGNORE` / `ON CONFLICT DO NOTHING`), then read the stored result rather than recomputing it, and call `run_job` only once.

**Probe:** "Name a pattern that makes this whole function safely idempotent end-to-end."
- Expected:
  1. **Outbox pattern**: write `{job_id, result}` AND the notification intent to the DB in one transaction. A separate process reads the outbox and fires `notify_downstream` at-least-once, with the external system de-duplicating on `job_id`.
  2. Or: **exactly-once delivery token** — pass a unique idempotency key to `notify_downstream` and let the downstream de-duplicate.

---

### A2 — Probe Correct Answer: CAS (Q1) — Verify Depth

**Ask:** "Three threads all start `increment()` with `{value:0, version:0}`. You correctly said the final value is guaranteed to be 3. Why is 3 *guaranteed* and not *possible*? What property of CAS ensures this?"

**Expected:**
- CAS is **atomic** — "check and swap" happens without interruption. If two threads both read `version=0` and race to CAS, **exactly one wins** (hardware-level atomicity via `LOCK CMPXCHG` on x86). The other gets `ok=false` and retries.
- Because retry is a loop that continues until CAS succeeds, **no increment is ever lost** — each of the 3 threads eventually wins a CAS round with a unique version. Final value is always 3.
- The guarantee comes from: liveness (threads always retry) + hardware atomicity (no two threads can simultaneously win the same CAS).

**Probe:** "What's the performance failure mode of CAS under high contention?"
- Expected: **ABA problem** (value is A → B → A, stale read matches but semantics are wrong) and **livelock/starvation** — under very high contention, threads can spin indefinitely retrying. True spinlock CAS loops waste CPU. Mitigation: backoff (exponential or random sleep between retries), or use lock-free queues where contention is lower.

---

## BLOCK B — Distributed Systems: Causality + Saga Failures (10 min)

### B1 — Probe Unanswered Question: Lamport Timestamps vs Vector Clocks (Q10)

**Ask:** "Two events have equal Lamport timestamps — L(A) = L(B) = 42. Can you determine if A causally precedes B?"

**Expected:** No. Lamport's theorem is: `A → B` implies `L(A) < L(B)`, but the **converse is false** — `L(A) < L(B)` does NOT imply `A → B`. Equal timestamps tell you nothing about causality; A and B could be concurrent or on the same process.

**Follow-up:** "What do vector clocks add? Define formally when V(A) < V(B)."
- Expected: Vector clocks assign each process its own counter. `V(A) < V(B)` (A causally precedes B) iff:
  - `∀i: V(A)[i] ≤ V(B)[i]` — every component is ≤
  - `∃j: V(A)[j] < V(B)[j]` — at least one is strictly <
  - If neither `V(A) < V(B)` nor `V(B) < V(A)`, the events are **concurrent** (no causal relationship)

**Probe:** "Why don't we just always use vector clocks instead of Lamport timestamps?"
- Expected: Vector clocks have **O(N) space and message overhead** where N is the number of processes. In a cluster with 1,000 nodes, every message carries a 1,000-element vector. For causality tracking across large systems, this becomes impractical. Lamport timestamps are O(1) — cheap to transmit but can only detect definitively that events are NOT causally related, not that they ARE.

**Probe:** "Name a real system that uses vector clocks and one that uses Lamport timestamps."
- Expected:
  - Vector clocks: **Riak**, **Dynamo** (for conflict detection / sibling reconciliation), **CRDTs** in distributed databases
  - Lamport timestamps: **Lamport's bakery algorithm**, **Cassandra** (uses hybrid logical clocks which are Lamport-based), **multi-leader replication** for rough ordering

---

### B2 — Probe Wrong Answer: Choreography Saga Failure (Q11)

**Ask:** "5-step choreography saga: payment reserves funds, inventory reserves stock, fraud-service crashes before emitting any event. What specifically happens next?"

**Expected (the correct "lost saga" failure mode):**
- `fraud-service` never emits `FraudApproved` → `fulfillment-service` waits indefinitely (or times out silently)
- `payment-service` and `inventory-service` are never notified to compensate — they emitted `PaymentReserved` and `StockReserved` and have no way to know the saga failed
- Result: funds are permanently reserved; stock is permanently held. The transaction is in an inconsistent half-committed state — neither committed nor rolled back.
- This is the **"lost saga"** failure mode under choreography.

**His exam answer:** "Choreography detects the missing event via a built-in circuit breaker and triggers automatic rollback." This mechanism doesn't exist in choreography. Ask directly: "Where would that circuit breaker live in a choreography model?"
- Expected self-correction: In choreography, services only react to events — there is no central coordinator watching for missing events. There's no built-in timeout-and-compensate mechanism.

**Follow-up:** "How does orchestration solve this?"
- Expected: An orchestrator (e.g. AWS Step Functions, Temporal, Conductor) centrally tracks each step. When fraud-service crashes, the orchestrator detects the failure (timeout or exception) and **explicitly invokes compensating transactions**:
  - Call `payment-service.CancelReservation(job_id)`
  - Call `inventory-service.ReleaseStock(job_id)`
  - The orchestrator holds the saga state machine and knows exactly where rollback must start.

**Probe:** "When would you still choose choreography over orchestration despite this risk?"
- Expected: Choreography is appropriate for:
  - **Loosely coupled, independent services** where each step can self-contain its rollback (e.g. reservation systems with TTL-based auto-release)
  - **Simple 2-3 step flows** where the failure surface is small
  - **Event-driven architectures** where services shouldn't know about each other
  - Orchestration is better for: complex multi-step transactions with mandatory compensation, financial workflows, and anywhere the "lost saga" failure is unacceptable.

---

### B3 — Probe Correct Answer: Raft Partition (Q9) — Depth

**Ask:** "5-node Raft, term 5. {A,B} and {C,D,E} partition. What happens on each side?"

**Expected:**
- `{A,B}`: A cannot commit new entries — needs 3/5 majority, only has 2. A's heartbeats stop reaching C/D/E.
- `{C,D,E}`: Start an election. Any of C/D/E becomes leader at term ≥ 6 (term increments on election). New leader has all committed entries from term 5 — guaranteed by Raft's election safety property (winner must have log at least as up-to-date as any majority).
- A eventually steps down when it stops receiving majority acknowledgement for heartbeats.

**Probe:** "What prevents A from continuing to accept writes from clients during the partition, causing split-brain?"
- Expected: A cannot **commit** writes — a write is only committed when acknowledged by a majority (3/5). Without B+C or B+D or B+E responding, A can accept writes to its log but cannot advance its commit index. Clients waiting for commit confirmation will time out. No data is durably written without a quorum.

---

## BLOCK C — Storage Engine Internals (10 min)

### C1 — Probe Correct Answer: HOT Update (Q0) — Depth

**Ask:** "The exam had two strategies for an update to a non-indexed column. Strategy B keeps the new row version on the same physical page, chained to the old via a pointer. You correctly gave the two conditions. What is this optimisation called in PostgreSQL, and why does it matter?"

**Expected:** This is PostgreSQL's **Heap-Only Tuple (HOT)** update. Conditions: (1) no indexed column changes; (2) the new version fits on the same heap page (page has free space). It matters because:
- Standard updates on indexed columns must update ALL secondary indexes pointing to the old physical location (ctid). On wide tables with many indexes, this is expensive.
- HOT avoids touching secondary indexes entirely. The old index entry still points to the old ctid; the page-internal chain (HOT chain) links old→new. A vacuum later prunes the chain.
- Result: significantly fewer WAL records and I/O for updates that only touch non-indexed columns.

**Probe:** "What happens to the index during a HOT update if someone queries on an indexed column — how do they find the new row version?"
- Expected: The old index entry still points to the old tuple's ctid. When the executor fetches that tuple, it follows the HOT chain through the page to find the current (live) version. The chain traversal is cheap (in-page pointer dereference). From the query's perspective, it looks up the index → finds the old ctid → follows HOT chain → gets the current version.

**Probe:** "What happens to HOT chains during vacuum?"
- Expected: Vacuum prunes HOT chains — it removes dead tuple versions from the chain, updating the index entry to point directly to the current live version (or latest surviving ancestor). After vacuuming, the chain shortens, freeing page space for new versions (contributing to the `fillfactor` budget).

---

### C2 — Probe Correct Answer: WAL Crash Recovery (Q4) — Mechanism

**Ask:** "The exam: WAL COMMIT is durably fsynced to disk. Process crashes before page_buffer.write(). After recovery, R is present. Walk me through the exact recovery mechanism."

**Expected:**
1. Recovery process scans the WAL from the last checkpoint
2. Finds `BEGIN` and `DATA(R)` entries followed by a `COMMIT` marker
3. Because the COMMIT is present and durable, R is a committed transaction — redo is required
4. `page_buffer.redo(R)` replays the write: R is written to the storage page
5. Recovery is complete — R is present in the database

**Follow-up:** "What would happen if the crash occurred after `BEGIN` and `DATA(R)` were written but BEFORE `COMMIT` was fsynced?"
- Expected: R is **rolled back** (discarded). Recovery scans the WAL, finds `BEGIN` and `DATA(R)` but no matching `COMMIT` → incomplete transaction → skip (undo). R is never written to the page buffer. The WAL provides durability for committed writes and atomicity for incomplete ones.

**Probe:** "What is checkpointing's role in this recovery process?"
- Expected: Checkpointing flushes all dirty page_buffer pages to disk and records the checkpoint LSN in the WAL. Recovery only needs to replay WAL from the last checkpoint forward — not from the beginning of the WAL file. This bounds recovery time. Without checkpoints, a long-running server crash could require replaying hours of WAL.

---

### C3 — Probe Correct Answer: Spanner TrueTime (Q12) — Linearizability

**Ask:** "Spanner commits T1 at `ts1 = TT.now().latest` and waits until `TT.now().earliest > ts1` before making T1 visible. Why is this wait necessary for linearizability?"

**Expected:**
- TrueTime returns a bounded interval `[earliest, latest]` — the real time is somewhere in this interval.
- By using `TT.now().latest` as the commit timestamp, Spanner ensures `ts1` is ≥ the actual commit time.
- The commit-wait ensures that by the time T1 is visible, `TT.now().earliest > ts1` — meaning every Spanner server's local clock has definitely advanced past ts1.
- Without the wait: a transaction T2 that starts *after* T1 is externally visible could be assigned a timestamp `ts2 < ts1` (T2's TrueTime interval hasn't advanced past ts1). T2 would read a snapshot predating T1, violating linearizability — T2 started after T1 was committed and visible, yet doesn't see T1's writes.

**Probe:** "TrueTime uncertainty ε is typically 1–7 ms. What does the commit-wait cost in practice?"
- Expected: Each committed write blocks for ε ms (1–7 ms) before becoming visible. For high-throughput transactional workloads, this is a significant latency floor — you cannot get sub-millisecond commit latency on Spanner. Google accepts this trade-off because external consistency (linearizability) is worth more than microsecond latency for their use cases.

---

## BLOCK D — OS/Systems Internals (8 min)

### D1 — Probe Correct Answer: Distributed Lease / Fencing Token (Q5) — Design

**Ask:** "Node A holds a 30s lease. GC pause of 45s. Node B acquires the lease and starts writing. You correctly said both A and B write concurrently → corruption. The fix is a fencing token. Implement it."

**Expected mechanism:**
1. Each lease acquisition returns a **monotonically increasing fencing token** (e.g. lease epoch number: 1, 2, 3…).
2. Node A acquired the lease at epoch 5. Node B acquires it at epoch 6 (after A's expired).
3. When writing to the external system, the writer includes the token: `write(data, fencing_token=5)`.
4. The external system tracks the **highest token seen** and rejects any write with a lower token: `if token < max_seen_token: reject`.
5. After A's 45s pause, it resumes and calls `write(data, fencing_token=5)` — but max_seen is now 6 (from B's writes) → A's write is rejected. State corruption avoided.

**Probe:** "What if the external system can't be modified to check tokens — it's a third-party API?"
- Expected: This is the hard case. Options:
  - Use a **compare-and-swap** style update: `write(data, expected_version=v, new_version=v+1)` — the API must support optimistic versioning.
  - Use a **lease heartbeat** within the critical section — A checks its lease is still valid immediately before writing. This narrows the window but doesn't eliminate it (still a TOCTOU race between check and write).
  - Accept the risk and design for idempotent writes + post-hoc reconciliation.

---

### D2 — Probe Correct Answer: cgroups OOM (Q7) — Depth

**Ask:** "8 GB cgroups memory limit, pipeline allocates 8.5 GB. Walk me through the exact kernel sequence."

**Expected:**
1. Memory allocation fails at the cgroup boundary (`memory.max = 8 GB` exceeded)
2. Kernel tries **page reclaim** within the cgroup — evicts page cache pages that belong to this cgroup's processes
3. If reclaim is insufficient: kernel invokes the **OOM killer**, scoped to the cgroup (not system-wide)
4. OOM killer selects the process within the cgroup with the highest `oom_score` (typically the largest RSS process)
5. Sends `SIGKILL` to the selected process

**Probe:** "If the container has `memory.memsw.max = 16 GB` set, does the same sequence play out at 8 GB?"
- Expected: No — `memory.max` caps RAM only; `memory.memsw.max` caps RAM + swap combined. If the pipeline hits 8 GB RAM but `memsw.max = 16 GB` and swap is available, the kernel uses swap instead of invoking OOM killer. The process slows down significantly (swap I/O) but keeps running. OOM only fires if both RAM and swap limits are exhausted.

---

### D3 — Probe Correct Answer: io_uring SQPOLL Wakeup (Q8) — Depth

**Ask:** "io_uring SQPOLL: a kernel thread polls the submission ring so the application avoids syscalls. Under what specific condition must the application still call `io_uring_enter()`?"

**Expected:** When the SQPOLL kernel thread has gone to sleep after `sq_thread_idle` ms of inactivity (configurable, typically a few seconds of no submissions). The application must check the `IORING_SQ_NEED_WAKEUP` flag in the SQ ring's flags field. If set, it must call `io_uring_enter(fd, 0, 0, IORING_ENTER_SQ_WAKEUP)` to wake the kernel thread before new SQEs are processed.

**Probe:** "Why does the kernel thread go to sleep at all? Why not spin forever?"
- Expected: A spinning kernel thread consumes 100% of one CPU core, even when the application has no I/O to submit. For applications with burst I/O patterns (active periods followed by idle periods), this wastes CPU. The idle timeout lets the kernel thread sleep and free the CPU, at the cost of one extra `io_uring_enter()` syscall on wakeup — which is still much cheaper than a syscall per-I/O.

---

## BLOCK E — Data Lakehouse + Live Design (7 min)

### E1 — Probe Correct Answer: Iceberg Manifest List Pruning (Q13) — Depth

**Ask:** "The exam: 1 million files, 365 daily partitions. Query `WHERE event_date = '2025-01-15'`. Pruning starts at the manifest list level. Walk me through exactly what metadata is stored and how the skip works."

**Expected:**
- **Manifest list**: one entry per manifest file; each entry stores partition-level bounds (`lower_bound`, `upper_bound` for each partition column — in this case, `event_date`)
- Query planner reads the manifest list (tiny — 365 entries), evaluates `event_date = '2025-01-15'` against each entry's bounds
- 364 entries fall outside the target date → eliminated without opening their manifest files
- 1 matching manifest file is opened → reads ~2,740 data file paths for Jan 15
- Data file min/max stats (within the manifest) do further pruning

**Probe:** "The exam has 1M data files. If there were no manifest list — just one giant manifest — how would this change?"
- Expected: The query would still need to read all 1M file entries from the single manifest to find those belonging to Jan 15. Manifest list's two-tier structure (manifest list → manifest files → data files) is what makes partition pruning O(1) at the top level rather than O(N data files).

---

### E2 — Probe Correct Answer: Hudi MOR/CoW CDC (Q14) — Design Tradeoff

**Ask:** "100K events/second CDC into a 50B row Hudi table, 80% UPDATEs. You correctly chose MOR. What specifically makes CoW wrong here, and what does the async compaction job need to do?"

**Expected why CoW fails:**
- CoW rewrites the entire Parquet file on every UPDATE — 80% of 100K events/sec = 80K rewrites/sec. Each rewrite reads the old file, merges the update, writes a new file. At this rate, CoW would fall behind immediately — write amplification is catastrophic.
- MOR appends UPDATE events to **Avro delta log files** (append-only, cheap). The base Parquet files are only rewritten during compaction.

**Compaction config:**
- `hoodie.compact.inline = false` — do NOT compact on every write (would kill write throughput)
- A separate scheduled Spark job runs compaction every N hours: `spark-submit ... --class HoodieCompactor`
- Compaction reads base Parquet + delta log files, merges, rewrites clean Parquet files
- Compaction scheduling: typically every 1–4 hours for hourly analytical queries

**Trade-off:**
- Between compaction runs, queries must **merge base + delta files at read time** — reading 1 hour of delta logs before getting a clean result. Read latency grows proportionally to uncompacted log volume.

**Probe:** "If analytical queries run every hour and compaction also runs every hour, is the read latency problem solved?"
- Expected: Mostly, but not fully. Compaction takes time to run (could be minutes for a 10 TB table). Queries that land during compaction see the full uncompacted logs. Also: if compaction falls behind (due to cluster load), log files accumulate faster than they're compacted → read latency degrades. The fix is monitoring `hoodie_table_metadata.log_file_count` and alerting when it grows beyond a threshold.

---

## Answer Key Summary

| Block | Topic | What to listen for | Red flag |
|-------|-------|-------------------|----------|
| A1 | TOCTOU idempotency | Race before insert; notify fires twice; fix: insert-first + conditional notify | "PK constraint prevents both notifies" |
| A2 | CAS guarantee | Exactly 3 because retry loops ensure all increments apply; hardware atomicity | "Could be 1–3 depending on timing" |
| B1 | Lamport / vector clocks | L(A)=L(B) tells nothing; ∀i ≤ and ∃j < defines causal precedence; O(N) cost | "Equal Lamport = concurrent" |
| B2 | Lost saga / choreography | No built-in compensation; funds/stock permanently held; orchestrator fixes by explicit compensating calls | "Circuit breaker auto-rolls back" |
| B3 | Raft partition | {A,B} can't commit without majority; {C,D,E} elects at term 6+; log safety from election rule | "A continues committing to {A,B}" |
| C1 | HOT update | Non-indexed column + same page = no index update; HOT chain; vacuum prunes | "HOT only applies to deletions" |
| C2 | WAL crash recovery | COMMIT durable → redo on recovery; no COMMIT → discard; checkpoint bounds replay window | "R is lost because page_buffer never wrote" |
| C3 | Spanner TrueTime | Commit-wait ensures T2 (starting after T1 visible) always gets ts2 > ts1; ε ms latency cost | "Commit-wait is a performance tuning knob" |
| D1 | Fencing token | Monotonic token per lease; external system rejects stale token; hard without API support | "Re-checking lease before write is sufficient" |
| D2 | cgroups OOM | Page reclaim first; OOM killer scoped to cgroup; memsw includes swap | "OOM is system-wide, kills any process" |
| D3 | io_uring SQPOLL | IORING_SQ_NEED_WAKEUP flag; wake call needed after idle timeout | "SQPOLL eliminates all syscalls permanently" |
| E1 | Iceberg manifest list | Two-tier: list → manifest → data files; partition bounds in list entries; 364 manifests skipped | "All 365 manifest files must be read" |
| E2 | Hudi MOR compaction | CoW write amplification at 80K ups/s; async compaction + trade-off: read must merge logs | "MOR is for insert-heavy workloads only" |

---

## Interviewer Notes

**80% in 31 minutes is elite-level performance on a hard systems exam.** The three misses are meaningful:

- **Q3 (TOCTOU)** is the most important probe — he understands CAS atomicity (Q1) perfectly but missed a simpler race condition in application-level code. This inconsistency is worth probing: ask him to trace through the timing step by step. If he can self-correct quickly, it was a reading error; if he doubles down on "PK prevents it," there's a genuine gap in understanding check-then-act races.

- **Q10 (Lamport clocks) — not answered** is the most unusual finding. At 31 minutes for a 45-minute exam, he had time. Possibilities: the question displayed poorly, he decided to skip it, or he genuinely wasn't confident. B1 will establish the truth quickly.

- **Q11 (lost saga)** probes architecture judgment — choosing choreography vs orchestration is a lead-level decision. The correct understanding of "lost saga" failure and when to use an orchestrator is essential for anyone designing distributed financial workflows at NatWest.

**His strongest zone is OS/systems internals** — io_uring SQPOLL, cgroups OOM killer, NUMA, and fencing tokens are all correct and niche. Block D should confirm these are real working knowledge, not lucky guesses, by asking for implementation details and failure modes.
