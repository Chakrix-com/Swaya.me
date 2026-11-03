"""
Retry of the manual Submit/Cancel/Confirm click test with precise button
selectors (found by inspecting the dialog's real DOM the first time around —
VS Code's dialog buttons are `.monaco-button` elements, not their wrapper).
"""
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

WEBDRIVER_URL = 'http://localhost:4444'
url = sys.argv[1]
out_dir = sys.argv[2]

options = webdriver.ChromeOptions()
options.add_argument('--window-size=1600,1000')
driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)


def shot(name):
    path = f'{out_dir}/{name}.png'
    driver.save_screenshot(path)
    print(f'[{time.strftime("%H:%M:%S")}] {name}: {path}')


def find_submit_item():
    return WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(@class,'statusbar')]//*[contains(text(),'Submit Solution')]")
        )
    )


try:
    driver.get(url)
    print('Loaded, waiting for workbench...')
    WebDriverWait(driver, 90).until(EC.presence_of_element_located((By.CLASS_NAME, 'monaco-workbench')))

    submit_el = find_submit_item()
    submit_el.click()
    time.sleep(1)
    shot('01_modal_open')

    dialog = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '.monaco-dialog-box'))
    )
    print('--- dialog outerHTML (buttons area) ---')
    buttons_html = driver.execute_script(
        "var el = arguments[0].querySelector('.dialog-buttons-row') || arguments[0].querySelector('.dialog-buttons');"
        "return el ? el.outerHTML : 'NOT FOUND: ' + arguments[0].outerHTML.slice(0,2000);",
        dialog,
    )
    print(buttons_html)

    cancel_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, '.monaco-dialog-box .monaco-button'))
    )
    all_buttons = driver.find_elements(By.CSS_SELECTOR, '.monaco-dialog-box .monaco-button')
    print(f'Found {len(all_buttons)} .monaco-button elements: {[b.text for b in all_buttons]}')
    cancel_candidates = [b for b in all_buttons if b.text.strip().lower() == 'cancel']
    if not cancel_candidates:
        print('No button with exact text Cancel — dumping all button texts above, aborting this run.')
        shot('02_no_cancel_found')
        sys.exit(1)
    cancel_candidates[0].click()
    time.sleep(1)
    shot('02_after_real_cancel_click')

    # Confirm dialog is gone
    dialogs_left = driver.find_elements(By.CSS_SELECTOR, '.monaco-dialog-box')
    visible_dialogs = [d for d in dialogs_left if d.is_displayed()]
    print(f'Dialogs still visible after Cancel: {len(visible_dialogs)}')

    # Re-open and this time confirm Submit
    submit_el = find_submit_item()
    submit_el.click()
    time.sleep(1)
    shot('03_reopened_modal')

    all_buttons = driver.find_elements(By.CSS_SELECTOR, '.monaco-dialog-box .monaco-button')
    submit_candidates = [b for b in all_buttons if b.text.strip().lower() == 'submit']
    print(f'Found {len(submit_candidates)} Submit buttons out of {len(all_buttons)}: {[b.text for b in all_buttons]}')
    if submit_candidates:
        submit_candidates[0].click()
        time.sleep(2)
        shot('04_after_confirmed_submit')
    else:
        print('No Submit button found — cannot complete confirm-path test.')

finally:
    driver.quit()
