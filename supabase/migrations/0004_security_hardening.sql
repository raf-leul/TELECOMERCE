-- Migration: 0004_security_hardening
-- Fixes two findings from Supabase's security advisor (get_advisors), run
-- after 0001-0003 were applied:
--
-- 1. function_search_path_mutable: public.set_updated_at() didn't pin
--    search_path, which is a hijacking risk for SECURITY DEFINER-adjacent
--    trigger functions.
-- 2. anon/authenticated_security_definer_function_executable:
--    public.handle_new_user() is SECURITY DEFINER and was, by default,
--    directly callable via PostgREST's RPC endpoint
--    (/rest/v1/rpc/handle_new_user) by anon/authenticated clients. It is
--    only meant to run as an AFTER INSERT trigger on auth.users, never as a
--    directly-invoked RPC. Revoke EXECUTE from anon/authenticated so it can
--    only fire via the trigger.
--
-- Note: this migration's anon/authenticated revoke turned out to be
-- insufficient on its own — see 0005 for why, and 0006 for a follow-up
-- performance fix. Left as-applied (not squashed) so the migration history
-- honestly reflects what was actually run and verified.

alter function public.set_updated_at() set search_path = public;

revoke execute on function public.handle_new_user() from anon, authenticated;
