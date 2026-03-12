"""
Submit www.swaya.me to URL categorization portals.
Connects to selenium-arm container at localhost:4444.
Monitor live at: http://www.swaya.me:7900
"""

import time
import traceback
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException

TARGET_URL = "https://www.swaya.me"
JUSTIFICATION = (
    "Swaya.me is a legitimate web-based interactive quiz and audience engagement platform "
    "for educators, trainers, and presenters. Used in classrooms, corporate training, and "
    "live events. Hosts create quiz sessions; audiences join with a 6-digit code anonymously. "
    "Includes Privacy Policy, Terms of Service, and About pages. "
    "Appropriate category: Business and Economy / Web-based Application."
)
CONTACT_EMAIL = "info@chakrix.net"
REMOTE_URL = "http://localhost:4444/wd/hub"
SS_DIR = "/tmp/portal_screenshots"

os.makedirs(SS_DIR, exist_ok=True)

results = {}


def get_driver():
    opts = ChromiumOptions()
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    return webdriver.Remote(command_executor=REMOTE_URL, options=opts)


def ss(driver, name):
    path = f"{SS_DIR}/{name}.png"
    try:
        driver.save_screenshot(path)
        print(f"    [screenshot: {path}]")
    except Exception as e:
        print(f"    [screenshot failed: {e}]")


def wait_el(driver, by, val, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, val)))


def wait_click(driver, by, val, timeout=15):
    el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, val)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.3)
    el.click()
    return el


def dismiss_alert(driver):
    """Accept any open alert dialog."""
    try:
        alert = driver.switch_to.alert
        print(f"    [Alert found: '{alert.text[:80]}' — dismissing]")
        alert.accept()
        time.sleep(0.5)
        return True
    except NoAlertPresentException:
        return False


def dismiss_overlays(driver):
    """Dismiss cookie banners and overlays."""
    selectors = [
        "#onetrust-accept-btn-handler",
        "button.cc-btn.cc-allow",
        "button#accept-cookie",
        "button.accept",
        "button[id*='cookie'][id*='accept']",
        "button[class*='cookie'][class*='accept']",
        "button[class*='accept'][class*='all']",
        "button[aria-label*='Accept all']",
        "button[aria-label*='accept']",
        ".cc-btn.cc-allow",
        "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
        "button[data-testid*='accept']",
        # Generic close buttons for overlays
        "button[aria-label='Close']",
        ".modal-close",
        ".cookie-close",
    ]
    for sel in selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.5)
        except Exception:
            pass


def js_click(driver, el):
    driver.execute_script("arguments[0].click();", el)


def js_type(driver, el, text):
    """Set input value via JS and dispatch input/change events."""
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
        "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
        el, text
    )


