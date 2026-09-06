# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 7 — Payment system (sandbox/mock provider first).

Per master instructions section 7 and the "if local payment integration
isn't available, build the provider abstraction plus a clearly-labeled
mock provider" guidance:

1. `apps/api/app/payments/`: a `PaymentProvider` interface
   (`create_payment()`, `verify_payment()`, `handle_webhook()`, `refund()`)
   and one concrete `MockPaymentProvider` implementation clearly labeled
   as sandbox-only (never claim it processes real money).
2. `POST /orders/{id}/pay` (or similar): creates a payment record tied to
   the order, using the mock provider, transitions the order
   pending_payment → paid through the existing state machine (reuse it,
   don't duplicate the transition logic).
3. A `payments` table (+ `payment_events` for webhook idempotency) via a
   new migration — payment_id, order_id, provider, status, amount_cents,
   provider_reference, created_at. `payment_events` stores raw provider
   event ids so a duplicate webhook delivery doesn't double-process
   (master instructions section 28 — idempotency).
4. A mock webhook endpoint (`POST /payments/webhook`) that simulates what
   a real provider would send, verifying it's idempotent: sending the same
   event id twice must not mark the order paid twice or create two
   payment records.
5. Do NOT integrate a real payment provider yet — that requires real
   credentials and a real testable account, which isn't available in this
   environment. Document exactly what a production integration would need
   to replace (per section 7's guidance) rather than building it now.

## Definition of done for this task
- Migration applied, verified via list_tables, RLS enabled (same
  deny-by-default pattern as cart/orders)
- PaymentProvider interface + MockPaymentProvider built and tested
- Order pay flow tested end-to-end at the mock level (unit tests + real
  server boot check)
- Webhook idempotency explicitly tested: same event id sent twice produces
  the same end state, not a duplicate
- Commit message: `feat: Stage 7 — payment system (mock provider, idempotent webhook)`
- Pushed to origin/main, CI confirmed green
- PROJECT_STATE.md and this file updated afterward

## Still open (real-data verification backlog, not blocking further stages)
Every stage from 2 onward has unit/mock-level verification but not a real
end-to-end run against live Supabase from any environment (this sandbox's
network can't reach *.supabase.co). Per the user's explicit instruction,
this is being deferred until all stages are built, then tested together.
When that happens, work through each stage's "what wasn't verified" notes
in DEVELOPMENT_LOG.md in order.

## After this task
Stage 8 — Telegram bot: /start, product browsing, cart, checkout, order
status — all calling the SAME apps/api endpoints already built (products,
cart, orders, payments), proving the "one backend, many channels"
architecture actually works, not just in theory.
