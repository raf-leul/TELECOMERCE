# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 5 — real-data verification, then apps/web cart UI, then Stage 6
(order engine).

The cart API is built and unit-tested (36/36 tests): guest carts via
X-Cart-Token, authenticated carts via JWT, server-side pricing, add/update
/remove all working against mocked PostgREST. What's not yet done:

1. Real-data verification (same recurring sandbox limitation — needs the
   user's machine or a future network-capable session): with real products
   seeded (see Stage 4's still-open real-data task), confirm
   `POST /cart/items` actually adds a real row, `GET /cart` shows the
   correct computed subtotal, `PATCH`/`DELETE` work against real data, and
   a guest cart created with one X-Cart-Token stays isolated from a
   different one.
2. `apps/web`: build a minimal cart UI — an "Add to cart" button on
   `/products/[slug]`, a `/cart` page showing items + subtotal, quantity
   controls. Guest carts need the X-Cart-Token persisted somewhere
   (localStorage is reasonable here since it's just an opaque identifier,
   not sensitive data — unlike the "never use localStorage in artifacts"
   restriction, this is a real Next.js app, not an artifact). Merge-on-login
   logic (Stage 5's guest→authenticated cart merge) is not built yet —
   note it as explicitly deferred, don't silently skip it.
3. Guest cart to authenticated cart merge: when a guest with items in
   their cart logs in, decide and implement what happens (merge into their
   existing authenticated cart, summing quantities for duplicate products).
   This is real business logic, not just wiring — plan it before building.

## Definition of done for this task
- Real-data verification performed and reported, or explicitly logged as
  still-unverified
- Cart UI built in apps/web, works with the API (or gracefully degrades
  if the API is unreachable, same pattern as /shop)
- Guest→authenticated cart merge implemented and tested
- Commit message: `feat: Stage 5 cart UI + guest cart merge` (split into
  smaller commits if it grows large — see Rule 5)
- Pushed to origin/main, CI confirmed green
- PROJECT_STATE.md and this file updated afterward

## Still open from earlier stages (low priority, tracked not forgotten)
- Stage 3: full login round-trip re-verification with an existing account
- Stage 4: real-data verification against live Supabase for the catalog
  CRUD endpoints
- General: Supabase's "leaked password protection" is disabled — an
  easy win, revisit in Stage 12 (Security Audit) or sooner

## After this task
Stage 6 — Order Engine: order creation from a cart, order_items, totals,
addresses, the PENDING_PAYMENT→PAID→...→DELIVERED state machine, order
history, admin order management, audit logs. This is also when
`inventory_movements` (deferred since Stage 2) finally gets built, since
order creation is the first thing that actually needs to write inventory
movement records.
