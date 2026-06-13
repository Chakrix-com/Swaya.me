# Technical Interview: Pankaj Kundu — B8 Data Engineer
**Duration:** 45 minutes | **Exam score:** 90/100 (18/20 correct, 29 min)

---

## BLOCK A — Python Execution Model (10 min)

---

**Q1.** Show the following code and ask the candidate to trace the output.

```
FUNCTION shallow_copy(obj):
    new_obj = {}
    FOR key IN obj.keys():
        new_obj[key] = obj[key]
    RETURN new_obj

original = {"score": 5, "tags": [10, 20]}
copy     = shallow_copy(original)

copy["score"] = 99
copy["tags"].append(30)

PRINT original["score"], original["tags"]
```

*What does this print, and why?*

**Answer:**
Output is `5   [10, 20, 30]`.

`copy["score"] = 99` — the shallow copy stored the integer value 5 into `copy["score"]`. Integers are immutable in Python; there is no shared object between the two dictionaries. Rebinding `copy["score"]` to 99 only updates `copy`'s key — `original["score"]` remains 5.

`copy["tags"].append(30)` — the shallow copy stored the *reference* to the list, not a copy of it. Both `copy["tags"]` and `original["tags"]` point to the same list object in memory. Calling `.append()` mutates that shared object, so `original["tags"]` becomes `[10, 20, 30]`.

The key principle: in Python, assignment copies a reference. For immutable types (int, str, float), any "change" creates a new object and rebinds the variable — the original is unaffected. For mutable types (list, dict, set), the reference is shared, so mutations through any binding are visible to all references.

---

**Q2.** *Consider the code below.*

```python
a = {"x": [1, 2], "y": {"z": 3}}
b = dict(a)       # shallow copy

b["x"].append(99)
b["y"] = {"z": 100}

print(a["x"])
print(a["y"])
```

*What does this print? Explain why `a["x"]` and `a["y"]` behave differently.*

**Answer:**
`a["x"]` prints `[1, 2, 99]`. `a["y"]` prints `{"z": 3}`.

`b["x"].append(99)` — `b["x"]` and `a["x"]` reference the same list object (shallow copy). Appending to it mutates the shared list, so `a["x"]` reflects the change.

`b["y"] = {"z": 100}` — this rebinds `b`'s key `"y"` to point at a new dictionary. It does not mutate the original dict that `a["y"]` points to. Rebinding a key in one dictionary never affects another dictionary's bindings.

---

**Q3.** *Trace the output of this pseudocode. Each call to `gen_squares` is a separate call.*

```
FUNCTION gen_squares(n):
    i = 0
    WHILE i < n:
        YIELD i * i
        i = i + 1

g  = gen_squares(5)
a  = NEXT(g)
b  = NEXT(g)
g2 = gen_squares(3)
c  = NEXT(g2)
d  = NEXT(g)

PRINT a, b, c, d
```

*Why are `g` and `g2` independent of each other?*

**Answer:**
Output is `0  1  0  4`.

- `a = NEXT(g)` → yields 0² = 0 (i=0), advances g to i=1
- `b = NEXT(g)` → yields 1² = 1 (i=1), advances g to i=2
- `g2 = gen_squares(3)` → creates a brand-new generator object with its own i=0
- `c = NEXT(g2)` → yields 0² = 0 from g2's frame (i=0), advances g2 to i=1
- `d = NEXT(g)` → resumes g (not g2) at i=2 → yields 2² = 4

`g` and `g2` are independent because each call to a generator function creates a *new generator object* — a fresh execution frame with its own local variables and its own position counter. Calling `gen_squares` a second time does not reset or share state with the first call. The two generators hold completely separate state.

---

**Q4.** *An async runtime runs the following. What does it print?*

```
log = []

ASYNC FUNCTION worker(n):
    AWAIT sleep(n)       # sleeps for n × 0.1 seconds
    log.append(n)
    RETURN n

ASYNC FUNCTION main():
    results = AWAIT gather([worker(3), worker(1), worker(2)])
    PRINT results
    PRINT log

RUN main()
```

