"""
Live interaction test for the swaya-submit-timer extension's MANUAL submit
path: click the "Submit Solution" status bar item -> confirm the modal
appears -> click Cancel -> confirm nothing changed -> click again -> click
Submit -> confirm it actually submits.

Usage: python3 selenium_submit_ext_manual_click.py <workspace_url> <out_dir>
"""
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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
    # The status bar item's accessible name is its tooltip text ("Submit your
    # solution now") set in extension.ts — search broadly by visible text
    # "Submit Solution" inside the status bar region instead of guessing at
    # VS Code's internal class names.
    return WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(@class,'statusbar')]//*[contains(text(),'Submit Solution')]")
        )
    )


try:
    driver.get(url)
    print('Loaded, waiting for workbench + extension activation...')
    WebDriverWait(driver, 90).until(EC.presence_of_element_located((By.CLASS_NAME, 'monaco-workbench')))

    submit_el = find_submit_item()
    shot('01_before_click')
    print('Found Submit Solution status bar item, clicking...')
    submit_el.click()
    time.sleep(1)
    shot('02_after_click_expect_modal')

    # Try to find a Cancel affordance inside whatever dialog appeared.
    try:
        cancel_el = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[self::a or self::button or contains(@class,'button')][contains(., 'Cancel')]")
            )
        )
        print('Found Cancel button, clicking...')
        cancel_el.click()
    except TimeoutException:
        print('No explicit Cancel button found — pressing Escape instead.')
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    time.sleep(1)
    shot('03_after_cancel_expect_unchanged')

    # Click Submit again, this time confirm.
    submit_el = find_submit_item()
    submit_el.click()
    time.sleep(1)
    shot('04_second_click_expect_modal')

    submit_confirm_el = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//*[self::a or self::button or contains(@class,'button')][normalize-space(text())='Submit']")
        )
    )
    print('Found Submit (confirm) button, clicking...')
    submit_confirm_el.click()

    time.sleep(2)
    shot('05_after_confirm_expect_submitted')

finally:
    driver.quit()
