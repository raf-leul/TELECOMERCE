# NEXT_TASK.md

## Immediate next task (single executable unit)

Scaffold the Stage 1 foundation:

1. `apps/web`: minimal Next.js 14 (App Router) + TypeScript + Tailwind CSS project
   with a placeholder home page ("TeleCommerce — coming soon") and a working
   `npm run build`.
2. `apps/api`: minimal FastAPI project with `app/main.py` exposing `GET /health`
   returning `{"status": "ok"}`, plus `requirements/base.txt` and a working
   `uvicorn app.main:app` boot.
3. Root `.env.example` documenting all env vars referenced in this file, with
   real (safe, publishable) Supabase URL/key placeholders and comments — no
   secrets.
4. Root `package.json` (npm workspaces) wiring `apps/web` as a workspace.
5. `.gitignore` covering node_modules, .next, __pycache__, .venv, .env*.local.
6. Basic `.github/workflows/ci.yml`: install + lint + build for apps/web only
   (backend CI added once apps/api has real dependencies to check).

## Definition of done for this task
- `npm run build` succeeds in apps/web (verified via bash tool)
- FastAPI app boots and `/health` returns 200 (verified via bash tool + curl)
- No secrets committed (verified via `git diff` review before commit)
- Commit message: `feat: Stage 1 foundation scaffold (web + api skeletons)`
- Pushed to origin/main
- PROJECT_STATE.md and this file updated afterward

## After this task
Stage 2 — Database: design initial schema (users/profiles, categories, products,
product_images, inventory) as Supabase migrations, apply via Supabase MCP tools,
verify with list_tables, enable RLS, commit the migration files.