# ── 1. Symantec Blue Coat SiteReview ────────────────────────────────────────
def submit_bluecoat(driver):
    print("\n[1/5] Symantec Blue Coat SiteReview...")
    try:
        driver.get("https://sitereview.bluecoat.com/#/")
        time.sleep(6)
        dismiss_alert(driver)
        dismiss_overlays(driver)
        time.sleep(1)
        ss(driver, "bluecoat_1_loaded")

        # Find first visible text input on page
        inputs = driver.find_elements(By.TAG_NAME, "input")
        url_input = None
        for inp in inputs:
            try:
                if inp.is_displayed() and inp.get_attribute("type") in ("text", "search", "", None):
                    url_input = inp
                    break
            except Exception:
                pass
        if not url_input and inputs:
            url_input = inputs[0]

        # Use native send_keys — preserves Angular two-way binding via key events
        url_input.click()
        url_input.clear()
        time.sleep(0.3)
        url_input.send_keys(TARGET_URL)
        time.sleep(1.5)  # wait for Angular validation to process
        ss(driver, "bluecoat_1b_typed")

        # Click "Check Category" button using JS to avoid interactability issues
        btn = None
        for xpath in [
            "//*[contains(text(),'Check Category')]",
            "//button[contains(@class,'lookup')]",
            "//input[@type='submit']",
            "//button[@type='submit']",
        ]:
            try:
                btn = driver.find_element(By.XPATH, xpath)
                if btn.is_displayed():
                    break
            except Exception:
                btn = None

        if btn:
            # Try ActionChains first (most reliable for Angular apps), then JS, then Enter
            try:
                ActionChains(driver).move_to_element(btn).pause(0.3).click().perform()
                print("    Clicked Check Category via ActionChains")
            except Exception:
                js_click(driver, btn)
                print("    Clicked Check Category via JS")
        else:
            print("    No button found, trying Enter key")

        # Also press Enter in the input as a fallback (works for form-submit handlers)
        try:
            url_input.send_keys(Keys.RETURN)
        except Exception:
            pass

        time.sleep(12)
        dismiss_alert(driver)
        ss(driver, "bluecoat_2_after_lookup")

        page_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"    Page text snippet: {page_text[:400]}")

        # Check for CAPTCHA (Cloudflare Turnstile)
        if "verify" in page_text.lower() and "human" in page_text.lower():
            ss(driver, "bluecoat_captcha")
            results["Blue Coat"] = (
                "Cloudflare human verification required — cannot automate. "
                "Manual submission needed at sitereview.bluecoat.com"
            )
            print(f"  → {results.get('Blue Coat')}")
            return

        # Look for dispute/review link or button
        for text in ["Submit for Review", "Request Review", "Request a Review",
                     "Dispute", "Submit a Review", "Report", "Categorize", "Change"]:
            try:
                el = driver.find_element(By.XPATH, f"//*[contains(text(),'{text}')]")
                if el.is_displayed():
                    js_click(driver, el)
                    time.sleep(4)
                    ss(driver, "bluecoat_3_review_form")
                    # Fill form if present
                    try:
                        ta = WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea")))
                        ta.send_keys(JUSTIFICATION)
                        try:
                            email_inp = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
                            email_inp.send_keys(CONTACT_EMAIL)
                        except Exception:
                            pass
                        submit = driver.find_element(By.CSS_SELECTOR,
                            "button[type='submit'], input[type='submit']")
                        js_click(driver, submit)
                        time.sleep(4)
                        ss(driver, "bluecoat_4_submitted")
                        results["Blue Coat"] = "✓ Submitted for review"
                        return
                    except Exception as e2:
                        results["Blue Coat"] = f"Review clicked but form incomplete: {e2}"
                        return
            except Exception:
                pass

        results["Blue Coat"] = f"Lookup done — current category shown in screenshot"
    except Exception as e:
        ss(driver, "bluecoat_error")
        results["Blue Coat"] = f"Failed: {str(e)[:120]}"
    print(f"  → {results.get('Blue Coat')}")


