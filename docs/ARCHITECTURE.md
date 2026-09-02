# ARCHITECTURE.md

## Overview
TeleCommerce is a modular monolith. A single FastAPI backend owns all business
logic (catalog, cart, orders, payments, inventory) and is consumed by two
presentation layers: a Next.js web storefront and a Telegram bot. Supabase
provides PostgreSQL, Auth, and Storage.

## Current state (Stage 1)
Only skeletons exist:

- `apps/web` — Next.js 16 (App Router) + TypeScript + Tailwind CSS 4.
  Placeholder home page only. No data fetching, no auth, no routes beyond `/`.
- `apps/api` — FastAPI skeleton. Single `GET /health` endpoint. No database
  connection wired up yet, no feature modules.
- `apps/bot` — not started (Stage 8).
- `supabase/` — project exists and is reachable, but has zero tables/migrations.

## Repository layout
See root `package.json` and folder structure in the repo root. Follows the
structure defined in the master instructions section 9, adapted only where
`create-next-app` conventions differ slightly from the original spec (e.g.
`apps/web/app/` is the Next.js App Router directory).

## Backend module boundaries (planned, Stage 2+)
```
apps/api/app/
  core/       # settings, shared config (exists)
  auth/       # Stage 3
  users/      # Stage 3
  products/   # Stage 4
  categories/ # Stage 4
  cart/       # Stage 5
  orders/     # Stage 6
  payments/   # Stage 7
  inventory/  # Stage 4/6
  telegram/   # Stage 8
  notifications/ # Stage 10
  analytics/  # Stage 9
  admin/      # Stage 9
```
Each module will be added only when its stage begins — no empty placeholder
modules are created ahead of time (avoids dead scaffolding).

## Data flow (target, not yet implemented)
Web / Telegram → FastAPI (shared business logic) → Supabase Postgres
Server-authoritative pricing/inventory/order-state — never trust client input
for price or stock (see master instructions, sections 11 and 27).

## Deployment (target, not yet implemented)
- apps/web → Vercel (team: raf's projects, not yet linked)
- apps/api → TBD Python-compatible host (not yet chosen)
- Database/Auth/Storage → Supabase project `telecommerce` (ref
  `hmsjerjguhxhwoubqdqm`, us-east-1)

## Decisions log
See DECISIONS.md for reasoning behind specific choices (e.g. why classic PAT
over fine-grained PAT, why Next.js App Router, etc).
