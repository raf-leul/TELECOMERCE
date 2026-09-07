# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 8 — Telegram bot (proves the "one backend, many channels"
architecture for real).

Per master instructions section 16-17: the bot is not a separate store —
it must call the SAME apps/api endpoints already built (products, cart,
orders, payments), not reimplement business logic.

1. `apps/bot/` (new): python-telegram-bot, webhook-based per master
   instructions section 16, structured as
   `bot/{handlers,keyboards,services,states,middleware}/main.py`.
2. `/start` — welcome message + main menu (Browse Products, Cart, My
   Orders, Account, Help).
3. Product browsing: list categories → list products in a category →
   product detail — all via HTTP calls to apps/api's `GET /categories`,
   `GET /products`, `GET /products/{slug}`. No direct Supabase access from
   the bot.
4. Cart: add to cart, view cart — via apps/api's `GET/POST /cart*`
   endpoints. Telegram users are guests from the API's point of view
   unless account-linking exists (it doesn't yet — see below), so use the
   guest cart path (X-Cart-Token), with the Telegram user's numeric id
   deterministically mapped to a stable UUID for the token (so the same
   Telegram user always gets the same cart across messages).
5. Checkout: calls `POST /orders` then `POST /orders/{id}/pay` (mock
   provider) — same as web, proving shared logic.
6. Order status: `GET /orders` via the bot.
7. Do NOT build: real Telegram-Supabase account linking (deferred —
   requires deciding how a Telegram user proves they're also a registered
   web user, which is a real design decision, not a quick add), admin
   operations via the bot (Stage 9+ concern), or a real bot token/webhook
   deployment (no real Telegram Bot API token exists in this environment —
   build and unit-test the handler logic, note honestly that live
   Telegram delivery hasn't been verified).

## Definition of done for this task
- `apps/bot` scaffolded with the structure above
- Handlers built calling real apps/api endpoints (via httpx), tested with
  mocked HTTP responses (same rigor as apps/api's own test suite)
- Guest-cart-via-deterministic-token approach implemented and tested
- Explicitly documented: no real Telegram token/webhook exists in this
  environment, so end-to-end bot behavior against real Telegram has NOT
  been verified — this needs a real bot token (from @BotFather) and a
  reachable webhook URL, neither available here
- Commit message: `feat: Stage 8 — Telegram bot (shared backend, no duplicated business logic)`
- Pushed to origin/main, CI confirmed green (add a bot test job to
  ci.yml if apps/bot has its own Python dependencies)
- PROJECT_STATE.md and this file updated afterward

## Still open (real-data verification backlog, not blocking further stages)
Every stage from 2 onward has unit/mock-level verification but not a real
end-to-end run against live Supabase from any environment. Per the user's
explicit instruction, this is deferred until all stages are built, then
tested together as one pass. Also still open: a real Telegram bot token
test (Stage 8), a real payment provider (explicitly out of scope until a
provider account exists).

## After this task
Stage 9 — Admin dashboard: revenue/orders/customers/products views in
apps/web's /admin routes, built on the RBAC pattern and CRUD endpoints
already in place.
