# PROJECT_STATE.md

Last updated: 2026-09-05 (session 1, continued)

## Current Stage
STAGE 9 — ADMIN DASHBOARD (built: apps/api /admin/{products,orders,overview}
endpoints, apps/web /admin/{,products,orders} pages with a layout-level
RBAC gate, 61/61 API tests passing including a real aggregation-math
test). STAGE 8 complete (Telegram bot: apps/bot scaffolded per master
instructions structure, browsing/cart via the SAME apps/api endpoints as
the web app, checkout/order-history honestly gated behind not-yet-built
account linking, 12/12 tests passing). No real Telegram bot token exists
in this environment — live behavior against real Telegram has NOT been
verified, only unit/mock-level.
STAGE 7 complete (payment system: schema + PaymentProvider abstraction +
MockPaymentProvider (sandbox-only, clearly labeled) + idempotent webhook,
57/57 tests passing, including the critical webhook-replayed-twice test).
STAGE 6 complete (order engine: schema + API, 47/47 tests, no bugs found —
first clean stage). STAGE 5 complete (cart: schema + API, 36/36 tests,
migration file gap found and fixed). STAGE 4 complete (admin CRUD: GET/POST/PATCH/DELETE for
both products and categories, GET /products/{slug}, storefront /shop +
/products/[slug] pages). STAGE 3 fully closed: password recovery flow
built (forgot-password
→ email → /auth/confirm → reset-password), session refresh confirmed
wired into every request via
proxy.ts (was already code-complete since the initial slice, re-verified),
RBAC-gated example satisfied by Stage 4's require_role pattern. Only the
full login-round-trip re-check with an existing account (a Stage 3 item)
remains genuinely unverified — noted below, not blocking further work.

## Current Milestone
Core auth flow (signup, session creation, logout+redirect) confirmed
working by the user running the app locally with real network access to
Supabase — closing the verification gap this sandbox couldn't close itself.
Moving to STAGE 4 — Product Catalog, which will include the RBAC-gated
admin-write pattern originally scoped as a separate Stage 3 task (more
useful to build it against a real endpoint than a throwaway example).

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
- STAGE 2: `profiles`, `categories`, `products`, `product_images`, `inventory`
  tables created via 6 migrations (see docs/DATABASE.md for full detail).
  RLS enabled on all tables. Security advisor: 0 findings (2 real findings
  caught and fixed). Performance advisor: 1 real finding caught and fixed
  (1 expected/non-actionable INFO note remains on an empty table).
  RLS behavior actually verified against the live database (anon role
  read/write tests), not just assumed from the policy SQL.
  `docs/DATABASE.md` created documenting schema + verification evidence.
- STAGE 3 (initial slice): `apps/web` — @supabase/ssr wired up
  (lib/supabase/client.ts, server.ts, proxy.ts), `/register`, `/login`,
  `/profile` pages, Server Actions for sign-up/sign-in/sign-out
  (app/auth/actions.ts). `apps/api` — JWT verification dependency against
  Supabase's JWKS (app/auth/security.py) with a `/me` endpoint, 4 passing
  unit tests (missing token, garbage token, expired token, valid token —
  the valid/expired cases sign real JWTs with a locally generated RSA
  keypair and monkeypatch the JWKS client, so no network access to
  Supabase is needed for these tests to be meaningful).
- STAGE 4 (started): `apps/api` products module —
  `app/core/supabase_client.py` (httpx wrapper for Supabase's PostgREST
  API: `anon_client()` for RLS-respecting reads, `service_client()` for
  admin writes), `app/auth/rbac.py` (`require_role(...)` FastAPI
  dependency looking up `profiles.role` via the service-role client),
  `app/products/router.py` (`GET /products` public/RLS-gated,
  `POST /products` admin-only via RBAC). 13/13 tests passing (up from 5),
  all via `httpx.MockTransport` — no real Supabase network access needed
  or used for these tests. Booting the real server surfaced and fixed a
  real bug: network/connection failures weren't caught by the original
  `except httpx.HTTPStatusError`, so they leaked as raw 500s; widened to
  `httpx.HTTPError` and now returns a clean structured 502/503.
