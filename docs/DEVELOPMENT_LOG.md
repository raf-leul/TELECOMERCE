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

## Session 1 (continued) — Stage 3 real-world verification + Stage 4 start

**Stage 3 real-world verification (by the user, not this sandbox):**
User ran `apps/web` locally with real network access to Supabase and
confirmed: signup created a real account (`raf`, role `customer`, correct
join date) and a matching `profiles` row, the profile page rendered that
real data, and logout redirected to `/login` correctly. This closes the
verification gap the sandbox couldn't close itself for the core signup
flow. NOT re-verified: full login round-trip with an existing account,
password recovery, session refresh, RBAC-gated example — user explicitly
chose to move to Stage 4 rather than complete these first; carried forward
in NEXT_TASK.md rather than dropped.

**Stage 4 — Product Catalog (started):**
Built on top of in-progress work already on disk from earlier in the
session (`app/core/supabase_client.py`, `app/auth/rbac.py` — a thin httpx
wrapper for Supabase's PostgREST API and a `require_role(...)` RBAC
dependency built on the Stage 3 JWT verification + Stage 2's `profiles.role`
enum). Added `app/products/router.py` (`GET /products` public,
`POST /products` admin-only) and wired it into `main.py`.

**Testing process and what it caught:**
- Wrote `tests/test_products.py` using `httpx.MockTransport` to intercept
  PostgREST calls without any real network access — appropriate given the
  sandbox's confirmed inability to reach `*.supabase.co`.
