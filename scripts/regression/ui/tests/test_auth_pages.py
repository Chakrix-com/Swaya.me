"""
Auth Pages Regression
Verifies /login, /register, /forgot-password render without console errors.
"""
import os
import pytest
from playwright.sync_api import Page

BASE_URL = os.getenv("APP_BASE_URL", "https://test.swaya.me")


def _collect_errors(page: Page):
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    return errors


def _check(errors: list, route: str):
    bad = [e for e in errors if "ReferenceError" in e or "TypeError" in e or "is not defined" in e]
    if bad:
        pytest.fail(f"JS error on {route}:\n" + "\n".join(bad))


def test_login_page(page: Page):
    errors = _collect_errors(page)
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle", timeout=10000)
    assert page.locator("input#login_email").count() > 0, "login form not rendered"
    _check(errors, "/login")
    print("OK: /login renders without JS errors")


def test_register_page(page: Page):
    errors = _collect_errors(page)
    page.goto(f"{BASE_URL}/register")
    page.wait_for_load_state("networkidle", timeout=10000)
    _check(errors, "/register")
    print("OK: /register renders without JS errors")


def test_forgot_password_page(page: Page):
    errors = _collect_errors(page)
    page.goto(f"{BASE_URL}/forgot-password")
    page.wait_for_load_state("networkidle", timeout=10000)
    _check(errors, "/forgot-password")
    print("OK: /forgot-password renders without JS errors")
