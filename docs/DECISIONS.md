# DECISIONS.md

Chronological log of notable technical/architecture decisions and why they
were made.

## 2026-09-02 — GitHub auth: classic PAT, not fine-grained
Attempted a fine-grained personal access token for git push access. The
GitHub REST API reported `push: true` for the token against the target repo,
but `git push` over HTTPS was rejected with `403 Permission to ... denied`.
This is a known inconsistency between fine-grained PAT scoping and git's
smart-HTTP auth path. Switched to a classic PAT with the `repo` scope, which
worked immediately. Decision: use classic PATs for this project's git
operations until GitHub App/OAuth-based auth is set up (not needed yet at
this scale).

## 2026-09-02 — Removed next/font Google Fonts dependency
`create-next-app`'s default template uses `next/font/google` (Geist/Geist
Mono), which fetches font CSS from fonts.googleapis.com at build time. The
development sandbox's network egress does not allow that domain, so builds
failed locally with a 403. Since local build verification is required before
every commit (Rule 6), switched to system fonts via Tailwind defaults instead
of self-hosting or working around the network restriction. This also avoids
an external network dependency at build time in CI. Can be revisited later
with `next/font/local` and a bundled font file if a specific typeface is
wanted for the design system (Stage 36).

## 2026-09-02 — Supabase project created fresh, not reused
Two existing Supabase projects existed on the account ("video posting
website", inactive; "premium membership platform", active) but neither is
related to this project. Created a new project (`telecommerce`) rather than
repurposing either, per user's explicit choice and to avoid cross-project
data/schema contamination.

## 2026-09-02 — npm workspaces instead of a monorepo tool (Turborepo/Nx)
Only `apps/web` is a Node project so far (`apps/api`/`apps/bot` are Python).
Plain npm workspaces are sufficient for now. Will reconsider a dedicated
monorepo tool only if/when there are multiple interdependent JS/TS packages
that need coordinated builds (e.g. `packages/shared-types` consumed by
multiple apps) — avoiding premature tooling per master instructions section
64 (do not over-engineer).

## 2026-09-02 — Auth: @supabase/ssr + proxy.ts (not middleware.ts), Server Actions for forms
Checked current Supabase docs (Rule 10 — don't rely on training-data memory
for fast-moving library APIs) before writing any auth code. Findings that
shaped the implementation:

- `@supabase/ssr` is the currently recommended package (the older
  `@supabase/auth-helpers-nextjs` is being phased out).
- Next.js 16's session-refresh file is named `proxy.ts` (not the older
  `middleware.ts` convention) with a `proxy()` export — verified by
  confirming the build output actually lists "ƒ Proxy (Middleware)" and
  that a live dev server logs `proxy.ts:` timing on each request, so this
  isn't just cargo-culted from a blog post.
- Use `getClaims()` (validates the JWT signature locally against the
  project's published public keys) to gate access to pages/data — never
  `getSession()` for that purpose, since `getSession()` doesn't
  re-validate the token and its embedded user object isn't safe to trust
  when it came from client-writable storage (cookies).
- Sign-up/sign-in/sign-out are implemented as Next.js Server Actions
  (`app/auth/actions.ts`) rather than client-side `fetch` calls to a
  route handler — this is the pattern the current docs demonstrate and it
  keeps the Supabase server client (with proper cookie handling) in one
  place.

## 2026-09-02 — profiles.role vs JWT "role" claim are different things
Supabase's JWT includes a `role` claim, but that's the Postgres role
(`authenticated`/`anon`/`service_role`), not the application-level
`profiles.role` enum (`customer`/`staff`/`admin`/`owner`) from Stage 2.
The `/me` endpoint in `apps/api` deliberately returns the JWT's Postgres
role and labels it as such (`postgres_role`) rather than implying it's the
app role, to avoid this becoming a confusing bug later when real
RBAC-gated endpoints are built. Looking up `profiles.role` for an
authenticated request is left to whichever endpoint actually needs
authorization logic — not built into the base verification dependency.

## 2026-09-02 — API JWT verification: JWKS, not the shared secret
Two ways exist to verify a Supabase JWT server-side: (1) fetch the
project's JWKS and verify signature locally (works for both legacy HS256
projects and newer ES256/asymmetric-signing-key projects, and needs no
long-lived secret in the backend), or (2) decode with the shared JWT
secret via HS256 directly. Chose JWKS verification via `PyJWKClient`
(from PyJWT) because it doesn't require storing Supabase's JWT signing
secret in `apps/api`'s own environment, and works regardless of whether
the project uses legacy symmetric or the newer default asymmetric signing
keys.