- Hit three real bugs while getting these tests to actually pass (not
  glossed over):
  1. Fake test clients lacked a `base_url`, causing relative-path requests
     to fail with a URL-parsing error — a test setup bug, fixed by giving
     fakes the same `base_url` shape as the real `anon_client()`/
     `service_client()`.
  2. FastAPI's `dependency_overrides` need the override to match the
     original dependency's generator-function shape; a plain
     `lambda: iter([...])` was silently wrong (returned an iterator object
     as the "client" instead of yielding the actual client) — fixed by
     using real generator functions for the overrides.
  3. **A genuine application bug**, not a test bug: caught by booting the
     real server and hitting `/products` for real (in this sandbox, where
     it can't reach Supabase) — the error handling only caught
     `httpx.HTTPStatusError`, so a connection failure bubbled up as an
     unhandled, unstructured 500. Widened to `httpx.HTTPError` in both
     `app/products/router.py` and `app/auth/rbac.py`'s role lookup; now
     returns a clean structured 502/503 instead. This is exactly the kind
     of bug that mocked unit tests alone don't catch, which is why both
     the test suite AND a real server boot-and-curl check were done, not
     just one.
- Added `tests/test_supabase_client.py` to directly test the
  header-setting logic (`anon_client()`/`service_client()`) that the
  products tests deliberately bypass by overriding the FastAPI dependency.
- Final state: 13/13 tests passing (was 5 before this session), `ruff
  check .` clean, `apps/web` build/lint unaffected and still clean.

**Files changed:** `apps/api/app/core/supabase_client.py`,
`apps/api/app/auth/rbac.py`, `apps/api/app/products/` (new),
`apps/api/app/main.py`, `apps/api/tests/test_products.py` (new),
`apps/api/tests/test_supabase_client.py` (new), `docs/DECISIONS.md` (3 new
entries), `docs/PROJECT_STATE.md`, `docs/NEXT_TASK.md`.

**Not yet done / explicitly not claimed:**
- No categories endpoints yet, no single-product-by-slug endpoint.
- No apps/web storefront pages (`/shop`, `/products/[slug]`) yet — apps/web
  still only has the auth pages from Stage 3.
- The new `/products` endpoints have not been exercised against real
  Supabase data from any environment yet (same network caveat as Stage 3).
- No admin UI — admin-only endpoints are proven via RBAC unit tests only,
  not a real admin JWT request yet (would need the network-access
  environment to test that end-to-end too).

**Next task:** see NEXT_TASK.md — categories endpoints, single-product
endpoint, and the first storefront browsing pages.

## Session 1 (continued) — Stage 4: categories, product slug lookup, storefront pages

**What I did:**
Continued Stage 4 on top of in-progress work already on disk (a shared
`app/core/postgrest_deps.py` refactor, `app/categories/` module — inspected
before touching per Rule 1, confirmed sound, then finished wiring it in).

- Wired `categories_router` into `main.py` (it existed but wasn't included
  yet).
- Confirmed the existing refactor didn't break anything: full test suite
  still 13/13 after wiring, before adding new tests.
- Added `tests/test_categories.py` (list/create/RBAC-denied/RBAC-allowed —
  same pattern as products) and two tests for the pre-existing but
  untested `GET /products/{slug}` endpoint (found + not-found).
- Built `apps/web/lib/api/client.ts` (typed fetch helpers) and two new
  pages: `/shop` (product listing) and `/products/[slug]` (detail), both
  calling `apps/api` rather than Supabase directly, matching the "shared
  backend across channels" architecture principle so the eventual
  Telegram bot doesn't duplicate this logic.
- Added `NEXT_PUBLIC_API_URL` to `.env.example`.

**Verification performed:**
- Fresh-venv `pytest`: 19/19 passing (up from 13). `ruff check .` clean.
- `npm run web:build`: succeeds, `/shop` and `/products/[slug]` correctly
  render as dynamic routes (not statically pre-rendered, since they need
  live data). `npm run web:lint` clean.
- Booted the real FastAPI server and confirmed via curl: all 5 routes
  present in `/openapi.json`, `/categories` and `/products/{slug}` both
  return a clean structured 502 (not a raw crash) when Supabase is
  unreachable — same fix pattern as the earlier products bug, applied
  consistently.
- Booted BOTH the real FastAPI server and the real Next.js dev server
  together and hit `/shop` and `/products/nonexistent-slug` through the
  actual running web app: confirmed the graceful "couldn't load" error
  message renders correctly end-to-end (apps/web successfully talked to
  apps/api, and apps/api's own graceful-failure design showed through
  correctly), rather than the page crashing. This is stronger evidence
  than testing either app in isolation.

**What's still NOT verified (same recurring, honestly-documented
limitation):** the actual "happy path" — real products/categories seeded
in Supabase, actually appearing correctly on `/shop`/`/products/[slug]`,
and a real admin JWT actually succeeding against `POST /products` — none
of this can be exercised from this sandbox. Written into NEXT_TASK.md as
the first thing to check from a network-capable environment.

**Files changed:** `apps/api/app/main.py`, `apps/api/tests/test_categories.py`
(new), `apps/api/tests/test_products.py` (2 new tests appended),
`apps/web/lib/api/client.ts` (new), `apps/web/app/shop/page.tsx` (new),
`apps/web/app/products/[slug]/page.tsx` (new), `.env.example`,
`docs/PROJECT_STATE.md`, `docs/NEXT_TASK.md`.

**Next task:** see NEXT_TASK.md — real-data verification, then
PATCH/DELETE for products/categories, then Stage 5 (cart).

## Session 1 (continued) — Closing out Stage 3: password recovery

**What I did:**
User asked whether Stage 3 was finished; it wasn't (password recovery and
session-refresh verification were still open, though the RBAC item got
satisfied incidentally by Stage 4's `require_role` pattern). Finished it:

- Checked current Supabase community/docs guidance before writing code
  (Rule 10) — confirmed the currently recommended password-reset pattern
  uses a `token_hash` + `type=recovery` query param handled by a
  server-side confirm route calling `supabase.auth.verifyOtp()`, not the
  older client-side URL-fragment-parsing approach.
- Added `requestPasswordReset` and `updatePassword` Server Actions to
  `app/auth/actions.ts`.
