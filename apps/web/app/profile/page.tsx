import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { signOut } from "@/app/auth/actions";

export default async function ProfilePage() {
  const supabase = await createClient();

  // getClaims validates the JWT signature — safe to use for gating access.
  // See lib/supabase/proxy.ts for why getSession() is not used for this.
  const { data: claimsData, error: claimsError } =
    await supabase.auth.getClaims();

  if (claimsError || !claimsData?.claims) {
    redirect("/login");
  }

  const userId = claimsData.claims.sub;

  // Relies on the profiles_select_own RLS policy from Stage 2
  // (supabase/migrations/0001_profiles.sql): a user may only select their
  // own row. No service-role client is used here on purpose.
  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("display_name, role, created_at")
    .eq("id", userId)
    .single();

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <h1 className="mb-6 text-2xl font-semibold text-zinc-900">
        Your profile
      </h1>

      {profileError && (
        <p className="mb-4 text-sm text-red-600">
          Could not load profile: {profileError.message}
        </p>
      )}

      {profile && (
        <dl className="mb-6 flex flex-col gap-2 text-sm text-zinc-700">
          <div>
            <dt className="font-medium">Display name</dt>
            <dd>{profile.display_name ?? "—"}</dd>
          </div>
          <div>
            <dt className="font-medium">Role</dt>
            <dd>{profile.role}</dd>
          </div>
          <div>
            <dt className="font-medium">Member since</dt>
            <dd>{new Date(profile.created_at).toLocaleDateString()}</dd>
          </div>
        </dl>
      )}

      <form action={signOut}>
        <button
          type="submit"
          className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-900"
        >
          Log out
        </button>
      </form>
    </div>
  );
}