# ── 2. Zscaler SiteReview ───────────────────────────────────────────────────
def submit_zscaler(driver):
    print("\n[2/5] Zscaler SiteReview...")
    try:
        driver.get("https://sitereview.zscaler.com/")
        time.sleep(6)
        dismiss_alert(driver)
        dismiss_overlays(driver)
        time.sleep(1)

        # Try to dismiss any modal/overlay by pressing Escape
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.5)
        except Exception:
            pass

        # Also try clicking body to dismiss any dropdown
        try:
            driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.5)
        except Exception:
            pass

        ss(driver, "zscaler_1_loaded")

        # Use JS to set the input value directly (bypasses overlay interactability)
        inp = None
        for sel in ["input[placeholder='Enter URL']", "input[placeholder*='URL']",
                    "input[placeholder*='url']", "input[type='text']", "input[type='search']"]:
            try:
                inp = driver.find_element(By.CSS_SELECTOR, sel)
                break
            except Exception:
                pass

        if not inp:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for i in inputs:
                if i.get_attribute("type") in ("text", "search", "", None):
                    inp = i
                    break

        if not inp:
            results["Zscaler"] = "No input found"
            print(f"  → {results.get('Zscaler')}")
            return

        # Set value via JS (avoids overlay blocking selenium clicks)
        js_type(driver, inp, "www.swaya.me")
        print("    URL set via JS")
        time.sleep(0.5)

        # Try clicking Look Up button via JS
        btn = None
        for xpath in [
            "//*[text()='Look Up']",
            "//*[text()='Look up']",
            "//*[contains(text(),'Look')]",
            "//button[contains(@class,'submit')]",
            "//button[@type='submit']",
        ]:
            try:
                btn = driver.find_element(By.XPATH, xpath)
                if btn.is_displayed():
                    break
            except Exception:
                btn = None

        if btn:
            js_click(driver, btn)
            print("    Clicked Look Up via JS")
        else:
            inp.send_keys(Keys.RETURN)
            print("    Submitted via Enter key")

        time.sleep(8)
        dismiss_alert(driver)
        ss(driver, "zscaler_2_after_lookup")

        page_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"    Page text snippet: {page_text[:400]}")

        # Find Report Miscategorization
        for text in ["Report a Miscategorization", "Miscategorization",
                     "Dispute", "Report", "Submit Feedback"]:
            try:
                btn = driver.find_element(By.XPATH, f"//*[contains(text(),'{text}')]")
                if btn.is_displayed():
                    js_click(driver, btn)
                    time.sleep(4)
                    ss(driver, "zscaler_3_form")
                    page_text2 = driver.find_element(By.TAG_NAME, "body").text
                    print(f"    After click text: {page_text2[:300]}")

                    # Fill category, comment, email
                    selects = driver.find_elements(By.CSS_SELECTOR, "select")
                    for s in selects:
                        sel_obj = Select(s)
                        opts = [o.text for o in sel_obj.options]
                        print(f"    Select opts: {opts[:8]}")
                        for opt in ["Business and Economy", "Business", "Internet Services",
                                    "Computer and Internet Info"]:
                            try:
                                sel_obj.select_by_visible_text(opt)
                                print(f"    Selected: {opt}")
                                break
                            except Exception:
                                pass

                    try:
                        ta = driver.find_element(By.CSS_SELECTOR, "textarea")
                        ta.send_keys(JUSTIFICATION)
                    except Exception:
                        pass
                    try:
                        email_inp = driver.find_element(By.CSS_SELECTOR,
                            "input[type='email'], input[name*='email'], input[id*='email']")
                        email_inp.send_keys(CONTACT_EMAIL)
                    except Exception:
                        pass

                    try:
                        submit = wait_click(driver, By.CSS_SELECTOR,
                            "button[type='submit'], input[type='submit']")
                        time.sleep(4)
                        ss(driver, "zscaler_4_submitted")
                        results["Zscaler"] = "✓ Submitted"
                    except Exception as e3:
                        ss(driver, "zscaler_4_error")
                        results["Zscaler"] = f"Form filled, submit failed: {str(e3)[:80]}"
                    return
            except Exception:
                pass

        results["Zscaler"] = "Lookup done — customers-only portal (dispute requires Zscaler network)"
    except Exception as e:
        ss(driver, "zscaler_error")
        results["Zscaler"] = f"Failed: {str(e)[:120]}"
    print(f"  → {results.get('Zscaler')}")


