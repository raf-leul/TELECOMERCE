-- Migration: 0001_profiles
-- One row per Supabase auth user. Role is a simple enum for now (not a full
-- roles/permissions table) — see docs/DECISIONS.md for why.

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  role text not null default 'customer'
    check (role in ('customer', 'staff', 'admin', 'owner')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.profiles is
  'One row per auth.users row. role is a simple enum until a full RBAC model is needed (Stage 3).';

-- Keep updated_at current on every row update.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger set_profiles_updated_at
  before update on public.profiles
  for each row
  execute function public.set_updated_at();

-- Auto-create a profile row whenever a new auth user is created, so the app
-- never has to remember to do this itself.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, new.raw_user_meta_data ->> 'display_name');
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row
  execute function public.handle_new_user();

-- RLS
alter table public.profiles enable row level security;

-- A user may read their own profile row. No public/anon read of other
-- people's profiles. No client-side INSERT/UPDATE policy yet: profile
-- creation happens only via the trigger above, and role changes must go
-- through the service role until admin RBAC exists (Stage 3) — this
-- intentionally prevents a user from granting themselves admin/owner via a
-- direct table update.
create policy "profiles_select_own"
  on public.profiles
  for select
  to authenticated
  using (auth.uid() = id);
