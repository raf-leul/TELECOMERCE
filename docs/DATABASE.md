# DATABASE.md

## Project
Supabase project `telecommerce` (ref `hmsjerjguhxhwoubqdqm`, us-east-1).
URL: https://hmsjerjguhxhwoubqdqm.supabase.co

## Migration history (as of Stage 2)
Applied via Supabase MCP tools (`apply_migration`) and mirrored into
`supabase/migrations/` in this repo:

| Version | Name | Purpose |
|---|---|---|
| 20260902062000 | 0001_profiles | profiles table, auto-provisioning trigger on signup, RLS |
| 20260902062011 | 0002_catalog | categories, products, product_images, RLS |
| 20260902062017 | 0003_inventory | inventory table, RLS |
| (same session) | 0004_security_hardening | pin function search_path, attempt to restrict `handle_new_user` execution |
| (same session) | 0005_fix_public_execute_grant | actual fix for the above (PUBLIC grant, not per-role) |
| (same session) | 0006_optimize_rls_initplan | rewrite `auth.uid()` call in profiles policy for per-query (not per-row) evaluation |

## Schema

### `profiles`
One row per `auth.users` row (Stage 3 will start actually using Supabase
Auth; this table is ready ahead of that).

| column | type | notes |
|---|---|---|
| id | uuid, PK | references `auth.users(id)`, cascade delete |
| display_name | text, nullable | |
| role | text | `customer` \| `staff` \| `admin` \| `owner`, default `customer`, enforced by CHECK constraint |
| created_at | timestamptz | default `now()` |
| updated_at | timestamptz | auto-updated by trigger |

A trigger (`on_auth_user_created` → `handle_new_user()`) automatically
inserts a profile row whenever a new `auth.users` row is created, populating
`display_name` from `raw_user_meta_data->>'display_name'` if present.

**RLS:** enabled. Only policy: authenticated users may `SELECT` their own
row (`auth.uid() = id`). No public read of other users' profiles. No
client-side INSERT/UPDATE policy — row creation only happens via the
trigger, and role changes are intentionally not self-service (a user cannot
grant themselves `admin`/`owner` via a direct table update). This will be
revisited in Stage 3 when real RBAC/admin flows are built.

### `categories`
| column | type | notes |
|---|---|---|
| id | uuid, PK | default `gen_random_uuid()` |
| name | text | |
| slug | text, unique | |
| parent_category_id | uuid, nullable | self-FK, `ON DELETE SET NULL`, for hierarchy |
| created_at | timestamptz | |

**RLS:** enabled. `SELECT` open to `anon` + `authenticated` (categories
aren't sensitive). No write policies — writes are service-role only until
Stage 3/4 define admin RBAC.

### `products`
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| category_id | uuid, nullable | FK → categories, `ON DELETE SET NULL` |
| name | text | |
| slug | text, unique | |
| description | text, nullable | |
| price_cents | integer | CHECK `>= 0`. **Integer cents, never float.** Client never supplies this at checkout — see ARCHITECTURE.md. |
| is_active | boolean | default `true` |
| created_at / updated_at | timestamptz | updated_at auto-maintained by trigger |

**RLS:** enabled. `SELECT` open to `anon` + `authenticated` **only where
`is_active = true`** — draft/inactive products are invisible to the public
API and only reachable via the service role (verified: see "RLS
verification" below). No write policies yet.

### `product_images`
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| product_id | uuid | FK → products, `ON DELETE CASCADE` |
| storage_path | text | path into Supabase Storage (bucket not yet created — Stage 4/25) |
| position | integer | default 0, for ordering |
| created_at | timestamptz | |

**RLS:** enabled. `SELECT` open to `anon` + `authenticated`, but only for
images belonging to an active product (subquery against `products.is_active`).

### `inventory`
| column | type | notes |
|---|---|---|
| product_id | uuid, PK | FK → products, `ON DELETE CASCADE` |
| quantity_available | integer | CHECK `>= 0`, default 0 |
| updated_at | timestamptz | auto-maintained by trigger |

**RLS:** enabled. `SELECT` open to everyone (needed for storefront
"in stock" display). No write policies — stock is never client-writable.

**Deliberately not built yet:** `inventory_movements` (audit trail of
purchase/sale/reservation/adjustment). Deferred to Stage 6 when the order
engine actually needs to write to it, per master instructions section 10
("do not create tables just for appearance").

## RLS verification performed this session
Rather than just enabling RLS and assuming it works, the following was
actually tested against the live database by switching to the `anon`
Postgres role inside a transaction (rolled back, not persisted) — this is
the same role PostgREST uses for unauthenticated REST requests:

- ✅ `anon` can `SELECT` active products; an inactive ("draft") product
  inserted alongside it was correctly excluded from the result.
- ✅ `anon` can `SELECT` categories.
- ✅ `anon` can `SELECT` inventory rows.
- ✅ `anon` attempting `UPDATE` on `inventory.quantity_available` affected
  zero rows (silently denied by RLS — verified the value was unchanged
  afterward).
- ✅ `anon` attempting `INSERT` into `products` raised an explicit
  `42501: new row violates row-level security policy` error.
- ✅ `anon` `SELECT` on `profiles` returned 0 rows (no profiles exist for
  the anon role to see, and no policy grants anon read access at all).

All test/seed rows created for this verification were deleted afterward;
production tables are empty as of the end of Stage 2.

## Security advisor findings and fixes
`get_advisors(type=security)` was run after applying 0001–0003 and found:

1. `set_updated_at()` had a mutable `search_path` (hijack risk) — fixed in
   0004 by pinning `search_path = public`.
2. `handle_new_user()` (a `SECURITY DEFINER` function) was directly callable
   by `anon`/`authenticated` via PostgREST's RPC endpoint
   (`/rest/v1/rpc/handle_new_user`), even though it's only meant to run as
   an `auth.users` trigger. First attempted fix (0004, revoking from the
   named roles) turned out to be a no-op because PostgreSQL had granted
   EXECUTE to `PUBLIC` by default, which `anon`/`authenticated` inherit.
   Verified this directly via `information_schema.role_routine_grants`, then
   fixed correctly in 0005 by revoking from `PUBLIC`. Re-ran the advisor
   afterward — zero security findings.
3. After 0005, verified the auth signup trigger still works (triggers run
   as the function owner, not the invoking client role, so revoking public
   EXECUTE does not break `handle_new_user`'s use as a trigger) by inserting
   a test row into `auth.users` directly and confirming a matching
   `profiles` row was created, then deleting the test user.

`get_advisors(type=performance)` found `auth.uid()` being re-evaluated
per-row in the `profiles_select_own` policy — fixed in 0006 by wrapping it
in `(select auth.uid())`. Re-ran the advisor afterward; that finding
cleared. One remaining `INFO`-level "unused index" note on
`idx_products_is_active` is expected on a freshly created, currently empty
table and isn't actionable yet.