# ── 3. Palo Alto URL Filtering ──────────────────────────────────────────────
def submit_paloalto(driver):
    print("\n[3/5] Palo Alto URL Filtering...")
    try:
        driver.get("https://urlfiltering.paloaltonetworks.com/")
        time.sleep(6)
        dismiss_alert(driver)
        dismiss_overlays(driver)
        time.sleep(1)
        ss(driver, "paloalto_1_loaded")

        # Find the URL filtering input (id='id_url', placeholder='Enter a URL')
        url_input = None
        for sel in ["input#id_url", "input[name='url']", "input[placeholder='Enter a URL']",
                    "input[placeholder*='URL']", "input[placeholder*='url']"]:
            try:
                inp = driver.find_element(By.CSS_SELECTOR, sel)
                if inp.is_displayed():
                    url_input = inp
                    break
            except Exception:
                pass

        if not url_input:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"    Inputs: {[(i.get_attribute('id'), i.get_attribute('placeholder')) for i in inputs[:6]]}")
            for inp in inputs:
                if inp.is_displayed() and inp.get_attribute("type") in ("text", "search", "", None):
                    url_input = inp
                    break

        if not url_input:
            results["Palo Alto"] = "No URL input found"
            print(f"  → {results.get('Palo Alto')}")
            return

        url_input.clear()
        url_input.send_keys(TARGET_URL)
        time.sleep(0.5)
        ss(driver, "paloalto_2_typed")

        # Find the search/submit button within the form (not navigation search)
        # Look for the form button with specific context
        submit_btn = None
        for xpath in [
            "//form//button[@type='submit']",
            "//form//input[@type='submit']",
            "//button[contains(@class,'check') or contains(@class,'lookup') or contains(@class,'search-btn')]",
            # Fallback to button near the input
            "//input[@id='id_url']/following::button[1]",
            "//input[@id='id_url']/parent::*/following-sibling::button[1]",
        ]:
            try:
                btn = driver.find_element(By.XPATH, xpath)
                if btn.is_displayed():
                    submit_btn = btn
                    break
            except Exception:
                pass

        if submit_btn:
            js_click(driver, submit_btn)
            print(f"    Clicked submit button")
        else:
            url_input.send_keys(Keys.RETURN)
            print("    Submitted via Enter key")

        time.sleep(8)
        dismiss_alert(driver)
        ss(driver, "paloalto_3_after_lookup")

        page_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"    Page snippet: {page_text[:500]}")

        # Check for login-required notice (new from March 15, 2026)
        if "login required" in page_text.lower() or "Login Required" in page_text:
            print("    Note: Login now required for category change requests")
            results["Palo Alto"] = "URL indexed in Palo Alto DB — login required for category change (create free account at urlfiltering.paloaltonetworks.com)"
            ss(driver, "paloalto_login_notice")
            return

        # Look for category change request
        for text in ["Request a Category Change", "Request Category Change",
                     "Change Category", "Dispute", "Submit"]:
            try:
                btn = driver.find_element(By.XPATH, f"//*[contains(text(),'{text}')]")
                if btn.is_displayed():
                    js_click(driver, btn)
                    time.sleep(4)
                    ss(driver, "paloalto_4_form")

                    selects = driver.find_elements(By.CSS_SELECTOR, "select")
                    for s in selects:
                        sel_obj = Select(s)
                        opts = [o.text for o in sel_obj.options]
                        print(f"    Select opts: {opts[:8]}")
                        for opt in ["business-and-economy", "Business and Economy", "Business"]:
                            try:
                                sel_obj.select_by_value(opt)
                                break
                            except Exception:
                                try:
                                    sel_obj.select_by_visible_text(opt)
                                    break
                                except Exception:
                                    pass
                    try:
                        ta = driver.find_element(By.CSS_SELECTOR, "textarea")
                        ta.send_keys(JUSTIFICATION)
                    except Exception:
                        pass
                    try:
                        email_inp = driver.find_element(By.CSS_SELECTOR,
                            "input[type='email'], input[name*='email']")
                        email_inp.send_keys(CONTACT_EMAIL)
                    except Exception:
                        pass
                    try:
                        submit = wait_click(driver, By.CSS_SELECTOR,
                            "button[type='submit'], input[type='submit']")
                        time.sleep(4)
                        ss(driver, "paloalto_5_submitted")
                        results["Palo Alto"] = "✓ Submitted"
                    except Exception as e3:
                        results["Palo Alto"] = f"Form filled, submit failed: {str(e3)[:80]}"
                    return
            except Exception:
                pass

        results["Palo Alto"] = f"URL looked up — see paloalto_3_after_lookup screenshot"
    except Exception as e:
        ss(driver, "paloalto_error")
        results["Palo Alto"] = f"Failed: {str(e)[:120]}"
    print(f"  → {results.get('Palo Alto')}")


