# Technical Interview: Venkata Ashok Medikonda — C11
**Duration:** 45 minutes | **Exam score:** 60/75 (12/15 correct, 45 min)
**Wrong answers:** HOT update conditions (Q0), Raft network partition (Q9), Choreography saga failure (Q11)

---

## BLOCK A — Storage Engine Internals (10 min)

---

**Q1.** *PostgreSQL has an optimisation called a HOT update (Heap-Only Tuple). Explain what a HOT update is, under what two conditions it can be used, and why it matters for performance.*

**Answer:**
A HOT update is an in-place update strategy where PostgreSQL writes the new row version onto the **same physical heap page** as the old version and chains the two versions together via a pointer inside the page — without touching any secondary index entries.

Two conditions that must both hold:
1. **The updated column does not appear in any secondary index.** If the changed column is indexed, index entries point to specific physical row locations (ctid). A HOT update does not move the row to a new page, but if the column is indexed, the index entries would still need updating. So HOT is only possible when no index references the changed column.
2. **The new row version fits on the same physical page as the old version.** If the page is full, the new version must go to a different page, making the chain across pages impossible.

Why it matters: a normal update in PostgreSQL creates a new row version on any page with space and then updates every secondary index to point to the new version's physical location (ctid). For a table with 10 indexes, one row update touches 11 structures. A HOT update touches only the heap page — index maintenance cost is zero. Under high UPDATE workloads this dramatically reduces write amplification and index bloat.

---

**Q2.** *A storage engine uses write-ahead logging (WAL). Explain the purpose of WAL and what guarantees it provides during crash recovery. Specifically: if a process crashes after writing a COMMIT marker to the WAL (fsynced to disk) but before flushing the corresponding data pages from memory to disk — what is the state of that record after recovery, and why?*

**Answer:**
WAL (Write-Ahead Logging) is the durability mechanism that ensures committed transactions survive crashes. The invariant is: the log record for a change must be durably written to disk **before** the change itself is considered committed and before the data pages are written. The log is sequential and append-only — much faster to write than random page updates.

Recovery procedure: on startup after a crash, the engine replays the WAL from the last checkpoint forward. For every log entry that has a matching COMMIT marker, it redoes the write to the data page (this is the **redo** phase). Entries without a COMMIT marker are incomplete transactions and are discarded (no rollback needed — they were never committed).

In the specific scenario — COMMIT marker fsynced to disk, data page not yet flushed — the record is **present after recovery**. The COMMIT marker on the WAL is durable (fsynced). The recovery procedure finds the committed entry in the WAL and replays the write to the data page. The fact that the in-memory page buffer was not flushed before the crash is irrelevant — WAL is the source of truth for what was committed.

This is precisely why WAL provides the D in ACID: durability is guaranteed by the WAL, not by when data pages happen to be flushed.

---

**Q3.** *A PostgreSQL primary database has logical replication configured with two subscribers. One subscriber's server is decommissioned, but the operations team forgets to drop the replication slot on the primary. What happens to the primary over time, and what are the two correct remediation steps?*

**Answer:**
WAL accumulates **indefinitely**.

Each replication slot records the oldest WAL position that the subscriber still needs. The primary retains all WAL from that position forward — it cannot delete any WAL that has not been confirmed consumed by the slot. Since the subscriber is gone, its slot position never advances. Over time, the WAL directory grows without bound, eventually filling the disk and crashing the primary database.

Remediation:
1. **Drop the stale replication slot** on the primary: `SELECT pg_drop_replication_slot('slot_name');`. This releases the WAL hold and allows the WAL cleanup process to resume normal operation.
2. **Set a maximum WAL retention cap** so future stale slots cannot grow unboundedly. PostgreSQL parameter: `max_slot_wal_keep_size` (introduced in PG 13) — the primary will invalidate a slot rather than retain WAL beyond this limit. A monitoring alert on `pg_replication_slots` where `active = false` should also be added to catch this operationally before it becomes critical.

---

## BLOCK B — Concurrency + Idempotency (10 min)

---

**Q4.** *A shared counter is implemented using compare-and-swap (CAS). CAS is atomic: it reads the current version, and only commits the new value if the version is unchanged since the read — otherwise it returns failure and the caller retries. Three threads simultaneously call `increment()`, all starting with `{value: 0, version: 0}`. What is the guaranteed final value of the counter, and why is it guaranteed — not just probable?*

**Answer:**
The guaranteed final value is **3**.

