# Technical Interview: Navneet Kumar Deswal — C11
**Duration:** 30 minutes | **Exam score:** 75/75 (15/15 correct, 26 min)

**Interview strategy:** Perfect score in 26 minutes means all 15 concepts were recognised correctly. These questions do not repeat the exam — they assume that foundation and go one level deeper: implementation, failure modes, edge cases, and design decisions. Every question here is something the exam could not test with multiple choice.

---

## BLOCK A — Storage + Recovery (8 min)

---

**Q1.** *You are designing a high-churn table in PostgreSQL: a `sessions` table where `last_seen_at` is updated every 30 seconds per active user. The table has 5 secondary indexes — none of which include `last_seen_at`. A DBA notices that VACUUM is spending most of its time on this table and that dead tuple count is very high. You explain HOT updates should be handling this efficiently. The DBA says HOT updates are barely firing — fewer than 10% of updates qualify. What is the most likely cause, and how do you fix it?*

**Answer:**
The most likely cause is **insufficient free space on heap pages** — the second HOT condition (new row version must fit on the same page) is failing.

When a page is full, PostgreSQL cannot write the new row version there and must find space elsewhere — breaking the HOT chain. Even though `last_seen_at` is not indexed (first condition met), pages are 100% packed, so HOT never fires.

Fix: set a **FILLFACTOR** below 100% on the table:
```sql
ALTER TABLE sessions SET (fillfactor = 70);
VACUUM FULL sessions;  -- rewrites pages at 70% fill density
```

`fillfactor = 70` leaves 30% of each page reserved for in-place updates (HOT). PostgreSQL will write new initial rows at 70% page fill but leave the remaining 30% for HOT updates on the same page. After the table is rewritten (VACUUM FULL or CLUSTER), HOT update rates will rise sharply, dead tuples will fall, and VACUUM overhead will decrease.

Secondary consideration: if the table is also append-heavy (new rows from new users), the reserved space gets consumed by inserts rather than HOT updates. A FILLFACTOR tuned specifically for the update-to-insert ratio of the workload is needed — a pure update table can use 50–70%; a mixed table may need 80–90%.

---

**Q2.** *PostgreSQL uses WAL for crash recovery. Describe the ARIES recovery algorithm: what are the three phases, and critically — when is an undo phase needed and when is it not? What is a Compensation Log Record (CLR) and why does ARIES write one during undo?*

**Answer:**
ARIES (Algorithm for Recovery and Isolation Exploiting Semantics) has three phases:

**Phase 1 — Analysis:** scan the WAL forward from the last checkpoint. Reconstruct the state at the time of the crash: which transactions were active (not yet committed), which were committed. Build the Dirty Page Table (pages modified but not yet flushed) and the Transaction Table (active transactions and their last LSN).

**Phase 2 — Redo:** replay all changes from the oldest dirty page LSN forward, regardless of whether transactions committed or not. This restores the database to the exact state it was in just before the crash — including the in-progress changes from uncommitted transactions.

**Phase 3 — Undo:** roll back all transactions that were active (uncommitted) at crash time, in reverse LSN order. Undo each change by applying its compensating operation.

**When is undo needed vs not:**
- **Undo is needed** whenever there were active (uncommitted) transactions at crash time. These transactions modified pages (now restored by redo) but never committed — their changes must be rolled back to maintain atomicity.
- **Undo is NOT needed** if all transactions had committed before the crash. In that case, redo restores the committed state and there is nothing to roll back. This is the common case for systems with short transactions and clean shutdowns.

**Compensation Log Record (CLR):** during the undo of an active transaction, ARIES writes a CLR for each operation it undoes. A CLR is a special WAL record that says "I undid this original log record." If the system crashes again during the undo phase, recovery redoes the CLR (not the original change), correctly skipping operations already undone. CLRs make undo **idempotent** — the undo phase can be safely repeated after a crash-during-recovery without double-undoing anything.

