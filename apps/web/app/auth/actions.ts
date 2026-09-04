"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export type AuthActionState = { error: string } | undefined;

export async function signUp(
  _prevState: AuthActionState,
  formData: FormData
): Promise<AuthActionState> {
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");
  const displayName = String(formData.get("displayName") ?? "");

  if (!email || !password) {
    return { error: "Email and password are required." };
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { display_name: displayName || null },
    },
  });

  if (error) {
    return { error: error.message };
  }

  redirect("/profile");
}

export async function signIn(
  _prevState: AuthActionState,
  formData: FormData
): Promise<AuthActionState> {
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");

  if (!email || !password) {
    return { error: "Email and password are required." };
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) {
    return { error: error.message };
  }

  redirect("/profile");
}

export async function signOut() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}

export async function requestPasswordReset(
  _prevState: AuthActionState,
  formData: FormData
): Promise<AuthActionState> {
  const email = String(formData.get("email") ?? "");
  if (!email) {
    return { error: "Email is required." };
  }

  const supabase = await createClient();
  const siteUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    // Confirmed server-side by app/auth/confirm/route.ts via verifyOtp,
    // then forwarded on to /reset-password. See docs/DECISIONS.md for why
    // this token_hash + verifyOtp pattern was used instead of parsing
    // tokens out of a URL fragment client-side.
    redirectTo: `${siteUrl}/auth/confirm?next=/reset-password`,
  });

  if (error) {
    return { error: error.message };
  }

  // Always the same message whether or not the email exists, so this
  // endpoint can't be used to enumerate registered accounts.
  return undefined;
}

export async function updatePassword(
  _prevState: AuthActionState,
  formData: FormData
): Promise<AuthActionState> {
  const password = String(formData.get("password") ?? "");
  if (!password || password.length < 8) {
    return { error: "Password must be at least 8 characters." };
  }

  const supabase = await createClient();

  // Requires an active session — only present if the visitor arrived via
  // a valid recovery link that app/auth/confirm/route.ts already verified
  // and exchanged for a session. If there's no session, this fails and
  // the person is sent back to request a new link.
  const { error } = await supabase.auth.updateUser({ password });

  if (error) {
    return { error: error.message };
  }

  redirect("/profile");
}
