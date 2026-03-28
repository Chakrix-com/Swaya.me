
import pytest
from playwright.sync_api import Page, expect
import os

BASE_URL = os.getenv("APP_BASE_URL", "https://test.swaya.me")
HOST_EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
HOST_PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")
REGULAR_USER_EMAIL = os.getenv("REGULAR_USER_EMAIL", "regression-free@swaya.me")
REGULAR_USER_PASSWORD = os.getenv("REGULAR_USER_PASSWORD", "RegTest2026!")


def _run_add_question_flow(page: Page, email: str, password: str, persona: str):
    """Core test: login, create quiz, add question, assert no JS errors."""
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    # 1. Login
    print(f"[{persona}] Logging in to {BASE_URL} as {email}...")
    page.goto(f"{BASE_URL}/login")
    page.fill("input#login_email", email)
    page.fill("input#login_password", password)
    page.click('button:has-text("Sign In")')
    page.wait_for_url(f"{BASE_URL}/dashboard", timeout=15000)
    print(f"[{persona}] Logged in")

    # 2. Create a new Quiz
    print(f"[{persona}] Creating a new quiz...")
    page.click('button:has-text("Create Online Quiz")')
    page.wait_for_url("**/quiz/new*", timeout=10000)
    page.fill("input#title", f"UI Regression Quiz {os.getpid()} [{persona}]")
    page.click('button:has-text("Create Online Quiz")')
    page.wait_for_url("**/edit", timeout=15000)
    print(f"[{persona}] At Quiz Edit page")

    # 3. Add a question
    print(f"[{persona}] Adding a question...")
    page.click('button:has-text("Add Question")')
    page.wait_for_selector("textarea", timeout=10000)
    page.locator("textarea").first.fill("Regression UI Test Question")
    page.locator("input.ant-input").nth(0).fill("Answer 1")
    page.locator("input.ant-input").nth(1).fill("Answer 2")

    print(f"[{persona}] Clicking '+ Add Question' (submit)...")
    page.click('button.ant-btn-primary:has-text("Add Question")')
    page.wait_for_timeout(3000)

    # 4. Assert no ReferenceError or TypeError in console
    bad_errors = [
        e for e in console_errors
        if "ReferenceError" in e or "TypeError" in e or "is not defined" in e
    ]
    for error in console_errors:
        print(f"[{persona}] Console error: {error}")

    if bad_errors:
        pytest.fail(
            f"[{persona}] JS error detected in handleAddQuestion:\n" + "\n".join(bad_errors)
        )

    print(f"[{persona}] No ReferenceErrors or TypeErrors detected")


def test_add_question_regular_user(page: Page):
    """Primary regression test: the stripHtml bug only surfaced for role=user."""
    _run_add_question_flow(page, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD, "regular_user")


def test_add_question_admin_user(page: Page):
    """Variant: same flow exercised as admin/super_admin user."""
    _run_add_question_flow(page, HOST_EMAIL, HOST_PASSWORD, "admin")


if __name__ == "__main__":
    pytest.main([__file__, "-s", "--headed"])
