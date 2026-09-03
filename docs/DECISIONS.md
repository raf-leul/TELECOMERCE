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
