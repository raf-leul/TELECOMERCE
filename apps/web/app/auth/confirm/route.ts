import { type EmailOtpType } from "@supabase/supabase-js";
import { type NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

/**
 * Handles the link Supabase emails for both signup confirmation and
 * password recovery: `{SITE_URL}/auth/confirm?token_hash=...&type=...&next=...`.
 * Verifies the token server-side (so the token never has to be parsed out
 * of a URL fragment in client JS) and, on success, the user has an active
 * session and is redirected to `next`. On failure, redirected to
 * `/forgot-password` with an error so they can request a fresh link —
 * recovery links are single-use and expire.
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const token_hash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = searchParams.get("next") ?? "/";

  if (token_hash && type) {
    const supabase = await createClient();
    const { error } = await supabase.auth.verifyOtp({ type, token_hash });
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  return NextResponse.redirect(
    `${origin}/forgot-password?error=Link+is+invalid+or+has+expired`
  );
}