---

**Q3.** *Your team runs a PostgreSQL primary with 8 logical replication subscribers. You are building an automated monitoring+remediation system. What specific metric from PostgreSQL system views do you monitor for each slot, at what threshold do you trigger an alert vs an auto-drop, and what is the risk of auto-dropping vs not dropping?*

**Answer:**
Primary metric: **`pg_replication_slots.confirmed_flush_lsn`** (or `restart_lsn`) compared to the current WAL write position (`pg_current_wal_lsn()`). The lag in bytes:
```sql
SELECT slot_name, active,
       pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn) AS lag_bytes
FROM pg_replication_slots;
```

Secondary metrics: `pg_replication_slots.active` (is the subscriber currently connected?), and wall-clock time since last activity.

**Threshold strategy:**

| Condition | Action |
|-----------|--------|
| `lag_bytes > 1 GB` AND `active = false` | Alert: subscriber may be down |
| `lag_bytes > 5 GB` OR WAL disk usage > 70% | Page on-call; investigate immediately |
| `active = false` for > 24 hours AND lag growing | Auto-drop the slot |

**Risk of auto-dropping:** if the subscriber was merely slow or temporarily disconnected (network blip, rolling restart), dropping the slot forces it to re-sync from scratch — potentially a full table copy and hours of replication lag. This is disruptive but recoverable.

**Risk of NOT dropping:** if the slot is truly orphaned (subscriber decommissioned), WAL accumulates without bound. When the primary disk fills, the database crashes hard — no graceful degradation, no time to react. This is an outage risk for all subscribers, not just the stale one.

Safe policy: alert at 1 GB lag, auto-drop only after a confirmed grace period (24h) with active=false and growing lag. Always set `max_slot_wal_keep_size` as a hard backstop so no single slot can cause a disk-full crash regardless of the alert pipeline's reliability.

---

## BLOCK B — Concurrency + Systems (7 min)

---

**Q4.** *CAS with retry guarantees no lost updates when the only change to the shared value is an increment. Describe the ABA problem: under what conditions does CAS with retry produce an incorrect result despite the version matching, and how is it solved?*

**Answer:**
The **ABA problem** occurs when a value changes from A to B and then back to A between a thread's read and its CAS. The CAS sees the version matches (still A) and succeeds — but the semantics of "unchanged" are violated because the value went through an intermediate state the thread is unaware of.

Example: a lock-free stack. Thread 1 reads top = Node_A (value=10). Thread 1 is preempted. Thread 2 pops Node_A, pushes Node_B, pops Node_B, and pushes Node_A back (perhaps reusing the memory). Thread 1 resumes: CAS sees top = Node_A — version matches — and succeeds. But Node_A's `next` pointer has changed during the interim. Thread 1 has now set the stack to a corrupted state based on a stale `next`.

This does not affect simple counters (where the version number is separate from the value and is strictly monotonically increasing — A→B→A cannot happen on the version integer). ABA is only a problem when the value being CAS'd on can cycle, and the intermediate state change is semantically significant.

Solutions:
1. **Tagged pointer / version stamp:** pair the pointer with a monotonically increasing counter in a single word. `cas((ptr, ver), (old_ptr, old_ver), (new_ptr, old_ver+1))`. Even if ptr returns to the same address, the version counter never matches the old snapshot.
2. **Hazard pointers:** before dereferencing a pointer, publish it in a thread-local hazard pointer list. Memory reclamation (freeing Node_A for reuse) is deferred until no hazard pointer references it — preventing the A→B→A reuse cycle at the root.
3. **Hardware DCAS (Double-CAS):** atomically CAS on two memory locations simultaneously — available on some architectures but not universally.

---

**Q5.** *You are building the external storage system that Raft-based writers write to, and you need to enforce fencing tokens to prevent stale leaders from corrupting state. Design the write handler: what data structure does it maintain, how does it handle a write from a stale token, and what happens if the storage system itself restarts?*

