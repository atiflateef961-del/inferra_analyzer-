# Inferra AI

Inferra AI is a production-oriented AI business document intelligence SaaS built with a Next.js frontend and a FastAPI backend.

## Stack

- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI + Pydantic + Python
- AI: Groq-ready service layer
- Data: Python analytics engine with structured processing workflows
- Infra: Firebase-ready architecture, environment-driven configuration

## Project layout

- `frontend/` — Next.js application
- `backend/` — FastAPI service and Python analytics foundation
- `.env.example` — environment variable template

## Run locally

Install dependencies first, then start the frontend. It asks whether you want Local or Network mode and starts the backend automatically when needed.

Use Python 3.12 for the backend virtual environment on Windows. Do not paste the surrounding Markdown backticks into PowerShell commands.

### Frontend

```powershell
# From the repository root
npm install
npm run dev
```

The frontend-only equivalent is `Set-Location frontend` followed by `npm install` and `npm run dev`.

Choose `1` for `http://localhost:3000` or `2` for the displayed LAN URL, such as `http://192.168.1.47:3000`. The backend started automatically by either frontend mode listens on both localhost and LAN addresses.

### Backend

Run these commands in sequence when starting FastAPI manually:

```powershell
Set-Location "D:\Inferra AI\backend"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\backend\scripts\dev.cmd Network
```

Keep that terminal running. Then open a second PowerShell terminal and start the frontend:

```powershell
Set-Location "D:\Inferra AI\frontend"
npm install
npm run dev
```

Choose `2`. The browser opens the displayed Network URL automatically; no link click is required. The frontend launcher also starts FastAPI automatically when port 8000 is unavailable, so the manual backend sequence is only needed when you want to run FastAPI separately.

To start FastAPI directly instead of using the launcher:

```powershell
Set-Location backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Use `..\backend\scripts\dev.cmd Network` if you want the LAN label explicitly. Both modes bind the backend to localhost and LAN addresses. Open `http://localhost:8000` locally or use the displayed LAN URL, such as `http://192.168.1.47:8000`, on another device. Never open `http://0.0.0.0:8000`; `0.0.0.0` is only a server bind address, not a browser address.

The frontend automatically proxies `/api/*` to the selected backend address, so no `NEXT_PUBLIC_API_URL` change is required for Local or Network development.

Run backend tests from the repository root:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
```

The health endpoint is available at `http://localhost:8000/api/health`.

## Verification status

- Frontend build: verified with `npm run build`
- Backend tests: verified with `7 passed`
- Backend health API: verified with `GET /api/health`
