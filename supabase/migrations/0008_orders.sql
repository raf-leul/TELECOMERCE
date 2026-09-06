-- Migration: 0008_orders
-- Order engine: orders, order_items, order_status_history. Snapshot
-- pricing/name at order time (never re-look-up product price later — an
-- order is a historical record, not a live view of the catalog). State
-- machine transitions are validated in application code (apps/api), not
-- the database, matching the cart module's "authorization in app code,
-- service-role-only access" pattern from Stage 5.

create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  status text not null default 'pending_payment'
    check (status in (
      'pending_payment', 'paid', 'processing', 'packed',
      'shipped', 'delivered', 'cancelled', 'refunded'
    )),
  subtotal_cents integer not null check (subtotal_cents >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_orders_user_id on public.orders (user_id);
create index if not exists idx_orders_status on public.orders (status);

create trigger set_orders_updated_at
  before update on public.orders
  for each row
  execute function public.set_updated_at();

create table if not exists public.order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders (id) on delete cascade,
  product_id uuid references public.products (id) on delete set null,
  -- Snapshotted at order time — must survive product edits/deletion.
  product_name text not null,
  unit_price_cents integer not null check (unit_price_cents >= 0),
  quantity integer not null check (quantity > 0),
  created_at timestamptz not null default now()
);

create index if not exists idx_order_items_order_id on public.order_items (order_id);

create table if not exists public.order_status_history (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders (id) on delete cascade,
  from_status text,
  to_status text not null,
  changed_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists idx_order_status_history_order_id
  on public.order_status_history (order_id);

-- RLS enabled, deliberately zero anon/authenticated policies (same
-- deny-by-default pattern as carts/cart_items in Stage 5). apps/api's
-- order module uses the service-role client exclusively and enforces
-- "a user can only see their own orders" in application code by filtering
-- on user_id = the verified JWT's subject, not via RLS.
alter table public.orders enable row level security;
alter table public.order_items enable row level security;
alter table public.order_status_history enable row level security;