CAS atomicity is enforced at the hardware level (a single CPU instruction such as `LOCK CMPXCHG` on x86). When multiple threads race to CAS on the same memory location, exactly **one** wins and the rest get a failure response — this is guaranteed by the hardware, not by OS scheduling. There is no window where two threads can simultaneously succeed on the same version.

Because each failing thread **retries indefinitely** until it wins a CAS round, no increment is ever lost. The sequence of events:
- Round 1: one of the three threads wins (e.g. Thread A). Counter becomes `{value: 1, version: 1}`. Threads B and C get failure and retry.
- Round 2: one of B or C wins. Counter becomes `{value: 2, version: 2}`. The other retries.
- Round 3: the last thread wins. Counter becomes `{value: 3, version: 3}`.

The guarantee rests on two properties: hardware-level atomicity of CAS (no two threads can win the same version), and the retry-until-success loop (no thread gives up). Remove either property and the guarantee breaks.

---

**Q5.** *A job submission service deduplicates on `job_id` to prevent double-processing. The code below checks for an existing record, runs the job, inserts the result, and then calls `notify_downstream()` — which sends an external notification that is not idempotent (e.g. charges a card or sends an email).*

```
function submit(job_id, payload):
  if db.exists("jobs", job_id):
    return "duplicate"

  result = run_job(payload)
  db.insert("jobs", {id: job_id, result: result})
  notify_downstream(job_id, result)
  return "done"
```

*Two concurrent calls arrive with the same `job_id`. Both read `db.exists() = false`. What is the worst-case outcome? What is the minimal correct fix?*

**Answer:**
Worst-case outcome: `notify_downstream()` fires **twice**.

Both threads pass the `db.exists()` check before either has inserted a record. Both call `run_job()` (acceptable — idempotent). Both then call `db.insert()` — one will succeed and the other will fail on the unique PK constraint. But critically, the code calls `notify_downstream()` **before** checking whether the insert succeeded. Both threads have already called `notify_downstream()` by the time the second insert fails. The duplicate external event (charge, email) has gone out twice. The unique constraint stops the second insert but cannot recall the already-fired external notification.

Minimal correct fix — two changes together:
1. Add a **unique constraint** on `jobs.job_id` (or ensure the PK constraint covers it) so the DB enforces deduplication atomically.
2. Move `notify_downstream()` to **after** verifying the insert succeeded. Only the thread whose insert returns rows-affected = 1 should call `notify_downstream()`:
```
result = run_job(payload)
inserted = db.insert_if_not_exists("jobs", {id: job_id, result: result})
if inserted:
    notify_downstream(job_id, result)
```

If the insert fails (duplicate), skip `notify_downstream()`. `run_job()` may still execute twice, but since it is idempotent that is safe. The non-idempotent notification fires at most once.

---

**Q6.** *A distributed system uses a lease for mutual exclusion. Node A holds a lease with TTL = 30 seconds and performs the following check before writing to an external system:*

```
rec = lock.read()
if rec.node != node_id OR now() >= rec.expires_at:
    return "not_leader"

// GC stop-the-world pause for 45 seconds here
// lease expires; Node B acquires the lease and begins writing

write_to_external_system()   // concurrent writes corrupt state
```

*The lease check passes. Then a GC pause suspends Node A for 45 seconds — longer than the TTL. During that pause, the lease expires and Node B acquires it and starts writing. When Node A resumes, it proceeds to call `write_to_external_system()`. What is the outcome, and what is the standard mitigation?*

**Answer:**
Outcome: **both Node A and Node B write concurrently** — state corruption.

The lease check in Node A passed correctly at the time it was evaluated. But the check and the write are not atomic. A 45-second pause occurred between them. By the time Node A resumes and calls `write_to_external_system()`, its lease is 15 seconds expired and Node B is already the lease holder. Node A has no mechanism to detect this on resume — it simply continues from where it paused. Both nodes write simultaneously to a system that requires exclusive access.

Standard mitigation: **fencing tokens**. The lease server issues a monotonically increasing integer (the fencing token) each time a lease is granted. Node A was granted token 7; Node B was granted token 8. Every write call to the external system includes the writer's token. The external system enforces a simple rule: **reject any write whose token is lower than the highest token it has seen**. When Node A (token 7) tries to write, the external system has already seen Node B's token 8 and rejects Node A's request. Node B's writes (token 8) proceed normally.

Fencing tokens work even if Node A never knows it is no longer the leader — the external system enforces exclusivity without requiring the writer to self-detect its own staleness.

