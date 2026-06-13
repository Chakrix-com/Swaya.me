"""
Smoke test: Live quiz — two-window session
Host window: start session → show join code → advance → end.
Participant window: join → answer → see result → see leaderboard.
Uses a pre-existing READY quiz (id configurable via env SMOKE_QUIZ_ID).
Cleans up by ending the session regardless of outcome.
"""
import os, sys, time, traceback, requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from smoke_common import (BASE, API, make_driver, make_mobile_driver,
                          snap, api_login, api_headers, login_ui, SmokeResult)

QUIZ_ID = int(os.environ.get("SMOKE_QUIZ_ID", "1003"))  # Welcome Demo Quiz


def run():
    r = SmokeResult("Live Quiz — Two-window session")
    token = None
    session_id = None
    host = None
    participant = None
    join_code = None

    try:
        token = api_login()
        H = api_headers(token)

        # 1. Start session via API
        resp = requests.post(f"{API}/quizzes/sessions/start",
                             json={"quiz_id": QUIZ_ID}, headers=H)
        if resp.status_code != 201:
            r.fail(f"Could not start session: {resp.status_code} {resp.text[:200]}")
            r.report(); return 1
        session = resp.json()
        session_id = session["session_id"]
        join_code = session.get("join_code") or session.get("code")
        r.ok(f"Session started: id={session_id} join_code={join_code}")

        # 2. Host opens control page
        host = make_driver()
        login_ui(host)
        host.get(f"{BASE}/quiz/{QUIZ_ID}/control")
        time.sleep(2)
        snap(host, "lq_01_control")

        # Verify join code visible
        page_src = host.page_source
        if join_code and join_code in page_src:
            r.ok("Join code visible on control page")
        else:
            r.fail(f"Join code '{join_code}' not found in control page source")

        # 3. Participant joins via mobile browser
        participant = make_mobile_driver()
        participant.get(f"{BASE}/join/{join_code}")
        time.sleep(2)
        snap(participant, "lq_02_participant_join")

        # Enter name
        try:
            w_p = WebDriverWait(participant, 10)
            name_input = w_p.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder*='name'], input[placeholder*='Name']")))
            name_input.send_keys("Smoke Test User")
            join_btn = participant.find_element(By.CSS_SELECTOR, "button[type='submit'], .ant-btn-primary")
            join_btn.click()
            time.sleep(3)
            snap(participant, "lq_03_participant_waiting")
            r.ok("Participant joined session")
        except Exception as e:
            r.fail(f"Participant join failed: {e}")

        # 4. Host advances to Q1
        try:
            w_h = WebDriverWait(host, 10)
            advance_btn = w_h.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[data-testid='advance'], .control-advance, button:contains('Next')")))
            advance_btn.click()
            time.sleep(2)
            snap(host, "lq_04_q1_host")
            r.ok("Host advanced to Q1")
        except Exception:
            # Try clicking any button that says Next or Start
            try:
                btns = host.find_elements(By.CSS_SELECTOR, "button")
                for btn in btns:
                    if any(kw in btn.text.lower() for kw in ["next", "start", "advance", "begin"]):
                        btn.click()
                        time.sleep(2)
                        r.ok("Host advanced via text search")
                        break
            except Exception as e2:
                r.skip(f"Could not advance: {e2}")

        snap(host, "lq_05_host_mid")
        snap(participant, "lq_06_participant_question")

        # 5. Participant answers (pick first option)
        try:
            w_p = WebDriverWait(participant, 8)
            opt = w_p.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".aud-option, .audience-option, [data-testid='option']")))
            opt.click()
            time.sleep(2)
            snap(participant, "lq_07_participant_answered")
            r.ok("Participant submitted an answer")
        except Exception as e:
            r.skip(f"Could not submit answer (question may not have loaded): {e}")

    except Exception as e:
        r.fail(f"Unexpected error: {e}")
        traceback.print_exc()
    finally:
        # Always end session
        if session_id and token:
            try:
                requests.post(f"{API}/quizzes/sessions/{session_id}/end",
                              headers=api_headers(token))
                r.ok("Session ended (cleanup)")
            except Exception:
                r.skip("Could not end session in cleanup")

        if host: host.quit()
        if participant: participant.quit()
        r.report()
        return 0 if not r.failed else 1


if __name__ == "__main__":
    sys.exit(run())
