-- Migration: 0007_cart
-- Server-side cart for both guests (identified by a client-generated UUID
-- token) and authenticated users (identified by auth.users id). Exactly
-- one cart per identity, enforced by a CHECK constraint plus partial
-- unique indexes.
--
-- Authorization is enforced in application code (apps/api/app/cart/), not
-- RLS: every cart request goes through the service-role client, and
-- app.cart.identity.CartIdentity matches the resolved identity
-- (authenticated user id, or guest token from the X-Cart-Token header) to
-- the correct cart_id/guest_token filter before any query runs. RLS is
-- still enabled with no anon/authenticated policies (default-deny), so a
-- future bug that accidentally used the anon/authenticated client here
-- would fail closed, not open. See docs/DECISIONS.md for the full
-- reasoning.

create table if not exists public.carts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete cascade,
  guest_token uuid unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint carts_exactly_one_owner check (
    (user_id is not null and guest_token is null)
    or (user_id is null and guest_token is not null)
  )
);

-- Exactly one cart per user. guest_token's uniqueness comes from the
-- column-level UNIQUE constraint above (Postgres allows multiple NULLs in
-- a unique column, which is exactly the behavior wanted here).
create unique index if not exists idx_carts_user_id_unique
  on public.carts (user_id) where user_id is not null;

create trigger set_carts_updated_at
  before update on public.carts
  for each row
  execute function public.set_updated_at();

create table if not exists public.cart_items (
  id uuid primary key default gen_random_uuid(),
  cart_id uuid not null references public.carts (id) on delete cascade,
  product_id uuid not null references public.products (id) on delete cascade,
  quantity integer not null check (quantity > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (cart_id, product_id)
);

create index if not exists idx_cart_items_cart_id on public.cart_items (cart_id);

create trigger set_cart_items_updated_at
  before update on public.cart_items
  for each row
  execute function public.set_updated_at();

-- RLS enabled, deliberately with NO anon/authenticated policies (default
-- deny). Only the service-role key (used exclusively by apps/api's cart
-- module) can read/write these tables. This means a future bug that
-- accidentally routed a cart request through the anon/authenticated
-- client would fail closed with a permission error, not silently expose
-- another identity's cart.
alter table public.carts enable row level security;
alter table public.cart_items enable row level security;
