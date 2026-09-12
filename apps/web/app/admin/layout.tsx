import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

/**
 * Gates the entire /admin route group. Uses getClaims() (signature-
 * validated) to establish identity, then looks up profiles.role — the
 * same pattern the profile page uses (Stage 3), now reused for
 * authorization rather than just display. Non-admins are redirected to
 * "/", not shown a 403 page, so as not to confirm/deny the existence of
 * admin routes to a logged-in-but-unauthorized user.
 */
export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();

  const { data: claimsData, error: claimsError } = await supabase.auth.getClaims();
  if (claimsError || !claimsData?.claims) {
    redirect("/login");
  }

  const userId = claimsData.claims.sub;

  const { data: profile } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", userId)
    .single();

  const allowedRoles = ["admin", "owner", "staff"];
  if (!profile || !allowedRoles.includes(profile.role)) {
    redirect("/");
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <nav className="border-b border-zinc-200 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center gap-6 text-sm">
          <span className="font-semibold text-zinc-900">TeleCommerce Admin</span>
          <Link href="/admin" className="text-zinc-600 hover:text-zinc-900">
            Overview
          </Link>
          <Link href="/admin/products" className="text-zinc-600 hover:text-zinc-900">
            Products
          </Link>
          <Link href="/admin/orders" className="text-zinc-600 hover:text-zinc-900">
            Orders
          </Link>
          <Link href="/" className="ml-auto text-zinc-400 hover:text-zinc-600">
            ⬅ Back to store
          </Link>
        </div>
      </nav>
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  );
}
