# Technologies Used

Detected strictly from code evidence (imports, config, usage). No assumptions made.

---

## Backend

| Technology | Confidence | Evidence |
|---|---|---|
| **FastAPI** | HIGH | `backend/main.py` → `from fastapi import FastAPI`; route decorators throughout |
| **Python 3.10** | HIGH | venv path `.venv/lib/python3.10/` |
| **SQLAlchemy 2.x (async)** | HIGH | `requirements.txt` → `SQLAlchemy==2.0.23`; async engine patterns in `*_service_async.py` |
| **MySQL** | HIGH | `settings.py` → `mysql+pymysql://` and `mysql+asyncmy://` connection strings; port 3306 default |
| **asyncmy** | HIGH | `requirements.txt` → `asyncmy==0.2.11`; `settings.py` async URL uses `mysql+asyncmy://` |
| **PyMySQL** | HIGH | `requirements.txt` → `PyMySQL==1.1.0`; `settings.py` sync URL uses `mysql+pymysql://` |
| **Redis (async)** | HIGH | `shared/utils/redis_client.py` → `import redis.asyncio as aioredis`; connection pool setup |
| **Pydantic v2 + pydantic-settings** | HIGH | `requirements.txt` → `pydantic==2.5.0`; `settings.py` → `from pydantic_settings import BaseSettings` |
| **Alembic** | HIGH | `requirements.txt` → `alembic==1.12.1`; migration files in `persistence/migrations/versions/` |
| **PyJWT** | HIGH | `requirements.txt` → `PyJWT==2.8.0`; `core/security/jwt.py` → `import jwt` |
| **passlib + bcrypt** | HIGH | `core/security/password.py` → `from passlib.context import CryptContext`; `schemes=["bcrypt"]` |
| **uvicorn + uvloop** | HIGH | `requirements.txt` → `uvicorn==0.24.0`, `uvloop==0.22.1` |
| **APScheduler (AsyncIO)** | HIGH | `core/stats/scheduler.py` → `from apscheduler.schedulers.asyncio import AsyncIOScheduler` |
| **slowapi** (rate limiting) | HIGH | `requirements.txt` → `slowapi==0.1.9` |
| **python-socketio** | HIGH | `requirements.txt` → `python-socketio==5.16.1`; `.venv` contains `socketio/` package |
| **openpyxl** | HIGH | `features/quiz/import_service.py` → `import openpyxl` |
| **wordcloud + Pillow** | HIGH | `features/quiz/export_service.py` → `from wordcloud import WordCloud`; `pillow==12.1.1` |
| **reportlab** | HIGH | `requirements.txt` → `reportlab==4.2.5`; referenced in `export_service.py` |
| **python-docx** | HIGH | `requirements.txt` → `python-docx==1.1.2` |
| **python-pptx** | HIGH | `requirements.txt` → `python-pptx==1.0.2` |
| **Locust** | HIGH | `locustfile.py` → `from locust import HttpUser, task`; `requirements.txt` → `locust==2.43.3` |
| **pytest** | HIGH | `requirements.txt` → `pytest==9.0.2` |

---

## Frontend

| Technology | Confidence | Evidence |
|---|---|---|
| **React 18** | HIGH | `package.json` → `"react": "^18.2.0"`; `frontend/src/main.jsx` |
| **Vite 5** | HIGH | `package.json` → `"vite": "^5.0.0"`; `scripts.build: "vite build"` |
| **Ant Design 5** | HIGH | `package.json` → `"antd": "^5.11.0"` |
| **@ant-design/pro-components + pro-layout** | HIGH | `package.json` → `@ant-design/pro-components`, `@ant-design/pro-layout`; used in `App.jsx` |
| **Redux Toolkit** | HIGH | `package.json` → `@reduxjs/toolkit`, `react-redux` |
| **React Router v6** | HIGH | `package.json` → `"react-router-dom": "^6.20.0"` |
| **Axios** | HIGH | `frontend/src/services/api.js` → `import axios from 'axios'`; `axios.create({...})` |
| **react-i18next / i18next** | HIGH | `package.json` → `i18next`, `react-i18next`; 11 locale JSON files in `src/locales/` |
| **Tiptap (rich text editor)** | HIGH | `package.json` → `@tiptap/react`, `@tiptap/starter-kit` + 10 extension packages |
| **Recharts** | HIGH | `features/admin/Statistics.jsx` → `import { LineChart, BarChart, PieChart... } from 'recharts'` |
| **D3 + d3-cloud** | HIGH | `package.json` → `"d3": "^7.9.0"`, `"d3-cloud": "^1.2.8"` |
| **react-wordcloud** | HIGH | `features/audience/AudienceSession.jsx` → `import ReactWordcloud from 'react-wordcloud'` |
| **@mediapipe/tasks-vision** | HIGH | `features/proctoring/hooks/useFaceDetector.js` → `import('@mediapipe/tasks-vision')`; BlazeFace model |
| **qrcode.react** | HIGH | `package.json` → `"qrcode.react": "^4.2.0"` |
| **xlsx** | HIGH | `package.json` → `"xlsx": "^0.18.5"` |
| **Bootstrap 5** | HIGH | `package.json` → `"bootstrap": "^5.3.8"` |

---

## Infrastructure / Runtime

| Technology | Confidence | Evidence |
|---|---|---|
| **Nginx** | HIGH | `frontend/dist` served by Nginx; production host `www.swaya.me` |
| **Selenium + Chromium** | HIGH | Multiple `test_*_selenium.py` files; `selenium-arm` Docker container |
| **Docker** | HIGH | `sudo docker` usage for `seleniumarm` container in test scripts |