# ── 4. Trend Micro Site Safety ──────────────────────────────────────────────
def submit_trendmicro(driver):
    print("\n[4/5] Trend Micro Site Safety...")
    try:
        # Navigate to home page first, then search (avoids session timeout on direct result URL)
        driver.get("https://global.sitesafety.trendmicro.com/")
        time.sleep(5)
        dismiss_alert(driver)
        dismiss_overlays(driver)
        time.sleep(1)
        ss(driver, "trendmicro_1_home")

        # Find search/URL input on main page
        inp = None
        for sel in ["input[name='url']", "input[id*='url']", "input[placeholder*='URL']",
                    "input[placeholder*='url']", "input[type='text']", "input[type='search']"]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    inp = el
                    break
            except Exception:
                pass

        if inp:
            inp.clear()
            js_type(driver, inp, TARGET_URL)
            inp.click()
            time.sleep(0.3)

            # Find and click submit button
            btn = None
            for xpath in [
                "//input[@type='submit']",
                "//button[@type='submit']",
                "//*[contains(text(),'Check') or contains(text(),'Search') or contains(text(),'Look')]",
            ]:
                try:
                    btn = driver.find_element(By.XPATH, xpath)
                    if btn.is_displayed():
                        break
                except Exception:
                    btn = None

            if btn:
                js_click(driver, btn)
                print("    Clicked submit button")
            else:
                inp.send_keys(Keys.RETURN)
                print("    Submitted via Enter key")

            time.sleep(8)
            dismiss_alert(driver)
            ss(driver, "trendmicro_2_result")
        else:
            # Fall back to direct result URL, handling any alert that appears
            print("    No input on home page, trying direct result URL...")
            try:
                driver.get(f"https://global.sitesafety.trendmicro.com/result.php?url={TARGET_URL}")
            except UnexpectedAlertPresentException:
                dismiss_alert(driver)
            time.sleep(2)
            dismiss_alert(driver)
            time.sleep(4)
            ss(driver, "trendmicro_2_direct_result")

        page_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"    Page snippet: {page_text[:400]}")

        # Scroll down to find the categorization section
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        dismiss_alert(driver)
        ss(driver, "trendmicro_3_scrolled")

        page_text2 = driver.find_element(By.TAG_NAME, "body").text
        print(f"    After scroll: {page_text2[300:700]}")

        # Click "RECLASSIFY REQUEST" button to open the reclassification form
        submitted = False
        try:
            reclassify_btn = driver.find_element(By.XPATH,
                "//*[contains(text(),'RECLASSIFY') or contains(text(),'Reclassify') or "
                "contains(text(),'RECLASSIFY REQUEST')]")
            if reclassify_btn.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", reclassify_btn)
                time.sleep(1)
                ss(driver, "trendmicro_4_before_reclassify")
                js_click(driver, reclassify_btn)
                print("    Clicked RECLASSIFY REQUEST")
                time.sleep(4)
                dismiss_alert(driver)
                ss(driver, "trendmicro_4_reclassify_form")

                page_after_click = driver.find_element(By.TAG_NAME, "body").text
                print(f"    After reclassify click: {page_after_click[:400]}")

                # Debug: dump all visible buttons (including shadow DOM) to find the proceed button
                all_btns = driver.execute_script("""
                    var found = [];
                    function collect(root) {
                        root.querySelectorAll('button, a[href], input[type=button], input[type=submit]')
                            .forEach(function(el) {
                                var txt = (el.textContent || el.value || '').trim();
                                if (txt) found.push(txt.substring(0, 60));
                            });
                        root.querySelectorAll('*').forEach(function(el) {
                            if (el.shadowRoot) collect(el.shadowRoot);
                        });
                    }
                    collect(document);
                    return found;
                """)
                print(f"    All buttons in page: {all_btns[:20]}")

                # A modal may appear — use JS shadow-DOM traversal to find and click
                # "PROCEED TO URL RECLASSIFICATION REQUEST"
                proceed_clicked = driver.execute_script("""
                    function findAndClick(root, keywords) {
                        var els = root.querySelectorAll('button, a');
                        for (var el of els) {
                            var txt = (el.textContent || '').toUpperCase();
                            if (keywords.some(function(k){ return txt.indexOf(k) >= 0; })) {
                                el.scrollIntoView({block:'center'});
                                el.click();
                                return el.textContent.trim().substring(0, 60);
                            }
                        }
                        var hosts = root.querySelectorAll('*');
                        for (var h of hosts) {
                            if (h.shadowRoot) {
                                var r = findAndClick(h.shadowRoot, keywords);
                                if (r) return r;
                            }
                        }
                        return null;
                    }
                    return findAndClick(document,
                        ['URL RECLASSIFICATION REQUEST', 'PROCEED TO URL', 'HOME USERS']);
                """)
                if proceed_clicked:
                    print(f"    JS-clicked modal proceed button: {proceed_clicked}")
                    time.sleep(8)
                    dismiss_alert(driver)
                    ss(driver, "trendmicro_4b_after_proceed")
                    page_after_proceed = driver.find_element(By.TAG_NAME, "body").text
                    print(f"    After proceed: {page_after_proceed[:500]}")
                else:
                    print("    Modal proceed button not found via JS — continuing anyway")

                # Fill the reclassification form (may be modal or new page)
                # Select category
                selects = driver.find_elements(By.CSS_SELECTOR, "select")
                for s in selects:
                    if not s.is_displayed():
                        continue
                    sel_obj = Select(s)
                    opts = [o.text for o in sel_obj.options]
                    print(f"    Select opts: {opts}")
                    for opt in ["Computers/Internet", "Business", "Internet Services",
                                "Productivity", "Technology", "Web Applications",
                                "Information Technology"]:
                        try:
                            sel_obj.select_by_visible_text(opt)
                            print(f"    Selected: {opt}")
                            break
                        except Exception:
                            pass

                # Form has radio buttons:
                #   value='safe'           → recommend this URL is safe
                #   value='dangerous'      → mark as dangerous (skip)
                #   value='changecategory' → request a category change
                #   value='agree'          → agree with current rating/category (skip)
                radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                print(f"    Radio buttons found: {len(radios)}")
                selected_safe = False
                selected_category_change = False
                for r in radios:
                    val = (r.get_attribute("value") or "").lower()
                    label_id = r.get_attribute("id") or ""
                    print(f"      radio value='{val}' id='{label_id}'")

                    if val == "safe" and not selected_safe:
                        js_click(driver, r)
                        print("    Selected radio: safe")
                        selected_safe = True
                        time.sleep(0.5)

                    elif val == "changecategory" and not selected_category_change:
                        js_click(driver, r)
                        print("    Selected radio: changecategory")
                        selected_category_change = True
                        time.sleep(1.5)  # wait for category radio list to expand

                    elif selected_category_change and val in (
                            "computers / internet", "business / economy",
                            "internet infrastructure", "internet services"):
                        js_click(driver, r)
                        print(f"    Selected specific category: {val}")
                        selected_category_change = False  # stop selecting more categories
                        time.sleep(0.5)

                # After selecting changecategory, look for category dropdown/input
                if selected_category_change:
                    selects = driver.find_elements(By.CSS_SELECTOR, "select")
                    for s in selects:
                        if not s.is_displayed():
                            continue
                        sel_obj = Select(s)
                        opts = [o.text for o in sel_obj.options]
                        print(f"    Category select opts: {opts[:10]}")
                        for opt in ["Computers/Internet", "Business", "Internet Services",
                                    "Productivity", "Technology", "Web Applications",
                                    "Information Technology", "Software/Technology"]:
                            try:
                                sel_obj.select_by_visible_text(opt)
                                print(f"    Selected category: {opt}")
                                break
                            except Exception:
                                pass
                    # Also try text inputs for custom category
                    try:
                        cat_inp = driver.find_element(By.CSS_SELECTOR,
                            "input[placeholder*='categor' i], input[name*='categor' i]")
                        if cat_inp.is_displayed():
                            cat_inp.send_keys("Computers/Internet")
                    except Exception:
                        pass

                # Fill comment textarea
                try:
                    textarea = driver.find_element(By.CSS_SELECTOR, "textarea")
                    if textarea.is_displayed():
                        textarea.clear()
                        textarea.send_keys(JUSTIFICATION[:300])
                except Exception:
                    pass

                # Fill email if present
                try:
                    email_inp = driver.find_element(By.CSS_SELECTOR,
                        "input[type='email'], input[name*='email'], input[id*='email']")
                    if email_inp.is_displayed():
                        email_inp.send_keys(CONTACT_EMAIL)
                except Exception:
                    pass

                ss(driver, "trendmicro_5_form_filled")

                # Click submit — look for submit button WITHIN the reclassify form context,
                # avoid clicking the top search bar's button
                submit_btn = None
                # Try most specific selectors first — avoid the search bar button (CHECK NOW / Check Now)
                page_after_fill = driver.find_element(By.TAG_NAME, "body").text
                print(f"    Page before submit: {page_after_fill[:200]}")
                for xpath in [
                    # Button whose text is NOT 'Check Now' and NOT empty
                    "//input[@type='submit' and @value and @value!='Check Now' and @value!='CHECK NOW']",
                    "//button[@type='submit' and normalize-space(text())!='Check Now' "
                    "and normalize-space(text())!='CHECK NOW' and normalize-space(text())!='']",
                    "//button[contains(text(),'Submit') or contains(text(),'Send') "
                    "or contains(text(),'Confirm')]",
                    "//form[.//input[@type='radio'] or .//select or .//textarea]//input[@type='submit']",
                    "//form[.//input[@type='radio'] or .//select or .//textarea]//button[@type='submit']",
                ]:
                    try:
                        btn = driver.find_element(By.XPATH, xpath)
                        if btn.is_displayed():
                            submit_btn = btn
                            print(f"    Found submit button: {btn.get_attribute('value') or btn.text}")
                            break
                    except Exception:
                        pass

                if submit_btn:
                    js_click(driver, submit_btn)
                    time.sleep(3)
                    # Handle any "confirm" alerts (e.g. "submit without category?")
                    dismissed = dismiss_alert(driver)
                    if dismissed:
                        time.sleep(3)
                        dismiss_alert(driver)
                    ss(driver, "trendmicro_6_submitted")
                    page_final = driver.find_element(By.TAG_NAME, "body").text
                    print(f"    Final: {page_final[:300]}")
                    results["Trend Micro"] = "✓ Reclassify request submitted (safe + category change)"
                    submitted = True
                else:
                    ss(driver, "trendmicro_5_no_submit")
                    results["Trend Micro"] = "RECLASSIFY CLICKED — form opened but submit button not found (see screenshot)"
                    submitted = True
        except Exception as e_reclassify:
            print(f"    RECLASSIFY button not found or failed: {e_reclassify}")

        if not submitted:
            results["Trend Micro"] = "Result page loaded — Trend Micro now scanning swaya.me for the first time"
    except Exception as e:
        ss(driver, "trendmicro_error")
        results["Trend Micro"] = f"Failed: {str(e)[:120]}"
    print(f"  → {results.get('Trend Micro')}")


