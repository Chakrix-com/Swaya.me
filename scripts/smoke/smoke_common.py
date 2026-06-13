"""Shared utilities for Swaya.me smoke tests (test.swaya.me)."""
import os, time, json, requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = os.environ.get("SMOKE_BASE", "https://test.swaya.me")
API  = f"{BASE}/api/v1"
# Credentials for the demo super-admin account on test env
EMAIL    = os.environ.get("SMOKE_EMAIL",    "demo@swaya.me")
PASSWORD = os.environ.get("SMOKE_PASSWORD", "Demo1234")
OUT = "/tmp/smoke"

os.makedirs(OUT, exist_ok=True)

SELENIUM_HUB = "http://localhost:4444/wd/hub"


def make_driver(width=1440, height=900):
    opts = webdriver.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"--window-size={width},{height}")
    return webdriver.Remote(command_executor=SELENIUM_HUB, options=opts)


def make_mobile_driver():
    return make_driver(width=430, height=932)


def api_login():
    resp = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    resp.raise_for_status()
    return resp.json()["access_token"]


def api_headers(token):
    return {"Authorization": f"Bearer {token}"}


def snap(driver, name, delay=1.0):
    time.sleep(delay)
    path = f"{OUT}/{name}.png"
    driver.save_screenshot(path)
    return path


def wait_for(driver, by, selector, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))


def click_wait(driver, by, selector, timeout=15):
    el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))
    el.click()
    return el


def login_ui(driver, wait=None):
    """Navigate to login and authenticate via UI."""
    driver.get(f"{BASE}/login")
    w = wait or WebDriverWait(driver, 15)
    w.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input#email")))
    driver.find_element(By.CSS_SELECTOR, "input[type='email'], input#email").send_keys(EMAIL)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    w.until(lambda d: "/dashboard" in d.current_url or "/activities" in d.current_url or d.current_url.rstrip("/") == BASE)
    time.sleep(1)


class SmokeResult:
    def __init__(self, name):
        self.name = name
        self.steps = []
        self.failed = False

    def ok(self, msg):
        self.steps.append(f"  ✅ {msg}")

    def fail(self, msg):
        self.steps.append(f"  ❌ {msg}")
        self.failed = True

    def skip(self, msg):
        self.steps.append(f"  ⏭  {msg}")

    def report(self):
        verdict = "FAIL" if self.failed else "PASS"
        print(f"\n{'='*60}")
        print(f"  {verdict}  {self.name}")
        print('='*60)
        for s in self.steps:
            print(s)