*Explain why `results` and `log` have different orderings.*

**Answer:**
`results` prints `[3, 1, 2]`. `log` prints `[1, 2, 3]`.

`gather()` runs all coroutines concurrently. `worker(1)` finishes first, then `worker(2)`, then `worker(3)` — so `log.append` is called in completion order: `log = [1, 2, 3]`.

However, `gather()` collects return values positionally — it places each result into the slot corresponding to its position in the input list, not its completion order. Slot 0 gets `worker(3)`'s result, slot 1 gets `worker(1)`'s result, slot 2 gets `worker(2)`'s result. So `results = [3, 1, 2]`.

This is a deliberate design choice: callers can safely unpack results in index order without tracking which task finished when.

---

## BLOCK B — SQL + Database Internals (10 min)

---

**Q5.** *A table is partitioned by `created_at` (one partition per day). This query takes 45 minutes:*

```sql
SELECT order_id, amount
FROM   orders
WHERE  DATE(created_at) = '2024-01-15';
```

*A rewrite runs in 2 seconds:*

```sql
WHERE created_at >= '2024-01-15 00:00:00'
  AND created_at <  '2024-01-16 00:00:00'
```

*Why does the original fail to prune partitions? Write a prunable predicate for "all orders in Q1 2024".*

**Answer:**
The partition map stores boundary conditions on the raw `created_at` column — e.g. `created_at >= '2024-01-15 00:00:00'`. To prune, the optimizer compares the query predicate directly against these boundaries. When `created_at` is wrapped in `DATE()`, the optimizer cannot mathematically invert the function to derive a range — it must evaluate `DATE(created_at)` for every row in every partition. The predicate is *non-sargable* (not Search-ARGument-Able).

Prunable predicate for Q1 2024:
```sql
WHERE created_at >= '2024-01-01 00:00:00'
  AND created_at <  '2024-04-01 00:00:00'
```

`WHERE YEAR(created_at) = 2024 AND QUARTER(created_at) = 1` is also non-sargable — the same problem applies to any function wrapping the column.

Other common non-sargable patterns: `UPPER(name) = 'ALICE'`, `amount + 100 > 500`, `LIKE '%keyword%'` (leading wildcard), `CAST(id AS VARCHAR) = '42'`.

---

**Q6.** *A table has 100M rows. A bulk INSERT adds 5M rows with `status = 'new'`. The query planner estimates only 100 matching rows for `WHERE status = 'new'` and picks a nested-loop join instead of a hash join — taking 45 minutes instead of seconds. Statistics were last collected before the bulk load. What is the root cause, and what is the fix?*

**Answer:**
Root cause: **stale column statistics**. The planner's histogram for the `status` column was collected before the bulk insert, so it has no data for the value `'new'`. With no histogram entry, the planner uses a default low cardinality estimate (100 rows). A low estimate makes nested-loop join look cheap — loop over ~100 outer rows, index-lookup each in the users table. At 5M rows, nested-loop is catastrophic; a hash join would have been chosen at the correct cardinality.

Fix: run `ANALYZE TABLE events` (MySQL) or `ANALYZE events` (PostgreSQL) immediately after the bulk load. This refreshes the column histograms so the planner sees the actual 5M rows for `status = 'new'` and picks the correct join strategy.

Prevention: configure auto-analyze thresholds to trigger after large inserts, or include `ANALYZE` as part of the bulk load pipeline.

---

**Q7.** *A hospital system requires at least one doctor on duty at all times. Both T1 and T2 run concurrently under Snapshot Isolation:*

```sql
BEGIN;
  SELECT COUNT(*) FROM duty WHERE status = 'on';  -- both see 2
  IF count > 1 THEN
    UPDATE duty SET status = 'off' WHERE doctor_id = <self>;
  END IF;
COMMIT;
```

