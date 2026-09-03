# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 3 — real end-to-end verification of the auth slice, then close out
the rest of Stage 3.

This sandbox cannot reach `*.supabase.co` over the network (confirmed by a
direct test — see docs/DECISIONS.md), so the auth code written this session
(apps/web register/login/profile pages + apps/api /me endpoint) has only
been verified at the unit/build/lint level, not end-to-end against real
Supabase Auth. Before adding more auth features, verify what already
exists actually works:

1. Run `apps/web` (`npm run web:dev`) somewhere with real network access
   (locally, Vercel preview, or a future session with different network
   permissions) and confirm:
   - `/register` with a real email+password creates a row in `auth.users`
     AND a matching row in `public.profiles` (check via Supabase
     `execute_sql` or the dashboard).
   - `/login` with those same credentials succeeds and redirects to
     `/profile`.
   - `/profile` renders the real `display_name`/`role`/`created_at` for
     that user (proves the `profiles_select_own` RLS policy works through
     the actual app, not just via a simulated `set local role anon`
     Postgres session as was done in Stage 2).
   - "Log out" on `/profile` actually clears the session and subsequent
     visits to `/profile` redirect to `/login` again.
2. Run `apps/api` (`uvicorn app.main:app`) and confirm `/me` with a real
   Supabase-issued access token (grab one from the browser's session after
   step 1, or via `supabase.auth.getSession()` in a script) returns 200
   with the correct `id`.
3. Fix anything that breaks during this real-world test — don't assume the
   unit tests fully cover it, since they intentionally mock the network
   boundary.
4. Once verified, finish the remaining Stage 3 scope:
   - Password recovery flow (`/forgot-password`, Supabase's reset-password
     email + confirm page).
   - Confirm session refresh actually works past the access token's
     expiry (proxy.ts should handle this — verify, don't assume).
   - Add one real RBAC-gated example: an endpoint or page reachable only
     when `profiles.role` is `admin`/`owner`, to prove the pattern before
     Stage 4 builds real admin CRUD on top of it.

## Definition of done for this task
- All four end-to-end checks in step 1-2 above actually performed with
  evidence (screenshots, curl output, or SQL query results — not just "it
  should work")
- Password recovery, session refresh, and the RBAC-gated example built and
  verified the same way
- Any bugs found during real-world testing fixed and re-verified
- `.env.example` updated if new vars were introduced (e.g. for
  password-reset redirect URLs)
- Commit message: `feat: Stage 3 complete — verified auth flow, password recovery, RBAC example`
- Pushed to origin/main
- PROJECT_STATE.md and this file updated afterward, replacing the
  "could not verify" caveats with real verification evidence

## After this task
Stage 4 — Product catalog: categories/products CRUD in apps/api (admin-only,
enforced via the RBAC pattern just built), storefront browsing/search/filter
pages in apps/web, admin product management UI, Supabase Storage bucket for
product images.