- Added `app/auth/confirm/route.ts` — a reusable route handler for both
  password-recovery and (future) signup-confirmation links.
- Added `/forgot-password` and `/reset-password` pages, and a link to
  `/forgot-password` from `/login` (a real usability fix, not scope creep
  — the login page had no way to reach it otherwise).

**A real bug caught by actually running the build, not just writing
code:** `npm run web:build` failed with
`useSearchParams() should be wrapped in a suspense boundary` on
`/forgot-password`. Fixed by extracting the search-param-reading bit into
a small component wrapped in `<Suspense>`. Rebuilt and confirmed the fix
worked before moving on.

**Verification performed:**
- `npm run web:build` and `npm run web:lint` both clean afterward.
- Booted the real dev server and curl-tested: `/forgot-password` (200),
  the error-message query param actually rendering the right text,
  `/reset-password` (200), and `/auth/confirm` with no token correctly
  307-redirecting to `/forgot-password?error=...`.
- Re-reviewed `lib/supabase/proxy.ts` against current Supabase docs — it
  already matched the recommended pattern from the Stage 3 initial slice.
  Session refresh is code-verified (proven wired into every request via
  the "ƒ Proxy (Middleware)" build output back in Stage 3) but not
  time-verified — actually observing a token expire and refresh requires
  a long-lived real session, which is a "run it and wait" check better
  done by the user than manufactured in a quick test.

**Still not verified (same recurring, honest limitation):** the actual
email delivery + link-click flow with a real inbox — this sandbox can't
send/receive real email or reach Supabase. If the user wants to fully
close this out, the test is: request a reset on `/forgot-password`, click
the link in the real email, confirm it lands on `/reset-password` with
a valid session, set a new password, and log in with it.

**Files changed:** `apps/web/app/auth/actions.ts`,
`apps/web/app/auth/confirm/route.ts` (new),
`apps/web/app/forgot-password/page.tsx` (new),
`apps/web/app/reset-password/page.tsx` (new),
`apps/web/app/login/page.tsx` (added a link), `docs/DECISIONS.md` (2 new
entries), `docs/PROJECT_STATE.md`.

**Stage 3 status:** now considered closed, modulo the always-honest caveat
that a real end-to-end email-click test hasn't been run by anyone yet.

## Session 1 (continued) — Stage 4 CRUD completeness: PATCH/DELETE

**What I did:**
Added PATCH and DELETE for both `products` and `categories`, gated by the
same `require_role("admin", "owner")` pattern as the existing POST
endpoints. Added `ProductUpdate`/`CategoryUpdate` schemas (all fields
optional, so PATCH only applies what's actually provided via
`exclude_unset=True`).

**A real bug caught immediately by running the test suite (not by
writing code and assuming it worked):** FastAPI raised
`AssertionError: Status code 204 must not have a response body` at
route-registration time — meaning the entire app failed to even start,
not just the new delete routes. Fixed by adding `response_model=None`
alongside `status_code=204` on both delete routes. This is documented in
DECISIONS.md as a "watch out for this again" note, since it's an easy
mistake to reintroduce on a future delete endpoint.

**Verification performed:**
- Fresh-venv `pytest`: 27/27 passing (up from 19 before this addition).
- `ruff check .` clean.
- Booted the real server and confirmed via `/openapi.json`: all 7 routes
  present with the correct HTTP methods
  (`/products` GET+POST, `/products/{slug}` GET, `/products/{product_id}`
  PATCH+DELETE, same shape for categories). Confirmed PATCH/DELETE both
  correctly return 401 without a token.
- Re-ran `npm run web:build`/`web:lint` to confirm the frontend was
  unaffected by backend-only changes — still clean.

**Also handled this session:** user hit a real environment issue trying to
run `apps/api` locally — their Python is 3.14, and the pinned
`pydantic-core==2.9.2` has no pre-built wheel for it yet, so pip tried to
compile it from Rust source and failed (missing MSVC linker). Advised
using Python 3.12 instead via `py -3.12 -m venv .venv`. Not yet confirmed
this resolved it — user moved on to continue Stage 4 building instead of
finishing that local setup in this session.

