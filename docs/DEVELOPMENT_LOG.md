# DEVELOPMENT_LOG.md

## Session 1 — 2026-09-02

**Tool setup:**
- Inspected GitHub repo `raf-leul/TELECOMERCE` — found essentially empty
  (placeholder README, 1 commit).
- Inspected Supabase — two unrelated existing projects found. Created new
  project `telecommerce` (ref `hmsjerjguhxhwoubqdqm`, us-east-1, free tier,
  confirmed $0/month before creating).
- Inspected Vercel — team "raf's projects" (hobby plan) available, no
  projects linked yet.
- GitHub push initially failed (403) with a fine-grained PAT despite the API
  reporting push access; resolved with a classic PAT (`repo` scope). See
  DECISIONS.md.

**Stage 1 — Foundation scaffold:**
- Created `apps/api`: FastAPI skeleton (`app/main.py`, `app/core/config.py`),
  `GET /health` endpoint, pytest test for it, `requirements/base.txt` and
  `requirements/dev.txt`.
  - Verified: `pytest` passes (1/1), server boots via uvicorn and
    `curl /health` returns `{"status":"ok"}`, `ruff check .` passes clean.
- Created `apps/web`: Next.js 16 (App Router) + TypeScript + Tailwind CSS 4
  via `create-next-app`. Replaced placeholder home page with a TeleCommerce
  placeholder. Removed the default `next/font/google` usage (build failed in
  this sandbox because fonts.googleapis.com isn't reachable here — see
  DECISIONS.md).
  - Verified: `npm run build` succeeds, `npm run lint` passes clean.
- Added root `.gitignore`, `.env.example` (with real, safe Supabase project
  URL, placeholder for the key — no secrets), root `package.json` (npm
  workspaces), and `.github/workflows/ci.yml` (web lint+build, api lint+test
  jobs).
- Created `docs/PROJECT_STATE.md`, `docs/NEXT_TASK.md`, `docs/ARCHITECTURE.md`,
  `docs/DECISIONS.md`, this log.

**CI verification (same session, continued):**
- First push of `.github/workflows/ci.yml` was rejected — the classic PAT
  had `repo` scope only, not `workflow`. Regenerated token with both scopes.
- First actual CI run failed both jobs. Did not assume the fix — pulled job
  step statuses via the GitHub API, then reproduced each failure locally:
  - Web job: `npm ci` failed. Root cause: root `package.json` declares
    `apps/web` as an npm workspace, so npm operations run from within
    `apps/web` now expect the lockfile at repo root, which didn't exist.
    Fix: `npm install` from repo root to generate the root lockfile, removed
    the stale one in `apps/web`, changed CI to run `npm ci` from root and
    use `npm run web:lint` / `npm run web:build`.
  - API job: `pytest` failed with `ModuleNotFoundError: No module named 'app'`
    when run in a genuinely fresh venv (my first local pytest run had
    passed only because of leftover interpreter/env state — a lesson in why
    Rule 6 requires real verification, not just "it worked once"). Fix:
    added `apps/api/pytest.ini` with `pythonpath = .`.
- Re-pushed, polled the new Actions run to completion via API: **status
  completed, conclusion success** (run id 33598029310). This is the actual
  verification evidence for the "CI passes" claim in PROJECT_STATE.md.

**Not yet done / explicitly not claimed:**
- No database schema/migrations yet (Stage 2).
- No Vercel project linked/deployed yet.
- No auth, RBAC, or any business logic implemented yet.

**Next task:** see NEXT_TASK.md (Stage 2 — database schema).