*Both see count=2, both pass the check, both commit. Final count is 0 — the invariant is violated. Which isolation level prevents this, and how would you fix it without changing the isolation level?*

**Answer:**
SERIALIZABLE (SSI or 2PL) prevents this. It detects the *write skew* anti-pattern: each transaction read a set of rows and updated a different row based on that read, with no direct write-write conflict for SI to catch. SSI tracks anti-dependencies and aborts one transaction at commit time.

Fix without changing isolation level — use `SELECT FOR UPDATE`:
```sql
BEGIN;
  SELECT COUNT(*) FROM duty WHERE status = 'on' FOR UPDATE;
  IF count > 1 THEN
    UPDATE duty SET status = 'off' WHERE doctor_id = <self>;
  END IF;
COMMIT;
```

`FOR UPDATE` takes a write lock on all on-duty rows at the SELECT. The second transaction blocks at the SELECT until the first commits. After the first commits (count=1), the second re-reads count=1, fails the check, and does nothing. The invariant holds.

---

**Q8.** *A database uses MVCC with Repeatable Read. T1 begins at T=100. T2 updates row R (500→900) and commits at T=110. T1 reads row R at T=120 and again at T=130. What does T1 see, and why?*

**Answer:**
T1 sees 500 at both T=120 and T=130.

MVCC maintains multiple row versions. T2's update created a new row version with creation timestamp T=110. T1's snapshot was fixed at transaction start time T=100. MVCC snapshot selection only returns row versions whose creation timestamp is ≤ T1's snapshot time (T=100). T2's version (created at T=110) is newer than T1's snapshot and is therefore invisible to T1. T1 sees the pre-T2 version (amount=500) for both reads.

This is why the isolation level is called Repeatable Read — the same row read twice within one transaction always returns the same value, regardless of concurrent commits.

In PostgreSQL, this is implemented via Snapshot Isolation (not 2PL) — readers never acquire shared locks and never block writers. In a locking-based system, T1 would hold a shared lock on row R from T=120 until commit, blocking T2 entirely.

---

## BLOCK C — Streaming + Distributed Systems (10 min)

---

**Q9.** *A Flink job consumes from Kafka. Monitoring shows:*
- *Source operator: 100K msg/s*
- *Stateful aggregation operator: 60K msg/s*
- *Consumer lag: growing at ~40K msg/s*
- *GC pause time on aggregation task managers: 800ms every 15 seconds*
- *CPU and network on all nodes: normal*

*What is the root cause of the backpressure? What is the fix?*

**Answer:**
Root cause: **unbounded state growth** in the aggregation operator.

The source is running at full speed (100K msg/s) — the bottleneck is not at the source. CPU normal and network normal rules out compute-bound or shuffle-bound causes. The diagnostic signal is the 800ms GC pause every 15 seconds — a stop-the-world GC event. This indicates JVM heap is filling up, forcing frequent full GC. During each 800ms pause, the operator processes nothing, stalling the pipeline and causing backpressure upstream.

The cause is a stateful aggregation with no state TTL — it accumulates one state entry per distinct key indefinitely. Over time, heap fills → GC frequency and duration increase → processing stalls → backpressure.

Fix 1 — State TTL:
```java
StateTtlConfig ttlConfig = StateTtlConfig
    .newBuilder(Time.hours(24))
    .setUpdateType(OnCreateAndWrite)
    .setStateVisibility(NeverReturnExpired)
    .build();
valueDescriptor.enableTimeToLive(ttlConfig);
```

Fix 2 — Switch to RocksDB state backend. State spills to disk instead of living in JVM heap. Eliminates heap pressure at the cost of serialisation overhead per state access. Appropriate when state volume exceeds what heap can hold.

---

**Q10.** *A Kafka → Flink → Kafka pipeline must provide exactly-once end-to-end. What combination of features achieves this? Describe how the two-phase commit works.*

**Answer:**
Flink checkpointing + Kafka transactional sink + `isolation.level=read_committed` on the consumer.

