-- Migration: 0005_fix_public_execute_grant
-- 0004's revoke targeted anon/authenticated directly, but PostgreSQL grants
-- EXECUTE on new functions to PUBLIC by default, and anon/authenticated
-- inherit through PUBLIC. Revoking from the specific roles was a no-op
-- while PUBLIC still had it (verified via information_schema.role_routine_grants
-- and the security advisor still flagging the same issue after 0004).
-- Revoke from PUBLIC instead, which is the grant that actually needs
-- removing. Verified afterward: only service_role/postgres retain EXECUTE,
-- the security advisor finding cleared, and the auth.users signup trigger
-- still successfully creates a profiles row (triggers run as the function
-- owner, not the invoking role, so this revoke does not break signup).

revoke execute on function public.handle_new_user() from public;
