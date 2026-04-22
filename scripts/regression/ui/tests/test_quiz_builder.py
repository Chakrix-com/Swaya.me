
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



def test_excel_export_button_visibility(page: Page):
    """Verify 'Download draft as Excel' shown for exam, hidden for regular quiz."""
    import requests as req
    api = BASE_URL.replace(":3000", "").rstrip("/")
    api_base = api.replace("https://test.swaya.me", "https://test.swaya.me/api/v1")

    # Get auth token via API
    token_r = req.post(f"{api_base}/auth/login",
                       json={"email": HOST_EMAIL, "password": HOST_PASSWORD}, timeout=10)
    token = token_r.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    # Find or create a draft exam quiz
    quizzes = req.get(f"{api_base}/quizzes/", headers=headers, timeout=10).json()
    exam = next((q for q in quizzes if q.get("quiz_type") == "exam" and q.get("status") == "draft"), None)
    if not exam:
        import datetime, pytz
        now = datetime.datetime.now(pytz.utc)
        r = req.post(f"{api_base}/quizzes/", headers=headers, timeout=10, json={
            "title": "Excel Visibility Test Exam",
            "quiz_type": "exam",
            "exam_start_at": (now + datetime.timedelta(hours=1)).isoformat(),
            "exam_end_at": (now + datetime.timedelta(hours=2)).isoformat(),
        })
        exam = r.json()

    exam_id = exam["id"]

    # Login in browser
    page.goto(f"{BASE_URL}/login")
    page.fill("input#login_email", HOST_EMAIL)
    page.fill("input#login_password", HOST_PASSWORD)
    page.click('button:has-text("Sign In")')
    page.wait_for_url(f"{BASE_URL}/dashboard")

    # Navigate directly to exam edit page
    page.goto(f"{BASE_URL}/quiz/{exam_id}/edit")
    page.wait_for_load_state("networkidle")

    # Exam: Download draft as Excel should be visible
    download_btn = page.locator('button:has-text("Download draft as Excel")')
    expect(download_btn).to_be_visible(timeout=10000)
    print("✓ Download draft as Excel button visible for exam type")

    # Find or create a regular draft quiz and verify button is hidden
    regular = next((q for q in quizzes if q.get("quiz_type") == "quiz" and q.get("status") == "draft"), None)
    if not regular:
        r = req.post(f"{api_base}/quizzes/", headers=headers, timeout=10, json={
            "title": "Excel Visibility Test Quiz",
            "quiz_type": "quiz",
        })
        regular = r.json()

    page.goto(f"{BASE_URL}/quiz/{regular['id']}/edit")
    page.wait_for_load_state("networkidle")
    expect(page.locator('button:has-text("Download draft as Excel")')).to_have_count(0)
    print("✓ Download draft as Excel button hidden for regular quiz type")

def test_create_test_persistence_ui(page: Page):
    """Verify creating a test via 'Create Test' button persists as exam."""
    page.goto(f"{BASE_URL}/login")
    page.fill("input#login_email", HOST_EMAIL)
    page.fill("input#login_password", HOST_PASSWORD)
    page.click('button:has-text("Sign In")')
    page.wait_for_url(f"{BASE_URL}/dashboard")

    # Click 'Create Test'
    page.click('button:has-text("Create Test")')
    page.wait_for_url("**/quiz/new?type=exam")
    
    title = f"UI Persistence Test {os.getpid()}"
    page.fill("input#title", title)
    
    # Check that it says 'Create Test' on the primary button
    submit_btn = page.locator('button.ant-btn-primary:has-text("Create Test")')
    expect(submit_btn).to_be_visible()
    
    submit_btn.click()
    page.wait_for_url("**/edit")
    
    # Check header says 'Edit Test'
    expect(page.locator('text=Edit Test')).to_be_visible()
    
    # Check persistence tag 'Test'
    expect(page.locator('.ant-tag:has-text("Test")')).to_be_visible()
    print(f"✓ Created test {title} successfully persisted as Exam type in UI")

def test_proctoring_settings_persistence(page: Page):
    """Verify proctoring settings can be enabled and persisted in Quiz Builder."""
    page.goto(f"{BASE_URL}/login")
    page.fill("input#login_email", HOST_EMAIL)
    page.fill("input#login_password", HOST_PASSWORD)
    page.click('button:has-text("Sign In")')
    page.wait_for_url(f"{BASE_URL}/dashboard")

    # Click 'Create Test'
    page.click('button:has-text("Create Test")')
    page.wait_for_url("**/quiz/new?type=exam")
    
    title = f"Proctoring UI Test {os.getpid()}"
    page.fill("input#title", title)
    page.click('button.ant-btn-primary:has-text("Create Test")')
    page.wait_for_url("**/edit")

    # Find Proctoring Settings section
    # Title is "Security & Proctoring" (based on i18n key proctoring.settings.title)
    proctoring_section = page.locator('div.ant-card').filter(has_text="Security & Proctoring").last
    expect(proctoring_section).to_be_visible(timeout=10000)

    # Enable proctoring switch
    # The switch is next to "Enable Proctoring" (proctoring.settings.enableLabel)
    enable_switch = proctoring_section.locator('button[role="switch"]').first
    enable_switch.click()
    
    # Wait for settings to expand
    expect(page.locator('text=Standard')).to_be_visible()
    
    # Click "Standard" preset
    # It's a div with text "Standard"
    page.click('div:has-text("Standard")')
    
    # Change lock threshold
    # InputNumber for lock_on_violation_count
    lock_input = page.locator('input.ant-input-number-input').first
    lock_input.fill("5")
    
    # Save the quiz
    # The button text for exams is "Save Settings"
    page.click('button:has-text("Save Settings")')
    page.wait_for_timeout(2000) # Give it time to save
    
    # Reload and verify
    page.reload()
    page.wait_for_load_state("networkidle")
    
    expect(page.locator('div.ant-card').filter(has_text="Security & Proctoring").last).to_be_visible()
    # Check if switch is still enabled
    expect(page.locator('button[role="switch"]').first).to_have_attribute("aria-checked", "true")
    
    # Check if lock threshold persisted
    expect(page.locator('input.ant-input-number-input').first).to_have_value("5")
    
    print(f"✓ Proctoring settings for {title} successfully persisted")

if __name__ == "__main__":
    pytest.main([__file__, "-s", "--headed"])
