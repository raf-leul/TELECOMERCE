# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 4 — real-data verification, then move to Stage 5 (cart).

Admin CRUD for products and categories is now complete
(GET/POST/PATCH/DELETE, all RBAC-gated, 27/27 tests passing) and the
storefront pages (`/shop`, `/products/[slug]`) work correctly when the API
is reachable or unreachable. What's left for Stage 4 is real-data
verification — this sandbox cannot reach Supabase, so it needs to happen
from an environment that can (the user's machine):

1. Run `apps/api` locally (see docs/DEVELOPMENT_LOG.md for the Python
   3.14/pydantic-core build issue and the fix — use Python 3.12, not 3.14).
2. Seed 2-3 real products + a category, either via Supabase directly
   (`execute_sql`/dashboard) or by calling the new `POST /products` /
   `POST /categories` endpoints with a real admin JWT (get one by logging
   in as a user whose `profiles.role` has been manually set to `admin`).
3. Confirm on `/shop` and `/products/[slug]` that the seeded data renders
   correctly, inactive products are hidden, and PATCH/DELETE actually work
   against real data (edit a price, delete a test product, confirm it's
   gone).
4. Do NOT build search/filter/pagination or image upload yet — explicitly
   scoped for later in Stage 4 (master instructions sections 21/25).

## Definition of done for this task
- Real-data verification performed and reported back, OR explicitly
  logged as still-unverified with the same honesty standard used
  throughout this project
- Any bugs found during real-world testing fixed and re-verified
- Commit message: `feat: Stage 4 real-data verification` (or a fix/docs
  commit if bugs were found and fixed)
- Pushed to origin/main, CI confirmed green
- PROJECT_STATE.md and this file updated afterward

## Still open from Stage 3 (very low priority, not blocking)
- Full login round-trip re-verification with an existing account (the
  underlying code hasn't changed since the partial Stage 3 verification,
  so this is a formality, not a real risk)

## After this task
Stage 5 — Cart: server-side cart API (add/remove/update quantity),
server-side pricing (never trust client price/quantity totals — see
docs/DATABASE.md's price_cents design and master instructions section 27),
guest + authenticated cart with merge-on-login logic.
