"""
One-shot Selenium watcher: opens a real code-server workspace URL (already
provisioned + extension manually installed), screenshots the status bar
repeatedly to observe the swaya-submit-timer extension's live behavior —
cold-load visibility, countdown ticking, and (if the budget is short enough)
the auto-submit-at-zero transition.

Usage: python3 selenium_submit_ext_live_watch.py <workspace_url> <out_dir> [n_shots] [interval_s]
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
n_shots = int(sys.argv[3]) if len(sys.argv) > 3 else 6
interval_s = float(sys.argv[4]) if len(sys.argv) > 4 else 20

options = webdriver.ChromeOptions()
options.add_argument('--window-size=1600,1000')
driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
try:
    driver.get(url)
    print('Loaded, waiting for workbench...')
    try:
        WebDriverWait(driver, 90).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'monaco-workbench'))
        )
    except Exception as e:
        print(f'workbench wait failed (may still be loading): {e}')

    for i in range(n_shots):
        time.sleep(1)  # let render settle
        path = f'{out_dir}/watch_{i:02d}.png'
        driver.save_screenshot(path)
        print(f'[{time.strftime("%H:%M:%S")}] shot {i}: {path}')
        if i < n_shots - 1:
            time.sleep(interval_s)
finally:
    driver.quit()
