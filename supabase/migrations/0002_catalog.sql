-- Migration: 0002_catalog
-- Categories, products, product images. Public/anon can read active
-- catalog data; all writes are service-role only until admin RBAC exists
-- (Stage 3/4).

create extension if not exists pgcrypto;

create table if not exists public.categories (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  parent_category_id uuid references public.categories (id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists idx_categories_parent_category_id
  on public.categories (parent_category_id);

create table if not exists public.products (
  id uuid primary key default gen_random_uuid(),
  category_id uuid references public.categories (id) on delete set null,
  name text not null,
  slug text not null unique,
  description text,
  -- Price stored as integer cents. Never store price as a float, and never
  -- accept it from the client at checkout time (see docs/ARCHITECTURE.md
  -- and master instructions section 27).
  price_cents integer not null check (price_cents >= 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_products_category_id on public.products (category_id);
create index if not exists idx_products_is_active on public.products (is_active);

create trigger set_products_updated_at
  before update on public.products
  for each row
  execute function public.set_updated_at();

create table if not exists public.product_images (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references public.products (id) on delete cascade,
  storage_path text not null,
  position integer not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists idx_product_images_product_id
  on public.product_images (product_id);

-- RLS
alter table public.categories enable row level security;
alter table public.products enable row level security;
alter table public.product_images enable row level security;

-- Categories are not sensitive; anyone (including anonymous storefront
-- visitors) can read them.
create policy "categories_select_all"
  on public.categories
  for select
  to anon, authenticated
  using (true);

-- Only active products are publicly visible. Inactive/draft products are
-- only visible to the service role (used by the future admin API).
create policy "products_select_active"
  on public.products
  for select
  to anon, authenticated
  using (is_active = true);

-- Images are only meaningful attached to a visible product.
create policy "product_images_select_for_active_products"
  on public.product_images
  for select
  to anon, authenticated
  using (
    exists (
      select 1 from public.products p
      where p.id = product_images.product_id
        and p.is_active = true
    )
  );

-- No insert/update/delete policies on any of these three tables yet.
-- Writes are performed via the service-role key from the backend only,
-- until Stage 3 RBAC defines which authenticated roles may manage the
-- catalog (see master instructions sections 23-24 — least privilege).
