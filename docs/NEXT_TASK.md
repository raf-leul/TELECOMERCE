# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 10 — Notifications.

1. `apps/api/app/notifications/`: a `NotificationChannel` abstraction
   (mirroring the Stage 7 `PaymentProvider` pattern — an interface, then
   concrete channels) with at minimum an `InAppNotification` channel
   (writes to a new `notifications` table) and a `TelegramNotification`
   channel (sends via the bot — requires apps/api to be able to call
   Telegram's API using the bot token, or push through an internal
   endpoint the bot polls; decide and document which approach, don't
   silently pick one without reasoning about it in DECISIONS.md).
2. New migration: `notifications` table (user_id, type, message, read_at,
   created_at) + `notification_deliveries` (notification_id, channel,
   status, sent_at) if delivery tracking across multiple channels is
   worth the complexity — decide based on whether Stage 10's actual scope
   needs it or whether a single `notifications` table suffices for now
   (master instructions section 64 — don't over-engineer ahead of need).
3. Wire notification creation into existing order status transitions
   (Stage 6): order created, paid, shipped, delivered, cancelled should
   each create a notification. Reuse the existing state machine — don't
   duplicate transition logic in the notification code.
4. Email channel: explicitly deferred unless a real email provider
   account exists (same reasoning as Stage 7's payment provider) — build
   the interface slot for it, but don't fake sending real email.
5. `apps/web`: a simple notifications list on `/profile` or a dedicated
   `/notifications` page, reading from a new `GET /notifications`
   endpoint (own notifications only, same ownership pattern as orders).

## Definition of done for this task
- Migration applied, verified, RLS enabled (same deny-by-default pattern)
- NotificationChannel interface + at least in-app implemented and tested
- Notification creation wired into order status transitions, tested
- `apps/web` notification list built and tested (build + lint + real
  server boot check)
- Commit message: `feat: Stage 10 — notifications (in-app + order status triggers)`
- Pushed to origin/main, CI confirmed green
- PROJECT_STATE.md and this file updated afterward

## Still open (real-data verification backlog, not blocking further stages)
Every stage from 2 onward has unit/mock-level verification but not a real
end-to-end run against live Supabase from any environment. Per the user's
explicit instruction, this is deferred until ALL stages are built, then
tested together as one pass. Also still open: a real Telegram bot token
test (Stage 8), a real payment provider (Stage 7), Telegram account
linking (Stage 8, deferred design decision).

## After this task
Stage 11 — Quality: backend unit/integration tests are already extensive
per-stage, but this stage should specifically add cross-cutting tests the
per-feature test files don't cover: full checkout-to-delivery flow across
multiple endpoints in sequence, permission tests across every role for
every endpoint systematically (a matrix, not ad-hoc), and duplicate-
webhook/race-condition-style tests beyond what Stage 7 already covers.