## 2026-09-02 — Sandbox cannot reach *.supabase.co over HTTP directly
This development sandbox's network egress allowlist covers package
registries and GitHub, but not `*.supabase.co`. This was discovered when
attempting to curl the Supabase REST API directly and when attempting a
real `supabase.auth.signUp()` call from a Node script — both were rejected
by the egress proxy with "Host not in allowlist". The Supabase MCP tools
still work because they go through a different (permitted) channel, which
is why Stage 2's RLS verification worked but a live end-to-end signup test
through the running Next.js dev server does not work from inside this
sandbox. See DEVELOPMENT_LOG.md for what was and wasn't verified as a
result, and NEXT_TASK.md for what still needs manual/deployed verification.

## 2026-09-03 — apps/api uses raw httpx against PostgREST, not the supabase-py SDK
For the small number of backend operations needed so far (a couple of
reads, one write, one role lookup), a thin `httpx.Client` wrapper
(`app/core/supabase_client.py`) against Supabase's auto-generated
PostgREST API is simpler to reason about, simpler to unit test (via
`httpx.MockTransport`, no real network or extra test dependency needed),
and has no hidden SDK behavior to account for. Revisit if/when the backend
needs realtime subscriptions, storage uploads, or other features the raw
REST API doesn't cover well — that's when `supabase-py` earns its
complexity.

## 2026-09-03 — Product writes always go through service_client(), reads through anon_client()
Mirrors the RLS design from Stage 2: `products`/`categories` have no
client-writable RLS policy on purpose (see docs/DATABASE.md), so the only
way to write from the backend is the service-role key, which bypasses RLS
entirely. This makes `app.auth.rbac.require_role(...)` the *only* gate on
writes — there's no RLS safety net on the write path the way there is on
reads. Verified this is intentional and documented so a future session
doesn't "fix" it by loosening RLS instead.

## 2026-09-03 — Bug found via real server testing, not just unit tests: unhandled network errors leaked as 500
Unit tests alone (which mock the network boundary) didn't catch this: the
first version of `app/products/router.py` only caught
`httpx.HTTPStatusError` (a PostgREST error response), not
`httpx.HTTPError`/connection failures. Booting the real server and hitting
`/products` for real (in this sandbox, where the request genuinely can't
reach Supabase) surfaced a raw unhandled 500. Widened the except clauses
in both `app/products/router.py` and `app/auth/rbac.py`'s profile lookup
to catch `httpx.HTTPError` broadly, returning a structured 502/503 instead.
Lesson reinforced: booting the real process and hitting it, not just
running the mocked test suite, is what caught this — keep doing both.

## 2026-09-03 — Password recovery: token_hash + verifyOtp, not URL-fragment parsing
Checked current Supabase docs/community guidance before implementing
(Rule 10). The older pattern has the client parse `access_token` out of a
URL fragment after the reset-email link redirect; the currently
recommended pattern instead sends a `token_hash` + `type=recovery` query
param to a server-side confirm route
(`app/auth/confirm/route.ts`), which calls `supabase.auth.verifyOtp()`
server-side to establish the session, then redirects to `/reset-password`.
This route handler is reused for future email-confirmation links too
(signup confirmation already emails a similar link), avoiding a second
near-duplicate handler later.

## 2026-09-03 — /forgot-password never reveals whether an email is registered
`requestPasswordReset` returns the same "if an account exists..." message
regardless of whether `resetPasswordForEmail` actually found a matching
user (Supabase's own API doesn't leak this either). Prevents using the
password-reset form as a way to enumerate registered email addresses.

