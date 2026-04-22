#!/usr/bin/env python3
"""
AI Features Regression Test
Tests: GET /ai/models → POST /ai/generate/questions →
       POST /ai/generate/options → POST /ai/generate/poll-prompt →
       POST /ai/rewrite
Note: These tests require the ollama daemon to be running.
If ollama is unreachable (503), the test will skip rather than fail
to avoid blocking CI in environments without local LLMs.
"""
import os
import sys
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1").rstrip("/")
ADMIN_EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
ADMIN_PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")
HOST_HEADER = os.getenv("HOST_HEADER")


def log(msg: str, level="INFO"):
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "ERROR": "\033[91m", "SKIP": "\033[93m"}
    print(f"{colors.get(level, '')}[{level}] {msg}\033[0m")


def api_request(session, method, url, **kwargs):
    if HOST_HEADER:
        headers = kwargs.get("headers", {})
        headers["Host"] = HOST_HEADER
        kwargs["headers"] = headers
    return session.request(method, url, **kwargs)


def main():
    s = requests.Session()
    s.verify = False

    # Login
    r = api_request(s, "POST", f"{BASE_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    if r.status_code != 200:
        log(f"Login failed: {r.status_code}", "ERROR")
        sys.exit(1)
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    log("Logged in as admin", "SUCCESS")

    # 1. GET /ai/models
    r = api_request(s, "GET", f"{BASE_URL}/ai/models", timeout=20)
    if r.status_code == 503:
        log("Ollama service unavailable (503) — skipping AI regression", "SKIP")
        sys.exit(0)
    
    if r.status_code != 200:
        log(f"GET /ai/models failed: {r.status_code}", "ERROR")
        sys.exit(1)
    
    models_data = r.json()
    log(f"Available models: {models_data.get('models')}", "SUCCESS")
    default_model = models_data.get("default_model")

    # 2. POST /ai/generate/questions
    log("Testing /ai/generate/questions...")
    r = api_request(s, "POST", f"{BASE_URL}/ai/generate/questions", json={
        "topic": "Python Programming",
        "count": 2,
        "language": "en"
    }, timeout=300) # Generous timeout for LLM
    
    if r.status_code == 200:
        data = r.json()
        qs = data.get("questions", [])
        if len(qs) == 2:
            log(f"Generated 2 questions: {qs[0]['text'][:50]}...", "SUCCESS")
        else:
            log(f"Expected 2 questions, got {len(qs)}", "ERROR")
            sys.exit(1)
    elif r.status_code == 503:
        log("Ollama timed out or unavailable during generation", "SKIP")
    else:
        log(f"API failed: {r.status_code} {r.text}", "ERROR")
        sys.exit(1)

    # 3. POST /ai/generate/options (distractors)
    log("Testing /ai/generate/options...")
    r = api_request(s, "POST", f"{BASE_URL}/ai/generate/options", json={
        "question": "What is the capital of France?",
        "correct_answer": "Paris",
        "count": 3
    }, timeout=60)
    
    if r.status_code == 200:
        distractors = r.json().get("distractors", [])
        if len(distractors) == 3:
            log(f"Generated 3 distractors: {distractors}", "SUCCESS")
        else:
            log(f"Expected 3 distractors, got {len(distractors)}", "ERROR")
            sys.exit(1)
    elif r.status_code == 503:
        log("Ollama timed out or unavailable during generation", "SKIP")
    else:
        log(f"API failed: {r.status_code} {r.text}", "ERROR")
        sys.exit(1)

    # 4. POST /ai/generate/poll-prompt
    log("Testing /ai/generate/poll-prompt...")
    r = api_request(s, "POST", f"{BASE_URL}/ai/generate/poll-prompt", json={
        "topic": "Climate Change",
        "language": "en"
    }, timeout=60)
    
    if r.status_code == 200:
        prompt = r.json().get("prompt")
        log(f"Generated poll prompt: {prompt}", "SUCCESS")
    elif r.status_code == 503:
        log("Ollama timed out or unavailable during generation", "SKIP")
    else:
        log(f"API failed: {r.status_code} {r.text}", "ERROR")
        sys.exit(1)

    # 5. POST /ai/rewrite
    log("Testing /ai/rewrite...")
    r = api_request(s, "POST", f"{BASE_URL}/ai/rewrite", json={
        "text": "What is the capital city of India?",
        "context": "quiz question"
    }, timeout=30)
    
    if r.status_code == 200:
        rewritten = r.json().get("rewritten")
        log(f"Rewritten text: {rewritten}", "SUCCESS")
    elif r.status_code == 503:
        log("Ollama timed out or unavailable during generation", "SKIP")
    else:
        log(f"API failed: {r.status_code} {r.text}", "ERROR")
        sys.exit(1)


    log("AI Features Regression Passed (or skipped due to unavailable LLM)", "SUCCESS")


if __name__ == "__main__":
    main()
