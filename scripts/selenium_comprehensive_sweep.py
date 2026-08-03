"""
Comprehensive Selenium sweep of test.swaya.me: Dashboard, Activities, QuizBuilder,
Admin User Management (incl. tier_override field), /plans page, public Home page,
NotFound page, and a language-switch check that newly-added translations actually
render (not just exist in JSON).

Run (test.swaya.me, default):
    sudo docker cp scripts/selenium_comprehensive_sweep.py selenium-arm:/scripts/
    sudo docker cp scripts/selenium_utils.py selenium-arm:/scripts/
    TOKEN=$(cd backend && source .venv/bin/activate && python /home/vinay/Swaya.me/scripts/generate_selenium_token.py meetnishant@gmail.com)
    sudo docker exec -e SWAYA_TOKEN="$TOKEN" selenium-arm python3 /scripts/selenium_comprehensive_sweep.py

Run against live (www.swaya.me) post-deploy — read-only, never clicks Save/submit:
    TOKEN=$(cd backend && source .venv/bin/activate && python /home/vinay/Swaya.me/scripts/generate_selenium_token.py meetnishant@gmail.com --env /www/wwwroot/swaya-live/backend/.env)
    sudo docker exec -e SWAYA_TOKEN="$TOKEN" -e SWAYA_TARGET_BASE=https://www.swaya.me -e SWAYA_COOKIE_DOMAIN=www.swaya.me \\
        selenium-arm python3 /scripts/selenium_comprehensive_sweep.py

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

sys.path.insert(0, '/scripts')
from selenium_utils import inject_error_collectors, collect_js_errors  # noqa: E402

WEBDRIVER_URL = 'http://localhost:4444'
TARGET_BASE = os.environ.get('SWAYA_TARGET_BASE', 'https://test.swaya.me')
COOKIE_DOMAIN = os.environ.get('SWAYA_COOKIE_DOMAIN', 'test.swaya.me')

PASS = '\033[92m PASS\033[0m'
FAIL = '\033[91m FAIL\033[0m'
INFO = '\033[94m INFO\033[0m'

issues = []


def check(name, condition, extra=""):
    if condition:
        print(f'{PASS} {name} {extra}')
    else:
        print(f'{FAIL} {name} {extra}')
        issues.append(f"{name} {extra}")
    return condition


def wait_for(driver, by, value, timeout=15, visible=True):
    try:
        cond = EC.visibility_of_element_located((by, value)) if visible else EC.presence_of_element_located((by, value))
        return WebDriverWait(driver, timeout).until(cond)
    except TimeoutException:
        return None


def load_authed(driver, path):
    driver.get(f"{TARGET_BASE}{path}")
    time.sleep(2.5)
    inject_error_collectors(driver)


def main():
    token = os.environ.get('SWAYA_TOKEN', '').strip()
    if not token:
        print(f'{FAIL} SWAYA_TOKEN env var not set')
        sys.exit(1)
    print(f'{PASS} Token ready ({token[:30]}...)')

    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1440,900')
    driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
    driver.set_page_load_timeout(30)

    try:
        driver.get(TARGET_BASE)
        driver.add_cookie({
            'name': 'access_token', 'value': token, 'domain': COOKIE_DOMAIN,
            'path': '/', 'secure': True, 'httpOnly': True,
        })
        print(f'{PASS} Cookie injected for {COOKIE_DOMAIN}')

        # --- Dashboard ---
        print(f'\n{INFO} --- Dashboard ---')
        load_authed(driver, '/dashboard')
        body = driver.find_element(By.TAG_NAME, 'body').text
        check('Dashboard: page has content', len(body) > 100)
        check('Dashboard: no raw i18n key leakage', 'dashboard.' not in body and 'quiz.' not in body)
        collect_js_errors(driver, 'Dashboard')

        # --- Activities ---
        print(f'\n{INFO} --- Activities ---')
        load_authed(driver, '/activities')
        body = driver.find_element(By.TAG_NAME, 'body').text
        check('Activities: page has content', len(body) > 50)
        collect_js_errors(driver, 'Activities')

        # --- /plans page: Coding Challenge Pro card ---
        print(f'\n{INFO} --- /plans ---')
        load_authed(driver, '/plans')
        time.sleep(1)
        body = driver.find_element(By.TAG_NAME, 'body').text
        check('/plans: page rendered', len(body) > 50)
        cards = driver.find_elements(By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'coding challenge')]")
        check('/plans: Coding Challenge Pro card present', len(cards) > 0, f"(found {len(cards)} matching nodes)")
        collect_js_errors(driver, 'Plans')

        # --- Admin User Management: tier_override field ---
        print(f'\n{INFO} --- Admin User Management ---')
        load_authed(driver, '/admin/users')
        time.sleep(1)
        rows = driver.find_elements(By.XPATH, "//table//tbody//tr")
        check('Admin Users: table has rows', len(rows) > 0, f"({len(rows)} rows)")
        edit_btns = driver.find_elements(By.XPATH, "//table//button[.//span[contains(@class,'anticon-more')]]")
        if check('Admin Users: at least one row actions button', len(edit_btns) > 0):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", edit_btns[0])
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", edit_btns[0])
            time.sleep(0.5)
            edit_item = driver.find_elements(By.XPATH, "//*[contains(text(),'Edit')]")
            if check('Admin Users: Edit menu item found', len(edit_item) > 0):
                driver.execute_script("arguments[0].click();", edit_item[0])
                time.sleep(1)
                modal = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
                if check('Admin Users: edit modal opened', modal is not None):
                    modal_text = modal.text
                    check(
                        'Admin Users: tier_override field visible for super_admin',
                        'Override' in modal_text or 'override' in modal_text.lower(),
                        f"(modal text sample: {modal_text[:150]!r})"
                    )
        collect_js_errors(driver, 'AdminUsers')

        # --- Public Home page (unauthenticated look) ---
        print(f'\n{INFO} --- Home (public) ---')
        auth_cookie = driver.get_cookie('access_token')
        driver.delete_cookie('access_token')
        driver.get(f"{TARGET_BASE}/")
        time.sleep(2)
        inject_error_collectors(driver)
        body = driver.find_element(By.TAG_NAME, 'body').text
        check('Home: page has content', len(body) > 50)
        check('Home: no raw i18n key leakage (home.v2.)', 'home.v2.' not in body)
        collect_js_errors(driver, 'Home')

        # Re-auth: NotFound only renders inside the authenticated route tree
        # (App.jsx's catch-all "*" is nested under AuthenticatedLayout) — an
        # unauthenticated hit on an unknown route redirects to Home instead.
        driver.get(TARGET_BASE)
        driver.add_cookie(auth_cookie)

        # --- NotFound page + language switch verification ---
        print(f'\n{INFO} --- NotFound + language switch ---')
        driver.get(f"{TARGET_BASE}/this-route-does-not-exist-sweep")
        time.sleep(1.5)
        subtitle_en_el = wait_for(driver, By.CLASS_NAME, 'ant-result-subtitle', timeout=5)
        check('NotFound (en): 404 Result component rendered', subtitle_en_el is not None)
        subtitle_en = subtitle_en_el.text if subtitle_en_el else ''
        check('NotFound (en): subtitle matches expected English default', subtitle_en == "This activity doesn't exist or has been removed.", f"(got: {subtitle_en!r})")

        driver.execute_script("window.localStorage.setItem('preferredLanguage','hi')")
        driver.get(f"{TARGET_BASE}/this-route-does-not-exist-sweep")
        time.sleep(1.5)
        subtitle_hi_el = wait_for(driver, By.CLASS_NAME, 'ant-result-subtitle', timeout=5)
        subtitle_hi = subtitle_hi_el.text if subtitle_hi_el else ''
        check(
            'NotFound (hi): subtitle actually translated (differs from English, non-empty)',
            bool(subtitle_hi) and subtitle_hi != subtitle_en,
            f"(hi subtitle: {subtitle_hi!r})"
        )
        collect_js_errors(driver, 'NotFound-hi')
        driver.execute_script("window.localStorage.removeItem('preferredLanguage')")

        print(f'\n{"="*60}')
        if issues:
            print(f'{FAIL} {len(issues)} issue(s):')
            for i in issues:
                print(f'  - {i}')
        else:
            print(f'{PASS} All checks passed')
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
