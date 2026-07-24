# giffgaff eSIM QR Tool

Lightweight production-oriented MVP for fetching existing giffgaff downloadable eSIM QR codes.

Stack:

- Frontend: Vue 3 + Vite + Pinia + Tailwind CSS
- Backend: FastAPI + httpx + Redis
- Session: short-lived Redis sessions

The first version logs in with a giffgaff account and only fetches existing `DOWNLOADABLE` eSIMs. It does not reserve eSIMs, swap SIMs, or activate new SIMs.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Redis must be available at `redis://localhost:6379/0`.

## Current Dev URLs

When started locally:

- Frontend: http://127.0.0.1:5174
- Backend health: http://127.0.0.1:8000/api/health
- Backend docs: http://127.0.0.1:8000/api/docs

Use `127.0.0.1` instead of `localhost` if another local service captures the IPv6 localhost route.

## Implemented MVP Flow

1. Log in with giffgaff account/password.
2. If giffgaff requires login MFA, enter the email/SMS code.
3. Backend stores only a short-lived Redis session ID for the frontend.
4. User fetches existing `DOWNLOADABLE` eSIMs.
5. If one eSIM exists, the backend fetches LPA automatically.
6. If multiple eSIMs exist, the frontend asks the user to choose one.
7. The frontend renders the QR code from the returned LPA string.
8. If giffgaff requires API MFA, the fallback MFA card appears.

Note: giffgaff may occasionally block server-side account/password login with its WAF. In that case the API returns `GIFFGAFF_WAF_BLOCKED`; the next recommended architecture is browser/OAuth login.

Not implemented by design:

- `reserveESim`
- `swapSim`
- OAuth login
- persistent user accounts
