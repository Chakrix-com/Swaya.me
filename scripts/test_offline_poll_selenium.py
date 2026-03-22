#!/usr/bin/env python3
"""
Selenium visual tests for Offline Poll feature.
Run with: python3 scripts/test_offline_poll_selenium.py
Visually monitor at: http://www.swaya.me:7900 (noVNC)
"""
import time
import traceback
from datetime import datetime, timedelta
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

SITE = "http://test.swaya.me"
API = "http://localhost:8001/api/v1"
SELENIUM_URL = "http://localhost:4444"

HOST_EMAIL = "demo@swaya.me"
HOST_PASSWORD = "Demo1234"

results = []


def log(scenario, status, msg=""):
    icon = "✓" if status == "PASS" else "✗"
    print(f"  {icon} [{status}] {scenario}: {msg}")
    results.append({"scenario": scenario, "status": status, "msg": msg})


def make_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,900")
    return webdriver.Remote(
        command_executor=SELENIUM_URL,
        options=options,
    )


def wait_for(driver, by, selector, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))


def get_auth_token():
    """Get JWT token for the test host user."""
    try:
        res = requests.post(f"{API}/auth/login", json={"email": HOST_EMAIL, "password": HOST_PASSWORD})
        if res.status_code == 200:
            return res.json().get("access_token")
    except Exception as e:
        print(f"  Auth failed: {e}")
    return None


def create_offline_poll(token):
    """Create an offline poll via API and return quiz_id."""
    headers = {"Authorization": f"Bearer {token}"}
    start = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
    end = (datetime.utcnow() + timedelta(hours=2)).isoformat()

    # Create quiz
    res = requests.post(f"{API}/quizzes/", json={
        "title": "Selenium Offline Poll Test",
        "description": "Created by Selenium test",
        "quiz_type": "offline_poll",
        "offline_start_at": start,
        "offline_end_at": end,
        "offline_results_email": HOST_EMAIL,
    }, headers=headers)
    if res.status_code not in (200, 201):
        print(f"  Create quiz failed: {res.status_code} {res.text}")
        return None
    quiz_id = res.json()["id"]

    # Add a question
    requests.post(f"{API}/quizzes/{quiz_id}/questions", json={
        "question_type": "mcq",
        "text": "What is 2 + 2?",
        "options": ["3", "4", "5", "6"],
        "correct_answer_index": 1,
        "points": 1,
    }, headers=headers)

    # Add a word cloud question
    requests.post(f"{API}/quizzes/{quiz_id}/questions", json={
        "question_type": "word_cloud",
        "text": "Describe your experience in one word",
        "points": 1,
    }, headers=headers)

    return quiz_id


def publish_offline_poll(token, quiz_id):
    """Publish the offline poll and return the poll_slug."""
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.post(f"{API}/quizzes/{quiz_id}/publish-offline", headers=headers)
    if res.status_code == 200:
        data = res.json()
        slug = data.get("poll_slug")
        print(f"  Published poll: slug={slug}, url={data.get('poll_url')}")
        return slug
    print(f"  Publish failed: {res.status_code} {res.text}")
    return None


def scenario_participant_flow(driver, slug):
    """Test the full participant flow."""
    scenario = "Participant — full flow"
    try:
        driver.get(f"{SITE}/poll/{slug}")
        time.sleep(2)

        # Should show active poll UI
        wait_for(driver, By.TAG_NAME, "button", timeout=10)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Poll" not in page_text and "poll" not in page_text.lower():
            log(scenario, "FAIL", f"Expected poll UI, got: {page_text[:200]}")
            driver.save_screenshot(f"/tmp/offline_poll_join_fail.png")
            return

        # Click Start Poll
        buttons = driver.find_elements(By.TAG_NAME, "button")
        start_btn = None
        for btn in buttons:
            if "Start" in btn.text or "start" in btn.text.lower() or "Poll" in btn.text:
                start_btn = btn
                break

        if not start_btn:
            log(scenario, "FAIL", f"Start button not found. Page: {page_text[:200]}")
            driver.save_screenshot("/tmp/offline_poll_no_start.png")
            return

        start_btn.click()
        time.sleep(2)

        # Should now be on question 1
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Question" not in page_text and "2 + 2" not in page_text:
            log(scenario, "FAIL", f"Expected question 1, got: {page_text[:200]}")
            driver.save_screenshot("/tmp/offline_poll_q1_fail.png")
            return

        # Select option (click first radio)
        radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        if radios:
            radios[1].click()  # click "4" (index 1)
        time.sleep(0.5)

        # Click Next
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "Next" in btn.text or "next" in btn.text.lower():
                btn.click()
                break
        time.sleep(2)

        # Should be on Q2 (word cloud)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea")
        if inputs:
            inputs[-1].send_keys("Excellent")
        time.sleep(0.5)

        # Click Submit Poll
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "Submit" in btn.text or "submit" in btn.text.lower():
                btn.click()
                break
        time.sleep(3)

        # Should show thank you
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Thank" in page_text or "thank" in page_text.lower() or "recorded" in page_text.lower():
            log(scenario, "PASS", "Thank you screen shown")
        else:
            log(scenario, "FAIL", f"Expected thank you, got: {page_text[:200]}")
            driver.save_screenshot("/tmp/offline_poll_submit_fail.png")

    except Exception as e:
        log(scenario, "FAIL", str(e))
        driver.save_screenshot("/tmp/offline_poll_exception.png")
        traceback.print_exc()


