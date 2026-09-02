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