How 2PC works:

1. Flink injects a checkpoint barrier into the source stream
2. The Kafka sink opens a Kafka **transaction** (`beginTransaction()`) — messages are sent inside the transaction but not yet committed to Kafka
3. The barrier propagates through all operators; each operator snapshots its state to durable storage
4. All operators acknowledge completion → Flink checkpoint coordinator marks the checkpoint done
5. The Kafka sink calls `commitTransaction()` — messages become visible to consumers
6. On failure before commit: Flink restores from the last checkpoint; the in-progress Kafka transaction is either timed out or explicitly aborted via `abortTransaction()`; no duplicate messages are produced

The consumer must use `isolation.level=read_committed` — the default `read_uncommitted` would expose messages from in-progress transactions that may later be aborted, breaking exactly-once on the read side.

---

**Q11.** *In a 2PC transaction across two shards, both shards vote READY. The coordinator crashes before sending COMMIT or ABORT. What state are the shards in, and why can't they resolve this on their own?*

**Answer:**
Both shards are in an **in-doubt (blocked)** state. They hold locks on the affected rows and cannot proceed.

They cannot unilaterally abort — a shard that voted YES cannot abort because the coordinator may have already sent COMMIT to the other shard before crashing. If this shard aborts while the other commits, atomicity is broken.

They cannot unilaterally commit — each shard doesn't know if the other also voted YES. Committing without confirmation risks one shard committing and the other never receiving a COMMIT (if the coordinator crashed before sending it to both).

The only safe state is to wait for coordinator recovery. The coordinator writes its decision to a durable WAL before sending COMMIT. On restart, it reads the WAL and re-sends COMMIT or ABORT to both shards. Shards handle duplicate COMMIT messages idempotently. This is the fundamental availability cost of 2PC — coordinator failure can block all participants indefinitely.

---

## BLOCK D — Data Lakehouse (8 min)

---

**Q12.** *A Schema Registry is configured with BACKWARD compatibility. A developer proposes Schema v2 which adds a field `currency: string` with no default value to an existing schema. Will the registry accept v2? Why or why not?*

**Answer:**
The registry will **reject** v2.

BACKWARD compatibility means: a consumer using the new schema (v2) must be able to correctly deserialise messages written with the old schema (v1). If v2 adds `currency: string` with no default, a v2 consumer reading a v1 message finds no `currency` field in the payload and has no instruction for what value to assign — deserialisation fails.

With a default value (e.g. `"USD"`), a v2 consumer fills in the default when the field is absent in v1 messages, making it backward-compatible.

The registry enforces this check at registration time, before any producer can publish v2 messages. This prevents the schema from being registered at all, protecting consumers proactively.

BACKWARD = new consumers can read old messages (add optional fields with defaults).
FORWARD = old consumers can read new messages (remove fields, or add fields old consumers ignore).
FULL = both directions simultaneously.

---

**Q13.** *A MySQL CDC solution uses `binlog_format=ROW`. A developer runs:*

```sql
UPDATE orders SET status = 'shipped' WHERE customer_id = 42;
```

*This matches 8,000 rows. What does the CDC consumer receive?*

**Answer:**
The CDC consumer receives **8,000 individual row-change events**, each containing the full before-image and after-image of one row.

`binlog_format=ROW` records the actual row data that changed, not the SQL statement. For an UPDATE affecting 8,000 rows, MySQL writes 8,000 binlog entries. Each entry contains all column values before the update and all column values after the update for that specific row.

This is intentional: CDC consumers get exactly what changed, per row, with no ambiguity. They do not need to re-execute SQL or infer which rows matched.

By contrast, `binlog_format=STATEMENT` would write the SQL once. This is dangerous for CDC because non-deterministic functions (`NOW()`, `RAND()`, `UUID()`) produce different values when replayed, and row ordering differences between source and replica can cause the statement to match different rows.

---

**Q14.** *Delta Lake provides ACID transactions on S3 without an external lock manager. How does it achieve isolation for concurrent writers?*