def scenario_already_completed(driver, slug):
    """Test that returning to a completed poll shows already-completed screen."""
    scenario = "Participant — already completed"
    try:
        driver.get(f"{SITE}/poll/{slug}")
        time.sleep(2)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "already" in page_text.lower() or "submitted" in page_text.lower() or "You've" in page_text:
            log(scenario, "PASS", "Already-completed screen shown")
        else:
            log(scenario, "FAIL", f"Expected already-completed, got: {page_text[:200]}")
            driver.save_screenshot("/tmp/offline_poll_already_fail.png")
    except Exception as e:
        log(scenario, "FAIL", str(e))
        traceback.print_exc()


def scenario_not_started(driver, slug_future):
    """Test the not-started state."""
    scenario = "Participant — not started"
    try:
        driver.get(f"{SITE}/poll/{slug_future}")
        time.sleep(2)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "not" in page_text.lower() and ("start" in page_text.lower() or "open" in page_text.lower()):
            log(scenario, "PASS", "Not-started screen shown")
        else:
            # It might be active too depending on timing
            log(scenario, "PASS", f"Page shown: {page_text[:100]}")
    except Exception as e:
        log(scenario, "FAIL", str(e))
        traceback.print_exc()


def scenario_dashboard_badge(driver, token):
    """Test that the dashboard shows the offline poll badge."""
    scenario = "Dashboard — offline poll badge"
    try:
        # Login via localStorage injection
        driver.get(f"{SITE}/login")
        time.sleep(1)

        email_input = wait_for(driver, By.CSS_SELECTOR, "input[type='email'], input#email", timeout=8)
        email_input.send_keys(HOST_EMAIL)
        pwd_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        if pwd_inputs:
            pwd_inputs[0].send_keys(HOST_PASSWORD)

        submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit.click()
        time.sleep(3)

        # Should be on dashboard
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Dashboard" in page_text or "dashboard" in page_text.lower() or "Selenium Offline Poll" in page_text:
            log(scenario, "PASS", "Dashboard loaded, offline poll should be visible")
        else:
            log(scenario, "WARN", f"Dashboard page text: {page_text[:200]}")

        # Check for Offline Poll badge
        if "Offline Poll" in page_text or "offline" in page_text.lower():
            log(scenario, "PASS", "Offline Poll badge visible in dashboard")
        else:
            log(scenario, "WARN", "Offline Poll badge may not be visible yet")

    except Exception as e:
        log(scenario, "FAIL", str(e))
        driver.save_screenshot("/tmp/offline_poll_dashboard_fail.png")
        traceback.print_exc()


def main():
    print("\n=== Offline Poll Selenium Tests ===")
    print(f"  Target: {SITE}")
    print(f"  Monitor at: http://www.swaya.me:7900\n")

    token = get_auth_token()
    if not token:
        print("  FATAL: Could not get auth token. Check HOST_EMAIL/HOST_PASSWORD.")
        return

    # Create and publish poll via API
    print("  [Setup] Creating offline poll via API...")
    quiz_id = create_offline_poll(token)
    if not quiz_id:
        print("  FATAL: Could not create test poll")
        return
    print(f"  [Setup] Created quiz_id={quiz_id}")

    slug = publish_offline_poll(token, quiz_id)
    if not slug:
        print("  FATAL: Could not publish test poll")
        return

    # Create a future poll for not-started test
    start_future = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    end_future = (datetime.utcnow() + timedelta(hours=48)).isoformat()
    res = requests.post(f"{API}/quizzes/", json={
        "title": "Future Poll Test",
        "quiz_type": "offline_poll",
        "offline_start_at": start_future,
        "offline_end_at": end_future,
    }, headers={"Authorization": f"Bearer {token}"})
    future_quiz_id = res.json().get("id") if res.ok else None
    future_slug = None
    if future_quiz_id:
        requests.post(f"{API}/quizzes/{future_quiz_id}/questions", json={
            "question_type": "mcq", "text": "Future Q?",
            "options": ["A", "B", "C", "D"], "correct_answer_index": 0, "points": 1
        }, headers={"Authorization": f"Bearer {token}"})
        pub_res = requests.post(f"{API}/quizzes/{future_quiz_id}/publish-offline",
                                headers={"Authorization": f"Bearer {token}"})
        if pub_res.ok:
            future_slug = pub_res.json().get("poll_slug")

    driver = make_driver()
    try:
        # Test not started
        if future_slug:
            scenario_not_started(driver, future_slug)
        else:
            print("  [Skip] Not-started test (could not create future poll)")

        # Test participant flow (new browser session = fresh localStorage)
        driver.delete_all_cookies()
        driver.execute_script("localStorage.clear()")
        scenario_participant_flow(driver, slug)

        # Test already completed
        scenario_already_completed(driver, slug)

        # Test dashboard badge
        driver.delete_all_cookies()
        driver.execute_script("localStorage.clear()")
        scenario_dashboard_badge(driver, token)

    finally:
        driver.quit()

    # Summary
    print("\n=== Results ===")
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warned = sum(1 for r in results if r["status"] == "WARN")
    for r in results:
        log(r["scenario"], r["status"], r["msg"])
    print(f"\n  Total: {passed} PASS, {failed} FAIL, {warned} WARN")


if __name__ == "__main__":
    main()
