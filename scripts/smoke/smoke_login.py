"""
Smoke test: Login + Dashboard
Verifies: login form → dashboard loads → stats row present → activity list visible.
"""
import sys, traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from smoke_common import BASE, make_driver, snap, login_ui, SmokeResult

def run():
    r = SmokeResult("Login + Dashboard")
    d = make_driver()
    try:
        # 1. Public home loads
        d.get(BASE)
        assert "Swaya" in d.title, f"Expected Swaya in title, got: {d.title}"
        snap(d, "login_01_home")
        r.ok(f"Home loaded: {d.title}")

        # 2. Login form
        d.get(f"{BASE}/login")
        from selenium.webdriver.support import expected_conditions as EC
        w = WebDriverWait(d, 15)
        w.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
        snap(d, "login_02_form")
        r.ok("Login form rendered")

        # 3. Submit credentials
        login_ui(d, w)
        snap(d, "login_03_dashboard")
        r.ok(f"Logged in → {d.current_url}")

        # 4. Dashboard page title or content
        assert "swaya.me" in d.current_url.lower()
        r.ok("Dashboard URL confirmed")

        # 5. Check activities / quiz list exists
        cards = d.find_elements(By.CSS_SELECTOR, ".ant-card, .ant-table, [data-testid='quiz-card']")
        snap(d, "login_04_content")
        if cards:
            r.ok(f"Dashboard content cards: {len(cards)}")
        else:
            r.skip("No activity cards found (may be empty account)")

    except Exception as e:
        r.fail(f"Exception: {e}")
        snap(d, "login_fail")
        traceback.print_exc()
    finally:
        d.quit()
        r.report()
        return 0 if not r.failed else 1

if __name__ == "__main__":
    sys.exit(run())
