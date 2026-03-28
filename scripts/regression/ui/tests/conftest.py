"""
Shared Playwright fixtures for Swaya.me UI regression tests.
"""
import os
import pytest
from playwright.sync_api import Page, BrowserContext, Browser, sync_playwright


BASE_URL = os.getenv("APP_BASE_URL", "https://test.swaya.me")
HOST_EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
HOST_PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")
REGULAR_USER_EMAIL = os.getenv("REGULAR_USER_EMAIL", "regression-free@swaya.me")
REGULAR_USER_PASSWORD = os.getenv("REGULAR_USER_PASSWORD", "RegTest2026!")


def login(page: Page, email: str, password: str):
    """Login helper: fills credentials, clicks Sign In, waits for dashboard."""
    page.goto(f"{BASE_URL}/login")
    page.fill("input#login_email", email)
    page.fill("input#login_password", password)
    page.click('button:has-text("Sign In")')
    page.wait_for_url(f"{BASE_URL}/dashboard", timeout=15000)


@pytest.fixture()
def console_errors(page: Page):
    """Collect browser console errors for the test."""
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    return errors


@pytest.fixture()
def admin_page(page: Page):
    """Page logged in as admin/super_admin."""
    login(page, HOST_EMAIL, HOST_PASSWORD)
    return page


@pytest.fixture()
def regular_page(page: Page):
    """Page logged in as regular user (role=user, tier=FREE)."""
    login(page, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD)
    return page


def assert_no_js_errors(errors: list, context: str = ""):
    """Fail if any ReferenceError or TypeError found in console errors."""
    bad = [e for e in errors if "ReferenceError" in e or "TypeError" in e or "is not defined" in e]
    if bad:
        prefix = f"[{context}] " if context else ""
        pytest.fail(f"{prefix}JS error(s) detected:\n" + "\n".join(bad))