**Answer:**
The storage system maintains a **per-resource monotonic high-water mark** — the highest fencing token it has ever accepted for each resource (e.g. keyed by the resource ID or the lock name).

```
FUNCTION write(resource_id, fencing_token, data):
    hwm = store.get_hwm(resource_id)   // durable read
    IF fencing_token < hwm:
        RETURN Error("stale token: %d < hwm %d", fencing_token, hwm)
    IF fencing_token > hwm:
        store.set_hwm(resource_id, fencing_token)  // durable write before data write
    store.write_data(resource_id, data)
    RETURN OK
```

Critical design points:

**The HWM must be stored durably before the data write.** If the storage system crashes between updating the HWM and writing the data, on recovery the HWM is at the new token — stale writers are still rejected. If the HWM were updated after the data write and a crash occurred between them, the HWM would be stale and a future stale writer could succeed. Write the HWM first, or in the same atomic transaction as the data.

**On storage system restart:** the HWM is read from durable storage (disk, database). An in-memory HWM is useless — after a restart it would be zero, allowing any token to succeed. The HWM must survive restarts to maintain its monotonic guarantee across the system's full lifetime.

**Stale token handling:** return a clear error — do not silently discard. The stale writer should log the rejection. The HWM in the error response can help the caller diagnose its own staleness.

**Token equality:** if `fencing_token == hwm`, the write is from the current lease holder — allow it. This handles the case where a write is retried after a network timeout without the leader knowing its first attempt succeeded.

---

## BLOCK C — Distributed Systems (9 min)

---

**Q6.** *Standard Raft has a vulnerability: a partitioned follower with a stale term that rejoins can disrupt the current leader by starting an election with a higher term, forcing the leader to step down even though this follower's log is behind. What is the Pre-Vote extension, how does it prevent this disruption, and what property of the Raft cluster does it preserve?*

**Answer:**
**The vulnerability:** when a follower is partitioned, it cannot receive heartbeats. After its election timeout, it increments its term and starts an election. When the partition heals, it sends `RequestVote` with the higher term. The current leader sees a higher term, steps down (Raft rule: any node seeing a higher term reverts to follower), and a new election is forced — even though the existing leader was healthy and the rejoining node's log may be behind.

**Pre-Vote extension:** before incrementing its term and sending a real `RequestVote`, a candidate first sends a `PreVote` request. The `PreVote` asks other nodes: "if I were to start an election right now, would you vote for me?" It uses the candidate's *current* term (not incremented) and current log position.

A node responds positively to `PreVote` only if:
1. It has not heard from a current leader recently (suggesting the leader may actually be down), AND
2. The pre-candidate's log is at least as up-to-date as its own

If the candidate cannot gather a majority of positive `PreVote` responses — meaning the cluster sees a healthy leader — it does not increment its term and does not send a real `RequestVote`. The current leader's term is never disrupted.

**Property preserved:** Pre-Vote preserves **leader stability** — a healthy leader is not forced to step down by a rejoining stale follower. Without Pre-Vote, a network partition can cause cascading elections even in an otherwise healthy cluster. With Pre-Vote, term inflation only occurs when a genuine leader failure is suspected by a majority.

---

**Q7.** *Two services, X and Y, use vector clocks with 3 processes {X, Y, Z}. Current state: X has processed events up to V(X) = [3, 2, 1]. Y has independently processed events up to V(Y) = [1, 4, 2]. X sends a message M to Y carrying timestamp [3, 2, 1]. When Y receives M, what does Y's vector clock become, and why? Then Y sends a response to X. What does X's clock become after receiving Y's response?*

**Answer:**
**When Y receives M from X:**

The rule on message receive: merge by taking the **element-wise maximum** of the receiver's current clock and the received timestamp, then increment the receiver's own component.