---

## BLOCK C — OS + Systems Internals (10 min)

---

**Q7.** *A Spark executor JVM is pinned to CPUs 16–23 on NUMA node 1 of a 2-socket server (node 0: CPUs 0–15, 64 GB RAM; node 1: CPUs 16–31, 64 GB RAM). The JVM was launched without NUMA control, so glibc defaulted all heap allocations to node 0. The executor reads 10 GB of data per minute into its heap. What is the performance penalty mechanism, and which `numactl` invocation correctly fixes it?*

**Answer:**
Performance penalty mechanism: **remote NUMA memory access latency**.

Every heap allocation lands on node 0's DRAM. Every heap access by a thread running on node 1's CPUs must traverse the inter-socket QPI/UPI interconnect to read from node 0's DRAM. Remote NUMA access takes approximately 100 ns vs 50 ns for local access — roughly **2× the memory latency**. At 10 GB/min (≈ 170 MB/s sustained), the executor spends the majority of its memory bandwidth budget crossing the interconnect unnecessarily. This manifests as high memory access latency, degraded throughput, and higher interconnect contention affecting all workloads on both sockets.

Correct fix:
```bash
numactl --cpunodebind=1 --membind=1 java -jar executor.jar
```

`--cpunodebind=1` ensures the JVM's threads are scheduled only on CPUs belonging to node 1. `--membind=1` ensures all memory allocations (including JVM heap, metaspace, and native off-heap) are satisfied from node 1's DRAM. Both pins together eliminate cross-socket traffic for this executor.

`--interleave=all` (often seen in documentation) spreads allocations across both nodes, which averages the latency rather than eliminating it — not appropriate here where full locality is achievable.

---

**Q8.** *A Python data pipeline runs inside a container with a cgroups v2 memory limit of `memory.max = 8 GB`. During a large batch, the pipeline allocates 8.5 GB of RAM. Describe the exact kernel sequence that follows. How does `memory.memsw.max` differ from `memory.max`?*

**Answer:**
Kernel sequence when a cgroup hits `memory.max`:

