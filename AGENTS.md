# Configuration & Smart Execution Loops for Devin

## System Boundaries & Token Minimization
To minimize token consumption and keep context windows highly dense:
- NEVER scan, search, or read files inside: `node_modules/`, `.expo/`, `dist/`, or `pos-backend/venv/`.
- Only modify backend files inside `pos-backend/app/` and frontend files inside `duka-ledger/`.
- Do not add external Python or npm dependencies without absolute necessity and explicit permission.

## Tech Stack Target Blueprint
- **Frontend:** React Native via Expo (JavaScript). Focuses on mobile POS layouts and client-side sync.
- **Backend:** FastAPI (Python), SQLAlchemy ORM, Pydantic, PostgreSQL/SQLite (`pos_dev.db`).

---

## Autonomous Verification & Self-Correction Loops

Whenever a task involving a feature, API route, or UI screen is assigned, you must independently run through these verification loops. If a check fails, parse the error, apply a fix, and reset the specific loop until it passes clean.

### Loop 1: Backend API Integrity Loop
Run this loop when any backend code, schema, or model is touched:
1. **Lint/Format Check:** From `pos-backend/`, run `python -m ruff check .` or `flake8` if available. Fix code issues.
2. **Schema & Typo Validation:** Compile the app headless to catch Python syntax or Pydantic validation errors by running:
   ```bash
   cd pos-backend && python -c "import app.main"


Database Consistency: Ensure changes match pos-backend/app/models.py.

Loop 2: Expo Mobile Frontend Build Loop
Run this loop when any UI components, screens, or configurations are updated:

Linter Validation: Run npm run lint or npx eslint . inside duka-ledger/ to catch missing imports or syntax issues early.

Offline-First Sync Integrity: If changing sync.js or data persistence layers, explicitly check that API calls safely fallback when the backend is unreachable.

Loop 3: Full Stack Integration Loop
Run this loop when a feature requires the mobile application to talk to the FastAPI backend:

Pre-flight Endpoint Validation: Use curl or a lightweight inline Python script to hit the specific modified endpoint (e.g., GET /items) to confirm the backend responds with a valid 200 OK and a correctly structured JSON schema before trying to wire up the React Native frontend code.