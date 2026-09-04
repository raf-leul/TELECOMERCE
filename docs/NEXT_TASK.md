# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 4 — real end-to-end verification with seeded data, then admin CRUD
completeness (edit/delete), then move toward Stage 5 (cart).

The catalog read path (`GET /products`, `GET /products/{slug}`,
`GET /categories`) and the admin write path (`POST /products`,
`POST /categories`, both RBAC-gated) are built and unit-tested (19/19
tests), and `apps/web`'s `/shop` + `/products/[slug]` pages correctly call
`apps/api` and degrade gracefully when it's unreachable — all confirmed by
booting the real servers, not just from the test suite. What's still
unverified is the "happy path" with real data, since this sandbox can't
reach Supabase:

1. From an environment with real network access to Supabase (user's
   machine, or a future session with different permissions): seed 2-3 real
   products and a category via Supabase (`execute_sql` or the dashboard),
   run both `apps/api` (`uvicorn app.main:app`) and `apps/web`
   (`npm run web:dev`), and confirm:
   - `/shop` lists the seeded active products (and does NOT list an
     inactive one, if you seed one to check)
   - `/products/<real-slug>` shows the correct name/price/description
   - `/products/<a-slug-that-does-not-exist>` shows Next.js's actual 404
     page (not the "couldn't load" error message — those are two visually
     different states, confirm the right one appears)
   - `POST /products` with a real admin JWT (get one via `/me` after
     logging in as a user whose `profiles.role` you've manually set to
     `admin` via SQL) succeeds; the same request with a non-admin JWT
     returns 403
2. Once verified, add PATCH/DELETE for both products and categories
   (admin-only, same RBAC pattern), with the same rigor: unit tests +
   real-server boot check + (when possible) real Supabase verification.
3. Do NOT build search/filter/pagination on `/shop` yet, and do NOT build
   image upload yet — both explicitly scoped for later in Stage 4 per
   master instructions section 21/25. Keep this task focused on CRUD
   completeness.

## Definition of done for this task
- Real-data verification performed and documented (screenshots, curl
  output, or described exactly what was seen) — or explicitly marked as
  still-unverified with the same honesty standard used in Stages 2-4 so
  far, if no network-capable environment was available this session
- PATCH/DELETE added for products and categories, admin-gated, tested
- Commit message: `feat: Stage 4 CRUD completeness (update/delete) + real-data verification`
- Pushed to origin/main, CI confirmed green
- PROJECT_STATE.md and this file updated afterward

## Still open from Stage 3 (mostly closed now, one item remains)
- Password recovery flow: BUILT and locally verified this session
  (routes render, error states correct). NOT yet tested with a real email
  click — do this from an environment with real email access: request a
  reset on `/forgot-password`, click the real email link, confirm it lands
  on `/reset-password` with a working session, set a new password, log in
  with it.
- Session refresh: code-verified (matches Supabase's current docs, proven
  wired into every request via the proxy build output) but not
  time-verified — nothing to build here, just something to notice if a
  long-lived session ever silently breaks.
- Full login round-trip re-verification with an existing account: still
  not explicitly re-checked (the Stage 3 test session moved on after
  signup+profile+logout). Low priority — the underlying code hasn't
  changed since that partial verification.

## After this task
Stage 5 — Cart: server-side cart API (add/remove/update quantity),
server-side pricing (never trust client price/quantity totals — see
docs/DATABASE.md's price_cents design and master instructions section 27),
guest + authenticated cart with merge-on-login logic.