**Files changed:** `apps/api/app/products/schemas.py`,
`apps/api/app/products/router.py`, `apps/api/app/categories/schemas.py`,
`apps/api/app/categories/router.py`, `apps/api/tests/test_products.py`
(6 new tests), `apps/api/tests/test_categories.py` (3 new tests),
`docs/DECISIONS.md`, `docs/PROJECT_STATE.md`, `docs/NEXT_TASK.md`.

**Not yet done / explicitly not claimed:** real-data verification against
live Supabase (same recurring sandbox limitation) — this is now the only
thing left to fully close Stage 4's CRUD scope, and it needs the user's
machine (once the Python 3.14 issue above is resolved) or a future session
with different network access.

**Next task:** see NEXT_TASK.md — real-data verification, then Stage 5
(cart).

## Session 1 (continued) — Stage 5: Cart

**What I did:**
- Applied `supabase/migrations/0007_cart.sql`: `carts` (user_id OR
  guest_token, exactly one via CHECK constraint) and `cart_items`
  (quantity, unique per cart+product). Verified via `list_tables` and
  `get_advisors` — two expected INFO-level "RLS enabled, no policy"
  findings (deliberate, documented) and one unrelated WARN
  (leaked-password-protection disabled, logged for later, not fixed now
  since it's out of scope for this migration).
- Built `apps/api/app/cart/`: identity resolution (`CartIdentity`,
  supporting both a verified JWT and a client-supplied `X-Cart-Token`
  guest UUID), and the router (`GET /cart`, `POST /cart/items`,
  `PATCH/DELETE /cart/items/{product_id}`). Added `get_optional_user` to
  `app.auth.security` for the guest-or-authenticated case (returns `None`
  instead of raising 401 when no token is present, but still raises 401
  for a present-but-invalid token — a typo'd token shouldn't silently
  downgrade someone to an empty guest cart).
- Pricing is looked up server-side from `products.price_cents` both when
  adding an item (to validate it's active) and when reading the cart (so
  price changes are reflected, not stale) — one test specifically proves
  the response price isn't influenced by anything in the request, since
  `CartItemAdd` has no price field at all.

**Two real bugs found by actually running things, not just writing code:**
1. Wrote 12 cart tests using the same `httpx.MockTransport` pattern as
   earlier modules — all passed on the first real run (35/35 total). No
   bug here, but worth noting the pattern continues to work well.
2. Booted the real server and hit `/cart` with a guest token but no
   `SUPABASE_SERVICE_ROLE_KEY` configured — cart is the first set of
   endpoints reachable without prior authentication, so it's the first
   place this could be hit directly instead of being masked by an earlier
   401. `service_client()` correctly raises `RuntimeError`, but nothing
   caught it — leaked as an unhandled 500. Fixed at the single shared
   choke point, `app.core.postgrest_deps.get_service_client` (the
   dependency every admin-write endpoint AND cart uses), so the fix
   covers all of them, not just cart. Re-verified on the real server:
   missing key → clean 503, key present but network unreachable → clean
   502 (the pre-existing, already-correct behavior for that case).

**Verification performed:**
- Fresh-venv `pytest`: 36/36 passing. `ruff check .` clean.
- Booted the real server: confirmed all cart routes present in
  `/openapi.json`, `GET /cart` without any identity returns 400 with a
  clear message, both failure modes above (503 misconfigured, 502
  unreachable) confirmed via curl.

**Files changed:** `supabase/migrations/0007_cart.sql` (new),
`apps/api/app/auth/security.py` (added `get_optional_user`),
`apps/api/app/cart/` (new: `__init__.py`, `schemas.py`, `identity.py`,
`router.py`), `apps/api/app/main.py`, `apps/api/app/core/postgrest_deps.py`
(bug fix), `apps/api/tests/test_cart.py` (new, 12 tests),
`apps/api/tests/test_supabase_client.py` (1 new test for the bug fix),
`docs/DECISIONS.md` (3 new entries), `docs/PROJECT_STATE.md`,
`docs/NEXT_TASK.md`.

**Not yet done / explicitly not claimed:**
- Real-data verification against live Supabase (same recurring
  limitation) — no real cart has been created against the actual database
  from any environment yet.
- No cart UI in `apps/web` yet — `/cart` page, "add to cart" button on
  product pages, guest-token persistence (localStorage) all still to do.
- Guest→authenticated cart merge-on-login is not designed or built yet —
  explicitly flagged as real business logic to plan, not just wire up.

**Next task:** see NEXT_TASK.md — real-data verification, cart UI, and the
guest-cart merge logic.

## Session 1 (continued) — Stage 6: Order Engine

**What I did:**
User asked to keep building through all remaining stages without testing
until the very end. Built Stage 6 (Order Engine):

- Applied `supabase/migrations/0008_orders.sql` (`orders`, `order_items`,
  `order_status_history`), same deny-by-default RLS pattern as cart.
  Verified via `list_tables` and `get_advisors` (only expected
  INFO-level "no policy" notes, no new real findings).
- Built `app/orders/state_machine.py`: the exact transition table from
  master instructions section 13, as a plain dict + `is_valid_transition`
  function — deliberately simple, no external state-machine library, since
  the transition set is small and fixed.
- Built `app/orders/router.py`: `POST /orders` (creates from the
  authenticated user's cart; re-validates product availability and
  re-reads price from the live catalog at checkout time rather than
  trusting whatever the cart last showed, snapshots name+price+quantity,
  records the initial status-history row, clears the cart), `GET /orders`
  (own orders only), `GET /orders/{id}` (404 whether not-found or
  not-owned, same non-leaking pattern as products), `PATCH
  /orders/{id}/status` (admin/owner/staff-gated, validates against the
  state machine, 409 on an illegal transition).
- Wrote `tests/test_orders.py` (7 tests) and
  `tests/test_order_state_machine.py` (4 tests) using the same
  httpx.MockTransport pattern as every other module.

**Verification performed:**
- Fresh-venv `pytest`: 47/47 passing (up from 36) — first stage this
  session where the initial full test run passed clean with no real bug
  found along the way (previous stages each surfaced at least one real
  issue: workspace lockfile mismatch, pytest import path, network-error
  handling, a 204/response_model FastAPI assertion, a missing migration
  file). Still ran the same rigor (fresh venv, real server boot) to make
  sure this stage wasn't an exception due to under-testing.
- `ruff check .` clean.
- Booted the real server and confirmed via `/openapi.json`: all 4 order
  routes present (`POST/GET /orders`, `GET /orders/{id}`,
  `PATCH /orders/{id}/status`), and confirmed via curl that POST and PATCH
  both correctly return 401 without a token.
- Re-ran `npm run web:build`/`web:lint` — unaffected, still clean.

**Key design decisions (see DECISIONS.md for full detail):** order items
snapshot name/price at creation time (orders are historical records, not
live views of the catalog); checkout requires authentication in this
slice (guest checkout explicitly deferred, `orders.user_id` left nullable
to leave room for it later); status transitions are validated against an
explicit table, never trusting a client-sent "previous status."

**Not yet done / explicitly not claimed:** real end-to-end order creation
against live Supabase (same recurring sandbox network limitation — this
is now the case for every stage from 2 onward, and per the user's explicit
instruction is being deferred until all stages are built, then tested
together in one pass).

**Files changed:** `supabase/migrations/0008_orders.sql` (new),
`apps/api/app/orders/` (new: `__init__.py`, `state_machine.py`,
`schemas.py`, `router.py`), `apps/api/app/main.py`,
`apps/api/tests/test_orders.py` (new),
`apps/api/tests/test_order_state_machine.py` (new), `docs/DECISIONS.md`
(2 new entries), `docs/PROJECT_STATE.md`, `docs/NEXT_TASK.md`.

**Next task:** see NEXT_TASK.md — Stage 7 (payment system, mock provider).

## Session 1 (continued) — Stage 7: Payment System (mock provider)

**What I did:**
Built Stage 7 per master instructions section 7's explicit guidance for
when a real local payment provider isn't available: a `PaymentProvider`
abstraction plus one concrete `MockPaymentProvider`, clearly labeled
sandbox-only throughout its own docstrings so it can never be mistaken
for something that processes real money.

- Applied `supabase/migrations/0009_payments.sql` (`payments`,
  `payment_events` with `UNIQUE(provider, provider_event_id)` for
  idempotency), same deny-by-default RLS pattern as cart/orders. Verified
  via `list_tables` and `get_advisors` (only expected INFO notes).
- `app/payments/provider.py`: the ABC interface, with a docstring
  explicitly listing what a real provider integration would need to add
  (signature verification, real credentials) — not just an implicit gap.
- `app/payments/mock_provider.py`: `create_payment()` always returns
  "pending" (never auto-succeeds) specifically so the webhook-driven
  completion path is genuinely exercised rather than bypassed.
- `app/payments/router.py`: `POST /orders/{id}/pay` (must own the order,
  order must be `pending_payment`) and `POST /payments/webhook`
  (idempotent — inserts the event row into `payment_events` BEFORE any
  payment/order mutation, so the database's own unique constraint is what
  prevents double-processing, not an in-memory check that two concurrent
  requests could both slip past).
- Test files (`test_mock_payment_provider.py`, `test_payments.py`) were
  already substantially written from earlier in the session — reviewed
  them for correctness before trusting them (Rule 1), found them sound,
  particularly the idempotency test's approach of making the mock
  transport raise an `AssertionError` if a duplicate webhook delivery ever
  reaches the order/payment update calls a second time.

**Verification performed:**
- Fresh-venv `pytest`: 57/57 passing (up from 47), including the
  webhook-idempotency test actually proving what it claims.
- `ruff check .` clean.
- Booted the real server, confirmed all payment routes exist via
  `/openapi.json`, confirmed `POST /orders/{id}/pay` returns 401 without
  auth.
- Investigated (rather than assumed) an odd result: a malformed
  `POST /payments/webhook` body against this sandbox's server returned 503
  instead of the expected 422. Didn't file it as a bug without checking —
  used `TestClient` with a working fake `get_service_client` override to
  confirm the real, production-relevant behavior (service client actually
  configured) correctly returns 422 with proper per-field errors, and
  never even reaches the backend. The 503 was a FastAPI
  dependency-resolution-order artifact specific to this sandbox's missing
  `SUPABASE_SERVICE_ROLE_KEY`, not an application bug. Documented in
  DECISIONS.md so a future session doesn't re-investigate this as a
  mystery.
- Re-ran `npm run web:build`/`web:lint` — unaffected, still clean.

**Not yet done / explicitly not claimed:** real end-to-end payment flow
against live Supabase (same recurring network limitation, deferred per
the user's instruction to test everything together at the end). No real
payment provider — explicitly out of scope until a real provider account
exists, per master instructions section 7.

**Files changed:** `supabase/migrations/0009_payments.sql` (new),
`apps/api/app/payments/` (new: `__init__.py`, `provider.py`,
`mock_provider.py`, `schemas.py`, `router.py`), `apps/api/app/main.py`,
`apps/api/tests/test_mock_payment_provider.py` (new),
`apps/api/tests/test_payments.py` (new, reviewed existing work),
`docs/DECISIONS.md` (3 new entries), `docs/PROJECT_STATE.md`,
`docs/NEXT_TASK.md`.

**Next task:** see NEXT_TASK.md — Stage 8 (Telegram bot, calling the same
apps/api endpoints as the web app).

## Session 1 (continued) — Stage 8: Telegram Bot

**What I did:**
Built the Telegram bot per master instructions section 16 — critically,
as a thin client of the SAME apps/api endpoints the web app uses, not a
separate implementation of catalog/cart/order logic.

- Checked current python-telegram-bot docs before writing any handler
  code (Rule 10) — confirmed v22.x's `ApplicationBuilder`/`CommandHandler`/
  `CallbackQueryHandler`/`ContextTypes` pattern (stable since v20, still
  current).
- `bot/services/api_client.py`: every function is a thin httpx call to an
  apps/api endpoint (categories, products, cart, orders, pay) — no
  Supabase client anywhere in this app, by design and enforced by test
  structure (tests mock at the apps/api HTTP boundary).
- `bot/services/identity.py`: deterministic `uuid5(telegram_user_id)` →
  guest cart token, so the bot can use apps/api's existing guest-cart path
  (Stage 5) without needing account linking for basic browsing/cart use.
- `bot/handlers/{start,products,cart,orders}.py` + `bot/keyboards/menus.py`
  + `bot/main.py`: `/start`, inline-keyboard category → product → detail
  → add-to-cart flow, cart viewing — all fully functional against the
  guest-cart path.
- Checkout and order-history handlers are deliberate, honest placeholders:
  both require an authenticated Supabase session (Stage 6 decision), which
  the bot has no way to get without a real account-linking flow. Rather
  than attempting a call that would 401, or silently no-op'ing, they
  directly tell the user this isn't available yet.

**Verification performed:**
- Fresh-venv `pytest`: 12/12 passing — identity derivation (same user →
  same token, different users → different tokens, valid UUID format),
  the API client wrapper (mocked HTTP, asserting correct paths/headers/
  bodies), and handler logic (mocked Telegram `Update`/`CallbackQuery`
  objects via `unittest.mock`, including a test proving the browse handler
  degrades gracefully — shows an error message, doesn't crash — when
  apps/api is unreachable).
- `ruff check .` clean (caught and fixed one unused-import lint issue).
- Actually built the real `Application` object (not just imported the
  module) and confirmed all 10 handlers registered. Confirmed a missing
  `TELEGRAM_BOT_TOKEN` env var fails with a clear `KeyError`, not a
  cryptic crash somewhere deep in python-telegram-bot's internals.
- Added a `bot` job to `.github/workflows/ci.yml` (lint + test, same
  pattern as the `api` job). Re-verified `apps/api` (57/57) and `apps/web`
  (build + lint) were unaffected by this addition before pushing.

**Not yet done / explicitly not claimed:** no real Telegram Bot API token
exists anywhere in this environment (would need @BotFather + a real
account), so actual message delivery, real webhook behavior, and the bot
actually running against Telegram's servers have NEVER been verified —
only the unit/mock-level logic above. This is the most significant
"unverified" item so far, since every other stage's unverified gap is
"real data against real Supabase" while this one is "the entire bot
against the entire external platform." Documented clearly rather than
implied to work.

**Files changed:** `apps/bot/` (entirely new: `bot/__init__.py`,
`bot/main.py`, `bot/handlers/{start,products,cart,orders}.py`,
`bot/keyboards/menus.py`, `bot/services/{api_client,identity}.py`,
`bot/states/__init__.py`, `bot/middleware/__init__.py`,
`requirements/{base,dev}.txt`, `pytest.ini`, `tests/*`),
`.github/workflows/ci.yml` (new `bot` job), `docs/DECISIONS.md` (3 new
entries), `docs/PROJECT_STATE.md`, `docs/NEXT_TASK.md`.

**Next task:** see NEXT_TASK.md — Stage 9 (admin dashboard in apps/web,
first real UI consumer of the RBAC pattern).
