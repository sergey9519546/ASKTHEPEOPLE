# Copilot Workspace Instructions for ASKTHEPEOPLE

## Purpose
This file provides essential guidance for AI coding agents (like GitHub Copilot) working in the ASKTHEPEOPLE repository. It summarizes project conventions, architecture, and anti-patterns, and links to deeper documentation. 

---

## Key Principles
- **Link, don't embed:** Reference detailed docs (see below) instead of duplicating content.
- **Respect boundaries:** Frontend (Vue/Vite) and backend (Flask/Python) are separate; changes should be scoped accordingly.
- **Preserve valuable comments and docstrings.**
- **Follow code style:** Python uses `black`; JS uses Prettier defaults.

---

## Project Structure
- **Frontend:** `frontend/` (Vue 3, Vite, API in `src/api/`, main entry `src/main.js`)
- **Backend:** `backend/` (Flask app, entry `run.py`, API in `app/api/`, services in `app/services/`)
- **Docs:** `docs/` (plans, specs, hardening, etc.)

---

## Build & Test
- **Frontend:**
  - Install: `cd frontend && npm install`
  - Dev: `npm run dev`
  - Build: `npm run build`
- **Backend:**
  - Install: `cd backend && pip install -r requirements.txt`
  - Run: `python run.py` or use Docker
  - Tests: `pytest` in `backend/tests/`
- **Docker:**
  - `docker-compose up` (runs both frontend and backend)

---

## Documentation Links
- [README.md](../README.md): Deep-dive intro, architecture, usage
- [docs/plans/2026-03-23-hardening-plan.md](../docs/plans/2026-03-23-hardening-plan.md): Backend hardening, rate limiting, timeouts
- [docs/superpowers/specs/2026-03-24-production-crash-remediation-design.md](../docs/superpowers/specs/2026-03-24-production-crash-remediation-design.md): Frontend crash fixes, error handling

---

## Anti-Patterns
- Do **not** duplicate doc content—link to docs above.
- Do **not** mix frontend/backend logic.
- Do **not** use OS-specific code (e.g., `signal.alarm()`—see hardening plan).
- Do **not** add multiple API interceptors (see crash remediation spec).

---

## Example Prompts
- "Add a global error handler to the Vue frontend (see crash remediation spec)."
- "Implement report generation timeout in backend (see hardening plan)."
- "Where is the main simulation entry point?"

---

## Next Steps
- For area-specific rules, create `frontend/.copilot-instructions.md` or `backend/.copilot-instructions.md` as needed.
- Consider agent customizations for test generation, doc linking, or API contract enforcement.
