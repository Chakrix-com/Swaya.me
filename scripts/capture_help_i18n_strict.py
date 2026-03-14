#!/usr/bin/env python3
import json, os, time, requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE='https://test.swaya.me'
API=f'{BASE}/api/v1'
ROOT=Path('/home/vinay/Swaya.me')
OUT=ROOT/'frontend/public/assets/help-screens'
MANIFEST_PATH=ROOT/'scripts/help_screenshot_manifest.json'
EMAIL='demo@swaya.me'; PASSWORD='Demo1234'

def load_home_h1():
    values = {}
    for lang in langs:
        p = ROOT / 'frontend' / 'src' / 'locales' / lang / 'translation.json'
        data = json.loads(p.read_text(encoding='utf-8'))
        values[lang] = data['home']['hero']['title']
    return values

with open(MANIFEST_PATH,encoding='utf-8') as f:
    m=json.load(f)
langs=m['languages']; themes=m['themes']; files=m['files']
HOME_H1=load_home_h1()

sess=requests.Session()
tok=sess.post(f'{API}/auth/login',json={'email':EMAIL,'password':PASSWORD},timeout=20).json().get('access_token')
H={'Authorization':f'Bearer {tok}'}
quiz_id=sess.get(f'{API}/quizzes',headers=H,timeout=20).json()[0]['id']


def ensure_session_and_join():
    sessions=sess.get(f'{API}/quizzes/{quiz_id}/sessions',headers=H,timeout=20).json()
    active=next((x for x in sessions if x.get('status') in ('CREATED','ACTIVE')),None) if isinstance(sessions,list) else None
    if not active:
        active=sess.post(f'{API}/quizzes/{quiz_id}/sessions',headers=H,timeout=20).json()
    join=active.get('join_code')
    if not join:
        detail=sess.get(f'{API}/quizzes/{quiz_id}',headers=H,timeout=20).json()
        join=detail.get('join_code')
    return join

def make_driver():
    o=webdriver.ChromeOptions(); o.add_argument('--no-sandbox'); o.add_argument('--disable-dev-shm-usage'); o.add_argument('--window-size=1440,900')
    return webdriver.Remote(command_executor='http://localhost:4444/wd/hub', options=o)

def force_font(driver):
    driver.execute_script("document.documentElement.style.fontFamily='Noto Sans, Noto Sans Devanagari, Noto Sans Tamil, Noto Sans Telugu, Noto Sans Kannada, Noto Sans Bengali, Noto Sans Gujarati, sans-serif'; if(document.body){document.body.style.fontFamily=document.documentElement.style.fontFamily;}")

def set_prefs(driver,lang,theme):
    driver.get(BASE)
    driver.execute_script("localStorage.setItem('preferredLanguage', arguments[0]); localStorage.setItem('visitor-theme-preference', arguments[1]);", lang, theme)

def assert_home_lang(driver,lang):
    WebDriverWait(driver,20).until(EC.presence_of_element_located((By.CSS_SELECTOR,'.hero-title')))
    txt=driver.find_element(By.CSS_SELECTOR,'.hero-title').text.strip()
    exp=HOME_H1[lang]
    if txt != exp:
        raise RuntimeError(f'Home language mismatch for {lang}: got={txt!r} expected={exp!r}')

def assert_theme_on_help(driver,theme):
    driver.get(BASE+'/help')
    WebDriverWait(driver,20).until(EC.presence_of_element_located((By.CSS_SELECTOR,'.visitor-theme')))
    cls=driver.find_element(By.CSS_SELECTOR,'.visitor-theme').get_attribute('class')
    expected=f'visitor-theme--{theme}'
    if expected not in cls:
        raise RuntimeError(f'Theme mismatch: expected {expected}, got {cls}')

def login_host(driver):
    wait=WebDriverWait(driver,20)
    driver.get(BASE+'/login')
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'input')))
    ins=[i for i in driver.find_elements(By.CSS_SELECTOR,'input') if i.is_displayed() and i.is_enabled()]
    ins[0].clear(); ins[0].send_keys(EMAIL)
    [i for i in ins if i.get_attribute('type')=='password'][0].send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR,"button[type='submit']").click()
    wait.until(EC.url_contains('/dashboard'))

def snap(driver,path):
    force_font(driver)
    time.sleep(1.1)
    driver.save_screenshot(str(path))

join_code=ensure_session_and_join()

for lang in langs:
    for theme in themes:
        print(f'capture {lang}/{theme}')
        outdir=OUT/lang/theme
        outdir.mkdir(parents=True,exist_ok=True)
        d=make_driver()
        try:
            set_prefs(d,lang,theme)
            d.get(BASE+'/')
            assert_home_lang(d,lang)
            assert_theme_on_help(d,theme)

            # public captures
            d.get(BASE+'/'); snap(d,outdir/'home.png')
            d.get(f'{BASE}/join/{join_code}')
            snap(d,outdir/'audience_join_with_code.png')
            snap(d,outdir/'audience_in_session_waiting.png')
            snap(d,outdir/'audience_answering_question.png')

            # host captures
            login_host(d)
            d.get(BASE+'/dashboard'); snap(d,outdir/'dashboard_buttons.png')
            d.get(f'{BASE}/quiz/{quiz_id}/edit'); snap(d,outdir/'quiz_builder.png')
            d.get(f'{BASE}/quiz/{quiz_id}/control'); snap(d,outdir/'quiz_session_joincode.png')
            d.get(f'{BASE}/quiz/{quiz_id}/control'); snap(d,outdir/'quiz_session_question_active.png')
            snap(d,outdir/'quiz_leaderboard_host.png')
            d.get(f'{BASE}/quiz/{quiz_id}/history'); snap(d,outdir/'quiz_history_page.png')
            snap(d,outdir/'quiz_history_results.png')
            try:
                for b in d.find_elements(By.XPATH,"//button[contains(., 'Export') or contains(., 'निर्यात') or contains(., 'ஏற்றுமதி') or contains(., 'ఎగుమతి') or contains(., 'ರಫ್ತು') or contains(., 'রপ্তানি') or contains(., 'નિકાસ')]"):
                    if b.is_displayed() and b.is_enabled():
                        b.click(); time.sleep(1); break
            except Exception:
                pass
            snap(d,outdir/'quiz_export_dropdown.png')

            # metadata for debugging
            meta={
              'language':lang,
              'theme':theme,
              'captured_at':time.time(),
              'quiz_id':quiz_id,
              'join_code':join_code
            }
            (outdir/'_meta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
            print(f'  ok {lang}/{theme}')
        finally:
            d.quit()

print('done')
