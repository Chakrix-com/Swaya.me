"""
Backfill integrity scores based on explicit violation events only.

Before this change, integrity_score was silently reduced by behavioral biometrics
(mouse entropy, keystroke rhythm) without any logged evidence. Going forward,
integrity_score is driven only by explicit, logged violations.

This script:
1. Resets integrity_score to 100 for every proctoring session
2. Re-deducts points based only on explicit violation events in proctoring_events
3. Skips biometric-only events that were never defensible evidence

Run against test first:
  DB_HOST=localhost DB_NAME=swayame_test python3 backend/scripts/backfill_integrity_scores.py

Then prod:
  DB_HOST=localhost DB_NAME=swayame python3 backend/scripts/backfill_integrity_scores.py
"""
import os
import sys
import pymysql
import pymysql.cursors

# Event types that were emitted by the old silent biometric scorer —
# these did not reflect explicit user actions and should not count.
BIOMETRIC_ONLY_EVENTS = frozenset({
    "BIOMETRIC_ANOMALY_MILD",
    "BIOMETRIC_ANOMALY",
    "LOW_INTEGRITY_SCORE",
    "SESSION_LOCKED",
    "SESSION_UNLOCKED_BY_ADMIN",
})

# Points deducted per explicit violation event type.
VIOLATION_DEDUCTIONS = {
    "FAST_FIRST_ANSWER": 10,
    "TAB_SWITCH": 10,
    "COPY": 15,
    "PASTE": 15,
    "CUT": 10,
    "RIGHT_CLICK_ATTEMPT": 5,
    "FULLSCREEN_EXIT": 15,
    "FULLSCREEN_BLOCKED": 10,
    "DEVTOOLS_OPEN": 15,
    "FACE_NOT_DETECTED": 10,
    "MULTIPLE_FACES_DETECTED": 15,
    "WEBCAM_PERMISSION_DENIED": 20,
    # Immediate-lock events — session is already locked, but score should show 0
    "MULTI_TAB_DETECTED": 100,
    "BOT_SIGNAL_DETECTED": 100,
    "FINGERPRINT_MISMATCH": 100,
    "IP_MISMATCH": 100,
    "WEBCAM_STREAM_ENDED": 100,
    "HONEYPOT_OPTION_CLICKED": 100,
    "HONEYPOT_FIELD_FILLED": 100,
    "HONEYPOT_INSTRUCTION_FOLLOWED": 100,
    "HONEYPOT_ENDPOINT_HIT": 100,
}
DEFAULT_DEDUCTION = 5


def compute_integrity(events: list[dict]) -> int:
    score = 100
    for evt in events:
        et = evt["event_type"]
        if et in BIOMETRIC_ONLY_EVENTS:
            continue
        deduction = VIOLATION_DEDUCTIONS.get(et, DEFAULT_DEDUCTION)
        score = max(0, score - deduction)
    return score


def main():
    db_host = os.environ.get("DB_HOST", "localhost")
    db_name = os.environ.get("DB_NAME", "swayame_test")
    db_user = os.environ.get("DB_USER", "swayame_user")
    db_pass = os.environ.get("DB_PASSWORD", "Sw4y4m3_S3cur3_P4ssw0rd!2026")
    db_port = int(os.environ.get("DB_PORT", 3306))

    conn = pymysql.connect(
        host=db_host, port=db_port, user=db_user, password=db_pass,
        database=db_name, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    print(f"Connected to {db_host}/{db_name}")

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, participant_id, quiz_id, integrity_score, is_locked FROM proctoring_sessions")
            sessions = cur.fetchall()

        print(f"Found {len(sessions)} proctoring sessions to evaluate")
        updated = 0
        unchanged = 0

        for sess in sessions:
            sid = sess["id"]
            pid = sess["participant_id"]
            qid = sess["quiz_id"]
            old_score = sess["integrity_score"]

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT event_type FROM proctoring_events "
                    "WHERE participant_id = %s AND quiz_id = %s ORDER BY occurred_at",
                    (pid, qid),
                )
                events = cur.fetchall()

            new_score = compute_integrity(events)

            if new_score != old_score:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE proctoring_sessions SET integrity_score = %s WHERE id = %s",
                        (new_score, sid),
                    )
                conn.commit()
                label = "RESET" if new_score > old_score else "ADJUSTED"
                print(f"  [{label}] session {sid} (participant={pid}, quiz={qid}): {old_score} → {new_score}")
                updated += 1
            else:
                unchanged += 1

        print(f"\nDone. Updated: {updated}, unchanged: {unchanged}")


if __name__ == "__main__":
    main()
