#!/usr/bin/env python3
"""
Folders & Templates Lifecycle Test
Tests: list folders, create folder, rename folder, assign quiz, delete folder
       list templates, list template-library, use template
Runs as REGULAR_USER_EMAIL (role=user, tier=FREE).
"""
import os
import sys
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1").rstrip("/")
EMAIL = os.getenv("REGULAR_USER_EMAIL", "regression-free@swaya.me")
PASSWORD = os.getenv("REGULAR_USER_PASSWORD", "RegTest2026!")


def fail(msg: str):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check(cond: bool, msg: str):
    if not cond:
        fail(msg)


def main():
    s = requests.Session()
    s.verify = False

    r = s.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    check(r.status_code == 200, f"login failed: {r.status_code}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    print("OK: login")

    # Create a quiz to use in folder tests
    r = s.post(f"{BASE_URL}/quizzes/", json={"title": "FolderTest Quiz"}, timeout=20)
    check(r.status_code in (200, 201), f"create quiz failed: {r.status_code} {r.text[:200]}")
    quiz_id = r.json()["id"]
    print(f"OK: created quiz  id={quiz_id}")

    # --- FOLDERS ---

    # List folders (may be empty)
    r = s.get(f"{BASE_URL}/quizzes/folders", timeout=20)
    check(r.status_code == 200, f"list folders failed: {r.status_code}")
    initial_count = len(r.json())
    print(f"OK: list folders  count={initial_count}")

    # Create folder
    r = s.post(f"{BASE_URL}/quizzes/folders", json={"name": "RegTest Folder"}, timeout=20)
    check(r.status_code in (200, 201), f"create folder failed: {r.status_code} {r.text[:200]}")
    folder_id = r.json()["id"]
    print(f"OK: create folder  id={folder_id}")

    # Rename folder
    r = s.put(f"{BASE_URL}/quizzes/folders/{folder_id}", json={"name": "RegTest Folder Renamed"}, timeout=20)
    check(r.status_code == 200, f"rename folder failed: {r.status_code} {r.text[:200]}")
    check(r.json()["name"] == "RegTest Folder Renamed", "folder name not updated")
    print("OK: rename folder")

    # Assign quiz to folder
    r = s.put(f"{BASE_URL}/quizzes/{quiz_id}/folder", json={"folder_id": folder_id}, timeout=20)
    check(r.status_code == 200, f"assign quiz to folder failed: {r.status_code} {r.text[:200]}")
    print("OK: assign quiz to folder")

    # Remove quiz from folder (assign folder_id=null)
    r = s.put(f"{BASE_URL}/quizzes/{quiz_id}/folder", json={"folder_id": None}, timeout=20)
    check(r.status_code == 200, f"remove quiz from folder failed: {r.status_code} {r.text[:200]}")
    print("OK: remove quiz from folder")

    # Delete folder
    r = s.delete(f"{BASE_URL}/quizzes/folders/{folder_id}", timeout=20)
    check(r.status_code in (200, 204), f"delete folder failed: {r.status_code} {r.text[:200]}")
    print("OK: delete folder")

    # --- TEMPLATES ---

    # List templates
    r = s.get(f"{BASE_URL}/quizzes/templates", timeout=20)
    check(r.status_code == 200, f"list templates failed: {r.status_code}")
    templates = r.json()
    print(f"OK: list templates  count={len(templates)}")

    # List template-library (same endpoint, stable path)
    r = s.get(f"{BASE_URL}/quizzes/template-library", timeout=20)
    check(r.status_code == 200, f"list template-library failed: {r.status_code}")
    print(f"OK: list template-library  count={len(r.json())}")

    # Use a template if any available
    if templates:
        tmpl_id = templates[0]["id"]
        r = s.post(f"{BASE_URL}/quizzes/template-library/{tmpl_id}/use", timeout=20)
        check(r.status_code in (200, 201), f"use template failed: {r.status_code} {r.text[:200]}")
        new_quiz_id = r.json()["id"]
        print(f"OK: use template  new_quiz_id={new_quiz_id}")
        # Cleanup new quiz
        s.delete(f"{BASE_URL}/quizzes/{new_quiz_id}", timeout=20)
    else:
        print("SKIP: no templates available for use-template test")

    # Cleanup original quiz
    s.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)

    print("\nOK: folders_templates — all steps passed")


if __name__ == "__main__":
    main()