- STAGE 4 continued: `app/categories/router.py` (`GET /categories` public,
  `POST /categories` admin-only, same RLS+RBAC pattern as products) built
  on shared plumbing pulled out to `app/core/postgrest_deps.py`.
  `GET /products/{slug}` added (404 for missing/inactive, same response
  either way so drafts aren't distinguishable from nonexistent slugs).
  19/19 tests passing (up from 13). `apps/web`: `/shop` (product listing)
  and `/products/[slug]` (detail) pages added, calling `apps/api` — not
  Supabase directly — via `lib/api/client.ts`, per the "one backend, many
  channels" architecture principle. Both pages degrade gracefully (visible
  error message, not a crash) when the API is unreachable — verified for
  real by booting both servers together in this sandbox (where the API
  genuinely can't reach Supabase) and confirming the graceful-error path
  renders correctly end-to-end through the actual running app, not just
  assumed from the code.
- STAGE 3 CLOSE-OUT: password recovery flow built (`/forgot-password`,
  `app/auth/confirm/route.ts` using the current token_hash+verifyOtp
  pattern, `/reset-password`), following current Supabase docs (Rule 10)
  rather than the older URL-fragment-parsing pattern. Caught and fixed a
  real Next.js build error via actual `npm run build` verification (a
  `useSearchParams()` call needed a Suspense boundary — build failed
  without it, passed after). Booted the real dev server and confirmed via
  curl: `/forgot-password` and `/reset-password` render, an error query
  param displays correctly, and `/auth/confirm` with no token correctly
  redirects back to `/forgot-password` with an error message. Session
  refresh (`proxy.ts`/`updateSession`) re-reviewed and confirmed to match
  Supabase's current documented pattern exactly, and was already
  confirmed wired into every request via the Stage 3 build output ("ƒ
  Proxy (Middleware)") — genuinely watching a token expire and refresh
  over time is not something this sandbox (or a quick test) can observe;
  noted as the one remaining thing about session refresh that's
  code-verified but not time-verified.
- STAGE 4 CRUD COMPLETION: added PATCH/DELETE for both products and
  categories, admin-gated via the same `require_role` pattern. Caught a
  real bug that would have broken the ENTIRE app (not just delete) —
  FastAPI raises an assertion error at startup if a `status_code=204`
  route doesn't also set `response_model=None`; the test suite failed to
  even collect until this was fixed. 27/27 tests passing (up from 19).
  Booted the real server and confirmed via curl: all 7 routes present in
  `/openapi.json` with correct methods, PATCH/DELETE both correctly
  return 401 without auth. `apps/web` build/lint re-confirmed unaffected.
- STAGE 5 — CART: `supabase/migrations/0007_cart.sql` applied and
  verified (`carts` + `cart_items`, RLS enabled with deliberately zero
  anon/authenticated policies — deny-all by design, since cart access
  goes exclusively through apps/api's service-role client with
  authorization enforced in application code; documented in DECISIONS.md).
  `apps/api/app/cart/` built: `GET /cart`, `POST /cart/items`,
  `PATCH /cart/items/{id}`, `DELETE /cart/items/{id}`, supporting both
  guest carts (X-Cart-Token header) and authenticated carts (JWT) via a
  shared identity-resolution helper. Pricing is always looked up
  server-side from `products.price_cents` at both add-time and read-time
  — a test explicitly proves the response price isn't influenced by
  anything the client sent. 36/36 tests passing (up from 27). Caught and
  fixed a second real bug via booting the actual server (not just the
  mocked suite): an unconfigured `SUPABASE_SERVICE_ROLE_KEY` raised an
  unhandled 500 instead of a clean error, since cart is the first
  endpoint set reachable without prior authentication. Fixed at the
  single shared dependency (`get_service_client`) so every admin-write
  and cart endpoint benefits, not just cart. Re-verified both failure
  modes (misconfigured key → 503, key present but network unreachable →
  502) behave correctly on the real running server.
- STAGE 6 — ORDER ENGINE: `supabase/migrations/0008_orders.sql` applied
  and verified (`orders`, `order_items`, `order_status_history` — same
  deny-by-default RLS pattern as cart). `apps/api/app/orders/` built:
  `POST /orders` (creates an order from the authenticated user's cart,
  re-validates product availability and re-reads price from the live
  catalog rather than trusting the cart snapshot, snapshots
  name+price+quantity into order_items, records initial status history,
  clears the cart), `GET /orders` (own orders only), `GET /orders/{id}`
  (404 if not found OR not owned — same non-leaking pattern as products),
  `PATCH /orders/{id}/status` (admin/owner/staff only, validates the
  transition against `app/orders/state_machine.py`'s explicit table from
  master instructions section 13, rejects illegal jumps with 409). 47/47
  tests passing (up from 36) — first stage where the fresh test run
  passed clean without finding a real bug along the way. Booted the real
  server and confirmed all 4 order routes exist and correctly return 401
  without auth. `apps/web` build/lint re-confirmed unaffected.
- STAGE 7 — PAYMENT SYSTEM: `supabase/migrations/0009_payments.sql`
  applied and verified (`payments`, `payment_events` — same deny-by-default
  RLS pattern). `apps/api/app/payments/`: a `PaymentProvider` ABC (
  `create_payment`/`verify_payment`/`handle_webhook`/`refund`) and one
  concrete `MockPaymentProvider`, explicitly labeled sandbox-only —
  documented exactly what a real provider integration would additionally
  need (signature verification, real credentials). `POST /orders/{id}/pay`
  (owner-only, only from `pending_payment`, creates a `pending` payment —
  deliberately never auto-succeeds so the webhook path is genuinely
  exercised). `POST /payments/webhook`: idempotent via
  `payment_events`' `UNIQUE(provider, provider_event_id)` constraint — the
  event insert happens BEFORE any payment/order mutation, so a replayed
  webhook is caught by the database constraint itself, not an in-memory
  check. 57/57 tests passing (up from 47), including a test that makes the
  mock transport raise an `AssertionError` if a duplicate webhook delivery
  ever reaches the order/payment update calls a second time. Investigated
  (not assumed) an odd 503-instead-of-422 result when testing a malformed
  webhook body against this sandbox's unconfigured server; confirmed via
  TestClient with a working fake service client that the real,
  production-relevant behavior correctly returns 422 — the 503 was purely
  a FastAPI dependency-resolution-order artifact specific to this
  sandbox's missing service-role key, not an app bug (documented in
  DECISIONS.md so it isn't re-investigated as a mystery later).
- STAGE 8 — TELEGRAM BOT: `apps/bot/` scaffolded per master instructions
  section 16's structure (handlers/keyboards/services/states/middleware).
  `bot/services/api_client.py` is the bot's ONLY path to data — thin httpx
  wrappers calling the SAME apps/api endpoints the web app uses (products,
  categories, cart, orders), never Supabase directly, proving the "one
  backend, many channels" architecture principle for real rather than
  just in documentation. `bot/services/identity.py` derives a stable
  guest-cart token from a Telegram user's numeric id (uuid5), so the same
  user always gets the same cart across messages without a mapping table.
  `/start` + inline-keyboard browsing (categories → products → detail →
  add to cart) fully implemented and working against the guest-cart path.
  Checkout and order-history are HONEST PLACEHOLDERS: both require an
  authenticated Supabase session, which the bot can't obtain without a
  real account-linking flow (explicitly deferred — a genuine design
  decision, not a shortcut), so the handlers directly tell the user this
  isn't available yet rather than failing silently or faking success.
  12/12 tests passing: identity derivation, the API client wrapper (mocked
  HTTP, verifying correct headers/paths/bodies sent to apps/api), and
  handler logic (mocked Telegram Update/CallbackQuery objects, including a
  test proving graceful degradation — not a crash — when apps/api is
  unreachable). Actually built the real `Application` object and confirmed
  all 10 handlers register correctly; confirmed a missing
  `TELEGRAM_BOT_TOKEN` fails with a clear error rather than a cryptic one.
  Added a `bot` job to `.github/workflows/ci.yml`. NOT verified: real
  behavior against the actual Telegram Bot API — no real bot token exists
  in this environment, so live message delivery/webhook behavior has
  never been exercised, only unit/mock-level logic.
- STAGE 9 — ADMIN DASHBOARD: `apps/api/app/admin/router.py` — three
  endpoints, all gated by `require_role("admin", "owner", "staff")`:
  `GET /admin/products` (ALL products including inactive, unlike the
  public RLS-filtered list), `GET /admin/orders` (all orders across all
  users, unlike the regular ownership-filtered list), `GET /admin/overview`
  (order counts by status, revenue — sum of subtotal_cents for
  paid/processing/packed/shipped/delivered orders, explicitly excluding
  pending/cancelled/refunded — and low-stock products below a
  configurable threshold). 61/61 tests passing (up from 57), including a
  test that verifies the aggregation math itself (specific revenue number
  computed from specific input rows), not just that the endpoint returns
  200. `apps/web/app/admin/`: a layout-level auth+role gate (checks
  `profiles.role` once, every nested page inherits it — verified for real
  by hitting `/admin` and `/admin/products` unauthenticated against a
  running dev server and confirming both redirect to `/login`), an
  overview page, a products page (toggle active/inactive, delete — wired
  to the existing Stage 4 PATCH/DELETE endpoints), and an orders page
  (status-update dropdown wired to the Stage 6 state-machine-validated
  endpoint). Caught a real TypeScript build error (`<form action>`
  requires a void-returning function; the first version returning a typed
  error object didn't type-check) via `npm run build`, fixed by
  simplifying admin actions to throw-on-failure rather than mirroring the
  auth forms' inline-error pattern — documented as a deliberate tradeoff,
  not an oversight.
discovered missing from the repo (see DECISIONS.md) — now verified to
exactly match the live, already-applied schema, including direct testing
of every constraint (owner-exclusivity, per-user/per-guest-token
uniqueness, quantity>0) against the real Supabase project, with all test
data cleaned up afterward. Cart's real end-to-end path (actually adding a
real product to a real cart through the running API) has NOT been
exercised from any environment yet — same recurring network limitation as
every other stage, deferred to NEXT_TASK.md. Everything else (Stages 1-4,
Stage 3's password recovery) is fully closed per the entries above.

## What Was Last Changed
Built Stage 3's initial auth slice in apps/web and apps/api, discovered and
documented a real sandbox limitation (no network path to *.supabase.co from
this environment) that caps how much of it can be verified here.

## Latest Commit
3a1181e (feat: Stage 9 — admin dashboard (overview, products, orders)) — pushed to origin/main, CI green (all 3 jobs: web, api, bot)

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
- STAGE 3 — what WAS verified locally:
  - `npm run web:build` succeeds with the new auth pages/actions/proxy; the
    build output explicitly lists a "ƒ Proxy (Middleware)" line, confirming
    `proxy.ts` was actually picked up by Next.js 16, not silently ignored.
  - `npm run web:lint` passes clean on the new code.
  - Booted the real Next.js dev server and confirmed via curl: `/`, `/login`,
    `/register` return 200; an unauthenticated request to `/profile` returns
    a 307 redirect to `/login` (this doesn't require reaching Supabase — an
    absent session cookie is a local decision, no JWKS lookup needed).
  - `apps/api`: fresh-venv `pytest` run, 5/5 passing, including 4 new auth
    tests (missing token → 401, garbage token → 401, expired token → 401,
    valid token → 200 with correct claims echoed). The valid/expired cases
    sign a real JWT with a locally generated RSA keypair and monkeypatch
    the JWKS client — genuine JWT verification logic is exercised, just
    against a test key instead of Supabase's real one.
  - Booted the real FastAPI server (not just TestClient) and confirmed via
    curl: `/health` returns 200, `/me` without a token and with a garbage
    token both return 401.
  - `ruff check .` passes clean.
- STAGE 3 — what could NOT be verified from this sandbox, and why:
  - A real end-to-end signup (`/register` → Supabase Auth → `profiles` row
    created by the Stage 2 trigger) — this sandbox's network egress
    allowlist does not include `*.supabase.co`. Directly tested this with
    a Node script calling `supabase.auth.signUp()` against the real
    project; it failed with "Host not in allowlist" from the egress proxy,
    not a code error. The Supabase MCP tools use a different, permitted
    channel, which is why Stage 2's database-level trigger test (inserting
    directly into `auth.users` via SQL) worked but this app-level call
    doesn't.
  - Real login setting a working session cookie, and the profile page
    rendering real Supabase-sourced data — blocked by the same network
    restriction.
  - The `/me` endpoint against a real Supabase-issued JWT (only tested
    against a locally-signed test JWT, for the same reason).
- STAGE 3 — resolved by the USER running the app locally (real network
  access to Supabase, unlike this sandbox), 2026-09-03:
  - ✅ `/register` with real credentials created a real account; the
    Stage 2 auto-provisioning trigger fired correctly — `/profile` showed
    the correct `display_name` ("raf"), `role` ("customer"), and a real
    join date.
  - ✅ Confirmed Supabase's default email-confirmation setting for this
    project does NOT block the initial session — signup logs the user in
    immediately even before the confirmation email is clicked. Worth
    knowing: this is a project-level Supabase Auth setting, not something
    this codebase enforces either way.
  - ✅ Logout correctly cleared the session and redirected to `/login`.
  - ⚠️ NOT explicitly re-confirmed: logging back in with the same
    credentials on `/login` after logout (the user moved on to Stage 4
    before completing this specific check). Worth a quick manual check
    later if a login-specific bug ever surfaces, but not blocking further
    work given everything else in the loop verified correctly.

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
None known, but see "What Was Tested" — the real signup/login/profile flow
against live Supabase has not been exercised end-to-end from any
environment yet (only unit-level and network-blocked-partial checks). This
is a verification gap, not a known bug, but should be closed before
Stage 3 is called fully done.

## What Must Happen Next
See NEXT_TASK.md. Short version: get real end-to-end verification of the
Stage 3 auth flow (signup, login, profile page, /me) somewhere with actual
network access to *.supabase.co — either by the user running the dev
servers locally/on Vercel, or in a future session with different network
permissions — then close out Stage 3 and move to Stage 4 (product catalog
CRUD + admin UI, building on the Stage 2 schema).

## Migration / Deployment State
- 6 database migrations applied and verified (see docs/DATABASE.md):
  0001_profiles, 0002_catalog, 0003_inventory, 0004_security_hardening,
  0005_fix_public_execute_grant, 0006_optimize_rls_initplan.
- All public-schema tables have RLS enabled with verified-correct policies.
- No Vercel project linked/deployed yet.
- No Supabase Storage buckets created yet (needed once product image upload
  is built, Stage 4/25).
- Auth code exists (Stage 3 initial slice) but has not been exercised
  end-to-end against real Supabase Auth from any environment yet — see
  "What Was Tested" above.

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
Get real end-to-end verification of signup → login → /profile → /me
against the live Supabase project, from an environment with actual network
access (this sandbox's egress allowlist blocks *.supabase.co — see
DECISIONS.md). Once verified, finish the rest of Stage 3 (password
recovery, session refresh edge cases, first RBAC-gated action) per
NEXT_TASK.md, then move to Stage 4.
