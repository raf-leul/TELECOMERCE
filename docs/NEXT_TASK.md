# NEXT_TASK.md

## Immediate next task (single executable unit)

STAGE 2 — DATABASE: initial schema for auth/catalog foundation.

Design and apply Supabase migrations for the minimum viable schema needed
before auth (Stage 3) and catalog (Stage 4) can be built:

1. `profiles` — one row per Supabase auth user (id references auth.users),
   display name, role reference.
2. `roles` and `permissions` (or a simpler role-enum on profiles if a full
   RBAC table is premature at this point — decide and document the choice
   in DECISIONS.md).
3. `categories` — id, name, slug, parent_category_id (nullable, for
   hierarchy), created_at.
4. `products` — id, category_id, name, slug, description, price (integer
   cents, never float), is_active, created_at, updated_at.
5. `product_images` — id, product_id, storage_path, position, created_at.
6. `inventory` — product_id (PK/unique), quantity_available, updated_at.
   (inventory_movements table can wait until Stage 6/12 when order flow
   needs to write to it — don't build unused tables yet per master
   instructions section 10.)

Requirements:
- Every table: primary key, created_at, appropriate FKs/constraints/indexes,
  correct nullability (per master instructions section 11).
- Enable RLS on every table in `public` schema.
- Write policies for the actual access pattern needed right now: anonymous +
  authenticated users can SELECT active products/categories; only an
  authenticated admin role can INSERT/UPDATE/DELETE. No admin role exists
  yet (Stage 3), so for now restrict writes to the service role only and
  document that write policies will be revisited once RBAC exists.
- Apply migrations via Supabase MCP tools against project `hmsjerjguhxhwoubqdqm`.
- Verify with `list_tables` (verbose) after applying.
- Write the migration SQL files into `supabase/migrations/` in the repo too,
  so schema history is in git, not just in Supabase.
- Update `docs/DATABASE.md` (new file) describing the schema and relationships.

## Definition of done for this task
- Tables exist and verified via `list_tables`
- RLS enabled on all new tables, verified by attempting an anonymous
  read/write and confirming the expected allow/deny behavior
- Migration SQL committed under `supabase/migrations/`
- `docs/DATABASE.md` created
- Commit message: `feat: Stage 2 database schema (categories, products, inventory)`
- Pushed to origin/main
- PROJECT_STATE.md and this file updated afterward

## After this task
Stage 3 — Authentication + RBAC: Supabase Auth wiring in apps/web and
apps/api, register/login/logout, protected routes, and a real role model
(revisit the roles/permissions decision made in this stage).
