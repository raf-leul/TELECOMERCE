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

## Session 1 (continued) — Stage 2: Database

**What I did:**
Designed and applied 6 migrations to the live Supabase project via the
Supabase MCP tools (not manual SQL copy-paste): `profiles` (with an
auto-provisioning trigger on `auth.users` signup), `categories`, `products`,
`product_images`, `inventory`, then two follow-up migrations fixing real
findings from Supabase's own security/performance advisors.

**Decisions made (see DECISIONS.md for the full versions):**
- Used a simple `role` text-enum on `profiles` instead of full
  roles/permissions tables — full RBAC deferred to when Stage 3 actually
  needs it, per "don't build tables just for appearance."
- Deferred `inventory_movements` (audit trail) to Stage 6 for the same
  reason — only `inventory.quantity_available` exists for now.
- Prices are `integer` cents (`price_cents`), never float, and never
  writable by anon/authenticated clients.

**Verification performed (not claimed without evidence):**
- `list_tables(verbose=true)` confirmed all 5 tables exist with correct
  columns, PKs, FKs, and `rls_enabled: true`.
- Inserted real test/seed rows (one active product, one inactive "draft"
  product, one category, one inventory row), then actually switched to the
  `anon` Postgres role inside a rolled-back transaction — the same role
  PostgREST uses for unauthenticated REST calls — and confirmed:
  - anon SELECT on products returns only the active one (draft correctly
    hidden)
  - anon SELECT on categories/inventory succeeds
  - anon UPDATE on inventory affects 0 rows and the value is provably
    unchanged afterward
  - anon INSERT on products raises an explicit
    `42501 row-level security policy` error
  - anon SELECT on profiles returns 0 rows
- All test/seed data deleted afterward; tables verified back to 0 rows.
- Ran `get_advisors(type=security)` — found 2 real issues (mutable
  `search_path` on a trigger function; a `SECURITY DEFINER` function
  directly callable via PostgREST RPC by anon/authenticated). First fix
  attempt (revoking EXECUTE from the named roles) was verified insufficient
  — checked `information_schema.role_routine_grants` directly and found
  `PUBLIC` still held the grant, which anon/authenticated inherit. Fixed
  correctly by revoking from `PUBLIC`. Re-ran the advisor: 0 findings.
  Then verified the auth signup trigger still worked after the revoke by
  inserting directly into `auth.users` and confirming a `profiles` row was
  auto-created (triggers execute as the function owner, not the calling
  role, so the revoke doesn't break the trigger's own operation).
- Ran `get_advisors(type=performance)` — found `auth.uid()` being
  re-evaluated per-row in the profiles policy. Fixed by wrapping it in a
  scalar subquery. Re-ran: that finding cleared; one INFO-level "unused
  index" note remains, expected on a currently-empty freshly-created table,
  not actionable yet.

**Files changed:** `supabase/migrations/0001_profiles.sql` through
`0006_optimize_rls_initplan.sql`, `docs/DATABASE.md` (new), plus updates to
`docs/PROJECT_STATE.md` and `docs/NEXT_TASK.md`.

**Not yet done / explicitly not claimed:**
- No Supabase Storage buckets yet (needed for product images, Stage 4/25).
- No real auth/signup flow in the actual apps yet — Stage 3.
- No admin write path exists yet for products/categories — currently only
  reachable via the service role directly (by design, until RBAC exists).

**Next task:** see NEXT_TASK.md (Stage 3 — authentication + RBAC, initial slice).

## Session 1 (continued) — Stage 3: Authentication (initial slice)

**What I did:**
Checked current Supabase docs before writing any code (Rule 10) rather than
relying on training-data memory of a fast-moving library. Confirmed the
current recommended pattern is `@supabase/ssr` with `createBrowserClient`/
`createServerClient`, a `proxy.ts` file (Next.js 16's renamed
`middleware.ts`) using `updateSession()`, and `getClaims()` (not
`getSession()`) for gating access to pages/data.

Built:
- `apps/web/lib/supabase/{client,server,proxy}.ts` — the three Supabase
  client utilities per current docs.
- `apps/web/proxy.ts` — wires `updateSession` into Next's proxy convention.
- `apps/web/app/auth/actions.ts` — Server Actions for sign-up/sign-in/sign-out.
- `apps/web/app/{register,login,profile}/page.tsx` — the three pages,
  using React 19's `useActionState` (confirmed React 19 is what
  `create-next-app` installed, not the older `useFormState`).
- `apps/api/app/auth/security.py` — JWT verification against Supabase's
  JWKS endpoint (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`) via
  PyJWT's `PyJWKClient`, exposed as a FastAPI dependency.
- `apps/api/app/main.py` — added `/me`, a minimal endpoint to prove the
  verification dependency works.
- `apps/api/tests/test_auth.py` — 4 new tests.

**A real limitation found and documented, not glossed over:**
While trying to verify the signup flow end-to-end, direct testing (both
`curl` against the Supabase REST host and a Node script calling
`supabase.auth.signUp()`) showed this sandbox's network egress allowlist
does not include `*.supabase.co` — every attempt failed with "Host not in
allowlist" from the egress proxy, not an application error. This means the
Supabase MCP tools (which go through a separate, permitted channel) could
verify the Stage 2 database directly, but nothing in this session could
verify a real signup/login/session through the actual running apps against
real Supabase Auth.

**What WAS actually verified (not claimed without evidence):**
- `apps/web`: clean `npm run build` (with `proxy.ts` confirmed picked up
  via the "ƒ Proxy (Middleware)" build output line) and clean
  `npm run lint`. Booted the real dev server and curl-tested `/`, `/login`,
  `/register` (200) and unauthenticated `/profile` (307 → `/login` —
  this specific check doesn't need Supabase network access, since an
  absent cookie is decided locally).
- `apps/api`: 5/5 pytest passing in a fresh venv, including 4 new auth
  tests. The valid/expired-token tests sign real JWTs with a locally
  generated RSA keypair and monkeypatch the JWKS client so the actual
  cryptographic verification path is exercised, just against a test key.
  Booted the real uvicorn server and curl-tested `/health` (200) and `/me`
  without/with a garbage token (401/401). Clean `ruff check .`.

**What was explicitly NOT verified, and is called out as such rather than
assumed:** a real signup creating an `auth.users` + `profiles` row through
the app, a real login setting a working cookie, the profile page rendering
real data, and `/me` against a real Supabase-issued token. All deferred to
NEXT_TASK.md with instructions to verify from an environment with real
network access before Stage 3 is considered done.

**Files changed:** see PROJECT_STATE.md "What Is Complete" for the full
list; docs updated: `docs/DECISIONS.md` (4 new entries), `docs/PROJECT_STATE.md`,
`docs/NEXT_TASK.md`, this log.

**Next task:** see NEXT_TASK.md — real end-to-end verification of this
slice from a network-capable environment, then finish the rest of Stage 3
(password recovery, session refresh check, one RBAC-gated example) before
moving to Stage 4.