Y's current clock: [1, 4, 2] (indices: X=1, Y=4, Z=2)
Received timestamp: [3, 2, 1] (X=3, Y=2, Z=1)

Element-wise max: [max(1,3), max(4,2), max(2,1)] = [3, 4, 2]
Increment Y's own component: [3, **5**, 2]

Y's clock after receiving M: **[3, 5, 2]**

This reflects that Y now knows: X has seen at least 3 events (from X's perspective), Y has processed 5 events, Z has processed at least 2 events. The causal history of M is now incorporated into Y's clock.

**When Y sends response R to X:**
Y's clock at send time: [3, 5, 2] (Y increments its own counter on send): [3, **6**, 2]
R is sent with timestamp [3, 6, 2].

**When X receives R:**
X's current clock: [3, 2, 1] (X has not processed any events since sending M)
Received timestamp: [3, 6, 2]

Element-wise max: [max(3,3), max(2,6), max(1,2)] = [3, 6, 2]
Increment X's own component: [**4**, 6, 2]

X's clock after receiving R: **[4, 6, 2]**

X now knows causally: this response from Y happened after Y had seen Y's 6th event, X's 3rd event, and Z's 2nd event. X can correctly determine that R causally followed M — V(M) = [3,2,1] < V(R) = [3,6,2] (all components ≤, Y component strictly <).

---

**Q8.** *Design the compensating transaction for the payment step in a 5-step choreography saga. The payment step reserves funds in an external payment gateway that does not support distributed transactions. What properties must the compensating transaction have, and what specific failure scenarios must it handle?*

**Answer:**
**Properties of a valid compensating transaction:**

1. **Idempotent:** the compensating transaction may be called multiple times (network retries, saga engine restarts). It must produce the same result regardless of how many times it runs. Calling `cancel_reservation(reservation_id)` twice must be safe — the second call on an already-cancelled reservation must return success (not an error that aborts the saga).

2. **Semantically reversing, not undoing:** compensation does not "undo" — the original reservation happened and may have had real effects (e.g. the funds were briefly held). Compensation creates a new forward action that reverses the business effect: `CancelPaymentReservation` event, not a rollback. The audit log shows both the reservation and the cancellation.

3. **Eventually consistent:** the compensating transaction may not take effect immediately (the payment gateway may be slow or temporarily unavailable). The saga must retry compensation until it succeeds — compensation cannot silently fail.

4. **Bounded by the resource's expiry:** if the payment gateway has a reservation TTL (e.g. 15 minutes), the compensation must complete before TTL expiry. After expiry, the gateway auto-releases the funds — compensation succeeds trivially. The saga engine must track the TTL and can short-circuit if it expires.

**Failure scenarios it must handle:**

- **Compensation called before original completed:** the reservation_id does not exist yet. Must return "not found" as a success (nothing to cancel). Do not retry indefinitely on a not-found.
- **Compensation called after TTL expiry:** gateway already auto-released. Must treat as success.
- **Compensation called while gateway is down:** retry with exponential backoff and a deadline. If deadline passes and funds remain held, escalate to manual resolution — do not silently give up.
- **Partial completion:** the reservation was created but the saga never received confirmation. The compensation must be able to cancel by idempotency key (the `job_id` / `saga_id`), not just by `reservation_id` that the saga may not have received.

The canonical implementation uses an **idempotency key** at the payment gateway: every reservation call includes `saga_id` as an idempotency key. The cancellation call uses the same `saga_id` to cancel — even if the reservation_id was never returned to the caller.

---

## BLOCK D — Data Lakehouse + Design (6 min)

---

**Q9.** *You are designing a new Iceberg table for a multi-region e-commerce platform. Expected query patterns: (a) `WHERE region = 'APAC' AND event_date BETWEEN ... AND ...` — 60% of queries; (b) `WHERE event_type = 'purchase' AND event_date = ...` — 30% of queries; (c) `WHERE region = 'EMEA' AND event_type = 'refund'` — 10% of queries. 5 years of data, ~2 billion rows/year. Design the partitioning strategy and within-partition optimisation. Justify every choice.*

**Answer:**
**Partition strategy: `(event_date MONTH, region)`**

Reasoning:
- `event_date` is in every query pattern — always prune by date first. Monthly granularity (not daily) avoids small-file problems at 2B rows/year (daily = ~5.5M rows/partition, which may produce thousands of small files at typical Parquet row group sizes).
- `region` as a second partition column further prunes for the 60% APAC-by-date queries. It reduces the number of data files read by a factor of ~5 (assuming 5 regions).
- `event_type` is NOT a partition column — it appears in 40% of queries but with `event_date` already partitioning, adding `event_type` would multiply partitions excessively (5 regions × 12 months × N event types = many small partitions).

**Within-partition optimisation: Z-order on `(event_type, region)`**

For query patterns (b) and (c) that filter on `event_type` (possibly combined with `region`), Z-ordering within each partition provides file-level skipping via per-file min/max statistics. Z-order on both columns gives partial skipping for single-column filters and strong skipping for combined filters — serving all three access patterns reasonably well.

**Hidden partitioning (Iceberg feature):** use Iceberg's hidden partitioning with `PARTITIONED BY (month(event_date), identity(region))` — queries can use `WHERE event_date BETWEEN 'X' AND 'Y'` without knowing the partition scheme; Iceberg translates the predicate to partition bounds automatically.

**File sizing target:** 256 MB–512 MB Parquet files within each partition. Too small (< 64 MB) increases manifest file count and metadata overhead; too large increases read amplification for point-in-partition queries.

---

**Q10.** *Your production Hudi MOR table has accumulated 3 weeks of delta log files with no compaction (a scheduled job failed silently). Hourly analytical queries are running 8–12× slower than normal. You cannot afford a table rewrite or a multi-hour reprocessing window. Design an emergency remediation plan, step by step.*

**Answer:**
**Immediate: stop the bleeding — separate reads from delta log merges**

Step 1 — **Switch analytical queries to Read-Optimised (RO) view:**
Hudi MOR exposes two read paths. The Read-Optimised view reads only the last compacted base Parquet files — it skips all delta logs. Queries are fast (no merge overhead) but return data up to the last successful compaction (3 weeks stale). For dashboards that can tolerate staleness temporarily, redirect them to the RO view immediately:
```sql
SELECT * FROM hudi_table.read_optimized WHERE ...
```

Step 2 — **Run emergency compaction on the hottest partitions first:**
Identify which partitions have the most delta log files (highest query latency contribution). Run targeted compaction on those partitions using a Spark/Flink compaction job:
```python
# Flink/Spark Hudi compaction on specific partitions
hudi_table.compact(partition_filter="event_date >= date_sub(today, 7)")
```
This is safe to run while ingestion continues — Hudi's MVCC ensures readers and the compaction job do not conflict. Start with the most recent 7 days (highest query frequency) and work backward.

Step 3 — **Resume scheduled compaction with corrected configuration:**
Fix the silent failure (likely a job scheduler issue, Spark resource starvation, or a misconfigured trigger). Set `hoodie.compact.inline=false` with a reliable external scheduler. Add a monitoring alert: if `hoodie_timeline` shows no completed compaction in > 2 hours, page on-call.

Step 4 — **For truly time-sensitive data (< 3 weeks lag):** use the **incremental view** to query only changes since the last compaction instant:
```sql
SELECT * FROM hudi_table.incremental
WHERE _hoodie_commit_time > '20260515000000'
```
Merge RO view results with incremental view results in the application layer. This is a manual merge but returns current data without scanning all delta logs.

**What NOT to do:** do not trigger a full table re-bootstrap or VACUUM FULL equivalent — this takes hours and blocks ingestion. Do not increase Spark executor memory as a first response — it addresses symptoms, not the structural problem of accumulated delta logs.