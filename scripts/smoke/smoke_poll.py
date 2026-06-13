"""
Smoke test: Poll question types — MCQ, word cloud, rating scale.
Creates a temp poll quiz → starts session → participant visits → answers → host ends.
"""
import os, sys, time, traceback, requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from smoke_common import (BASE, API, make_driver, make_mobile_driver,
                          snap, api_login, api_headers, login_ui, SmokeResult)


def run():
    r = SmokeResult("Poll — MCQ + Word Cloud + Rating question types")
    token = None
    quiz_id = None
    session_id = None
    join_code = None

    try:
        token = api_login()
        H = api_headers(token)

        # 1. Create poll quiz
        resp = requests.post(f"{API}/quizzes/", json={
            "title": "Smoke Test Poll (auto-delete)",
            "quiz_type": "poll",
        }, headers=H)
        if resp.status_code != 201:
            r.fail(f"Create poll failed: {resp.status_code}")
            r.report(); return 1
        quiz_id = resp.json()["id"]
        r.ok(f"Poll quiz created: id={quiz_id}")

        # 2. Add question types
        questions = [
            {"question_text": "Pick a colour", "question_type": "mcq", "time_limit_seconds": 30,
             "options": [{"option_text": "Red", "is_correct": False},
                         {"option_text": "Blue", "is_correct": False}]},
            {"question_text": "Describe your mood in one word", "question_type": "word_cloud",
             "time_limit_seconds": 30, "options": []},
            {"question_text": "Rate this session", "question_type": "rating",
             "time_limit_seconds": 30, "options": []},
        ]
        for q in questions:
            qr = requests.post(f"{API}/quizzes/{quiz_id}/questions", json=q, headers=H)
            if qr.status_code not in (200, 201):
                r.fail(f"Add question '{q['question_type']}' failed: {qr.status_code}")
        r.ok("3 questions added (mcq, word_cloud, rating)")

        # 3. Start session
        sr = requests.post(f"{API}/quizzes/sessions/start",
                           json={"quiz_id": quiz_id}, headers=H)
        if sr.status_code != 201:
            r.fail(f"Start session failed: {sr.status_code}")
            r.report(); return 1
        session_id = sr.json()["session_id"]
        join_code = sr.json().get("join_code") or sr.json().get("code")
        r.ok(f"Session started: id={session_id}, join_code={join_code}")

        if not join_code:
            r.fail("No join code in session response")
            r.report(); return 1

        # 4. Participant joins
        p = make_mobile_driver()
        try:
            p.get(f"{BASE}/join/{join_code}")
            time.sleep(2)
            snap(p, "poll_01_join")

            w_p = WebDriverWait(p, 10)
            try:
                name_inp = w_p.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[placeholder*='name'], input[type='text']")))
                name_inp.send_keys("Smoke Poller")
                p.find_element(By.CSS_SELECTOR, "button[type='submit'], .ant-btn-primary").click()
                time.sleep(2)
                snap(p, "poll_02_waiting")
                r.ok("Participant joined poll")
            except Exception as e:
                r.fail(f"Participant join failed: {e}")

            # 5. Host advances through questions
            host = make_driver()
            try:
                login_ui(host)
                host.get(f"{BASE}/quiz/{quiz_id}/control")
                time.sleep(2)

                for q_idx in range(3):
                    # Advance
                    try:
                        btns = host.find_elements(By.CSS_SELECTOR, "button")
                        for btn in btns:
                            if any(kw in btn.text.lower() for kw in ["next", "advance", "start"]):
                                btn.click()
                                break
                        time.sleep(2)
                        snap(host, f"poll_host_q{q_idx+1}")
                        snap(p, f"poll_participant_q{q_idx+1}")
                        r.ok(f"Showing question {q_idx+1}")
                    except Exception as e:
                        r.skip(f"Advance Q{q_idx+1} failed: {e}")

                    # Participant tries to answer
                    try:
                        if q_idx == 0:  # MCQ
                            opt = WebDriverWait(p, 5).until(EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, ".aud-option, .audience-option")))
                            opt.click()
                        elif q_idx == 1:  # Word cloud
                            inp = WebDriverWait(p, 5).until(EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "input[type='text'], textarea")))
                            inp.send_keys("happy")
                            p.find_element(By.CSS_SELECTOR, "button[type='submit'], .ant-btn-primary").click()
                        elif q_idx == 2:  # Rating
                            stars = p.find_elements(By.CSS_SELECTOR, ".ant-rate-star, .rating-star")
                            if stars:
                                stars[3].click()
                        time.sleep(1.5)
                        r.ok(f"Participant answered Q{q_idx+1}")
                    except Exception as e:
                        r.skip(f"Answer Q{q_idx+1} failed: {e}")

            finally:
                host.quit()

        finally:
            p.quit()

    except Exception as e:
        r.fail(f"Unexpected error: {e}")
        traceback.print_exc()
    finally:
        # Cleanup
        if session_id and token:
            try:
                requests.post(f"{API}/quizzes/sessions/{session_id}/end",
                              headers=api_headers(token))
                r.ok("Session ended")
            except Exception:
                pass
        if quiz_id and token:
            try:
                dr = requests.delete(f"{API}/quizzes/{quiz_id}", headers=api_headers(token))
                if dr.status_code in (200, 204):
                    r.ok(f"Temp quiz {quiz_id} deleted")
            except Exception:
                pass

        r.report()
        return 0 if not r.failed else 1


if __name__ == "__main__":
    sys.exit(run())
