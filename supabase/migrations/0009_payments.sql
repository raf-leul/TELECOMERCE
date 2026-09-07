-- Migration: 0009_payments
-- Payment records and a raw event log for idempotent webhook processing
-- (master instructions section 28-29). payment_events stores every
-- inbound provider event by its own event id — processing the same event
-- id twice must be a no-op, not a double-charge/double-fulfillment.

create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders (id) on delete cascade,
  provider text not null,
  status text not null default 'pending'
    check (status in ('pending', 'succeeded', 'failed', 'refunded')),
  amount_cents integer not null check (amount_cents >= 0),
  provider_reference text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_payments_order_id on public.payments (order_id);

create trigger set_payments_updated_at
  before update on public.payments
  for each row
  execute function public.set_updated_at();

create table if not exists public.payment_events (
  id uuid primary key default gen_random_uuid(),
  payment_id uuid references public.payments (id) on delete set null,
  provider text not null,
  -- The provider's own event identifier. Unique per provider so a
  -- redelivered webhook (same event id) is detected and skipped rather
  -- than processed twice.
  provider_event_id text not null,
  event_type text not null,
  raw_payload jsonb,
  processed_at timestamptz not null default now(),
  unique (provider, provider_event_id)
);

create index if not exists idx_payment_events_payment_id
  on public.payment_events (payment_id);

-- RLS enabled, deliberately zero anon/authenticated policies — same
-- deny-by-default pattern as carts/orders. Only apps/api's service-role
-- client touches these tables; a user's own payment status is exposed
-- indirectly through GET /orders/{id} (the order's status), not by
-- reading these tables directly.
alter table public.payments enable row level security;
alter table public.payment_events enable row level security;
