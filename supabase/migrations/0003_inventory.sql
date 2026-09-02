-- Migration: 0003_inventory
-- Minimal stock-on-hand table. inventory_movements (audit trail of
-- purchases/sales/reservations/adjustments) is intentionally deferred to
-- Stage 6 when the order engine actually needs to write to it — see
-- master instructions section 10 ("do not create tables just for
-- appearance") and section 12.

create table if not exists public.inventory (
  product_id uuid primary key references public.products (id) on delete cascade,
  quantity_available integer not null default 0 check (quantity_available >= 0),
  updated_at timestamptz not null default now()
);

create trigger set_inventory_updated_at
  before update on public.inventory
  for each row
  execute function public.set_updated_at();

alter table public.inventory enable row level security;

-- Stock level needs to be publicly readable so the storefront can show
-- "in stock" / "out of stock" / quantity remaining. It is not writable by
-- anon/authenticated clients — only the service role (backend) can adjust
-- it, since inventory must never be trusted from the client
-- (master instructions section 12).
create policy "inventory_select_all"
  on public.inventory
  for select
  to anon, authenticated
  using (true);
