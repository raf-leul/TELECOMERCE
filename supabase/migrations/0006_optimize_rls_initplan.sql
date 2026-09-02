-- Migration: 0006_optimize_rls_initplan
-- Fixes a performance advisor finding: auth.uid() in the profiles_select_own
-- policy was being re-evaluated per row instead of once per query. Wrapping
-- it in a scalar subquery lets Postgres treat it as an InitPlan (evaluated
-- once), per Supabase's documented RLS performance guidance. Verified via
-- pg_policies that the rewritten qual is
-- "(( SELECT auth.uid() AS uid) = id)" and that the performance advisor
-- finding cleared.

drop policy "profiles_select_own" on public.profiles;

create policy "profiles_select_own"
  on public.profiles
  for select
  to authenticated
  using ((select auth.uid()) = id);
