# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 3 — AUTHENTICATION + RBAC (initial slice).

Scope this into a first working slice rather than all of Stage 3 at once:

1. `apps/web`: install `@supabase/supabase-js` (and `@supabase/ssr` if using
   Next.js App Router server components/cookies properly — check current
   docs, don't assume API shape from memory per master instructions rule 10).
   Add `/register` and `/login` pages with real Supabase Auth email/password
   sign-up and sign-in. Add a `/profile` page that is only reachable when
   signed in (redirect to `/login` otherwise) and displays the user's
   `profiles` row (display_name, role) fetched with the user's own session
   (relying on the `profiles_select_own` RLS policy from Stage 2 — this is
   the first real usage of that policy).
2. `apps/api`: add a dependency/middleware that verifies the Supabase JWT
   from the `Authorization` header on protected routes, and exposes the
   authenticated user's id/role to route handlers. No protected routes exist
   yet to use it on — this stage just builds and unit-tests the verification
   dependency itself (e.g. against a `/me` endpoint that echoes back the
   verified user id and role).
3. Do NOT build the full RBAC permissions-table system yet — the `profiles.role`
   enum from Stage 2 is sufficient for now. Document in DECISIONS.md if this
   changes.
4. `.env.example`: confirm the Supabase anon key placeholder section is
   actually sufficient for what apps/web needs now that real auth calls
   are being made (update if a new env var is needed, e.g. cookie
   configuration).

## Definition of done for this task
- Manual signup creates a real `auth.users` row and a matching `profiles`
  row (verified via Supabase, not just "should work")
- Login/logout works end-to-end in the running dev server (verified via
  bash tool + curl or a scripted check, not just visual inspection claims)
- `/profile` correctly redirects unauthenticated visitors and correctly
  shows data for authenticated ones
- API JWT-verification dependency has a passing test for both valid and
  invalid/missing tokens
- No secrets committed; `.env.example` updated if new vars were introduced
- Commit message: `feat: Stage 3 auth slice (web sign-up/login/profile, api JWT verification)`
- Pushed to origin/main
- PROJECT_STATE.md and this file updated afterward

## After this task
Continue Stage 3: password recovery, session refresh handling, and the
first real RBAC-gated action (e.g. an admin-only endpoint) before moving to
Stage 4 (product catalog CRUD + admin UI).