1. The kernel first attempts **page-cache reclaim** within the cgroup — it tries to free memory by evicting recently unused file-backed pages (OS page cache) that belong to processes in the cgroup. If this reclaims enough memory, the allocation succeeds and processing continues normally.
2. If page-cache reclaim is insufficient (the process's working set is genuinely too large), the kernel invokes the **OOM killer scoped to the cgroup**. The OOM killer selects the process in the cgroup with the highest `oom_score` (a heuristic based on memory usage and other factors) and sends it `SIGKILL`. In a container with a single process tree, this typically kills the main application process.
3. The container runtime (Docker/containerd) detects the OOM kill and can be configured to restart the container or mark it as failed.

`memory.max` vs `memory.memsw.max`:
- `memory.max` caps **RAM only**. A process that hits this limit can still use swap space if swap is available and `memory.memsw.max` is not set or is higher.
- `memory.memsw.max` caps **RAM + swap combined**. Setting it equal to `memory.max` effectively disables swap for the cgroup. Setting it higher allows some swap beyond the RAM cap. This is the critical difference for data pipelines: a container hitting only `memory.max` may survive by swapping to disk (with severe throughput degradation), while one also hitting `memory.memsw.max` is OOM-killed immediately.

---

**Q9.** *A high-throughput file pipeline uses `io_uring` with `IORING_SETUP_SQPOLL`. In this mode, a kernel thread continuously polls the submission queue — the application can write SQEs (Submission Queue Entries) directly to the ring without making a syscall. Under what specific condition must the application still call `io_uring_enter()` even in SQPOLL mode, and what must it pass?*

**Answer:**
The application must call `io_uring_enter()` when the **kernel SQPOLL thread has gone to sleep** after being idle for longer than `sq_thread_idle` milliseconds.

When there are no submissions to process for a configurable idle timeout, the kernel thread voluntarily sleeps to avoid burning CPU unnecessarily. At this point, new SQEs written to the ring by the application will not be noticed — the polling thread is no longer active.

The application detects this by checking the `IORING_SQ_NEED_WAKEUP` flag in the SQ ring's `flags` field. If this flag is set, the application must call:
```c
io_uring_enter(fd, 0, 0, IORING_ENTER_SQ_WAKEUP)
```
This syscall wakes the kernel SQPOLL thread, which then resumes polling and processes the pending SQEs. After the wakeup, normal zero-syscall operation resumes as long as submissions keep coming within the idle timeout.

The correct pattern in application code:
```c
// After writing SQEs to the ring:
if (sq_ring->flags & IORING_SQ_NEED_WAKEUP)
    io_uring_enter(fd, 0, 0, IORING_ENTER_SQ_WAKEUP);
```

`IORING_SETUP_SQPOLL` does not eliminate syscalls for all operation types — it only eliminates the per-submission syscall. Completion events are still read from the CQ ring without a syscall (memory-mapped ring).

---

## BLOCK D — Distributed Systems (8 min)

---

**Q10.** *A 5-node Raft cluster — nodes A (leader), B, C, D, E — is at term 5. A network partition splits it into two groups: {A, B} and {C, D, E}. Answer three questions: (a) Can A commit new log entries while partitioned? (b) What happens in the {C, D, E} partition? (c) When the partition heals, how does Raft prevent data loss or inconsistency?*

**Answer:**

**(a) Can A commit new entries?**
No. In Raft, a leader can only commit an entry once it has been acknowledged by a **majority** of nodes (3 out of 5). A and B are only 2 nodes — a minority. A cannot reach majority quorum, so it cannot commit any new entries. A will continue sending heartbeats to B and attempting to replicate log entries, but none will be committed. Clients connected to A will receive timeouts or errors.

**(b) What happens in {C, D, E}?**
{C, D, E} is a majority (3 out of 5). After not receiving heartbeats from A for an election timeout period, one of C, D, or E starts an election at **term 6** (higher than A's term 5). It requests votes from the other two. Since it is in the majority partition and has a log at least as up-to-date as any majority member, it wins. A new leader is elected in {C, D, E} and can commit new entries at term 6+.

**(c) How does Raft prevent inconsistency on partition heal?**
Two mechanisms work together:
- **Term number**: when the partition heals, A receives a message from the new leader (or any node) with term 6. Raft rules require any node that sees a higher term to immediately step down and revert to follower state. A steps down.
- **Log safety (Leader Completeness Property)**: Raft's election rules require a candidate to have a log at least as up-to-date as any majority. The new leader (elected from {C, D, E}) has all entries that were committed during term 5 (because those were committed with majority acknowledgment, which required at least one node from any majority — and {C, D, E} contains at least one). The new leader's log is the authoritative source. On heal, A and B receive the new leader's log and overwrite any uncommitted entries that diverge.

The entries A may have appended but not committed during the partition are simply overwritten — they were never committed and visible to clients.

---

**Q11.** *A financial transaction is implemented as a choreography-based saga across 5 services: payment-service reserves funds and emits `PaymentReserved`; inventory-service reserves stock and emits `StockReserved`; fraud-service consumes both events, performs fraud checking, and should emit `FraudApproved` — but it crashes before emitting anything. Fulfillment-service and notification-service are waiting for `FraudApproved`. Describe what happens next. Then explain how orchestration avoids this failure mode.*

**Answer:**
**What happens under choreography:**

fraud-service never emits `FraudApproved`. fulfillment-service and notification-service wait indefinitely for that event — or time out silently with no further action. Crucially, **no compensating events are emitted**:
- `PaymentCancelled` is never emitted → payment-service never releases the reserved funds
- `StockReleased` is never emitted → inventory-service never releases the reserved stock

The funds and stock remain permanently reserved. The transaction is neither committed nor rolled back — it is in a limbo state with resources locked. From the user's perspective the payment appears to have been taken (funds reserved) but no order is fulfilled. This is the **lost saga** failure mode. Choreography has no built-in mechanism to detect that a saga has stalled and trigger compensation — each service only reacts to events it receives, and if no event arrives, nothing happens.

**How orchestration avoids it:**

In orchestration, a central saga orchestrator explicitly coordinates all steps. The orchestrator:
1. Calls fraud-service directly (or sends it a command and tracks the response)
2. If fraud-service crashes or times out, the **orchestrator detects the failure** (via timeout or error response)
3. The orchestrator explicitly issues compensation commands: `CancelPayment` to payment-service and `ReleaseStock` to inventory-service
4. The orchestrator tracks the full saga state in a durable store — it knows at every moment which steps succeeded and which failed

The orchestrator is the single source of truth for saga progress. It can be made fault-tolerant itself (by persisting its state to a database before each step). There is no "lost saga" because the coordinator always knows the saga exists and what state it is in.

---

**Q12.** *Two events are observed in a distributed pipeline. Event A has Lamport timestamp L(A) = 42. Event B has Lamport timestamp L(B) = 42. Can you determine whether A causally precedes B from these timestamps? What is the formal limitation of Lamport timestamps, and what do vector clocks provide that Lamport timestamps do not?*

**Answer:**
You **cannot** determine from `L(A) = L(B) = 42` whether A causally precedes B.

Lamport's theorem states: if A causally precedes B (A → B), then L(A) < L(B). The contrapositive: if L(A) ≥ L(B), then A does not causally precede B. But the **converse does not hold**: L(A) < L(B) does NOT imply A → B. Equal timestamps (and even a lower timestamp for A) are consistent with A and B being concurrent — with no causal relationship.

Formal limitation: Lamport timestamps can rule out causality (if L(A) ≥ L(B), then definitively A ↛ B), but they cannot confirm it (L(A) < L(B) is necessary but not sufficient for A → B).

Vector clocks assign each of N processes its own counter. Each event carries a vector of N integers. `V(A) < V(B)` (A causally precedes B) is defined formally as:
- ∀i: V(A)[i] ≤ V(B)[i] — every component of A's vector is ≤ the corresponding component in B
- ∃j: V(A)[j] < V(B)[j] — at least one component is strictly less

This is both necessary and sufficient for A → B. If neither `V(A) < V(B)` nor `V(B) < V(A)`, the events are **concurrent** — no causal relationship in either direction.

The cost: vector clocks carry O(N) data per event. In a 1,000-node cluster, every message carries a 1,000-element vector. Lamport timestamps are O(1) — cheap to transmit but imprecise. Vector clocks are precise but expensive at scale.

---

**Q13.** *Google Spanner assigns commit timestamps using TrueTime, which returns a time interval [TT.earliest, TT.latest] reflecting bounded clock uncertainty (typically 1–7 ms). A transaction T1 commits with timestamp `ts1 = TT.now().latest`. Spanner then waits until `TT.now().earliest > ts1` before making T1 visible to any reader. Why is this wait necessary? What linearizability violation would occur without it?*

**Answer:**
The wait is necessary to guarantee **external consistency (linearizability)** — specifically: any transaction that starts after T1 is externally visible must see T1's writes.

Without the commit-wait — violation scenario:
- T1 commits at timestamp ts1 and is immediately made visible
- T2 starts "observably after" T1 (a user sees T1's result and then initiates T2)
- T2's server has a clock that has not yet advanced past ts1 — it is within the [TT.earliest, TT.latest] uncertainty window
- T2 receives a start timestamp ts2 < ts1
- T2 reads a snapshot at ts2, which predates T1 — it sees a world where T1 never happened
- The real-world order is T1 before T2, but T2 does not see T1's writes — a linearizability violation

How commit-wait prevents it:
By waiting until `TT.now().earliest > ts1`, Spanner guarantees that every server's clock has advanced past ts1 before T1 becomes visible. TrueTime's guarantee is: the true current time is within [TT.earliest, TT.latest]. If TT.earliest > ts1, then the true current time is definitely past ts1. Any transaction that starts after T1 becomes visible will receive a start timestamp from a clock that has already passed ts1 — it is guaranteed to see a snapshot that includes T1.

The wait duration equals the clock uncertainty ε (1–7 ms typically). This is the fundamental cost Spanner pays for external consistency without global synchronised clocks.

---

## BLOCK E — Data Lakehouse (7 min)

---

**Q14.** *An Iceberg table stores 365 days of event data — one partition per day. The metadata hierarchy has: 1 manifest list (with 365 entries, one per manifest file), 365 manifest files (each listing ~2,740 data files for one partition), and 1,000,000 total Parquet data files. A query runs `WHERE event_date = '2025-01-15'`. At which metadata level is pruning first applied, how many manifest files does the query open, and what information in the manifest list entries enables this?*

**Answer:**
Pruning is first applied at the **manifest list level** — before any manifest file is opened.

Each entry in the manifest list stores **partition-level bounds** for the partition covered by that manifest file — specifically `lower_bound` and `upper_bound` for each partition column (here, `event_date`). These bounds are stored directly in the manifest list as a compact summary.

Query execution:
1. The query planner reads the manifest list (1 small file, 365 entries)
2. It compares `event_date = '2025-01-15'` against each entry's `event_date` bounds
3. 364 entries have bounds that exclude '2025-01-15' — they are eliminated without being opened
4. Only **1 manifest file** is opened — the one whose bounds include '2025-01-15'
5. That manifest file lists its ~2,740 data files, which are then subject to file-level statistics pruning (min/max per column per data file)

This two-level pruning (manifest list → manifest file → data file) is what makes Iceberg's metadata hierarchy efficient at scale. Reading 365 manifest files to find one partition's data files would be equivalent to a full metadata scan — the manifest list's partition bounds make this O(1) per partition regardless of how many partitions exist.

---

**Q15.** *A platform ingests CDC (change-data-capture) from MySQL at 100,000 events per second onto a 10 TB Hudi table with 50 billion rows. 80% of events are UPDATEs to existing rows; 20% are INSERTs. Analytical queries run hourly over the full table. Which Hudi table type should be used, why, and what compaction configuration is required? What read-time trade-off remains even after compaction runs?*

**Answer:**
**Merge-on-Read (MOR)** is the correct choice.

**Why not Copy-on-Write (CoW):** CoW rewrites the entire Parquet file containing an updated row for every update event. At 80,000 UPDATEs/second across a 10 TB table, each write triggers a file rewrite. The write amplification is catastrophic — the storage I/O required to rewrite large Parquet files on every update exceeds what the system can sustain at this throughput.

**Why MOR:** MOR absorbs updates as **append-only delta log files** (Avro format). Each update appends a small record to the delta log for the affected file group — no Parquet rewrite occurs at write time. At 100K events/second, MOR write cost is proportional to the event stream size, not the table size. This is sustainable.

**Compaction configuration:** compaction must run **asynchronously** to avoid blocking the ingestion pipeline:
- `hoodie.compact.inline=false` — disables inline (synchronous) compaction that would block writes
- A separate scheduled Spark job (or Flink compaction service) runs `HoodieCompactionJob` on a schedule (e.g. every 30–60 minutes), merging delta log files back into base Parquet files

**Read-time trade-off:** Between compaction runs, readers must **merge base Parquet files with delta log files at query time** (the Hudi read-optimised or snapshot read path). The more delta log entries have accumulated since the last compaction, the more merge work each query must do. In the worst case (right before a compaction run), readers may need to merge many delta records into each base file — increasing scan latency proportionally to uncompacted log volume. This is the fundamental MOR trade-off: fast writes at the cost of slower reads when delta logs are large.

---

## Answer Summary

| Q | Topic | Exam | Key answer |
|---|-------|------|-----------|
| 1 | HOT update | ❌ WRONG | No index on changed column AND new version fits same page — both required |
| 2 | WAL crash recovery | ✅ | COMMIT in WAL is durable; recovery replays redo — record is present |
| 3 | WAL replication slot leak | ✅ | WAL accumulates indefinitely; fix: drop stale slot + set max_slot_wal_keep_size |
| 4 | CAS guaranteed value | ✅ | Exactly 3 — hardware atomicity + retry-until-success = no lost increments |
| 5 | TOCTOU idempotency | ✅ | notify_downstream fires twice; fix: unique constraint + move notify after insert |
| 6 | Distributed lease / fencing token | ✅ | Lease check ≠ atomic with write; fencing token lets external system reject stale writers |
| 7 | NUMA memory locality | ✅ | Remote DRAM 2× latency; fix: numactl --cpunodebind=1 --membind=1 |
| 8 | cgroups OOM killer | ✅ | Page-cache reclaim first; then OOM-kill highest oom_score; memsw.max = RAM+swap cap |
| 9 | io_uring SQPOLL wakeup | ✅ | Call io_uring_enter with IORING_ENTER_SQ_WAKEUP when IORING_SQ_NEED_WAKEUP flag set |
| 10 | Raft network partition | ❌ WRONG | {A,B} minority cannot commit; {C,D,E} elects new leader at term 6; no split-brain |
| 11 | Choreography saga / lost saga | ❌ WRONG | No built-in rollback; funds + stock permanently held; orchestration adds central coordinator |
| 12 | Lamport vs vector clocks | ✅ | L(A)=L(B) tells nothing; Lamport is necessary not sufficient; vector clocks are exact |
| 13 | Spanner TrueTime commit-wait | ✅ | Without wait: T2 could read snapshot before ts1; commit-wait ensures all clocks past ts1 |
| 14 | Iceberg manifest pruning | ✅ | Manifest list pruning first; partition bounds in list entries; 1 manifest file opened |
| 15 | Hudi MOR vs CoW | ✅ | MOR for 80% UPDATE rate; async compaction; read merges base + delta until compaction |
