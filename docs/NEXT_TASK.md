# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 9 — Admin dashboard (apps/web /admin routes).

Built on top of the RBAC pattern (Stage 4) and the full CRUD API already
in place (products, categories, orders, payments):

1. `apps/web/app/admin/` — route group with a layout that checks
   `profiles.role` (via a Server Component reading the Supabase session +
   a profile lookup) and redirects non-admins away. This is the first
   real UI consumer of the RBAC pattern that's existed API-side since
   Stage 4.
2. `/admin` — overview: counts of orders by status, revenue (sum of paid
   orders' subtotal_cents), low-stock products (inventory.quantity_available
   below some threshold), pulled from apps/api (add read endpoints if
   apps/api doesn't already expose what's needed — don't query Supabase
   directly from apps/web for this, same "shared backend" principle as
   Stage 8's bot work).
3. `/admin/products` — list + create/edit/delete UI wired to the existing
   `GET/POST/PATCH/DELETE /products` endpoints.
4. `/admin/orders` — list + status-update UI wired to `GET /orders` (note:
   this currently only returns the OWN user's orders — will need an
   admin-scoped `GET /orders` variant or a query param, since an admin
   needs to see ALL orders, not just their own. Design this properly,
   don't just remove the ownership filter for admins without deciding
   how that's gated).
5. Do NOT build customer management, coupons, or full analytics charts
   yet — explicitly scoped for later per master instructions section 22
   (start with the core dashboard, not every listed widget at once).

## Definition of done for this task
- `apps/api` changes (if any, e.g. an admin-scoped orders endpoint) tested
  the same rigorous way as every other endpoint (unit tests + real server
  boot check)
- `/admin` pages built, route-protected, tested via `npm run web:build`/
  `web:lint`, and a real dev-server boot-and-curl check confirming
  non-admins/unauthenticated visitors are redirected
- Commit message: `feat: Stage 9 — admin dashboard (overview, products, orders)`
- Pushed to origin/main, CI confirmed green
- PROJECT_STATE.md and this file updated afterward

## Still open (real-data verification backlog, not blocking further stages)
Every stage from 2 onward has unit/mock-level verification but not a real
end-to-end run against live Supabase from any environment. Per the user's
explicit instruction, this is deferred until ALL stages are built, then
tested together as one pass. Also still open: a real Telegram bot token
test (Stage 8), a real payment provider (Stage 7, needs a real account),
Telegram account linking (Stage 8, deferred design decision).

## After this task
Stage 10 — Notifications: email abstraction, Telegram notifications (the
bot can now actually push messages, not just respond to them), in-app
notifications for order status changes.
