# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 4 — continue Product Catalog: categories endpoints + apps/web
storefront browsing.

apps/api already has the RBAC pattern proven (GET/POST /products). Extend
it and connect it to the frontend:

1. `apps/api`: add `app/categories/` mirroring the products module —
   `GET /categories` (public), `POST /categories` (admin-only via
   `require_role`). Add `GET /products/{slug}` (public, single product by
   slug — 404 if not found or inactive, relying on RLS the same way the
   list endpoint does). Tests for all three, same pattern as
   `tests/test_products.py` (httpx.MockTransport, no real network).
2. `apps/web`: build a storefront product listing page (`/shop` or similar)
   that fetches from `apps/api`'s `GET /products` (not directly from
   Supabase — apps/web should go through the shared backend per
   docs/ARCHITECTURE.md's "one source of truth" principle, even for public
   reads, so business logic doesn't fork between channels later). A
   product detail page at `/products/[slug]`.
3. Real end-to-end check once this is testable somewhere with network
   access to Supabase (see the recurring caveat in DECISIONS.md): seed one
   or two real products via `execute_sql`/`apply_migration` (or build a
   minimal seed script), confirm they render on `/shop` and
   `/products/[slug]`, and confirm an inactive product does NOT appear.
4. Do NOT build the full admin dashboard UI yet (Stage 9) — just prove the
   admin-only POST endpoints work by testing them directly (curl/Postman
   with a real admin JWT) rather than building UI for them this stage.

## Definition of done for this task
- Categories endpoints built and tested the same rigorous way as products
  (unit tests + a real server boot-and-curl check, since that's what
  caught the Stage 4 network-error bug already found this session)
- `GET /products/{slug}` built and tested (found + not-found + inactive
  cases)
- `/shop` and `/products/[slug]` pages built in apps/web, fetching from
  apps/api
- Real seed data used to verify the storefront pages actually render
  correctly once network access allows it — or explicitly documented as
  not yet verified, same honesty standard as Stage 3
- Commit message: `feat: Stage 4 continued — categories API, storefront browsing pages`
- Pushed to origin/main, CI confirmed green (not just locally)
- PROJECT_STATE.md and this file updated afterward

## Still open from Stage 3 (not forgotten, deliberately deferred)
- Full login round-trip re-verification with an existing account
- Password recovery flow
- Session refresh past token expiry
These can be picked up whenever convenient — they don't block Stage 4 but
should be closed before calling the project's auth "done."

## After this task
Continue Stage 4: admin product/category CRUD (edit/delete, not just
create), inventory visibility on the storefront, image upload via Supabase
Storage (new bucket + RLS policies), search/filter/pagination on `/shop`.
