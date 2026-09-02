# PROJECT_STATE.md

Last updated: 2026-09-02 (session 1)

## Current Stage
STAGE 1 — FOUNDATION (complete, verified green in CI)

## Current Milestone
Tool setup complete. Web + API skeletons scaffolded, built, tested, linted
locally AND verified passing in GitHub Actions CI (run id 33598029310,
conclusion: success).

## What Is Complete
- GitHub repo verified: https://github.com/raf-leul/TELECOMERCE (push access confirmed,
  classic PAT with `repo` + `workflow` scopes)
- Supabase project created: `telecommerce`
  - project ref: `hmsjerjguhxhwoubqdqm`
  - region: us-east-1
  - URL: https://hmsjerjguhxhwoubqdqm.supabase.co
  - status: ACTIVE_HEALTHY, empty (no tables yet)
- Vercel: connected, team "raf's projects" (slug `rafs-projects-9996bc62`, hobby plan). No project linked yet.
- Top-level repo folder structure created (apps/web, apps/api, apps/bot, packages/, supabase/, docs/, .github/workflows/)
- `apps/api`: FastAPI skeleton with `GET /health`, passing pytest test, clean ruff lint.
- `apps/web`: Next.js 16 (App Router) + TypeScript + Tailwind 4, placeholder home page,
  clean build, clean eslint.
- Root npm workspace config (`package.json` + root `package-lock.json`) wiring `apps/web`.
- `.gitignore`, `.env.example` (safe placeholders + real Supabase URL, no secrets).
- `.github/workflows/ci.yml`: web (lint+build) and api (lint+test) jobs.
  **Verified actually green on GitHub Actions**, not just locally
  (run id 33598029310, https://github.com/raf-leul/TELECOMERCE/actions).
- `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/DEVELOPMENT_LOG.md` created.

## What Is Partially Complete
Nothing partially complete right now — Stage 1 scope is finished and verified.

## What Was Last Changed
Fixed two real CI failures found only by actually running the pipeline
(not assumed): (1) npm workspace + subdirectory lockfile mismatch causing
`npm ci` to fail, (2) pytest module import path issue causing test collection
to fail in a clean environment. Both fixed and re-verified green.

## Latest Commit
eff9511 (fix: correct CI failures (workspace lockfile location, pytest import path)) — pushed to origin/main

## Current Branch
main

## What Was Tested
- GitHub push/pull verified working with classic PAT (session-scoped, not stored)
- Supabase project creation and API URL/publishable key retrieval verified via Supabase MCP tools
- Vercel team listing verified via Vercel MCP tools
- `apps/web`: `npm run build` and `npm run lint` both pass (verified twice: once
  standalone, once from repo root as a workspace)
- `apps/api`: `pytest` (1/1 pass) and `ruff check .` both pass, verified in a
  completely fresh venv matching CI conditions
- GitHub Actions CI pipeline itself run and confirmed green (not just local
  command success) — run id 33598029310

## What Failed (and was fixed)
- First two GitHub tokens (fine-grained PATs) could authenticate to the REST API but
  were rejected by git's smart-HTTP push (403 Permission denied), despite the API
  reporting push:true. Fixed by switching to a classic PAT with `repo` scope.
- A classic PAT with only `repo` scope was rejected specifically when pushing
  `.github/workflows/ci.yml` (needs `workflow` scope too). Fixed by regenerating
  the token with `workflow` added.
- First CI run failed both jobs:
  - web job: `npm ci` failed because the root `package.json` made `apps/web` an
    npm workspace member, so npm looked for a root-level lockfile instead of
    the one inside `apps/web`. Fixed by generating the root lockfile and
    removing the now-redundant one in `apps/web`, and updating CI to run from
    repo root with the `web:build`/`web:lint` workspace scripts.
  - api job: `pytest` failed with `ModuleNotFoundError: No module named 'app'`
    in a clean venv (had passed locally only due to leftover environment
    state). Fixed by adding `apps/api/pytest.ini` with `pythonpath = .`.

## Known Bugs
None yet — no application code exists.

## What Must Happen Next
See NEXT_TASK.md. Short version: scaffold apps/web (Next.js/TS/Tailwind), apps/api
(FastAPI), root configs (.env.example, package.json workspaces, linting), and a
minimal CI workflow. Then commit + push as the Stage 1 checkpoint.

## Migration / Deployment State
- No database migrations exist yet.
- No Vercel project linked/deployed yet.
- No Supabase Auth/Storage/RLS configured yet.

## Environment Variable Notes
Supabase project credentials obtained this session (safe, publishable-only):
- NEXT_PUBLIC_SUPABASE_URL=https://hmsjerjguhxhwoubqdqm.supabase.co
- NEXT_PUBLIC_SUPABASE_ANON_KEY / publishable key retrieved via Supabase MCP
  (not committed to git; will go in .env.local only, referenced as placeholder
  in .env.example)
- No service-role key has been requested or stored anywhere.
- No Telegram bot token exists yet.
- No payment provider secrets exist yet.

## Exact Next Recommended Action
Begin STAGE 2 — DATABASE: design the initial Supabase schema (users/profiles,
roles/permissions, categories, products, product_images, inventory), write it
as SQL migrations under `supabase/migrations/`, apply via Supabase MCP tools,
verify with `list_tables`, enable RLS with least-privilege policies, and
commit the migration files. See NEXT_TASK.md for the precise breakdown.
