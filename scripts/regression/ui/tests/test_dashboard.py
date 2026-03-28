"""
Dashboard Regression
Verifies dashboard loads for both regular user and admin without console JS errors.
"""
import os
import pytest
from playwright.sync_api import Page
from conftest import login, assert_no_js_errors, BASE_URL, HOST_EMAIL, HOST_PASSWORD, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD


def test_dashboard_regular_user(page: Page):
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    login(page, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD)
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(2000)

    # Dashboard should have quiz list or "Create" button
    assert page.url.startswith(f"{BASE_URL}/dashboard"), f"expected dashboard, got {page.url}"
    assert_no_js_errors(errors, "dashboard/regular_user")
    print("OK: dashboard renders for regular user without JS errors")


def test_dashboard_admin(page: Page):
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    login(page, HOST_EMAIL, HOST_PASSWORD)
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(2000)

    assert page.url.startswith(f"{BASE_URL}/dashboard"), f"expected dashboard, got {page.url}"
    assert_no_js_errors(errors, "dashboard/admin")
    print("OK: dashboard renders for admin without JS errors")