**Answer:**
Delta Lake uses **optimistic concurrency via the transaction log** (`_delta_log/`).

When two writers (A and B) start concurrently at log version 5:

1. Both read the current log (v5) and stage their data files to storage
2. Writer A atomically appends `_delta_log/000...6.json` using a conditional put operation (equivalent to `put-if-absent`) — succeeds
3. Writer B tries to append version 6 — fails because Writer A already created it
4. Writer B reads v6 to discover what changed, then performs a **conflict check**: did v6 modify the same partitions or files that Writer B is writing to?
5. No overlap → Writer B retries as v7 (optimistic retry succeeds)
6. Overlap → Writer B's transaction is aborted; must restart from scratch

`WriteSerializable` isolation (default) only detects write-write conflicts. `Serializable` adds read-write conflict detection (similar to SSI), at the cost of more aborts under concurrency.

---

**Q15.** *An Iceberg table is partitioned by `event_date` (daily). Within each partition, files are written in arrival order. The most common query filters on `event_date = '2024-03-10' AND region = 'APAC' AND event_type = 'purchase'`. Partition pruning handles the date. But the query still scans all 200 files in that partition. What is the highest-impact single optimisation?*

**Answer:**
Apply **Z-ordering on `(region, event_type)`** within each partition.

After Z-ordering, Iceberg records per-file column statistics (min/max for `region` and `event_type`). When a query filters on `region = 'APAC' AND event_type = 'purchase'`, Iceberg compares the filter against each file's statistics and skips files whose min/max ranges cannot contain the target values — without opening those files. In random-arrival order, min/max for `region` spans the full range in almost every file, so no skipping is possible. After Z-ordering, files that hold APAC/purchase rows are co-located, tightening the statistics so most of the 200 files can be skipped.

For a single-column filter (e.g. only `region = 'APAC'`), Z-ordering on `(region, event_type)` provides only partial skipping — weaker than a plain `SORT BY region`. Z-ordering is the right choice when queries use multiple different filter combinations, as it provides a multi-dimensional locality compromise across all access patterns.

---

## BLOCK E — Architecture + SLA + Live Design (7 min)

---

**Q16.** *A data platform has four sequential components with these monthly availabilities: Kafka 99.95%, Flink 99.8%, DW load 99.7%, BI dashboard 99.9%. Compound availability ≈ 99.35%, below the 99.5% SLA. Which single component gives the highest leverage, and how would you improve it in practice?*

**Answer:**
The **data warehouse load at 99.7%** is the weakest component and gives the largest absolute gain per unit of investment.

Improving DW load from 99.7% to 99.9% raises compound availability by ~0.2 percentage points — more than any other single improvement, because it is the lowest term in the product.

Practical improvements:
- Retry with exponential backoff for transient failures (connection resets, timeouts)
- Dead-letter queue — failed load batches go to DLQ, never silently dropped; reprocess from DLQ once DW recovers
- Multi-AZ DW deployment (Aurora Multi-AZ, Redshift RA3)
- Circuit breaker — isolate DW failures from the upstream Flink pipeline to prevent cascade failures
- Connection pre-warming and health check before committing large load batches
- Real-time alerting on DW load failure rate — catch degradation before the SLA breach, not after

At 99.5% SLA, the allowed downtime is 0.5% × 43,200 min/month = **216 minutes per month** (~3.6 hours). Current compound availability (99.35%) exceeds budget by ~64 minutes/month.

---

**Q17.** *Design a CDC pipeline: ingest row-level changes from a MySQL production database (500K changes/day) into a data warehouse, available within 5 minutes of the DB change. Assume no managed services.*

*As part of the design: (a) You need to enrich every CDC event with a 40MB customer segments lookup table — would you use a broadcast join, and what is the risk? (b) Two CDC replicas run for HA; both may process the same DB row change — how do you prevent the older write from winning in the DW?*

**Answer:**

