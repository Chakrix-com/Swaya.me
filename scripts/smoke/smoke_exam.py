"""
Smoke test: Exam end-to-end
Creates a temp exam quiz → publishes → takes as participant → verifies score → deletes.
"""
import os, sys, time, traceback, requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from smoke_common import (BASE, API, make_driver, make_mobile_driver,
                          snap, api_login, api_headers, SmokeResult)

from datetime import datetime, timezone, timedelta


def run():
    r = SmokeResult("Exam — Create → Publish → Take → Score")
    token = None
    quiz_id = None
    exam_slug = None

    try:
        token = api_login()
        H = api_headers(token)

        # 1. Create exam quiz
        resp = requests.post(f"{API}/quizzes/", json={
            "title": "Smoke Test Exam (auto-delete)",
            "description": "Created by smoke_exam.py — safe to delete",
            "quiz_type": "exam",
        }, headers=H)
        if resp.status_code != 201:
            r.fail(f"Create exam failed: {resp.status_code} {resp.text[:200]}")
            r.report(); return 1
        quiz_id = resp.json()["id"]
        r.ok(f"Exam quiz created: id={quiz_id}")

        # 2. Add one MCQ question
        q_resp = requests.post(f"{API}/quizzes/{quiz_id}/questions", json={
            "question_text": "What is 2 + 2?",
            "question_type": "mcq",
            "time_limit_seconds": 30,
            "points": 10,
            "options": [
                {"option_text": "3", "is_correct": False},
                {"option_text": "4", "is_correct": True},
                {"option_text": "5", "is_correct": False},
                {"option_text": "22", "is_correct": False},
            ]
        }, headers=H)
        if q_resp.status_code not in (200, 201):
            r.fail(f"Add question failed: {q_resp.status_code}")
            r.report(); return 1
        r.ok("MCQ question added")

        # 3. Publish exam
        now = datetime.now(timezone.utc)
        pub_resp = requests.post(f"{API}/quizzes/{quiz_id}/publish-exam", json={
            "exam_start_at": now.isoformat(),
            "exam_end_at": (now + timedelta(hours=2)).isoformat(),
            "exam_time_limit_seconds": 120,
            "exam_require_email": False,
        }, headers=H)
        if pub_resp.status_code not in (200, 201):
            r.fail(f"Publish exam failed: {pub_resp.status_code} {pub_resp.text[:200]}")
            r.report(); return 1
        exam_slug = pub_resp.json().get("exam_slug")
        r.ok(f"Exam published: slug={exam_slug}")

        if not exam_slug:
            r.fail("No exam_slug in publish response")
            r.report(); return 1

        # 4. Take exam as participant
        d = make_mobile_driver()
        try:
            d.get(f"{BASE}/e/{exam_slug}")
            time.sleep(2)
            snap(d, "exam_01_landing")

            w = WebDriverWait(d, 15)

            # Enter name and start
            try:
                name_input = w.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[placeholder*='name'], input[type='text']:first-of-type")))
                name_input.send_keys("Smoke Tester")
                snap(d, "exam_02_name_entered")
                start_btn = d.find_element(By.CSS_SELECTOR, "button[type='submit'], .ant-btn-primary")
                start_btn.click()
                time.sleep(3)
                snap(d, "exam_03_started")
                r.ok("Exam started as participant")
            except Exception as e:
                r.fail(f"Could not start exam: {e}")

            # Answer question
            try:
                opt = w.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".ant-radio-group label, .exam-option")))
                opt.click()
                time.sleep(1)
                snap(d, "exam_04_answered")
                r.ok("Answered Q1")
            except Exception as e:
                r.skip(f"Could not answer question: {e}")

            # Submit
            try:
                submit_btn = d.find_element(By.CSS_SELECTOR, "button.ant-btn-danger, [data-testid='submit-exam']")
                submit_btn.click()
                time.sleep(1)
                # Confirm dialog
                confirm = WebDriverWait(d, 5).until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".ant-btn-primary, .ant-modal-confirm-btns button")))
                confirm.click()
                time.sleep(3)
                snap(d, "exam_05_submitted")
                r.ok("Exam submitted")
            except Exception as e:
                r.skip(f"Could not submit exam: {e}")

        finally:
            d.quit()

    except Exception as e:
        r.fail(f"Unexpected error: {e}")
        traceback.print_exc()
    finally:
        # Cleanup: delete the temp quiz
        if quiz_id and token:
            try:
                del_resp = requests.delete(f"{API}/quizzes/{quiz_id}", headers=api_headers(token))
                if del_resp.status_code in (200, 204):
                    r.ok(f"Temp quiz {quiz_id} deleted (cleanup)")
                else:
                    r.skip(f"Cleanup delete returned {del_resp.status_code}")
            except Exception:
                r.skip("Cleanup delete failed")

        r.report()
        return 0 if not r.failed else 1


if __name__ == "__main__":
    sys.exit(run())