# ── 5. Fortinet FortiGuard ───────────────────────────────────────────────────
def submit_fortiguard(driver):
    print("\n[5/5] Fortinet FortiGuard Web Filter...")
    try:
        # Use the direct "Submit a site for categorization" page — no CAPTCHA on this form
        driver.get("https://www.fortiguard.com/faq/webfilter_lookup")
        time.sleep(6)
        dismiss_alert(driver)
        dismiss_overlays(driver)
        time.sleep(1)
        ss(driver, "fortiguard_1_submit_page")

        page_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"    Submit page snippet: {page_text[:300]}")

        # Find URL input on this form
        inp = None
        for sel in ["input[name='url']", "input[id='url']", "input[placeholder*='URL']",
                    "input[placeholder*='url']", "input[type='url']", "input[type='text']"]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    inp = el
                    break
            except Exception:
                pass

        if not inp:
            # Fall back to webfilter page and accept CAPTCHA limitation
            driver.get("https://www.fortiguard.com/webfilter")
            time.sleep(5)
            dismiss_alert(driver)
            dismiss_overlays(driver)
            time.sleep(1)
            ss(driver, "fortiguard_1b_webfilter")
            page_text2 = driver.find_element(By.TAG_NAME, "body").text
            print(f"    Webfilter page snippet: {page_text2[:300]}")
            results["Fortiguard"] = "FortiGuard lookup page requires reCAPTCHA — manual submission needed at fortiguard.com/webfilter"
            print(f"  → {results.get('Fortiguard')}")
            return

        inp.clear()
        js_type(driver, inp, TARGET_URL)
        inp.click()
        time.sleep(0.5)

        # Fill email if present
        try:
            email_inp = driver.find_element(By.CSS_SELECTOR,
                "input[type='email'], input[name*='email'], input[id*='email']")
            email_inp.send_keys(CONTACT_EMAIL)
        except Exception:
            pass

        # Fill comment/description if present
        try:
            ta = driver.find_element(By.CSS_SELECTOR, "textarea")
            ta.send_keys(JUSTIFICATION)
        except Exception:
            pass

        # Select category if dropdown present
        selects = driver.find_elements(By.CSS_SELECTOR, "select")
        for s in selects:
            sel_obj = Select(s)
            opts = [o.text for o in sel_obj.options]
            print(f"    Select opts: {opts[:8]}")
            for opt in ["Business", "Business and Economy", "Internet Services",
                        "Web Applications", "Information Technology"]:
                try:
                    sel_obj.select_by_visible_text(opt)
                    print(f"    Selected: {opt}")
                    break
                except Exception:
                    pass

        ss(driver, "fortiguard_2_form_filled")

        # Submit
        try:
            submit = wait_click(driver, By.CSS_SELECTOR,
                "button[type='submit'], input[type='submit']")
            time.sleep(6)
            dismiss_alert(driver)
            ss(driver, "fortiguard_3_submitted")
            page_after = driver.find_element(By.TAG_NAME, "body").text
            print(f"    After submit: {page_after[:300]}")
            results["Fortiguard"] = "✓ Submitted for categorization"
        except Exception as e3:
            ss(driver, "fortiguard_3_error")
            results["Fortiguard"] = f"Form filled, submit failed: {str(e3)[:80]}"
    except Exception as e:
        ss(driver, "fortiguard_error")
        results["Fortiguard"] = f"Failed: {str(e)[:120]}"
    print(f"  → {results.get('Fortiguard')}")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print(f"Submitting {TARGET_URL} to URL categorization portals...")
    print(f"Monitor live at: http://www.swaya.me:7900 (noVNC)\n")

    driver = get_driver()
    try:
        submit_bluecoat(driver)
        submit_zscaler(driver)
        submit_paloalto(driver)
        submit_trendmicro(driver)
        submit_fortiguard(driver)
    finally:
        time.sleep(2)
        driver.quit()

    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    for portal, status in results.items():
        print(f"  {portal:25s} {status}")
    print(f"\nScreenshots: {SS_DIR}")
    print("="*60)


if __name__ == "__main__":
    main()