**Core pipeline:**
- MySQL `binlog_format=ROW` → Debezium (row-level CDC capture) → Kafka (per-table topics, keyed by primary key to preserve per-row ordering)
- Flink consumes Kafka → schema evolution via Avro + Schema Registry → UPSERT semantics in the DW
- Exactly-once: Flink checkpointing + Kafka transactional sink + `read_committed` consumer
- Flink checkpoint interval ≤ 5 minutes to satisfy the latency SLA; Kafka consumer lag monitoring as the primary health signal

**(a) Broadcast join for the 40MB lookup table:**
Yes, broadcast state is appropriate in Flink — the 40MB table is broadcast to all task managers once and stored in operator state, avoiding a network shuffle on every enrichment lookup. The risk: as the lookup table grows, each task manager holds a full copy in memory. If it grows past heap capacity, the task manager OOMs silently. A hard size check must gate the use of broadcast; if the table exceeds ~100MB, switch to an `AsyncFunction` that looks up a Redis/local cache or directly queries the DW per record.

**(b) Preventing stale writes in the DW from dual-replica processing:**
Use the MySQL binlog sequence number (LSN / log position) as the conflict-resolution key. Each CDC event carries the LSN at which the change was committed. The DW UPSERT should apply the new row only if the incoming LSN is greater than the stored LSN for that primary key:

```sql
INSERT INTO orders (..., _lsn)
VALUES (...)
ON CONFLICT (id) DO UPDATE
  SET ..., _lsn = EXCLUDED._lsn
  WHERE EXCLUDED._lsn > orders._lsn;
```

This is application-level Last-Write-Wins with a monotonically increasing, logically meaningful key (LSN). Wall-clock timestamps are unsafe because replica clocks drift — a replica slightly ahead in clock time can silently overwrite a later-committed change. LSNs are assigned by the database and are strictly ordered within a single MySQL instance.

---

## Answer Summary

| Q | Topic | Key answer |
|---|-------|-----------|
| 1 | Shallow copy | `5  [10, 20, 30]` — int is value-copy; list reference is shared; rebinding ≠ mutation |
| 2 | Rebind vs mutate | `[1,2,99]` and `{"z":3}` — append mutates shared list; rebinding a key changes only one dict |
| 3 | Generator state | `0  1  0  4` — each call creates a new independent generator frame |
| 4 | Async gather | `[3,1,2]` then `[1,2,3]` — gather returns in input order; log reflects completion order |
| 5 | Non-sargable DATE() | Optimizer cannot invert function to derive range; must use bare column with range predicate |
| 6 | Stale statistics | Planner underestimates cardinality → wrong join strategy; fix with ANALYZE after bulk load |
| 7 | Write skew | SERIALIZABLE prevents it; FOR UPDATE re-serialises the check without changing isolation level |
| 8 | MVCC RR snapshot | Snapshot fixed at T=100; T2's version (T=110) invisible; both reads return 500 |
| 9 | Flink backpressure | 800ms GC pauses = heap pressure = unbounded state; fix: state TTL or RocksDB backend |
| 10 | Flink exactly-once | Barrier → transaction buffered → commit on checkpoint complete; read_committed on consumer |
| 11 | 2PC in-doubt | Cannot abort unilaterally (other may have committed); coordinator WAL enables recovery |
| 12 | Schema Registry BACKWARD | Field without default = no fallback for old messages; registry rejects at registration time |
| 13 | CDC row binlog | 8,000 row-change events with before/after images; statement-based risks non-determinism |
| 14 | Delta optimistic concurrency | Atomic log append; conflict check on partition overlap; retry or abort |
| 15 | Iceberg Z-ordering | Co-locates multi-column combinations; partial skipping on single column; multi-access compromise |
| 16 | SLA weakest link | DW at 99.7% weakest; 216 min/month budget; DLQ + retry + multi-AZ |
| 17 | CDC design | Debezium→Kafka→Flink→DW; LSN-based LWW; broadcast size risk |