## 2026-09-04 — PATCH/DELETE routes need response_model=None for 204 status
Caught by actually running the test suite, not writing-and-assuming:
FastAPI raises `AssertionError: Status code 204 must not have a response
body` at route-registration time (app fails to even start) if a route
declares `status_code=204` without also setting `response_model=None`.
Both `DELETE /products/{id}` and `DELETE /categories/{id}` needed this
fix. Small thing, but it's the kind of error that would have silently
broken the entire app (every route fails to register, not just delete) had
it shipped — worth noting so a future session doesn't reintroduce it on
a new delete endpoint.

## 2026-09-05 — Cart tables have RLS enabled with zero policies (deliberate deny-all)
Unlike products/categories, `carts`/`cart_items` have no anon/authenticated
RLS policies at all — RLS is enabled, which with no policies means
default-deny for those roles. All cart access goes through apps/api using
the service-role client, which enforces authorization in application code
(matching the verified JWT's user id for authenticated carts, matching a
caller-supplied guest_token for guest carts). This is stricter than the
products/categories pattern because cart data is per-visitor state, not
shared catalog data — there's no safe "anyone can read this" policy to
write the way `is_active = true` worked for products. Supabase's security
advisor flags this as an INFO-level "RLS enabled, no policy" finding,
which is expected and correct here, not a gap to fill.

## 2026-09-05 — Noted but deferred: leaked password protection disabled
Supabase's security advisor flagged `auth_leaked_password_protection` as
disabled (WARN level) — an Auth-project-level setting (checks new
passwords against HaveIBeenPwned), unrelated to this session's migration
work. Not fixed now since it's an Auth configuration change, not a schema
change, and out of scope for Stage 5. Logged here so it's not forgotten;
revisit in Stage 12 (Security Audit) or sooner if convenient.

## 2026-09-05 — Second real bug from booting the real server: unconfigured service-role key leaked as unhandled 500
Cart is the first set of endpoints reachable without prior authentication
(guests can use it), so it's the first place a misconfigured/missing
`SUPABASE_SERVICE_ROLE_KEY` could be hit directly by a real, unauthenticated
request rather than being masked by an earlier 401. Booting the real
server without that env var set surfaced exactly that: `service_client()`
correctly raises `RuntimeError`, but nothing caught it, so it leaked as an
unhandled 500. Fixed at the single shared choke point
(`app.core.postgrest_deps.get_service_client`, the FastAPI dependency
every admin-write and cart endpoint uses) rather than wrapping each route
individually — now returns a clean structured 503. This is the same
"boot the real process, not just the mocked test suite" lesson as the
earlier `httpx.HTTPStatusError` vs `httpx.HTTPError` bug in Stage 4;
recorded here so it's clear this is a recurring, effective verification
step, not a one-off.

## 2026-09-05 — Found and fixed: 0007_cart.sql migration was applied to Supabase but never saved to the repo
Before continuing Stage 5, inspected the actual repo state (Rule 1) and
found `apps/api/app/cart/` code and 36 passing tests already existed
locally, but `supabase/migrations/0007_cart.sql` did not — despite
`docs/PROJECT_STATE.md` and `docs/DEVELOPMENT_LOG.md` both stating it had
been "applied," and `list_migrations` confirming the migration really was
applied to the live Supabase project (version `20260905043923`). The
`.sql` file itself was simply never written to disk/committed in the
session that applied it.

Recreated the file from the actual live schema (introspected via
`pg_constraint`/`pg_indexes`, not guessed) rather than reconstructing it
from memory of what the migration probably contained — this caught a real
naming discrepancy: the live schema uses a plain `UNIQUE (guest_token)`
column constraint and an index named `idx_carts_user_id_unique` (not the
`idx_carts_unique_user`/`idx_carts_unique_guest_token` names an
independent reconstruction first guessed). The corrected file now matches
the live database exactly, verified by testing the constraints directly
against Supabase (rejected null/null and non-null/non-null owner
combinations, rejected duplicate user_id, rejected quantity=0 — then
cleaned up all test data afterward).

Lesson: "migration applied" and "migration file exists in git" are two
separate facts that must both be checked — a green CI run and passing
tests don't catch a missing schema file when the database itself already
has the schema from a prior direct application.
