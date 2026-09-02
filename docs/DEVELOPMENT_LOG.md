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

**Not yet done / explicitly not claimed:**
- CI workflow has not actually been run on GitHub Actions yet — only the
  underlying commands (`npm run build`, `npm run lint`, `pytest`,
  `ruff check`) were verified locally. Will confirm the Actions run itself
  after pushing.
- No database schema/migrations yet (Stage 2).
- No Vercel project linked/deployed yet.
- No auth, RBAC, or any business logic implemented yet.

**Next task:** see NEXT_TASK.md (Stage 2 — database schema).
